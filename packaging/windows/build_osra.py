"""Build OSRA with an isolated, already-extracted MSYS2 UCRT64 environment."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


SOURCES = {
    "osra-2.2.4.tar.gz": "419d87fbf540338d881aaf6df6227785c7af8cbab73e487877a2fb182216bf46",
    "gocr-0.50pre-patched-2.tgz": "3ff73f03845878a4f08585b25d1e2b690e3f2d03bb4df1bbebb2ae2ead25287a",
    "openbabel-3-0-0-patched-3.tgz": "58a6adef6508e6361e1ebea1e756f89c36697d3f6f3cc360bf4fc597c86a654c",
    "ocrad-0.23.tar.lz": "f5bc9479c01fe8c64aa836c8636dff65e9b459c2edbd4fc0656f47f435d9a06f",
    "tclap-1.2.5.tar.gz": "bb649f76dae35e8d0dcba4b52acfd4e062d787e6a81b43f7a4b01275153165a6",
    "eigen-3.4.0.tar.gz": "8586084f71f9bde545ee7fa6d00288b264a2b7ac3607b974e54d13e7162c1c72",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msys2-root", type=Path, required=True)
    parser.add_argument("--downloads", type=Path)
    parser.add_argument("--step", choices=("update", "deps", "build"), required=True)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Run using native Windows Python")
    root = args.msys2_root.resolve()
    bash = root / "usr/bin/bash.exe"
    if not bash.is_file():
        parser.error("Extract the verified MSYS2 base archive first")
    work = root / "opt/osra-build"
    work.mkdir(parents=True, exist_ok=True)
    if args.step == "update":
        command = "pacman -Syu --noconfirm"
    elif args.step == "deps":
        packages = ["make", "patch", "lzip", "autoconf", "automake", "libtool"]
        packages += ["mingw-w64-ucrt-x86_64-" + name for name in (
            "gcc", "cmake", "ninja", "pkgconf", "graphicsmagick", "potrace",
            "eigen3", "zlib", "libxml2", "poppler")]
        command = "pacman -S --needed --noconfirm " + " ".join(packages)
    else:
        if args.downloads is None:
            parser.error("--downloads is required for the build step")
        downloads = work / "downloads"
        downloads.mkdir(exist_ok=True)
        for name, checksum in SOURCES.items():
            archive = args.downloads / name
            if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
                raise RuntimeError(f"Source checksum mismatch: {archive}")
            shutil.copy2(archive, downloads / name)
        for name in ("osra-portable.patch", "osra_portable.h", "openbabel-compat.patch", "osra-cimg.patch"):
            shutil.copy2(Path(__file__).with_name(name), work / name)
        shutil.copy2(Path(__file__).with_name("osra_build.sh"), work / "build.sh")
        command = f"bash /opt/osra-build/build.sh {max(1, args.jobs)}"
    environment = os.environ.copy()
    environment.update(MSYSTEM="UCRT64", CHERE_INVOKING="1", MSYS2_PATH_TYPE="strict")
    log = root.parent / f"osra-{args.step}.log"
    print(f"OSRA {args.step}: {command}\nLog: {log}", flush=True)
    with log.open("a", encoding="utf-8") as output:
        result = subprocess.run([str(bash), "-lc", command], cwd=root,
                                env=environment, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-65:]), flush=True)
        return result.returncode
    print(f"OSRA {args.step} completed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
