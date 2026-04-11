"""Application entry point."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow

STYLESHEET = """
QMainWindow {
    background-color: #f5f6fa;
}

/* ---- Menu bar ---- */
QMenuBar {
    background-color: #2c3e50;
    color: #ecf0f1;
    font-size: 15px;
    font-weight: 500;
    padding: 4px 0px;
    min-height: 36px;
}
QMenuBar::item {
    padding: 8px 16px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #3498db;
}

/* ---- Drop-down menus ---- */
QMenu {
    background-color: #34495e;
    color: #ecf0f1;
    font-size: 14px;
    padding: 6px;
    border: 1px solid #2c3e50;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #3498db;
}
QMenu::separator {
    height: 1px;
    background: #4a6278;
    margin: 6px 12px;
}

/* ---- Toolbar container ---- */
QToolBar {
    background-color: #ecf0f1;
    border: none;
    border-bottom: 2px solid #bdc3c7;
    padding: 6px 8px;
    spacing: 4px;
}

/* ---- Tool buttons ---- */
QToolButton {
    background-color: #ffffff;
    border: 1.5px solid #bdc3c7;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    min-height: 28px;
    color: #2c3e50;
}
QToolButton:hover {
    background-color: #d5e8f7;
    border-color: #3498db;
}
QToolButton:checked {
    background-color: #3498db;
    color: #ffffff;
    border-color: #2980b9;
}
QToolButton:pressed {
    background-color: #2980b9;
    color: #ffffff;
}

/* ---- Combo boxes ---- */
QComboBox {
    background-color: #ffffff;
    border: 1.5px solid #bdc3c7;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 13px;
    min-width: 70px;
    min-height: 28px;
    color: #2c3e50;
}
QComboBox:hover {
    border-color: #3498db;
}
QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #bdc3c7;
    selection-background-color: #3498db;
    selection-color: #ffffff;
    font-size: 13px;
    padding: 4px;
}

/* ---- Push buttons ---- */
QPushButton {
    background-color: #3498db;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    min-height: 36px;
}
QPushButton:hover {
    background-color: #2980b9;
}
QPushButton:pressed {
    background-color: #2471a3;
}

/* ---- Dock widget (info panel) ---- */
QDockWidget {
    font-size: 13px;
    titlebar-close-icon: none;
}
QDockWidget::title {
    background-color: #2c3e50;
    color: #ecf0f1;
    padding: 8px 12px;
    font-weight: 600;
    font-size: 14px;
}

/* ---- Text fields ---- */
QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #bdc3c7;
    border-radius: 6px;
    padding: 8px;
    font-family: "Courier New", monospace;
    font-size: 13px;
    color: #2c3e50;
    selection-background-color: #3498db;
}

/* ---- List widget ---- */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #bdc3c7;
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
}
QListWidget::item {
    padding: 4px 8px;
    border-radius: 3px;
}
QListWidget::item:hover {
    background-color: #eaf2f8;
}

/* ---- Labels ---- */
QLabel {
    font-size: 13px;
    color: #2c3e50;
    font-weight: 600;
}

/* ---- Status bar ---- */
QStatusBar {
    background-color: #2c3e50;
    color: #bdc3c7;
    font-size: 12px;
    padding: 4px 8px;
    min-height: 24px;
}

/* ---- Graphics view (canvas) ---- */
QGraphicsView {
    border: 1px solid #bdc3c7;
    border-radius: 6px;
}
"""


def main():
    app = QApplication(sys.argv)
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
