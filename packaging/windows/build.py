"""Build a Windows x64 portable folder, validate it, then make a ZIP.

Run with native Windows Python 3.11+, not the WSL/Linux interpreter. No system
installation, PATH editing, downloads of OSRA, signing or release publishing.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def validate_embedded_icon(executable: Path) -> list[int]:
    """Check the actual PE resources, not just that an .ico file was copied."""
    import pefile

    with pefile.PE(str(executable)) as pe:
        groups = [entry for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries if entry.id == 14]
        if not groups:
            raise ValueError(f"No embedded application icon in {executable}")
        data = groups[0].directory.entries[0].directory.entries[0].data.struct
        payload = pe.get_data(data.OffsetToData, data.Size)
        reserved, kind, count = struct.unpack_from("<HHH", payload)
        if (reserved, kind) != (0, 1):
            raise ValueError(f"Invalid icon group in {executable}")
        sizes = []
        for index in range(count):
            width, height = struct.unpack_from("<BB", payload, 6 + 14 * index)
            if width != height:
                raise ValueError(f"Non-square icon in {executable}")
            sizes.append(width or 256)
        if set(sizes) != {16, 20, 24, 32, 40, 48, 64, 96, 128, 256}:
            raise ValueError(f"Missing embedded icon sizes in {executable}: {sizes}")
        return sorted(sizes)


def validate_osra(directory: Path) -> Path:
    """Reject a Linux binary or incomplete runtime before building the GUI."""
    directory = directory.resolve()
    executable = directory / "bin" / "osra.exe"
    if not executable.is_file():
        raise ValueError(f"Expected {executable}; provide the whole Windows OSRA runtime")
    with executable.open("rb") as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise ValueError("OSRA must be a Windows PE executable, not a Linux binary")
        stream.seek(struct.unpack_from("<I", header, 60)[0])
        signature = stream.read(6)
        if signature[:4] != b"PE\0\0" or signature[4:] not in (b"\x64\x86", b"\x4c\x01"):
            raise ValueError("OSRA must be an x86 or x64 Windows executable")
    for name in ("chain.txt", "spelling.txt", "superatom.txt"):
        if not (directory / "share" / name).is_file():
            raise ValueError(f"Missing OSRA dictionary: share/{name}")
    # These are supplied/reviewed by the distributor, never fabricated here.
    if not any(path.is_file() for path in (directory / "licenses").rglob("*")):
        raise ValueError("Include OSRA/dependency license files in an OSRA licenses/ folder")
    if not (directory / "SOURCE-NOTICE.txt").is_file():
        raise ValueError("Include SOURCE-NOTICE.txt documenting OSRA's origin and corresponding sources")
    return directory


def collect_licenses(destination: Path) -> dict[str, str]:
    packages = ("molrecognizer", "rdkit", "numpy", "Pillow", "PySide6",
                "PySide6_Essentials", "PySide6_Addons", "shiboken6", "PyInstaller")
    versions = {}
    for name in packages:
        distribution = metadata.distribution(name)
        versions[name] = distribution.version
        folder = destination / name
        folder.mkdir(parents=True)
        # Keep the original text. Serializing email.Message metadata can fail
        # on wheels whose multi-line License header includes a whole license.
        folder.joinpath("METADATA.txt").write_text(distribution.read_text("METADATA") or "",
                                                encoding="utf-8")
        for item in distribution.files or ():
            if any("license" in part.lower() or part.lower().startswith("copying")
                   for part in item.parts):
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    # Wheel-relative paths can contain '..'; flatten safely.
                    target = folder / "__".join(part for part in item.parts if part not in ("..", "."))
                    shutil.copy2(source, target)
    shutil.copy2(ROOT / "LICENSE", destination / "MolRecognizer-LICENSE.txt")
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", destination / "Python-LICENSE.txt")
    return versions


def build(args) -> Path:
    if sys.platform != "win32" or struct.calcsize("P") != 8 or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("Build with native Windows x64 Python, not WSL/Linux Python")
    from release_checks import require_source_revision, validate_qt_payload
    osra = validate_osra(args.osra_dir) if args.osra_dir else None
    source_revision = require_source_revision(getattr(args, "source_revision", None))
    compiler = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not compiler.is_file():
        raise RuntimeError("The .NET Framework 4.x C# compiler was not found")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    version = metadata.version("molrecognizer")
    materials = getattr(args, "release_materials_dir", None)
    if re.fullmatch(r"\d+\.\d+\.\d+", version) and osra and (materials is None or source_revision is None):
        raise ValueError("A stable OSRA build requires --release-materials-dir and --source-revision")
    material_index = None
    if materials is not None:
        from release_materials import verify_materials
        expected_versions = {name: metadata.version(name) for name in
                             json.loads((materials / "MATERIALS.json").read_text(encoding="utf-8"))["packages"]}
        material_index = verify_materials(materials, expected_versions)
    label = f"MolRecognizer-{version}-windows-x64" + ("" if osra else "-no-osra")
    archive = output / f"{label}.zip"
    if archive.exists():
        raise FileExistsError(f"Refusing to overwrite {archive}; move it or use --output")
    # A new directory for every build: never --clean/rmtree a user's output.
    args.work_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="windows-", dir=args.work_dir.resolve()))
    build_env = {**os.environ, "PYINSTALLER_CONFIG_DIR": str(staging / "pyinstaller-cache")}
    log_path = staging / "pyinstaller.log"
    print(f"Building Windows executables; detailed log: {log_path}", flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", "--noconfirm",
            "--distpath", str(staging / "dist"), "--workpath", str(staging / "work"),
            str(ROOT / "packaging/windows/MolRecognizer.spec"),
        ], cwd=ROOT, check=False, env=build_env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:])
        raise RuntimeError(f"PyInstaller failed; see {log_path}\n{tail}")
    bundle = staging / "dist" / "MolRecognizer"
    validate_qt_payload(bundle)
    helper_dir = bundle / "tools"
    helper_dir.mkdir()
    subprocess.run([
        str(compiler), "/nologo", "/target:exe", "/platform:x64", "/optimize+",
        f"/win32icon:{ROOT / 'src/molrecognizer/gui/icons/molrecognizer.ico'}",
        "/reference:System.Windows.Forms.dll", "/reference:System.Drawing.dll",
        f"/out:{helper_dir / 'MolRecognizerCapture.exe'}",
        str(ROOT / "src/molrecognizer/gui/capture_overlay.cs"),
    ], cwd=ROOT, check=True)
    # A stable, explicit shortcut icon avoids Explorer's cached EXE artwork.
    shutil.copy2(ROOT / "src/molrecognizer/gui/icons/molrecognizer.ico", bundle / "MolRecognizer.ico")
    if osra:
        shutil.copytree(osra, helper_dir / "osra")
    embedded_icons = {
        str(path.relative_to(bundle)): validate_embedded_icon(path)
        for path in (bundle / "MolRecognizer.exe", bundle / "MolRecognizerWorker.exe",
                     helper_dir / "MolRecognizerCapture.exe")
    }
    versions = collect_licenses(bundle / "licenses")
    if materials is not None:
        shutil.copytree(materials, bundle / "licenses/release-materials")
        verify_materials(bundle / "licenses/release-materials", versions)
        shutil.copy2(materials / "SOURCE-README.md", bundle / "SOURCE-ACCESS.md")
        shutil.copy2(ROOT / "packaging/windows/RELEASE-NOTES-0.3.0.md", bundle / "RELEASE-NOTES.md")
    qt_notices = getattr(args, "qt_notices_dir", None)
    if qt_notices is not None:
        for component in ("qtbase", "qtsvg", "qtimageformats", "pyside-setup"):
            if not (qt_notices / component / "LICENSES/LGPL-3.0-only.txt").is_file():
                raise ValueError(f"Missing original Qt LGPL notice for {component}")
        shutil.copytree(qt_notices, bundle / "licenses/qt-source-notices")
    shutil.copy2(ROOT / "packaging/windows/PORTABLE-README.txt", bundle / "README.txt")
    shutil.copy2(ROOT / "packaging/windows/THIRD-PARTY-NOTICES.md", bundle / "THIRD-PARTY-NOTICES.md")
    manifest = {"version": version, "osra_included": bool(osra),
                "python": sys.version, "packages": versions, "signed": False,
                "source_revision": source_revision,
                "release_status": "candidate-not-cleared-for-publication",
                "qt_source_notices_included": qt_notices is not None or materials is not None,
                "release_materials_included": materials is not None,
                "release_materials_sha256": (hashlib.sha256((materials / "MATERIALS.json").read_bytes()).hexdigest()
                                              if materials else None),
                "release_material_file_count": len(material_index["files"]) if material_index else 0,
                "source_archive": f"MolRecognizer-{version}-sources.zip" if materials else None,
                "embedded_icon_sizes": embedded_icons}
    (bundle / "BUILD-INFO.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not osra:
        (bundle / "NO-OSRA.txt").write_text(
            "This preview does not include OSRA. Image recognition requires a separate "
            "Windows OSRA runtime. Load SMILES, editing and 3D/XYZ tools are available.\n",
            encoding="utf-8",
        )
    # Test a relocated copy with a space in its path, without the builder's
    # Python/Conda/OSRA on PATH. Test results describe the bundled EXE, not source.
    relocated = staging / "relocated test" / "MolRecognizer"
    shutil.copytree(bundle, relocated)
    report = relocated / "SMOKE-TEST.json"
    env = os.environ.copy()
    for name in ("OSRA_EXECUTABLE", "PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
        env.pop(name, None)
    system = Path(os.environ.get("WINDIR", r"C:\Windows"))
    env["PATH"] = os.pathsep.join(map(str, (system / "System32", system)))
    command = [str(relocated / "MolRecognizer.exe"), "--smoke-test", str(report)]
    if osra:
        command.append("--require-osra")
    print(f"Checking relocated Windows executables; report: {report}", flush=True)
    result = subprocess.run(command, cwd=staging, env=env, timeout=180, check=False)
    if result.returncode or not report.is_file() or not json.loads(report.read_text(encoding="utf-8"))["ok"]:
        detail = report.read_text(encoding="utf-8") if report.is_file() else "No report; check missing DLLs/Windows event log"
        raise RuntimeError(f"Portable EXE smoke test failed ({result.returncode}): {detail}\nBuild kept at {staging}")
    shutil.copy2(report, bundle / "SMOKE-TEST.json")
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=bundle.parent, base_dir=bundle.name)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    # LF also works with GNU sha256sum; Windows CRLF can become part of the
    # filename when the checksum is checked on Linux/macOS.
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n",
                                                encoding="ascii", newline="\n")
    print(f"Portable ZIP: {archive}\nBuild and diagnostics retained at: {staging}")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--osra-dir", type=Path, help="Reviewed Windows runtime with bin/, share/, licenses/ and SOURCE-NOTICE.txt")
    choice.add_argument("--without-osra", action="store_true", help="Explicitly build an editor-only preview, NOT a complete recognizer")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--work-dir", type=Path, default=ROOT / "build",
                        help="Parent for build intermediates (use local NTFS when sources are on a WSL share)")
    parser.add_argument("--source-revision", help="Full commit hash for a build from that verified source revision")
    parser.add_argument("--qt-notices-dir", type=Path,
                        help="Original notices extracted from matching Qt sources by inspect_release_sources.py")
    parser.add_argument("--release-materials-dir", type=Path,
                        help="Verified output from release_materials.py; required for stable OSRA builds")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
