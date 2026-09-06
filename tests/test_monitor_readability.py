"""Isolated, offscreen Qt regression checks; never touch the user's settings."""

import os
import subprocess
import sys
import textwrap

import pytest


_BOOTSTRAP = """
import sys
from unittest.mock import patch
from PySide6.QtCore import QSettings, QSize, QPoint, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMenu
from molrecognizer.gui.main_window import MainWindow
from molrecognizer.gui.theme import STYLESHEET
from molrecognizer.gui.inline_menu import InlineMenuBar

app = QApplication([])
app.setOrganizationName("readability-test")
app.setApplicationName("readability-test")
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, sys.argv[1])
app._base_stylesheet = STYLESHEET
app._base_font = QFont("Segoe UI", 11)
app.setStyleSheet(STYLESHEET)
app.setFont(app._base_font)
patch("molrecognizer.gui.screenshot.is_wsl", return_value=False).start()
patch("molrecognizer.gui.main_window.is_wsl", return_value=sys.argv[2] == "wsl").start()
patch.object(MainWindow, "_connect_screen_scaling", lambda self: None).start()
captures = []
patch.object(MainWindow, "_on_screenshot", lambda self: captures.append(True)).start()
settings = QSettings()
settings.setValue("ui_scale/windows:laptop", 1.5)
settings.setValue("window_size/windows:laptop", QSize(1344, 1211))
settings.setValue("ui_scale/windows:external", 0.8)
settings.setValue("external_compact_scale/external", True)
settings.setValue("window_size/windows:external", QSize(1344, 756))
window = MainWindow()
window.show()
window.activateWindow()
app.processEvents()
"""


