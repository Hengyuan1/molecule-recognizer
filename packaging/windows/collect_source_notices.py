"""Copy original notices from inventoried source archives, never execute code.

This is a notice-preservation aid, not a license selector. The resulting index
identifies exact inputs and copied files for the distributor's review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

from fetch_release_sources import sha256


HEADER_COMPONENTS = frozenset({"inchi", "rdkit", "numpy", "openblas", "cairo", "rdkit-cairo",
                               "rdkit-pixman", "rdkit-dirent", "pubchem-align3d", "chemdraw"})


def leading_notice(payload):
    """Preserve complete leading C/C++ notice comments, not arbitrary code."""
    match = re.match(rb"\s*(?:(?:/\*.*?\*/|//[^\n]*(?:\n|$))\s*)+", payload, re.S)
    if match is None or b"copyright" not in match[0].lower():
        return None
    return match[0]


def is_notice(name):
    name = name.lower()
    return (name.startswith(("license", "licence", "copying", "copyright", "notice"))
            or "_license" in name or name.endswith(".license")
            or name in ("ofl.txt", "ftl.txt", "authors", "legal"))


def extract_notices(path, component, output):
    if component in (".", "..") or not re.fullmatch(r"[A-Za-z0-9_.+-]+", component):
        raise ValueError("Unsafe component name")
    records = []
    seen = set()

    def selected(name):
        relative = PurePosixPath(name)
        if (relative.is_absolute() or ".." in relative.parts or "\\" in name
                or any(":" in part for part in relative.parts)):
            raise ValueError(f"Unsafe notice path: {name}")
        header = (component in HEADER_COMPONENTS
                  and relative.suffix.lower() in (".c", ".cpp", ".h", ".hpp", ".cc", ".cxx"))
        if len(relative.parts) < 2 or not (is_notice(relative.name) or header):
            return None
        inner = PurePosixPath(*relative.parts[1:])
        # This source tree holds thousands of unrelated ports; their presence
        # in a build-tool archive does not make them runtime dependencies.
        if component == "rdkit-vcpkg-recipes" and len(inner.parts) > 1:
            return None
        if component == "gcc-rtools-runtime-source" and len(inner.parts) > 1:
            if inner.parts[0] not in ("libgcc", "libgfortran", "libquadmath"):
                return None
        return inner

    def save(inner, payload):
        if not is_notice(inner.name):
            payload = leading_notice(payload)
            if payload is None:
                return
            inner = inner.with_name(inner.name + ".notice.txt")
        key = str(inner).casefold()
        if key in seen:
            raise ValueError(f"Duplicate notice path: {inner}")
        seen.add(key)
        target = output / component / Path(*inner.parts)
        if any(parent.is_symlink() for parent in (target, *target.parents)):
            raise ValueError(f"Refusing a symlink in notice destination: {target}")
        if target.exists() and target.read_bytes() != payload:
            raise ValueError(f"Refusing to overwrite modified notice: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        records.append({"file": str(PurePosixPath(component) / inner),
                        "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)})

    limit = 5 * 1024 * 1024
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                inner = selected(member.filename)
                if inner is None or member.is_dir():
                    continue
                if member.file_size > limit or (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError(f"Oversized or symlink notice: {member.filename}")
                save(inner, archive.read(member))
    else:
        with tarfile.open(path, "r|*") as archive:
            for member in archive:
                inner = selected(member.name)
                if inner is None or member.isdir():
                    continue
                if not member.isfile() or member.size > limit:
                    raise ValueError(f"Oversized or non-file notice: {member.name}")
                save(inner, archive.extractfile(member).read())
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for manifest in args.manifest:
        for source in json.loads(manifest.read_text(encoding="utf-8"))["archives"]:
            name = PurePosixPath(source["archive"])
            if (name.is_absolute() or ".." in name.parts or "\\" in source["archive"]
                    or any(":" in part for part in name.parts)):
                raise ValueError("Unsafe source path")
            path = args.sources / Path(*name.parts)
            if sha256(path) != source["sha256"]:
                raise ValueError(f"Source checksum mismatch: {name}")
            component = source["component"]
            notices = extract_notices(path, component, args.output)
            records.append({"component": component, "archive": str(name),
                            "source_sha256": source["sha256"], "notices": notices})
            print(f"Preserved {len(notices)} notices: {component}", flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"schema": 1, "components": records,
        "note": "Original source notices retained; optional source-only components may also have notices. See the distribution component inventory for license selections."}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
