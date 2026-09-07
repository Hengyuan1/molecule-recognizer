"""The shared application identity, separate from editing-toolbar icons."""

import ctypes
import logging
from pathlib import Path
import sys

from PySide6.QtGui import QIcon


WINDOWS_APP_ID = "Hengyuan.MolRecognizer.Desktop"
ICON_PATH = Path(__file__).with_name("icons") / "molrecognizer.ico"


def application_icon() -> QIcon:
    return QIcon(str(ICON_PATH))


def set_windows_app_id() -> None:
    """Call before QApplication so native Windows does not group us as Python."""
    if sys.platform != "win32":
        return
    try:
        function = ctypes.WinDLL("shell32").SetCurrentProcessExplicitAppUserModelID
        function.argtypes = [ctypes.c_wchar_p]
        function.restype = ctypes.c_long
        result = function(WINDOWS_APP_ID)
        if result < 0:
            raise OSError(f"SetCurrentProcessExplicitAppUserModelID failed: {result:#x}")
    except (AttributeError, OSError):
        # Branding must not prevent a source/portable build from launching.
        logging.getLogger(__name__).warning("Could not set Windows taskbar identity", exc_info=True)
