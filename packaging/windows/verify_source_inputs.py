"""Check nested source/patch hashes without running downloaded build recipes.

This checks recorded integrity, not upstream signatures or license compliance.
VCS inputs and inputs marked SKIP are reported separately, never as hash-verified.
Requires zstandard only for MSYS2 .zst containers.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
from urllib.parse import urlsplit


ALGORITHMS = {"md5sums": "md5", "sha1sums": "sha1", "sha224sums": "sha224",
              "sha256sums": "sha256", "sha384sums": "sha384", "sha512sums": "sha512",
              "b2sums": "blake2b"}


def fields_from_srcinfo(text):
    fields = {}
    for key, value in re.findall(r"^\s*([\w]+) = (.*)$", text, re.MULTILINE):
        fields.setdefault(key, []).append(value)
    return fields


def source_filename(source):
    alias, separator, location = source.partition("::")
    name = alias if separator else PurePosixPath(urlsplit(source).path).name
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError(f"Unsafe source filename: {source}")
    return name


def verify_payload(fields, digests, files):
    results = []
    for key, sources in fields.items():
        if key != "source" and not key.startswith("source_"):
            continue
        suffix = key[len("source"):]
        checks = {algorithm: fields[label + suffix] for label, algorithm in ALGORITHMS.items()
                  if label + suffix in fields}
        if any(len(values) != len(sources) for values in checks.values()):
            raise ValueError(f"Checksum count differs from {key} count")
        for index, source in enumerate(sources):
            name = source_filename(source)
            location = source.split("::", 1)[-1]
            record = {"source": source, "file": name, "group": key}
            if re.match(r"(?:git|svn|hg|bzr)\+", location):
                prefix = name + "/"
                if not any(member.startswith(prefix) for member in files):
                    raise ValueError(f"Missing VCS source payload: {name}")
                record.update(status="vcs-payload-present-not-verified",
                              declared_checksums={a: values[index] for a, values in checks.items()})
            else:
                if name not in digests:
                    raise ValueError(f"Missing source input: {name}")
                verified = []
                for algorithm, values in checks.items():
                    expected = values[index]
                    if expected == "SKIP":
                        continue
                    if not re.fullmatch(r"[0-9a-fA-F]+", expected):
                        raise ValueError(f"Invalid checksum for {name}")
                    if digests[name][algorithm] != expected.lower():
                        raise ValueError(f"{algorithm} mismatch: {name}")
                    verified.append(algorithm)
                record.update(status="hash-verified" if verified else "present-not-hash-verified",
                              verified_algorithms=verified, sha256=digests[name]["sha256"])
            results.append(record)
    if not results:
        raise ValueError("No source inputs declared")
    return results


@contextmanager
def open_container(path):
    if path.name.endswith(".zst"):
        import zstandard
        with path.open("rb") as raw, zstandard.ZstdDecompressor().stream_reader(raw) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as archive:
                yield archive
    else:
        with tarfile.open(path, "r|*") as archive:
            yield archive


def verify_package(path, component, version):
    if not re.fullmatch(r"[A-Za-z0-9_.+\-]+", component):
        raise ValueError("Unsafe package component")
    digests, files, metadata = {}, set(), None
    with open_container(path) as archive:
        for member in archive:
            relative = PurePosixPath(member.name)
            if (relative.is_absolute() or ".." in relative.parts or "\\" in member.name
                    or not relative.parts or relative.parts[0] != component):
                raise ValueError(f"Unsafe archive path: {member.name}")
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"Unexpected non-file source entry: {member.name}")
            name = str(PurePosixPath(*relative.parts[1:]))
            if name in files:
                raise ValueError(f"Duplicate source entry: {name}")
            files.add(name)
            if len(relative.parts) != 2:
                continue  # VCS objects are inventory-only here.
            stream = archive.extractfile(member)
            if name == ".SRCINFO":
                if member.size > 1024 * 1024:
                    raise ValueError("Oversized source metadata")
                metadata = fields_from_srcinfo(stream.read().decode("utf-8"))
                continue
            hashes = {a: hashlib.new(a, usedforsecurity=False) for a in ALGORITHMS.values()}
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                for checksum in hashes.values():
                    checksum.update(chunk)
            digests[name] = {a: checksum.hexdigest() for a, checksum in hashes.items()}
    if metadata is None or "PKGBUILD" not in files:
        raise ValueError("Missing source metadata/build recipe")
    actual = f"{metadata.get('pkgver', [''])[0]}-{metadata.get('pkgrel', [''])[0]}"
    if metadata.get("pkgbase") != [component] or actual != version:
        raise ValueError("Source package identity mismatch")
    inputs = verify_payload(metadata, digests, files)
    return {"component": component, "version": version, "archive": path.name,
            "inputs": inputs,
            "all_inputs_hash_verified": all(item["status"] == "hash-verified" for item in inputs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for item in json.loads(args.manifest.read_text(encoding="utf-8"))["archives"]:
        if not item.get("component", "").startswith("mingw-w64-"):
            continue
        name = item["archive"]
        if Path(name).name != name or "\\" in name:
            raise ValueError("Unsafe source container name")
        path = args.sources / name
        checksum = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                checksum.update(chunk)
        if checksum.hexdigest() != item["sha256"]:
            raise ValueError(f"Container hash mismatch: {name}")
        record = verify_package(path, item["component"], item["version"])
        records.append(record)
        print(f"Checked inputs for {item['component']}", flush=True)
    if not records:
        raise ValueError("No MSYS2 source containers to verify")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"license_review_complete": False,
        "limitations": ["No recipes executed and no upstream signatures verified.",
                        "VCS object contents/revisions and SKIP inputs are not hash-verified."],
        "components": records}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
