"""Windows split-button drawing and mixed-DPI logical sizing regressions."""

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QMargins, QRect, QSize

from molrecognizer.gui.screen_layout import fitted_geometry, recommended_scale, recommended_size
from tests.test_monitor_readability import _run


@pytest.mark.parametrize("cached", [None, True])
def test_windows_python_on_wsl_share_is_not_wsl(monkeypatch, cached):
    from molrecognizer.gui import screenshot
    monkeypatch.setattr(screenshot.sys, "platform", "win32")
    monkeypatch.setattr(screenshot, "_wsl_cached", cached)
    reader = Mock(side_effect=AssertionError("Windows must not read /proc/version"))
    monkeypatch.setattr("builtins.open", reader)
    assert not screenshot.is_wsl()
    reader.assert_not_called()


@pytest.mark.parametrize("width,height,dpr,scale,fraction", [
    (1152, 720, 2.5, 0.7, 0.8),  # User's 2880x1800 laptop at 250%.
    (1440, 900, 2.0, 0.9, 0.8),
    (1920, 1200, 1.5, 1.2, 0.8),
    (1920, 1080, 1.0, 0.8, 0.7),
])
def test_native_scale_does_not_apply_windows_dpi_twice(width, height, dpr, scale, fraction):
    screen = Mock()
    screen.geometry.return_value = QRect(0, 0, width, height)
    screen.availableGeometry.return_value = QRect(0, 0, width, height - 48)
    screen.devicePixelRatio.return_value = dpr
    assert recommended_scale(screen) == scale
    assert recommended_size(screen) == QSize(round(width * fraction), round((height - 48) * fraction))


@pytest.mark.parametrize("area", [QRect(0, 0, 1152, 672), QRect(-641, -1083, 1920, 1032),
                                  QRect(1279, -1080, 1920, 1032)])
def test_whole_frame_fits_actual_work_area_including_negative_origins(area):
    margins = QMargins(8, 30, 8, 8)
    target = fitted_geometry(QRect(-401, -360, 1537, 868), QSize(921, 538),
                             QSize(860, 540), area, margins)
    assert area.contains(target.marginsAdded(margins))
    assert target.width() >= 860 and target.height() >= 540


def test_native_laptop_startup_fit_drag_dpi_change_and_manual_size(tmp_path):
    _run(tmp_path, "native", '''
        from unittest.mock import Mock
        from PySide6.QtCore import QRect
        def monitor(name, rect, work, dpr):
            s = Mock()
            s.name.return_value = name
            s.geometry.return_value = rect
            s.availableGeometry.return_value = work
            s.devicePixelRatio.return_value = dpr
            return s
        laptop = monitor('laptop', QRect(0,0,1152,720), QRect(0,0,1152,672), 2.5)
        external = monitor('external', QRect(1279,-1080,1920,1080), QRect(1279,-1080,1920,1032), 1.0)
        patch.object(window, '_native_windows_layout', return_value=True).start()
        screen = patch.object(window, 'screen', return_value=laptop).start()
        QSettings().setValue('window_size/laptop', QSize(1537,868))
        window.resize(1537,868)
        window._fit_native_monitor()
        app.processEvents()
        assert window._ui_scale == .7, window._ui_scale
        assert laptop.availableGeometry().contains(window.frameGeometry()), (window.frameGeometry(), window.minimumSizeHint())
        assert window.size().width() >= window.minimumSizeHint().width()
        assert window.size().height() >= window.minimumSizeHint().height()

        # A+ cannot grow the logical window beyond the laptop's usable height.
        for _ in range(12):
            window._change_ui_scale(.1)
            app.processEvents()
            assert laptop.availableGeometry().contains(window.frameGeometry())
        window._reset_ui_scale()
        QTest.qWait(220)

        # Monitor changes defer until the native move/resize operation ends.
        original = window.geometry()
        window._native_geometry_busy = True
        screen.return_value = external
        window._schedule_native_fit()
        QTest.qWait(220)
        assert window.geometry() == original
        window._native_geometry_busy = False
        window._schedule_native_fit()
        QTest.qWait(220)
        assert window._ui_scale == .8
        # The offscreen plugin can add a 2px synthetic-frame offset when
        # moving to a mocked screen it doesn't own. Real desktop checks use
        # exact bounds; the pure geometry tests above also include all margins.
        assert external.availableGeometry().adjusted(-2,-2,2,2).contains(window.frameGeometry()), (window.geometry(), window.frameGeometry(), window.minimumSizeHint())
        assert window.width() <= round(1920 * .7)
        assert window.height() <= round(1032 * .7)

        # Ordinary manual resizing on one screen isn't undone by polling.
        window.resize(window.width() + 40, window.height() + 20)
        app.processEvents()
        custom = window.geometry()
        window._fit_native_monitor()
        assert window.geometry() == custom
        window._fit_window_btn.click()
        QTest.qWait(220)
        assert window.width() <= round(1920 * .7)

        # Changing scale on the same physical panel is also detected.
        screen.return_value = laptop
        window._fit_native_monitor()
        laptop.geometry.return_value = QRect(0,0,1440,900)
        laptop.availableGeometry.return_value = QRect(0,0,1440,852)
        laptop.devicePixelRatio.return_value = 2.0
        QSettings().remove('ui_scale/laptop')
        window._poll_window_screen()
        QTest.qWait(220)
        assert window._ui_scale == .9
        assert laptop.availableGeometry().contains(window.frameGeometry())

        window.showMaximized()
        window._fit_window_btn.click()
        QTest.qWait(220)
        assert window.isMaximized()
        window.close()
        assert not window._native_fit_timer.isActive()
    ''')


