# Build via build.py; the GUI and worker share one _internal dependency tree.
from pathlib import Path
import sys

from PyInstaller.utils.hooks import (
    collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata,
    collect_delvewheel_libs_directory,
)

root = Path(SPECPATH).parents[1]
sys.path.insert(0, str(root / "packaging/windows"))
from release_checks import include_binary
app_icon = str(root / "src/molrecognizer/gui/icons/molrecognizer.ico")
rdkit_imports = collect_submodules(
    "rdkit", filter=lambda name: not any(
        part.startswith(("test", "Test", "UnitTest")) or part in ("Contrib", "sping")
        for part in name.split(".")
    )
)
rdkit_data = collect_data_files("rdkit")
rdkit_binaries = collect_dynamic_libs("rdkit")
rdkit_data, rdkit_binaries = collect_delvewheel_libs_directory(
    "rdkit", datas=rdkit_data, binaries=rdkit_binaries,
)
excluded = ["molscribe", "torch", "torchvision", "huggingface_hub", "pytest",
            "IPython", "matplotlib", "tkinter", "PyQt5", "PyQt6", "PySide2"]

gui = Analysis(
    [str(root / "packaging/windows/launcher.py")],
    pathex=[str(root / "src")],
    binaries=rdkit_binaries,
    datas=rdkit_data + collect_data_files("molrecognizer") + copy_metadata("molrecognizer"),
    hiddenimports=rdkit_imports,
    excludes=excluded,
)
worker = Analysis(
    [str(root / "packaging/windows/worker.py")],
    pathex=[str(root / "src")],
    binaries=rdkit_binaries,
    datas=rdkit_data,
    hiddenimports=rdkit_imports,
    excludes=excluded + ["PySide6"],
)
# Filter at collection time, after hook dependency discovery. The builder
# checks the final payload and exercises it in a relocated Windows folder.
gui.binaries = [entry for entry in gui.binaries if include_binary(entry[0])]
gui_exe = EXE(
    PYZ(gui.pure), gui.scripts, [], exclude_binaries=True,
    name="MolRecognizer", console=False, upx=False, icon=app_icon,
)
worker_exe = EXE(
    PYZ(worker.pure), worker.scripts, [], exclude_binaries=True,
    name="MolRecognizerWorker", console=True, upx=False, icon=app_icon,
)
COLLECT(gui_exe, worker_exe, gui.binaries, worker.binaries, gui.datas, worker.datas,
        name="MolRecognizer", upx=False)
