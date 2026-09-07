"""Portable paths, external processes and helper protocols without Windows."""

import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
from threading import Event
from unittest.mock import Mock, call, patch

import pytest
from rdkit import Chem

from molrecognizer import runtime
from molrecognizer.core.recognizer import OSRARecognizer


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    install = tmp_path / "Portable app"
    install.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(install / "MolRecognizer.exe"))
    monkeypatch.setattr(sys, "_MEIPASS", str(install / "_internal"), raising=False)
    monkeypatch.delenv("OSRA_EXECUTABLE", raising=False)
    return install


def test_source_render_command():
    assert runtime.render_command() == (sys.executable, ["-m", "molrecognizer.render_worker"])


def test_frozen_render_command_never_relaunches_gui(frozen, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert runtime.render_command() == (str(frozen / "MolRecognizerWorker.exe"), [])


def test_bundled_osra_wins_over_path_and_ignores_cwd(frozen, tmp_path, monkeypatch):
    binary = frozen / "tools/osra/bin/osra.exe"
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.chdir(tmp_path)
    with patch("molrecognizer.core.recognizer.shutil.which", return_value="/unrelated/osra"):
        assert OSRARecognizer().executable == str(binary)


def test_explicit_override_wins_and_bad_override_does_not_fall_back(frozen, monkeypatch):
    binary = frozen / "tools/osra/bin/osra.exe"
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setenv("OSRA_EXECUTABLE", "custom-osra")
    with patch("molrecognizer.core.recognizer.shutil.which", return_value="/custom/osra") as which:
        assert OSRARecognizer().executable == "/custom/osra"
        which.assert_called_once_with("custom-osra")
    with patch("molrecognizer.core.recognizer.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="OSRA_EXECUTABLE"):
            OSRARecognizer()


@pytest.mark.parametrize("share", ["share", "share/osra", "bin"])
def test_relocatable_dictionary_flags(tmp_path, share):
    binary = tmp_path / "osra runtime/bin/osra.exe"
    binary.parent.mkdir(parents=True)
    binary.touch()
    directory = binary.parent.parent / share
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("chain.txt", "spelling.txt", "superatom.txt"):
        (directory / name).write_text("dictionary", encoding="utf-8")
    with patch("molrecognizer.core.recognizer.shutil.which", return_value=str(binary)):
        recognizer = OSRARecognizer()
    assert recognizer._dictionary_options() == [
        "-A", str(directory / "chain.txt"), "-l", str(directory / "spelling.txt"),
        "-a", str(directory / "superatom.txt"),
    ]


def test_external_environment_strips_only_internal_libraries(frozen, monkeypatch):
    monkeypatch.setenv("PATH", os.pathsep.join(map(str, [frozen / "_internal", frozen / "_internal/PySide6",
                                                       frozen / "tools/osra/bin", Path("/system/bin")])))
    monkeypatch.setenv("LD_LIBRARY_PATH", "bundled")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "system")
    monkeypatch.setattr(sys, "platform", "linux")
    env = runtime.external_environment()
    assert env["PATH"] == os.pathsep.join(map(str, [frozen / "tools/osra/bin", Path("/system/bin")]))
    assert env["LD_LIBRARY_PATH"] == "system"
    assert os.environ["LD_LIBRARY_PATH"] == "bundled"  # Parent is unchanged.


def test_external_windows_options_hide_console(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert runtime.subprocess_options()["creationflags"] == 0x08000000


def test_windows_dll_search_restored_after_launch_error(frozen, monkeypatch):
    import ctypes
    monkeypatch.setattr(sys, "platform", "win32")
    previous = str(frozen / "_internal")
    kernel = Mock()
    def get_directory(size, buffer):
        if buffer is not None:
            buffer.value = previous
        return len(previous)
    kernel.GetDllDirectoryW.side_effect = get_directory
    kernel.SetDllDirectoryW.return_value = 1
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **kw: kernel, raising=False)
    with pytest.raises(RuntimeError, match="launch failed"):
        with runtime.external_dll_search():
            assert kernel.SetDllDirectoryW.call_args == call(None)
            raise RuntimeError("launch failed")
    assert kernel.SetDllDirectoryW.call_args_list == [call(None), call(previous)]


def test_compiled_capture_discovery_needs_no_powershell(frozen, monkeypatch):
    from molrecognizer.gui import native_capture
    monkeypatch.setattr(sys, "platform", "win32")
    binary = frozen / "tools/MolRecognizerCapture.exe"
    binary.parent.mkdir()
    binary.touch()
    with patch.object(native_capture, "is_wsl", return_value=False), \
         patch.object(native_capture.shutil, "which", side_effect=AssertionError("No PowerShell lookup")):
        assert native_capture.native_capture_executable() == str(binary)


def test_render_helper_binary_protocol_and_errors(tmp_path):
    result = subprocess.run([sys.executable, "-m", "molrecognizer.render_worker"],
                            input=b"CCO", capture_output=True, timeout=20, cwd=tmp_path)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    mol = Chem.Mol(result.stdout)
    assert mol.GetConformer().Is3D()
    assert Chem.MolToSmiles(Chem.RemoveHs(mol)) == "CCO"
    result = subprocess.run([sys.executable, "-m", "molrecognizer.render_worker"],
                            input=b"not-a-smiles", capture_output=True, timeout=20)
    assert result.returncode == 1 and not result.stdout
    assert b"Cannot parse SMILES" in result.stderr


def test_frozen_osra_uses_process_creation_context(tmp_path):
    # Real cancellable subprocess, with the same path the frozen app uses.
    recognizer = OSRARecognizer(executable=sys.executable, cancel_event=Event())
    with patch("molrecognizer.core.recognizer.external_dll_search") as context:
        result = recognizer._run_osra([sys.executable, "-c", "print('ok')"], timeout=5, text=True)
    assert result.stdout.strip() == "ok"
    context.return_value.__enter__.assert_called_once()
    context.return_value.__exit__.assert_called_once()


def _builder():
    path = Path(__file__).resolve().parents[1] / "packaging/windows/build.py"
    spec = importlib.util.spec_from_file_location("windows_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _windows_osra(tmp_path):
    directory = tmp_path / "Windows OSRA"
    (directory / "bin").mkdir(parents=True)
    header = bytearray(64)
    header[:2] = b"MZ"
    struct.pack_into("<I", header, 60, 64)
    (directory / "bin/osra.exe").write_bytes(header + b"PE\0\0\x64\x86")
    (directory / "share").mkdir()
    for name in ("chain.txt", "spelling.txt", "superatom.txt"):
        (directory / "share" / name).write_text("fixture", encoding="utf-8")
    (directory / "licenses").mkdir()
    (directory / "licenses/LICENSE.txt").write_text("fixture", encoding="utf-8")
    (directory / "SOURCE-NOTICE.txt").write_text("fixture", encoding="utf-8")
    return directory


def test_osra_bundle_validation(tmp_path):
    directory = _windows_osra(tmp_path)
    assert _builder().validate_osra(directory) == directory.resolve()


@pytest.mark.parametrize("missing", ["bin/osra.exe", "share/chain.txt", "share/spelling.txt",
                                   "share/superatom.txt", "licenses/LICENSE.txt", "SOURCE-NOTICE.txt"])
def test_incomplete_osra_bundle_is_rejected(tmp_path, missing):
    directory = _windows_osra(tmp_path)
    (directory / missing).unlink()
    with pytest.raises(ValueError):
        _builder().validate_osra(directory)


def test_linux_osra_cannot_be_shipped_as_windows(tmp_path):
    directory = _windows_osra(tmp_path)
    (directory / "bin/osra.exe").write_bytes(b"\x7fELF" + b"\0" * 128)
    with pytest.raises(ValueError, match="Windows PE"):
        _builder().validate_osra(directory)


def test_license_collection_keeps_raw_multiline_metadata(tmp_path, monkeypatch):
    builder = _builder()
    raw = "Name: dependency\nLicense: first line\n        second line\n"
    class Wheel:
        version = "1.0"
        files = []
        @property
        def metadata(self):
            raise AssertionError("Do not serialize email.Message license headers")
        def read_text(self, name):
            assert name == "METADATA"
            return raw
    monkeypatch.setattr(builder.metadata, "distribution", lambda name: Wheel())
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path))
    (tmp_path / "LICENSE.txt").write_text("Python license fixture", encoding="utf-8")
    destination = tmp_path / "notices"
    versions = builder.collect_licenses(destination)
    assert versions["numpy"] == "1.0"
    assert (destination / "numpy/METADATA.txt").read_text(encoding="utf-8") == raw
