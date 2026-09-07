"""Exercise a staged OSRA runtime without compiler/Python/Conda paths.

Run with the build venv's native Windows Python. Only generated test drawings
are used; no screenshots or user images are captured. Results are not a claim
that arbitrary chemical images will be recognized accurately.
"""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    args.report = args.report.resolve()
    if sys.platform != "win32":
        parser.error("Run using native Windows Python")
    from rdkit import Chem
    from rdkit.Chem import Draw
    from molrecognizer.core.recognizer import OSRARecognizer

    executable = args.runtime.resolve() / "bin/osra.exe"
    for name in list(os.environ):
        if name.startswith(("OSRA_", "BABEL_", "MAGICK_", "FONTCONFIG_")) or name in (
                "PYTHONPATH", "PYTHONHOME", "MSYSTEM", "MSYS2_PATH_TYPE"):
            os.environ.pop(name, None)
    system = Path(os.environ.get("WINDIR", r"C:\Windows"))
    os.environ["PATH"] = os.pathsep.join(map(str, (system / "System32", system)))
    report = {"executable": str(executable), "PATH": os.environ["PATH"], "tests": []}
    with tempfile.TemporaryDirectory(prefix="osra recognition test ") as temporary, working_directory(temporary):
        version = subprocess.run([str(executable), "--version"], capture_output=True,
                                 text=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        report["version"] = version.stdout.strip()
        if version.returncode or "2.2.4" not in version.stdout:
            raise RuntimeError(f"OSRA could not start: {version}")
        recognizer = OSRARecognizer(executable=str(executable), timeout=45)
        cases = [
            ("benzene", "c1ccccc1", "png"),
            ("aspirin", "CC(=O)Oc1ccccc1C(=O)O", "png"),
            ("aspirin-jpeg", "CC(=O)Oc1ccccc1C(=O)O", "jpg"),
            ("aspirin-bmp", "CC(=O)Oc1ccccc1C(=O)O", "bmp"),
            ("caffeine", "Cn1c(=O)c2c(ncn2C)n(C)c1=O", "png"),
            ("nitrile", "N#Cc1ccc(N)cc1", "png"),
            ("stereo", "C[C@H](O)C(=O)O", "png"),
        ]
        for label, smiles, extension in cases:
            mol = Chem.MolFromSmiles(smiles)
            expected = Chem.MolToSmiles(mol)
            path = Path(temporary) / f"{label} test.{extension}"
            Draw.MolToImage(mol, size=(600, 450)).convert("RGB").save(path)
            result = {"name": label, "expected": expected, "ok": False}
            start = time.monotonic()
            try:
                recognized = recognizer._read_sdf(path)
                if recognized is None:
                    raw = recognizer._run_osra(
                        [str(executable), "-f", "sdf", *recognizer._dictionary_options(), str(path)],
                        timeout=55, text=True,
                    )
                    raise RuntimeError(f"No SDF returned (exit {raw.returncode}): "
                                       f"{raw.stdout[:2000]} {raw.stderr[:2000]}")
                Chem.SanitizeMol(recognized)
                result["actual"] = Chem.MolToSmiles(Chem.RemoveHs(recognized))
                result["ok"] = result["actual"] == expected
            except Exception as error:
                result["error"] = str(error)
            result["seconds"] = round(time.monotonic() - start, 2)
            report["tests"].append(result)
            print(json.dumps(result), flush=True)
        report["ok"] = all(test["ok"] for test in report["tests"])
        args.report.resolve().write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
