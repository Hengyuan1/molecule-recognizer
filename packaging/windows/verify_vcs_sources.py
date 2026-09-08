"""Verify pinned Git trees in source containers without using archived Git config.

Only object files enter a fresh temporary repository. Archived hooks, config,
refs, alternates and worktrees are never copied or executed; no network fetch
is attempted. Requires Git and zstandard for MSYS2 source containers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from fetch_release_sources import sha256
from verify_source_inputs import open_container


OBJECT = re.compile(r"(?:[0-9a-f]{2}/[0-9a-f]{38}|pack/pack-[0-9a-f]{40}\.(?:pack|idx|rev))")


def verify_git(path, component, source):
    match = re.search(r"#commit=([0-9a-f]{40})$", source["source"])
    if not match or not source["source"].split("::", 1)[-1].startswith("git+"):
        raise ValueError("Expected a full pinned Git commit")
    commit = match[1]
    prefix = f"{component}/{source['file']}/objects/"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    with tempfile.TemporaryDirectory(prefix="molrecognizer-git-source-") as temporary:
        directory = Path(temporary)
        template = directory / "empty-template"
        template.mkdir()
        repository = directory / "objects.git"
        subprocess.run(["git", "init", "--bare", f"--template={template}", str(repository)],
                       env=env, check=True, capture_output=True)
        copied = set()
        with open_container(path) as archive:
            for member in archive:
                if not member.name.startswith(prefix) or member.isdir():
                    continue
                name = member.name[len(prefix):]
                if not OBJECT.fullmatch(name):
                    # In particular, never honor an objects/info/alternates file.
                    raise ValueError(f"Unexpected Git object entry: {name}")
                if not member.isfile() or name in copied:
                    raise ValueError(f"Non-file or duplicate Git object: {name}")
                copied.add(name)
                target = repository / "objects" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    stream = archive.extractfile(member)
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        output.write(chunk)
        if not copied:
            raise ValueError("No Git objects in source container")
        base = ["git", "--no-replace-objects", f"--git-dir={repository}"]
        subprocess.run(base + ["cat-file", "-e", commit + "^{commit}"], env=env,
                       check=True, capture_output=True)
        # git archive reads the actual commit tree/blobs. Never check out a
        # worktree or invoke submodule commands on this untrusted archive.
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(base + ["archive", "--format=tar", commit],
                                       env=env, stdout=subprocess.PIPE, stderr=errors)
            digest = hashlib.sha256()
            for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
                digest.update(chunk)
            if process.wait():
                errors.seek(0)
                raise ValueError(f"Cannot read pinned source tree: {errors.read(4096)!r}")
        actual = digest.hexdigest()
        expected = source.get("declared_checksums", {}).get("sha256")
        if expected not in (None, "SKIP") and actual != expected:
            raise ValueError(f"Git archive SHA-256 mismatch: {path.name}")
        return {"archive": path.name, "component": component, "commit": commit,
                "tree_archive_sha256": actual, "matches_declared_sha256": actual == expected,
                "object_files": len(copied), "status": "pinned-tree-readable"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    containers = {item["archive"]: item["sha256"]
                  for item in json.loads(args.manifest.read_text())["archives"]}
    records = []
    for item in json.loads(args.inputs.read_text())["components"]:
        vcs = [source for source in item["inputs"]
               if source["status"] == "vcs-payload-present-not-verified"]
        if not vcs:
            continue
        name = item["archive"]
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+", name):
            raise ValueError("Unsafe source container name")
        path = args.sources / name
        if sha256(path) != containers[name]:
            raise ValueError(f"Source container hash mismatch: {name}")
        for source in vcs:
            records.append(verify_git(path, item["component"], source))
            print(f"Verified pinned Git source: {name}", flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"schema": 1, "sources": records,
        "limitations": ["No upstream signature certification.",
                        "Only source objects read; no archived recipes/config/hooks executed."]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
