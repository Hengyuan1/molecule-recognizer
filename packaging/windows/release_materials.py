"""Assemble verified local notices/source maps; never download or publish.

The resulting inventory is an integrity check, not a legal certification.
Only explicitly inventoried files enter the build; local caches are not copied
wholesale. Run after collecting the exact source inputs and original notices.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile

from collect_source_notices import leading_notice
from fetch_release_sources import sha256
from inspect_release_sources import inspect_qt
from package_sources import inventory


ROOT = Path(__file__).resolve().parents[2]
INDEX = "MATERIALS.json"
QT_COMPONENTS = ("qtbase", "qtsvg", "qtimageformats", "pyside-setup")
CIMG_DOCUMENTS = ("CIMG-PERMISSION.md", "CIMG-PERMISSION.json")


def cimg_permission(root):
    """Check the recorded permission materials, not legal sufficiency."""
    record = json.loads(safe_path(root, "CIMG-PERMISSION.json").read_text(encoding="utf-8"))
    permission = record["permission"]
    if (record.get("schema") != 1 or permission.get("user") != "dtschump"
            or permission.get("html_url") !=
            "https://github.com/GreycLab/CImg/issues/492#issuecomment-5618853659"):
        raise ValueError("Unexpected CImg permission provenance")
    required = (*CIMG_DOCUMENTS, "license-texts/CECILL-C.txt", "license-texts/CECILL-2.1.txt")
    for name in required:
        if not safe_path(root, name).is_file():
            raise ValueError(f"Missing CImg permission material: {name}")
    return {"record": "CIMG-PERMISSION.json", "record_sha256": sha256(root / "CIMG-PERMISSION.json"),
            "permission_url": permission["html_url"], "selected_license": "CECILL-2.1",
            "scope": record["scope"]}


def safe_path(root, name):
    relative = PurePosixPath(name)
    if (not name or name == "." or str(relative) != name or relative.is_absolute()
            or ".." in relative.parts or "\\" in name
            or any(":" in part for part in relative.parts)):
        raise ValueError(f"Unsafe material path: {name}")
    result = root / Path(*relative.parts)
    if any(path.is_symlink() for path in (result, *result.parents)):
        raise ValueError(f"Symlink material path: {name}")
    return result


def tree_files(root):
    records = {}
    folded = set()
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        safe_path(root, name)
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"Non-file material: {name}")
        if name == INDEX:
            continue
        if name.casefold() in folded:
            raise ValueError(f"Case-insensitive material collision: {name}")
        folded.add(name.casefold())
        records[name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    return records


def verify_materials(root, versions=None):
    index = json.loads(safe_path(root, INDEX).read_text(encoding="utf-8"))
    if index.get("schema") != 1 or not index.get("files"):
        raise ValueError("Missing release material inventory")
    for name in index["files"]:
        safe_path(root, name)
    if tree_files(root) != index["files"]:
        raise ValueError("Release materials changed, missing, or contain unlisted files")
    if "cimg_permission" in index and cimg_permission(root) != index["cimg_permission"]:
        raise ValueError("CImg permission record differs from material inventory")
    if versions is not None:
        for name, expected in index["packages"].items():
            if versions.get(name) != expected:
                raise ValueError(f"Release notices are for {name} {expected}, not {versions.get(name)}")
    return index


def copy_wheel_notices(directory, report, source_records, output):
    sources = {item["archive"]: item for item in source_records}
    report_data = json.loads(report.read_text(encoding="utf-8"))
    names = set()
    count = 0
    for component in report_data["components"]:
        source = sources.get(component["archive"])
        if (source is None or source.get("component") != component["component"]
                or source["sha256"] != component["source_sha256"]):
            raise ValueError(f"Notice/source provenance mismatch: {component['component']}")
        for notice in component["notices"]:
            name = notice["file"]
            path = safe_path(directory, name)
            if PurePosixPath(name).parts[0] != component["component"]:
                raise ValueError(f"Notice outside its component: {name}")
            if name.casefold() in names:
                raise ValueError(f"Duplicate notice: {name}")
            names.add(name.casefold())
            if sha256(path) != notice["sha256"] or path.stat().st_size != notice["bytes"]:
                raise ValueError(f"Changed original notice: {name}")
            target = safe_path(output, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream, path.open("rb") as original:
                shutil.copyfileobj(original, stream)
            count += 1
    if not count:
        raise ValueError("No wheel source notices")
    return count


def prepare(args):
    sources = inventory(args.sources, args.manifest)
    packages = json.loads((ROOT / "packaging/windows/RELEASE-PACKAGES.json").read_text(encoding="utf-8"))
    for component, package in (("numpy", "numpy"), ("rdkit", "rdkit"),
                               *((name, "PySide6") for name in QT_COMPONENTS)):
        matches = [item for item in sources if item.get("component") == component]
        if len(matches) != 1 or matches[0].get("version") != packages[package]:
            raise ValueError(f"Source version does not match release packages: {component}")
    safe_path(args.output, INDEX)
    args.output.mkdir(parents=True, exist_ok=False)
    count = copy_wheel_notices(args.wheel_notices, args.wheel_report, sources,
                              args.output / "wheel-source-notices")
    qt_sources = {item.get("component"): item for item in sources
                  if item.get("component") in QT_COMPONENTS}
    for component in QT_COMPONENTS:
        if component not in qt_sources:
            raise ValueError(f"Missing source input: {component}")
        inspect_qt(args.sources / qt_sources[component]["archive"], component,
                   args.output / "qt-source-notices")
    osra_source = next(item for item in sources
                       if item["archive"] == "osra-local/osra-2.2.4.tar.gz")
    original = args.output / "osra-header-notices"
    original.mkdir()
    with tarfile.open(args.sources / osra_source["archive"]) as archive:
        for name in ("CImg.h", "greycstoration.h"):
            payload = archive.extractfile("osra-2.2.4/src/" + name).read()
            notice = leading_notice(payload)
            if notice is None:
                raise ValueError(f"Missing original OSRA header notice: {name}")
            (original / (name + ".notice.txt")).write_bytes(notice)
    for name in ("DEPENDENCY-LICENSES.md", "SOURCE-README.md", "MICROSOFT-RUNTIME-NOTICE.txt",
                 *CIMG_DOCUMENTS):
        shutil.copy2(ROOT / "packaging/windows" / name, args.output / name)
    shutil.copytree(ROOT / "packaging/windows/license-texts", args.output / "license-texts")
    source_map = {"schema": 1, "archives": sources,
                  "scope": "Sources and build recipes for the recorded Windows package",
                  "license_review_complete": False}
    (args.output / "SOURCE-INPUTS.json").write_text(json.dumps(source_map, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(args.wheel_report, args.output / "WHEEL-NOTICES.json")
    index = {"schema": 1, "packages": packages,
             "publication_cleared": False,
             "note": "Verified notice/source inventory with scoped upstream CImg permission; not publication approval.",
             "cimg_permission": cimg_permission(args.output),
             "files": tree_files(args.output)}
    (args.output / INDEX).write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    verify_materials(args.output, packages)
    print(f"Prepared {len(index['files'])} release files ({count} wheel notices): {args.output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--wheel-notices", type=Path, required=True)
    parser.add_argument("--wheel-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory; never overwritten")
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
