"""Collect matching OSRA/Qt source archives as data, never execute their recipes.

This is a source-inventory aid, not a license-compliance certification. The
manifest records HTTPS origins and locally computed hashes; a hash recorded
here is not an upstream signature verification. Run on Windows or Linux.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request


def sha256(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def source_requests(osra_manifest, qt_version):
    if not re.fullmatch(r"\d+\.\d+\.\d+", qt_version):
        raise ValueError("Expected an exact Qt x.y.z version")
    requests = []
    seen = set()
    for package in osra_manifest["msys2_packages"]:
        base, version = package["base"][0], package["version"][0]
        if not all(re.fullmatch(r"[A-Za-z0-9_.+\-]+", item) for item in (base, version)):
            raise ValueError("Unsafe package identifier")
        name = f"{base}-{version}.src.tar.zst"
        if name in seen:
            continue
        seen.add(name)
        requests.append({"component": base, "version": version, "archive": name,
                         "url": f"https://repo.msys2.org/mingw/sources/{name}",
                         "declared_license": package["licenses"]})
    qt_series = qt_version.rsplit(".", 1)[0]
    for module in ("qtbase", "qtsvg", "qtimageformats"):
        name = f"{module}-everywhere-src-{qt_version}.tar.xz"
        requests.append({"component": module, "version": qt_version, "archive": name,
                         "url": f"https://download.qt.io/official_releases/qt/{qt_series}/{qt_version}/submodules/{name}"})
    name = f"pyside-setup-everywhere-src-{qt_version}.tar.xz"
    requests.append({"component": "pyside-setup", "version": qt_version, "archive": name,
                     "url": f"https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-{qt_version}-src/{name}"})
    return requests


def fetch_one(request, directory):
    destination = directory / request["archive"]
    receipt = destination.with_name(destination.name + ".json")
    if destination.exists():
        if not receipt.is_file():
            raise ValueError(f"Existing archive has no receipt: {destination}")
        previous = json.loads(receipt.read_text(encoding="utf-8"))
        if previous["url"] != request["url"] or sha256(destination) != previous["sha256"]:
            raise ValueError(f"Cached archive differs from its receipt: {destination}")
        print(f"Verified cached source: {destination.name}", flush=True)
        return previous
    # Unique partial files, and atomic publication only after download completes.
    with tempfile.NamedTemporaryFile(dir=directory, prefix="download-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            with urllib.request.urlopen(request["url"], timeout=60) as response:
                if not response.url.startswith("https://"):
                    raise ValueError("Refusing an insecure source redirect")
                shutil.copyfileobj(response, stream, 1024 * 1024)
                origin = response.url
        except BaseException:
            stream.close()
            temporary.unlink()
            raise
    record = {**request, "resolved_url": origin, "sha256": sha256(temporary),
              "size_bytes": temporary.stat().st_size, "verification": "HTTPS download; local SHA-256"}
    temporary.replace(destination)
    receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Collected source: {destination.name} ({record['size_bytes'] // 1048576} MiB)", flush=True)
    return record


def collect(osra, output, qt_version):
    manifest = json.loads((osra / "BUILD-INFO.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    copied = []
    local = output / "osra-local"
    local.mkdir(exist_ok=True)
    for name, expected in manifest["source_sha256"].items():
        if Path(name).name != name or "\\" in name:
            raise ValueError("Unsafe source archive name")
        source = osra / "sources" / name
        if sha256(source) != expected:
            raise ValueError(f"OSRA source differs from build manifest: {name}")
        target = local / name
        if target.exists() and sha256(target) != expected:
            raise ValueError(f"Refusing to overwrite modified source: {target}")
        shutil.copy2(source, target)
        copied.append({"archive": "osra-local/" + name, "sha256": expected,
                       "verification": "matches OSRA BUILD-INFO.json"})
    for source in (osra / "sources").iterdir():
        if source.is_file() and source.name not in manifest["source_sha256"]:
            target = local / source.name
            if target.exists() and sha256(target) != sha256(source):
                raise ValueError(f"Refusing to overwrite modified build recipe: {target}")
            shutil.copy2(source, target)
            copied.append({"archive": "osra-local/" + source.name, "sha256": sha256(source),
                           "verification": "copied from tested OSRA runtime"})
    requests = source_requests(manifest, qt_version)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda request: fetch_one(request, output), requests))
    result = {"schema": 1, "scope": "OSRA runtime and reduced Qt Widgets payload",
              "license_review_complete": False,
              "note": "Collection does not validate archive contents or certify complete corresponding source.",
              "archives": sorted(records + copied, key=lambda item: item["archive"])}
    (output / "SOURCES.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osra-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qt-version", default="6.11.0")
    args = parser.parse_args()
    collect(args.osra_dir.resolve(), args.output.resolve(), args.qt_version)


if __name__ == "__main__":
    main()
