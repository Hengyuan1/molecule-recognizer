"""Download explicitly inventoried source archives, without executing their code.

Receipts record HTTPS origins and local hashes. Optional expected hashes come
from upstream build recipes, not from a claim of legal compliance. Existing
downloads are checked, not silently replaced. No archives are extracted.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

from fetch_release_sources import fetch_one, sha256


def validate_request(request):
    name = request["archive"]
    if (not re.fullmatch(r"[A-Za-z0-9_.+-]+", name)
            or not name.endswith((".tar.gz", ".tar.xz", ".tar.bz2", ".zip"))):
        raise ValueError(f"Unsafe source archive name: {name}")
    if not request["url"].startswith("https://"):
        raise ValueError("Source URLs must use HTTPS")
    for algorithm, expected in request.get("expected_hashes", {}).items():
        if algorithm not in ("md5", "sha256", "sha512"):
            raise ValueError(f"Unsupported expected hash: {algorithm}")
        length = hashlib.new(algorithm, usedforsecurity=False).digest_size * 2
        if not re.fullmatch(r"[0-9a-f]{%d}" % length, expected):
            raise ValueError(f"Invalid {algorithm} hash")


def check_archive(path, request):
    for algorithm, expected in request.get("expected_hashes", {}).items():
        digest = hashlib.new(algorithm, usedforsecurity=False)
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError(f"Upstream {algorithm} mismatch: {path.name}")
    count = 0
    def check_path(name):
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError(f"Unsafe archive path: {name}")

    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                check_path(member.filename)
                count += 1
            if archive.testzip() is not None:
                raise ValueError(f"Invalid ZIP CRC: {path.name}")
        if not count:
            raise ValueError(f"Empty source archive: {path.name}")
        return count
    # Inspect paths only; upstream source trees can legitimately contain
    # symbolic links, but nothing here follows or extracts those links.
    with tarfile.open(path, "r|*") as archive:
        for member in archive:
            check_path(member.name)
            count += 1
    if not count:
        raise ValueError(f"Empty source archive: {path.name}")
    return count


def collect(requests, output):
    names = [request["archive"] for request in requests]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate source archive requests")
    for request in requests:
        validate_request(request)
    output.mkdir(parents=True, exist_ok=True)

    def download(request):
        record = fetch_one(request, output)
        path = output / request["archive"]
        count = check_archive(path, request)
        if sha256(path) != record["sha256"]:
            raise ValueError(f"Source changed during inspection: {path.name}")
        return {**record, "archive_entries": count,
                "expected_hashes_verified": sorted(request.get("expected_hashes", {}))}

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(download, requests))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    requests = json.loads(args.requests.read_text(encoding="utf-8"))["archives"]
    records = collect(requests, args.output)
    result = {"schema": 1, "license_review_complete": False,
              "scope": "Additional wheel dependency sources and build recipes",
              "limitations": ["No downloaded code executed; no signature certification.",
                              "A source inventory is not a completed license review."],
              "archives": records}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