@pytest.mark.parametrize("scale", [0.7, 0.8, 1.0, 1.8])
def test_split_button_arrow_has_its_own_space_and_click_target(tmp_path, scale):
    _run(tmp_path, "native", f'''
        from PySide6.QtWidgets import QStyle, QStyleOptionToolButton
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtCore import QTimer
        from molrecognizer.gui.theme import STYLESHEET
        from pathlib import Path
        assert '__CHEVRON_DOWN__' not in STYLESHEET
        if sys.platform == 'win32':
            # Qt's offscreen backend doesn't discover Windows system fonts;
            # without these it measures/draws each character as a square.
            import os
            for name in ('segoeui.ttf', 'seguisb.ttf'):
                assert QFontDatabase.addApplicationFont(str(Path(os.environ['WINDIR']) / 'Fonts' / name)) >= 0
        # Permit the logical 70% used on the high-DPI laptop in this fixture.
        patch.object(window, '_minimum_ui_scale', return_value=.6).start()
        patch.object(window, '_maximum_ui_scale', return_value=2.0).start()
        window._apply_ui_scale({scale})
        window.resize(round(1600 * {scale}), round(1000 * {scale}))
        app.processEvents()
        buttons = [window._editor._toolbar._tool_buttons['bond'],
                   window._editor._toolbar._ring_btn,
                   window._left_panel._xyz_btn, window._left_panel._copy_xyz_btn]
        for index, button in enumerate(buttons):
            option = QStyleOptionToolButton()
            button.initStyleOption(option)
            menu_rect = button.style().subControlRect(QStyle.ComplexControl.CC_ToolButton, option,
                                                      QStyle.SubControl.SC_ToolButtonMenu, button)
            assert menu_rect.width() >= round(22 * {scale}), (button.text(), menu_rect)
            assert button.rect().contains(menu_rect)
            assert menu_rect.left() > option.fontMetrics.horizontalAdvance(button.text()), (button.text(), button.size(), menu_rect)
            # Verify that the SVG chevron, not a native theme glyph, was drawn.
            pixmap = button.grab()
            pixmap.save(str(Path(sys.argv[1]) / f'dropdown-{{index}}.png'))
            image = pixmap.toImage()
            dpr = pixmap.devicePixelRatio()
            ink = 0
            for x in range(round((menu_rect.left()+3) * dpr), round((menu_rect.right()-2) * dpr)):
                for y in range(image.height()):
                    c = image.pixelColor(x,y)
                    # At 70%/1x the thin stroke is antialiased throughout, so
                    # accept its blend with white as well as solid SVG ink.
                    ink += c.red() < 180 and c.blue()-c.red() > 20 and c.green() > c.red()
            assert ink > 0, (button.text(), 'SVG arrow not rendered')
        button = window._left_panel._copy_xyz_btn
        clicked = []
        window._left_panel.copy_xyz.connect(clicked.append)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=QPoint(5,button.height()//2))
        assert clicked == ['angstrom']
        option = QStyleOptionToolButton()
        button.initStyleOption(option)
        arrow = button.style().subControlRect(QStyle.ComplexControl.CC_ToolButton, option,
                                              QStyle.SubControl.SC_ToolButtonMenu, button)
        opened = []
        def choose_bohr():
            opened.append(button.menu().isVisible())
            button.menu().actions()[1].trigger()
            button.menu().close()
        QTimer.singleShot(100, choose_bohr)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=arrow.center())
        assert opened == [True] and clicked == ['angstrom', 'bohr']
        window.close()
    ''')