def _run(tmp_path, platform, script):
    result = subprocess.run(
        [sys.executable, "-c", _BOOTSTRAP + textwrap.dedent(script),
         str(tmp_path), platform],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("platform", ["wsl", "native"])
def test_high_resolution_profile_upgrade(tmp_path, platform):
    _run(tmp_path, platform, """
        normal_menu_height = window._menu_bar.height()
        window._on_windows_monitor_detected(("laptop", 2880, 1800))
        app.processEvents()
        assert window._ui_scale == 1.8
        assert window.size() == QSize(2304, 1440), window.size()
        assert window._menu_bar.height() > normal_menu_height
        assert window._menu_bar.parentWidget() == window.centralWidget()
        assert window._status_bar.parentWidget() == window.centralWidget()
        window.resize(2200, 1440)
        window._on_windows_monitor_detected(("laptop", 2880, 1800))
        assert window.width() == 2200
        window._apply_ui_scale(1.7, save=True)
        window._on_windows_monitor_detected(("external", 1920, 1080))
        app.processEvents()
        assert window._ui_scale == 0.8
        assert window.size() == QSize(1344, 756), window.size()
        window._on_windows_monitor_detected(("laptop", 2880, 1800))
        assert window._ui_scale == 1.7
        assert window.width() == 2200
        window._reset_ui_scale()
        window._request_windows_monitor_fit()
        assert window._ui_scale == 1.8
        assert window.size() == QSize(2304, 1440)
        window.close()
        window = MainWindow()
        window.resize(1344, 756)
        window._on_windows_monitor_detected(("laptop", 2880, 1800))
        assert window.size() == QSize(2304, 1440)
        window.close()
    """)


def test_inline_menu_switching_and_actions(tmp_path):
    _run(tmp_path, "wsl", """
        window._on_windows_monitor_detected(("laptop", 2880, 1800))
        app.processEvents()
        bar = window._menu_bar
        assert isinstance(bar, InlineMenuBar)
        assert not bar.findChildren(QMenu)
        assert not bar._panel.isWindow()
        assert bar._panel.windowHandle() is None
        original_size = window.size()
        QTest.mouseClick(bar._headings[0], Qt.MouseButton.LeftButton)
        app.processEvents()
        assert bar._current == 0 and bar._panel.isVisible()
        for index in [1, 2, 3, 4, 3, 2, 1, 0] * 10:
            # Ordinary child-widget enter events, with no popup mouse grab.
            QApplication.sendEvent(bar._headings[index], QEvent(QEvent.Type.Enter))
            app.processEvents()
            assert bar._current == index
            assert bar._panel.isVisible()
            assert bar._headings[index].isChecked()
            assert sum(b.isChecked() for b in bar._headings) == 1
            assert QApplication.activePopupWidget() is None
            assert bar._panel.windowHandle() is None
        assert window.size() == original_size
        QTest.keyClick(app.focusWidget(), Qt.Key.Key_Right)
        assert bar._current == 1
        QTest.keyClick(app.focusWidget(), Qt.Key.Key_Left)
        assert bar._current == 0
        QTest.keyClick(app.focusWidget(), Qt.Key.Key_Down)
        assert app.focusWidget() == bar._rows[1]
        QTest.keyClick(app.focusWidget(), Qt.Key.Key_Return)
        app.processEvents()
        assert len(captures) == 1
        assert bar._current is None and not bar._panel.isVisible()
        # The exact same action remains available as a window shortcut.
        QTest.keyClick(window, Qt.Key.Key_Y, Qt.KeyboardModifier.AltModifier)
        app.processEvents()
        assert len(captures) == 2
        QTest.keyClick(window, Qt.Key.Key_F, Qt.KeyboardModifier.AltModifier)
        QTest.qWait(150)  # Standard button mnemonics use animateClick().
        assert bar._current == 0
        QTest.keyClick(app.focusWidget(), Qt.Key.Key_Escape)
        assert not bar._panel.isVisible()
        QTest.keyClick(window, Qt.Key.Key_F10)
        assert bar._current == 0
        # Click a command rather than using the keyboard.
        bar.open_menu(2)
        QTest.mouseClick(bar._rows[2], Qt.MouseButton.LeftButton)
        assert window._editor._current_tool.name == "atom"
        assert bar._current is None
        # An outside click dismisses without adding an atom underneath.
        bar.open_menu(0)
        canvas = window._editor.canvas.viewport()
        QTest.mouseClick(canvas, Qt.MouseButton.LeftButton,
                         pos=QPoint(canvas.width() - 20, canvas.height() - 20))
        app.processEvents()
        assert bar._current is None
        assert window._editor.molecule.num_atoms == 0
        # Disabled commands are not activated.
        action = window._menu_actions["Capture screenshot"]
        action.setEnabled(False)
        bar.open_menu(0)
        assert not bar._rows[1].isEnabled()
        QTest.mouseClick(bar._rows[1], Qt.MouseButton.LeftButton)
        assert len(captures) == 2
        bar.close_menu()
        action.setEnabled(True)
        # Menus close on move, resize, hiding and loss of window activation.
        bar.open_menu(0)
        window.move(35, 35)
        assert not bar._panel.isVisible()
        bar.open_menu(0)
        window.resize(2310, 1440)
        assert not bar._panel.isVisible()
        bar.open_menu(0)
        QApplication.sendEvent(window, QEvent(QEvent.Type.WindowDeactivate))
        assert not bar._panel.isVisible()
        window._apply_ui_scale(0.8)
        window.resize(1344, 756)
        app.processEvents()
        bar.open_menu(0)
        assert window.centralWidget().rect().contains(bar._panel.geometry())
        bar.close_menu()
        window._apply_ui_scale(1.8)
        window.resize(2304, 1440)
        app.processEvents()
        bar.open_menu(0)
        app.processEvents()
        assert bar._scroll.verticalScrollBar().maximum() == 0
        window.grab().save(sys.argv[1] + "/inline-menu.png")
        window.hide()
        assert not bar._panel.isVisible()
        window.close()
    """)


def test_toolbar_dropdown_cleanup_is_preserved(tmp_path):
    _run(tmp_path, "wsl", """
        for dropdown in window._popup_menus:
            for attempt in range(2):
                dropdown.popup(window.mapToGlobal(QPoint(100, 100)))
                app.processEvents()
                assert dropdown.isVisible()
                QTest.keyClick(dropdown, Qt.Key.Key_Escape)
                QTest.qWait(200)
                assert not dropdown.testAttribute(Qt.WidgetAttribute.WA_WState_Created)
        window.close()
    """)
