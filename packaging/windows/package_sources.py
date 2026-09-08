"""Package hash-checked source inputs and a committed app tree for a release.

No binaries are built or published. The archive contains original compressed
inputs, so users can access the accompanying sources independently of the app.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import zipfile

from fetch_release_sources import public_origin, sha256
from release_checks import require_source_revision


def inventory(sources, manifests):
    records = {}
    names = {}
    for manifest in manifests:
        for item in json.loads(manifest.read_text(encoding="utf-8"))["archives"]:
            name = item["archive"]
            relative = PurePosixPath(name)
            if (not name or str(relative) != name or name == "."
                    or relative.is_absolute() or ".." in relative.parts or "\\" in name
                    or any(":" in part for part in relative.parts)):
                raise ValueError(f"Unsafe source archive path: {name}")
            if name.casefold() in names and names[name.casefold()] != name:
                raise ValueError(f"Case-insensitive source path collision: {name}")
            names[name.casefold()] = name
            path = sources / Path(*relative.parts)
            if any(parent.is_symlink() for parent in (path, *path.parents)):
                raise ValueError(f"Symlink source input: {name}")
            if sha256(path) != item["sha256"]:
                raise ValueError(f"Source checksum mismatch: {name}")
            previous = records.get(name)
            if previous and previous["sha256"] != item["sha256"]:
                raise ValueError(f"Conflicting source input: {name}")
            record = {**item, "size_bytes": path.stat().st_size}
            if "resolved_url" in record:
                record["resolved_url"] = public_origin(record["resolved_url"])
            records[name] = record
    if not records:
        raise ValueError("No source inputs to package")
    return sorted(records.values(), key=lambda item: item["archive"])


def package(sources, manifests, output, revision, version, root):
    require_source_revision(revision)
    if revision is None or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("A committed revision and stable x.y.z version are required")
    records = inventory(sources, manifests)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"MolRecognizer-{version}-sources.zip"
    if archive.exists():
        raise FileExistsError(f"Refusing to overwrite {archive}")
    manifest = {"schema": 1, "version": version, "app_revision": revision,
                "license_review_complete": False,
                "publication_status": "source-materials-only-not-release-clearance",
                "scope": "Original dependency source archives, recipes/patches and committed application source",
                "archives": records}
    prefix = f"MolRecognizer-{version}-sources/"
    # git archive reads a commit, not the dirty working directory or ignored
    # files. In particular, local screenshots, credentials and build trees
    # cannot enter the application-source archive through this operation.
    with tempfile.TemporaryDirectory(prefix="molrecognizer-source-package-") as temporary:
        app_source = Path(temporary) / "molrecognizer-source.tar.gz"
        subprocess.run(["git", "archive", "--format=tar.gz", "--prefix=molrecognizer/",
                        f"--output={app_source}", revision], cwd=root, check=True)
        readme = subprocess.check_output(
            ["git", "show", f"{revision}:packaging/windows/SOURCE-README.md"], cwd=root)
        manifest["application_source"] = {"archive": app_source.name,
                                           "sha256": sha256(app_source)}
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as package_zip:
            package_zip.writestr(prefix + "SOURCES.json", json.dumps(manifest, indent=2) + "\n")
            package_zip.writestr(prefix + "README.md", readme)
            package_zip.write(app_source, prefix + app_source.name)
            for item in records:
                path = sources / item["archive"]
                package_zip.write(path, prefix + "archives/" + item["archive"])
                # Detect accidental edits during the copy as well.
                if sha256(path) != item["sha256"]:
                    raise ValueError(f"Source changed during packaging: {path}")
                print(f"Packaged source: {item['archive']}", flush=True)
    with zipfile.ZipFile(archive) as package_zip:
        if package_zip.testzip() is not None:
            raise ValueError("Source ZIP CRC verification failed")
    digest = sha256(archive)
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii", newline="\n")
    (output / "SOURCE-MATERIALS.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Source package: {archive}\nSHA-256: {digest}", flush=True)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    package(args.sources, args.manifest, args.output, args.revision, args.version,
            Path(__file__).resolve().parents[2])


if __name__ == "__main__":
    main()
