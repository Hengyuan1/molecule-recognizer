"""Collect a native UCRT64 OSRA build into a new, relocatable runtime folder.

Requires pefile (included with the Windows PyInstaller build dependencies).
This collects available notices and provenance, not a redistribution clearance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

from build_osra import SOURCES


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def imported_libraries(path):
    import pefile

    with pefile.PE(str(path), fast_load=True) as pe:
        if pe.FILE_HEADER.Machine != 0x8664:
            raise RuntimeError(f"Not a native x64 binary: {path}")
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
        ])
        return {
            entry.dll.decode("ascii").lower()
            for table in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT")
            for entry in getattr(pe, table, [])
        }


def collect_dependencies(seeds, search, destination, system):
    available = {path.name.lower(): path for directory in search
                 for path in directory.glob("*.dll")}
    pending = list(seeds)
    visited = set()
    copied = []
    while pending:
        source = pending.pop()
        if source in visited:
            continue
        visited.add(source)
        for name in sorted(imported_libraries(source)):
            if name.startswith(("msys-", "cygwin")):
                raise RuntimeError(f"Unix emulation dependency is not portable Windows: {name}")
            if name in available:
                dependency = available[name]
                target = destination / dependency.name
                if not target.exists():
                    shutil.copy2(dependency, target)
                    copied.append(dependency)
                pending.append(dependency)
            elif name.startswith(("api-ms-win-", "ext-ms-win-")) or (system / name).is_file():
                continue
            else:
                raise RuntimeError(f"Unresolved dependency {name} required by {source}")
    return copied


def package_provenance(root, binaries):
    """Record the installed package version/recipe base for each shipped DLL."""
    names = {str(path.relative_to(root)).replace("\\", "/") for path in binaries}
    packages = []
    for directory in (root / "var/lib/pacman/local").iterdir():
        if not directory.is_dir():
            continue
        files = directory / "files"
        if not files.is_file():
            continue
        matches = sorted(names.intersection(files.read_text(encoding="utf-8").splitlines()))
        if not matches:
            continue
        fields = {}
        for section in (directory / "desc").read_text(encoding="utf-8").split("\n\n"):
            lines = section.splitlines()
            if lines and lines[0].startswith("%"):
                fields[lines[0].strip("%").lower()] = lines[1:]
        packages.append({"name": fields.get("name"), "version": fields.get("version"),
                         "base": fields.get("base"), "licenses": fields.get("license"),
                         "upstream": fields.get("url"), "files": matches})
        names.difference_update(matches)
    if names:
        raise RuntimeError(f"No MSYS2 package provenance found for: {sorted(names)}")
    return packages


def stage(root, output):
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}; choose a new directory")
    prefix = root / "opt/osra-build/prefix"
    source = root / "opt/osra-build/src"
    ucrt = root / "ucrt64"
    executable = prefix / "bin/osra.exe"
    if not executable.is_file():
        raise FileNotFoundError(f"Build OSRA first: {executable}")
    binary = output / "bin"
    binary.mkdir(parents=True)
    shutil.copy2(executable, binary / "osra.exe")
    (output / "share").mkdir()
    for name in ("chain.txt", "spelling.txt", "superatom.txt"):
        dictionary = source / "osra-2.2.4/dict" / name
        shutil.copy2(dictionary, output / "share" / name)
        # OSRA's command-line fallback also searches beside the executable.
        shutil.copy2(dictionary, binary / name)
    shutil.copytree(prefix / "share/openbabel", output / "share/openbabel")
    magick_roots = list((ucrt / "lib").glob("GraphicsMagick-*/modules-Q*/coders"))
    if len(magick_roots) != 1:
        raise RuntimeError(f"Expected one GraphicsMagick coder directory: {magick_roots}")
    module_destination = output / "lib/GraphicsMagick/modules"
    module_destination.mkdir(parents=True)
    # MolRecognizer supplies PNGs. Include common standalone raster inputs and
    # Magick's internal pixel formats, not optional HEIF/JXL/video delegates
    # whose separately installed dependencies are not part of this runtime.
    codecs = ("png", "jpeg", "bmp", "gif", "tiff", "pnm", "gray", "rgb", "miff", "xc", "null")
    modules = [magick_roots[0] / f"{name}.dll" for name in codecs]
    if any(not path.is_file() for path in modules):
        raise RuntimeError("A required GraphicsMagick raster codec is missing")
    for module in modules:
        shutil.copy2(module, module_destination / module.name)
        # GraphicsMagick's libltdl loader searches for .la, not .dll directly.
        # Dependencies are already in bin/; remove build-time linker paths so
        # libltdl loads the DLL beside this descriptor after relocation.
        descriptor = module.with_suffix(".la").read_text(encoding="utf-8")
        for field in ("dependency_libs", "libdir"):
            descriptor = re.sub(rf"^{field}=.*$", f"{field}=''", descriptor, flags=re.MULTILINE)
        (module_destination / module.with_suffix(".la").name).write_text(descriptor, encoding="utf-8")
    shutil.copytree(magick_roots[0].parents[1] / "config", output / "lib/GraphicsMagick/config")
    magick_share = ucrt / "share" / magick_roots[0].parents[1].name / "config"
    for config in magick_share.glob("*.mgk"):
        shutil.copy2(config, output / "lib/GraphicsMagick/config" / config.name)
    shutil.copytree(ucrt / "etc/fonts", output / "etc/fonts")
    if (ucrt / "share/poppler").is_dir():
        shutil.copytree(ucrt / "share/poppler", output / "share/poppler")
    dependencies = collect_dependencies(
        [executable, *modules], [prefix / "bin", ucrt / "bin"], binary,
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32",
    )
    licenses = output / "licenses"
    shutil.copytree(ucrt / "share/licenses", licenses / "msys2-ucrt64")
    if (root / "usr/share/licenses/common").is_dir():
        shutil.copytree(root / "usr/share/licenses/common", licenses / "common")
    for folder in ("osra-2.2.4", "gocr-0.50pre-patched-2", "ocrad-0.23",
                   "openbabel-3-0-0-patched-3", "tclap-1.2.5", "eigen-3.4.0"):
        (licenses / folder).mkdir()
        for item in (source / folder).iterdir():
            if item.is_file() and item.name.upper().startswith(("COPYING", "LICENSE", "AUTHORS")):
                shutil.copy2(item, licenses / folder / item.name)
    sources = output / "sources"
    sources.mkdir()
    for name, checksum in SOURCES.items():
        archive = root / "opt/osra-build/downloads" / name
        if sha256(archive) != checksum:
            raise RuntimeError(f"Source checksum mismatch: {archive}")
        shutil.copy2(archive, sources / name)
    for name in ("build_osra.py", "osra_build.sh", "osra-portable.patch", "osra_portable.h",
                 "openbabel-compat.patch", "osra-cimg.patch", "stage_osra.py", "check_osra.py", "OSRA-BUILD.md"):
        shutil.copy2(Path(__file__).with_name(name), sources / name)
    manifest = {
        "osra": "2.2.4", "architecture": "windows-x64-ucrt", "signed": False,
        "graphicsmagick_codecs": codecs,
        "source_sha256": SOURCES,
        "msys2_packages": package_provenance(root, [*modules, *dependencies]),
        "runtime_sha256": {str(path.relative_to(output)).replace("\\", "/"): sha256(path)
                           for path in sorted(output.rglob("*"))
                           if path.is_file() and path.suffix.lower() in (".dll", ".exe", ".txt", ".mgk", ".la")},
    }
    (output / "BUILD-INFO.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "SOURCE-NOTICE.txt").write_text(
        "OSRA 2.2.4, local native Windows x64 build for MolRecognizer.\n"
        "Not the paid upstream Windows distribution; not endorsed by OSRA.\n"
        "Official sources: https://sourceforge.net/projects/osra/files/\n"
        "The sources/ folder contains OSRA, patched GOCR/Open Babel, OCRAD,\n"
        "TCLAP, Eigen, the local patches and build instructions.\n"
        "Additional DLLs come from signed MSYS2 UCRT64 packages; exact package\n"
        "versions and upstream URLs are in BUILD-INFO.json. Build recipes:\n"
        "https://github.com/msys2/MINGW-packages\n"
        "Package/source archive service: https://repo.msys2.org/\n"
        "Available original license notices are in licenses/. OSRA is GPL-2.0-or-later.\n"
        "This is a private testing bundle, not a cleared public distribution.\n"
        "Before redistribution, review ALL dependencies' licenses and provide\n"
        "their exact corresponding sources/build recipes as required; the\n"
        "links and automatically collected notices alone do not establish compliance.\n",
        encoding="utf-8",
    )
    size = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    print(f"OSRA runtime: {output}\n{len(dependencies)} dependency DLLs, "
          f"{len(modules)} image codecs; {size / 1024**2:.1f} MiB including sources", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msys2-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Run using native Windows Python")
    stage(args.msys2_root.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
