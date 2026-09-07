"""Read PE import tables and check portable-bundle DLL closure without running it.

OSRA and the Python GUI have separate DLL search scopes. Existence is checked,
not binary compatibility; relocated native smoke tests remain necessary.
"""

import argparse
import json
from pathlib import Path

from fetch_release_sources import sha256


def audit(bundle, system):
    import pefile
    binaries = sorted(path for path in bundle.rglob("*")
                      if path.suffix.lower() in (".dll", ".pyd", ".exe"))
    system_names = {path.name.lower() for path in system.iterdir() if path.is_file()}
    osra_names = {path.name.lower() for path in binaries if "osra" in path.relative_to(bundle).parts}
    app_names = {path.name.lower() for path in binaries if "osra" not in path.relative_to(bundle).parts}
    records = []
    missing = []
    for path in binaries:
        relative = path.relative_to(bundle)
        available = osra_names if "osra" in relative.parts else app_names
        with pefile.PE(str(path), fast_load=True) as pe:
            pe.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
            ])
            imports = sorted({entry.dll.decode("ascii").lower()
                              for table in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT")
                              for entry in getattr(pe, table, [])})
            unresolved = [name for name in imports
                          if name not in available and name not in system_names
                          and not name.startswith(("api-ms-win-", "ext-ms-win-"))]
            record = {"path": relative.as_posix(), "sha256": sha256(path),
                      "machine": hex(pe.FILE_HEADER.Machine), "imports": imports,
                      "unresolved": unresolved}
            records.append(record)
            if unresolved:
                missing.append(record)
    return {"ok": not missing, "binary_count": len(records), "binaries": records,
            "limitations": ["Does not discover every optional dynamic LoadLibrary call.",
                            "Existence in a bundle is not proof of version/ABI compatibility.",
                            "This inventory does not certify licenses or malware safety."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--system-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.bundle.resolve(), args.system_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {result['binary_count']} native binaries; import closure: {result['ok']}")
    for record in result["binaries"]:
        if record["unresolved"]:
            print(record["path"], record["unresolved"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
