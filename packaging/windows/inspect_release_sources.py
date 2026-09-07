"""Inventory downloaded source archives and recover original Qt notices.

Never execute a PKGBUILD or extract arbitrary archive paths. This checks
source-package identity and archive readability, not legal sufficiency.
Requires zstandard for MSYS2 source containers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

from fetch_release_sources import sha256


def inspect_package(path, component, version):
    import zstandard
    with path.open("rb") as raw, zstandard.ZstdDecompressor().stream_reader(raw) as reader:
        with tarfile.open(fileobj=reader, mode="r|") as archive:
            files = []
            srcinfo = None
            for member in archive:
                if member.isfile():
                    files.append(member.name)
                    if member.name == f"{component}/.SRCINFO":
                        srcinfo = archive.extractfile(member).read().decode("utf-8")
    if srcinfo is None or f"{component}/PKGBUILD" not in files:
        raise ValueError(f"Missing package metadata/build recipe: {path}")
    fields = {}
    for key, value in re.findall(r"^\s*([\w]+) = (.*)$", srcinfo, flags=re.MULTILINE):
        fields.setdefault(key, []).append(value)
    actual = f"{fields['pkgver'][0]}-{fields['pkgrel'][0]}"
    if fields["pkgbase"] != [component] or actual != version:
        raise ValueError(f"Source identity mismatch in {path}: {actual}")
    payload = [name for name in files if not name.endswith(("/PKGBUILD", "/.SRCINFO"))]
    if not payload:
        raise ValueError(f"No source payload in {path}")
    return {"component": component, "version": version, "archive": path.name,
            "declared_licenses": fields.get("license", []), "source_inputs": fields.get("source", []),
            "files": files, "status": "identity-and-container-checked"}


def is_notice(path):
    # Match original license/copyright notices, not arbitrary source files
    # containing the word license somewhere in their name.
    lowered = path.name.lower()
    return (lowered.startswith(("license", "licence", "copying", "copyright", "notice"))
            or lowered == "qt_attribution.json" or "LICENSES" in path.parts)


def inspect_qt(path, component, output):
    notices = []
    with tarfile.open(path, "r:xz") as archive:
        members = {member.name: member for member in archive.getmembers()}
        referenced = set()
        for member in members.values():
            relative = PurePosixPath(member.name)
            if {"tests", "examples"}.intersection(relative.parts):
                continue  # Attribution-scanner tests deliberately include invalid JSON.
            if member.isfile() and relative.name == "qt_attribution.json":
                try:
                    # Some upstream copyright strings contain literal newlines.
                    # Preserve the original file; allow those controls only
                    # when reading metadata to locate referenced license files.
                    attribution = json.loads(archive.extractfile(member).read(), strict=False)
                except ValueError as error:
                    raise ValueError(f"Invalid production attribution: {member.name}") from error
                for item in attribution if isinstance(attribution, list) else [attribution]:
                    names = item.get("LicenseFile", [])
                    for name in [names] if isinstance(names, str) else names:
                        # Normalize references inside the archive, without any
                        # filesystem extraction or traversal outside its root.
                        import posixpath
                        referenced.add(posixpath.normpath(str(PurePosixPath(member.name).parent / name)))
        for member in members.values():
            relative = PurePosixPath(member.name)
            if not member.isfile() or not (is_notice(relative) or member.name in referenced):
                continue
            if relative.is_absolute() or ".." in relative.parts or "\\" in member.name:
                raise ValueError(f"Unsafe archive path: {member.name}")
            if member.size > 5 * 1024 * 1024:
                raise ValueError(f"Unexpectedly large license file: {member.name}")
            destination = output / component / Path(*relative.parts[1:])
            content = archive.extractfile(member).read()
            if destination.exists() and destination.read_bytes() != content:
                raise ValueError(f"Refusing to overwrite changed notice: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            notices.append(str(destination.relative_to(output)).replace("\\", "/"))
    if not any(name.endswith("/LGPL-3.0-only.txt") for name in notices):
        raise ValueError(f"No LGPLv3 license text found in {path}")
    return {"component": component, "archive": path.name, "notices": notices,
            "status": "archive-readable-and-original-notices-collected"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.sources / "SOURCES.json").read_text(encoding="utf-8"))
    results = []
    for source in manifest["archives"]:
        path = args.sources / source["archive"]
        if sha256(path) != source["sha256"]:
            raise ValueError(f"Source hash mismatch: {path}")
        if "component" not in source:
            continue
        if source["component"].startswith("mingw-w64-"):
            result = inspect_package(path, source["component"], source["version"])
        else:
            result = inspect_qt(path, source["component"], args.output / "qt-notices")
        results.append(result)
        print(f"Checked {source['component']} {source['version']}", flush=True)
    (args.output / "SOURCE-INSPECTION.json").write_text(json.dumps({
        "license_review_complete": False, "components": results,
        "limitations": ["No downloaded recipes were executed.",
                        "Identity checks do not validate every nested input hash or VCS checkout.",
                        "This is not a complete SBOM or legal compliance certification."],
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
