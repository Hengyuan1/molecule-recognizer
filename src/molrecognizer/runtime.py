"""Paths and child-process settings for source and portable installations."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sys
from threading import RLock


_dll_lock = RLock()


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def application_directory() -> Path:
    """Tools live beside the EXE, not in PyInstaller's private _internal tree."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def render_command() -> tuple[str, list[str]]:
    if is_frozen():
        name = "MolRecognizerWorker.exe" if sys.platform == "win32" else "MolRecognizerWorker"
        return str(application_directory() / name), []
    return sys.executable, ["-m", "molrecognizer.render_worker"]


def capture_helper() -> Path | None:
    if sys.platform == "win32":
        candidate = application_directory() / "tools" / "MolRecognizerCapture.exe"
        if candidate.is_file():
            return candidate
    return None


def external_environment() -> dict[str, str]:
    """Do not make OSRA load Qt/RDKit's bundled copies of unrelated libraries."""
    env = os.environ.copy()
    if not is_frozen():
        return env
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        root = Path(bundle).resolve()
        env["PATH"] = os.pathsep.join(
            entry for entry in env.get("PATH", "").split(os.pathsep)
            if entry and not Path(entry).resolve().is_relative_to(root)
        )
    if sys.platform.startswith("linux"):
        if "LD_LIBRARY_PATH_ORIG" in env:
            env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
        else:
            env.pop("LD_LIBRARY_PATH", None)
    return env


@contextmanager
def external_dll_search():
    """Temporarily undo the Windows bootloader's inherited DLL search path.

    Keep this context around synchronous process *creation* only, never around
    recognition/communicate(). Restore the exact previous path on failure too.
    """
    if not (is_frozen() and sys.platform == "win32"):
        yield
        return
    import ctypes
    with _dll_lock:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_directory = kernel32.GetDllDirectoryW
        get_directory.argtypes = [ctypes.c_ulong, ctypes.c_wchar_p]
        get_directory.restype = ctypes.c_ulong
        set_directory = kernel32.SetDllDirectoryW
        set_directory.argtypes = [ctypes.c_wchar_p]
        set_directory.restype = ctypes.c_int
        size = get_directory(0, None)
        previous = ctypes.create_unicode_buffer(size + 1)
        get_directory(len(previous), previous)
        if not set_directory(None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            if not set_directory(previous.value or None):
                raise ctypes.WinError(ctypes.get_last_error())


def subprocess_options() -> dict:
    """Suppress console flashes without hiding recognition errors in the pipes."""
    options = {"env": external_environment()}
    if sys.platform == "win32":
        # CREATE_NO_WINDOW; use the value so discovery tests also run on Linux.
        options["creationflags"] = 0x08000000
    return options
