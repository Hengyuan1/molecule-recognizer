"""Application entry point."""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def _setup_logging():
    """Redirect Python warnings and errors to a log file.

    Only redirects Python's ``sys.stderr``.  The C-level fd 2 is left
    untouched because redirecting it before the display server
    connection is established can break cursor rendering on WSLg.
    Location: ``~/.molrecognizer/molrecognizer.log``
    """
    log_dir = os.path.expanduser("~/.molrecognizer")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "molrecognizer.log")
        log_file = open(log_path, "w")  # noqa: SIM115  — kept open for lifetime
        sys.stderr = log_file
    except OSError:
        pass  # fall back to terminal stderr

STYLESHEET = """
/* ---- Main window ---- */
QMainWindow {
    background-color: #f8f9fa;
}

/* ---- Menu bar (light) ---- */
QMenuBar {
    background-color: #ffffff;
    color: #333333;
    font-size: 15px;
    font-weight: 500;
    border-bottom: 1px solid #dde1e6;
    padding: 2px 0;
}
QMenuBar::item {
    padding: 6px 14px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #e8f0fe;
    color: #1a73e8;
}

/* ---- Drop-down menus ---- */
QMenu {
    background-color: #ffffff;
    color: #333333;
    font-size: 13px;
    padding: 6px;
    border: 1px solid #dde1e6;
    border-radius: 8px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #e8f0fe;
    color: #1a73e8;
}
QMenu::separator {
    height: 1px;
    background: #e8eaed;
    margin: 4px 10px;
}

/* ---- Toolbar container ---- */
QWidget#toolbar_container {
    background-color: #ffffff;
    border-bottom: 1px solid #e8eaed;
}

/* ---- Tool buttons ---- */
QToolButton {
    background-color: #f1f3f5;
    border: 1px solid #dde1e6;
    border-radius: 6px;
    padding: 3px 14px;
    font-size: 17px;
    font-weight: 600;
    min-height: 24px;
    color: #444444;
}
QToolButton:hover {
    background-color: #e8f0fe;
    border-color: #a8c7fa;
    color: #1a73e8;
}
QToolButton:checked {
    background-color: #1a73e8;
    color: #ffffff;
    border-color: #1a73e8;
}
QToolButton:pressed {
    background-color: #1557b0;
    color: #ffffff;
}
QToolButton::menu-indicator {
    subcontrol-position: right center;
    subcontrol-origin: padding;
    width: 12px;
    padding-right: 2px;
}

/* ---- Combo boxes ---- */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #dde1e6;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 14px;
    min-height: 30px;
    color: #333333;
}
QComboBox:hover {
    border-color: #a8c7fa;
}
QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #dde1e6;
    selection-background-color: #e8f0fe;
    selection-color: #1a73e8;
    font-size: 14px;
    padding: 4px;
    border-radius: 6px;
}

/* ---- Left panel ---- */
QWidget#left_panel {
    background-color: #f0f2f5;
}

/* ---- Panel title ---- */
QLabel#panel_title {
    font-size: 13px;
    font-weight: 700;
    color: #333333;
}

/* ---- Action buttons ---- */
QPushButton#action_btn {
    background-color: #1a73e8;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 14px;
    font-weight: 600;
    min-height: 26px;
}
QPushButton#action_btn:hover {
    background-color: #1557b0;
}
QPushButton#action_btn:pressed {
    background-color: #0d47a1;
}

QPushButton#action_btn_secondary {
    background-color: #ffffff;
    color: #1a73e8;
    border: 1.5px solid #1a73e8;
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 14px;
    font-weight: 600;
    min-height: 26px;
}
QPushButton#action_btn_secondary:hover {
    background-color: #e8f0fe;
}

/* ---- Splitter handles ---- */
QSplitter::handle {
    background-color: #dde1e6;
}
QSplitter::handle:hover {
    background-color: #a8c7fa;
}

/* ---- Element palette ---- */
QWidget#element_palette {
    background-color: #f0f2f5;
}

/* ---- Bottom bar ---- */
QWidget#bottom_bar {
    background-color: #ffffff;
    border-top: 1px solid #e8eaed;
}

QLabel#smiles_label {
    font-size: 14px;
    font-weight: 700;
    color: #555555;
}

QLineEdit#smiles_field {
    background-color: #f8f9fa;
    border: 1px solid #dde1e6;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
    font-size: 14px;
    color: #222222;
}

QPushButton#small_btn {
    background-color: #1a73e8;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 15px;
    font-weight: 600;
    min-height: 24px;
}
QPushButton#small_btn:hover {
    background-color: #1557b0;
}

QPushButton#small_btn_green {
    background-color: #0d904f;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 15px;
    font-weight: 600;
    min-height: 30px;
}
QPushButton#small_btn_green:hover {
    background-color: #0a7a42;
}

QLabel#valence_label {
    font-size: 13px;
    color: #666666;
    padding-left: 56px;
}

/* ---- Canvas ---- */
QGraphicsView {
    background-color: #ffffff;
    border: 1px solid #e0e3e7;
    border-radius: 8px;
}

/* ---- Status bar ---- */
QStatusBar {
    background-color: #f0f2f5;
    color: #666666;
    font-size: 11px;
    border-top: 1px solid #e8eaed;
    padding: 3px 10px;
}

/* ---- General labels ---- */
QLabel {
    font-size: 12px;
    color: #444444;
}

/* ---- Scrollbars ---- */
QScrollBar:vertical {
    width: 8px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: #c4c9cf;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


def main():
    # Ensure cursor theme is set for WSLg/Wayland — without this,
    # Qt6 may fail to render any cursor at all.
    os.environ.setdefault("XCURSOR_THEME", "Adwaita")
    os.environ.setdefault("XCURSOR_SIZE", "24")

    app = QApplication(sys.argv)
    _setup_logging()
    app.setApplicationName("Molecule Recognizer")
    app.setOrganizationName("molrecognizer")
    app.setStyleSheet(STYLESHEET)

    font = QFont("Segoe UI", 11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
