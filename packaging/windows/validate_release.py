"""Validate the exact local Windows/source ZIP pair without publishing it.

Native Windows only for the executable/DLL/Defender checks. Archive integrity
helpers also run under Linux tests. Desktop capture is never performed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import zipfile

from fetch_release_sources import sha256
from release_checks import validate_qt_payload
from release_materials import verify_materials


def stream_sha256(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def verified_members(archive, prefix):
    names = set()
    files = {}
    for item in archive.infolist():
        path = PurePosixPath(item.filename)
        if (item.orig_filename != item.filename
                or not item.filename.startswith(prefix) or path.is_absolute()
                or ".." in path.parts or "\\" in item.filename
                or any(":" in part or part.endswith((".", " ")) for part in path.parts)
                or str(path) != item.filename.rstrip("/")
                or (item.external_attr >> 16) & 0o170000 == 0o120000):
            raise ValueError(f"Unsafe release ZIP member: {item.filename}")
        key = item.filename.rstrip("/").casefold()
        if key in names:
            raise ValueError(f"Duplicate release ZIP member: {item.filename}")
        names.add(key)
        if not item.is_dir():
            files[item.filename] = item
    if not files:
        raise ValueError("Empty release archive")
    return files


def verify_checksum(path):
    expected = path.with_suffix(".zip.sha256").read_text(encoding="ascii").strip()
    actual = sha256(path)
    if expected != f"{actual}  {path.name}":
        raise ValueError(f"ZIP checksum/filename mismatch: {path.name}")
    return actual


def verify_source_zip(path, version, revision):
    prefix = f"MolRecognizer-{version}-sources/"
    with zipfile.ZipFile(path) as archive:
        members = verified_members(archive, prefix)
        manifest = json.loads(archive.read(prefix + "SOURCES.json"))
        if manifest["version"] != version or manifest["app_revision"] != revision:
            raise ValueError("Binary/source version or revision mismatch")
        expected = {prefix + "SOURCES.json", prefix + "README.md"}
        inputs = [(manifest["application_source"]["archive"], manifest["application_source"]["sha256"])]
        inputs += [("archives/" + item["archive"], item["sha256"]) for item in manifest["archives"]]
        for name, checksum in inputs:
            member = prefix + name
            if member in expected:
                raise ValueError(f"Duplicate source inventory member: {member}")
            expected.add(member)
            with archive.open(members[member]) as stream:
                if stream_sha256(stream) != checksum:
                    raise ValueError(f"Source ZIP member checksum mismatch: {name}")
        if set(members) != expected:
            raise ValueError("Source ZIP contains missing or unlisted files")
        return {"version": version, "app_revision": revision,
                "archives_checked": len(inputs), "files_checked": len(members)}


def extract_checked(path, destination):
    if destination.exists():
        raise FileExistsError(f"Use a new extraction directory: {destination}")
    with zipfile.ZipFile(path) as archive:
        members = verified_members(archive, "MolRecognizer/")
        destination.mkdir(parents=True)
        for name, member in members.items():
            target = destination / Path(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            with archive.open(member) as source:
                if stream_sha256(source) != sha256(target):
                    raise ValueError(f"Extracted file differs from ZIP: {name}")
    return destination / "MolRecognizer", len(members)


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=kwargs.pop("timeout", 180), **kwargs)
    return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def validate(args):
    if sys.platform != "win32":
        raise RuntimeError("Run the executable validation with native Windows Python")
    from audit_binary_dependencies import audit
    args.output.mkdir(parents=True, exist_ok=False)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="release validation ", dir=args.work_dir))
    record = {"schema": 1, "publication_cleared": False, "ok": False,
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "binary_zip": args.binary.name, "binary_sha256": verify_checksum(args.binary),
              "source_zip": args.sources.name, "source_sha256": verify_checksum(args.sources)}

    def save():
        (args.output / "VALIDATION.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    try:
        print("Checking every extracted binary ZIP file", flush=True)
        bundle, count = extract_checked(args.binary, work / "extracted")
        info = json.loads((bundle / "BUILD-INFO.json").read_text(encoding="utf-8"))
        if not (info["osra_included"] and info["release_materials_included"] and info["qt_source_notices_included"]):
            raise ValueError("Expected the complete OSRA/materials bundle")
        record.update(version=info["version"], source_revision=info["source_revision"],
                      zip_files_checked=count, extracted_bundle=str(bundle))
        print("Verifying matching source ZIP and inner source hashes", flush=True)
        record["sources"] = verify_source_zip(args.sources, info["version"], info["source_revision"])
        materials = bundle / "licenses/release-materials"
        material_index = verify_materials(materials, info["packages"])
        permission = material_index.get("cimg_permission")
        if not permission or permission != info.get("cimg_permission"):
            raise ValueError("CImg permission must be included and match BUILD-INFO")
        record["cimg_permission"] = permission
        if sha256(materials / "MATERIALS.json") != info["release_materials_sha256"]:
            raise ValueError("Notice inventory differs from BUILD-INFO")
        validate_qt_payload(bundle)
        system = Path(os.environ.get("WINDIR", r"C:\Windows"))
        imports = audit(bundle, system / "System32")
        (args.output / "PE-IMPORTS.json").write_text(json.dumps(imports, indent=2) + "\n", encoding="utf-8")
        record["pe_imports"] = {"ok": imports["ok"], "binary_count": imports["binary_count"]}
        if not imports["ok"]:
            raise ValueError("Unresolved PE imports in extracted ZIP")
        env = dict(os.environ)
        for name in list(env):
            if name.startswith(("OSRA_", "BABEL_", "MAGICK_", "FONTCONFIG_")) or name in (
                    "PYTHONHOME", "PYTHONPATH", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
                env.pop(name, None)
        env["PATH"] = os.pathsep.join(map(str, (system / "System32", system)))
        report = args.output.resolve() / "EXTRACTED-SMOKE-TEST.json"
        print("Running the extracted EXE with a system-only PATH", flush=True)
        smoke = run([str(bundle / "MolRecognizer.exe"), "--smoke-test", str(report), "--require-osra"],
                    cwd=work, env=env)
        record["smoke_process"] = smoke
        if smoke["exit_code"] or not report.is_file():
            raise ValueError(f"Extracted EXE smoke test failed: {smoke}")
        record["smoke"] = json.loads(report.read_text(encoding="utf-8"))
        if not record["smoke"]["ok"]:
            raise ValueError("Extracted EXE reported smoke-test failure")
        shutil.copy2(bundle / "BUILD-INFO.json", args.output / "BUILD-INFO.json")
        powershell = str(system / "System32/WindowsPowerShell/v1.0/powershell.exe")
        record["defender_status"] = run([powershell, "-NoProfile", "-NonInteractive", "-Command",
            "Get-MpComputerStatus | Select-Object AMProductVersion,AMEngineVersion,"
            "AntivirusSignatureVersion,AntivirusSignatureLastUpdated,AntivirusEnabled,"
            "RealTimeProtectionEnabled | ConvertTo-Json -Compress"])
        record["defender_scans"] = []
        # A custom scan without automatic remediation does not disable any
        # system protection or add exclusions. Never suppress a threat report.
        if args.scan:
            local_zip = work / args.binary.name
            shutil.copy2(args.binary, local_zip)
            if sha256(local_zip) != record["binary_sha256"]:
                raise ValueError("Local scan copy differs from binary ZIP")
            scanner = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Windows Defender/MpCmdRun.exe"
            for label, target in (("extracted", bundle), ("zip", local_zip)):
                print(f"Defender scanning {label}", flush=True)
                scan = run([str(scanner), "-Scan", "-ScanType", "3", "-File", str(target),
                            "-DisableRemediation"], timeout=1800)
                record["defender_scans"].append({"target": label, **scan})
                save()
                if scan["exit_code"] != 0:
                    raise ValueError(f"Defender scan did not pass: {scan}")
        record["ok"] = True
        record["completed_utc"] = datetime.now(timezone.utc).isoformat()
        record["limitations"] = ["Local automated checks, not a clean-machine interactive test.",
                                  "No desktop screenshots were captured.",
                                  "A scan result is not a safety guarantee or code signature.",
                                  "Scoped CImg permission is recorded; publication still requires owner approval."]
    except Exception as error:
        record["error"] = str(error)
        raise
    finally:
        save()
    print(f"Validated matching ZIP pair; reports: {args.output}\nTest copy: {bundle}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New report directory")
    parser.add_argument("--work-dir", type=Path, required=True, help="Local Windows staging parent")
    parser.add_argument("--scan", action="store_true", help="Run Defender custom scans; no configuration changes")
    validate(parser.parse_args())


if __name__ == "__main__":
    main()
