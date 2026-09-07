"""Application entry point."""

import logging
import os
import sys

from PySide6.QtCore import QRect, QSettings, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .app_icon import application_icon, set_windows_app_id
from .theme import STYLESHEET


_log_file = None  # kept alive for process lifetime


def _setup_logging():
    """Redirect Python's sys.stderr to a log file."""
    global _log_file
    log_dir = os.path.expanduser("~/.molrecognizer")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "molrecognizer.log")
        _log_file = open(log_path, "w")  # noqa: SIM115
        sys.stderr = _log_file
        logging.basicConfig(level=logging.INFO, stream=_log_file,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    except OSError:
        pass


def _redirect_native_stderr():
    """Redirect C-level fd 2 to the log file.

    Must be called AFTER QApplication is created and the window is
    shown, so the display server connection is fully established.
    Redirecting fd 2 earlier breaks cursor rendering on WSLg.
    """
    if _log_file is not None:
        try:
            os.dup2(_log_file.fileno(), 2)
        except OSError:
            pass


def _restore_window_geometry(window: MainWindow):
    """Restore a resizable normal window, or centre a large default one."""
    saved = QSettings().value("main_window/normal_geometry")
    if isinstance(saved, QRect) and saved.isValid():
        # Ignore geometry for a monitor that is no longer connected.
        if any(screen.availableGeometry().intersects(saved)
               for screen in QApplication.screens()):
            window.setGeometry(saved)
            return

    screen = QApplication.primaryScreen()
    if screen is None:
        return
    available = screen.availableGeometry()
    width = round(available.width() * 0.80)
    height = round(available.height() * 0.80)
    window.setGeometry(
        available.x() + (available.width() - width) // 2,
        available.y() + (available.height() - height) // 2,
        width,
        height,
    )



def main():
    # Ensure cursor theme is set for WSLg/Wayland — without this,
    # Qt6 may fail to render any cursor at all.
    os.environ.setdefault("XCURSOR_THEME", "Adwaita")
    os.environ.setdefault("XCURSOR_SIZE", "24")

    set_windows_app_id()
    app = QApplication(sys.argv)
    _setup_logging()
    app.setApplicationName("Molecule Recognizer")
    app.setOrganizationName("molrecognizer")
    app.setWindowIcon(application_icon())
    app._base_stylesheet = STYLESHEET
    app.setStyleSheet(STYLESHEET)

    font = QFont("Segoe UI", 11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app._base_font = QFont(font)
    app.setFont(font)

    window = MainWindow()
    _restore_window_geometry(window)
    window.show()
    # Redirect C-level stderr AFTER the window is shown so the display
    # server connection is fully established (avoids cursor issues).
    _redirect_native_stderr()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
