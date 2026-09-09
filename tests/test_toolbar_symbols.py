"""Chemistry tool symbols stay legible without platform-specific font glyphs."""

import pytest

from tests.test_monitor_readability import _run


@pytest.mark.parametrize("scale", [0.7, 0.8, 1.0, 1.8])
def test_large_symbols_follow_ui_scale_and_keep_tool_behavior(tmp_path, scale):
    _run(tmp_path, "native", f'''
        from pathlib import Path
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QStyle, QStyleOptionToolButton
        from molrecognizer.gui.toolbar import RING_TYPES
        patch.object(window, '_minimum_ui_scale', return_value=.6).start()
        patch.object(window, '_maximum_ui_scale', return_value=2.0).start()
        window._apply_ui_scale({scale})
        window.resize(round(1600 * {scale}), round(1000 * {scale}))
        app.processEvents()
        toolbar = window._editor._toolbar
        size = round(24 * {scale})
        assert toolbar._tool_buttons['bond'].iconSize() == QSize(round(20 * {scale}), round(20 * {scale}))

        def check_symbol(button):
            assert button.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
            assert button.accessibleName() == button.text()
            assert button.toolTip()
            assert button.iconSize() == QSize(size, size)
            assert not button.icon().isNull()
            assert button.width() >= size and button.height() >= size
            # Check actual painted coverage, not just a large empty icon box.
            image = button.icon().pixmap(QSize(size, size), QIcon.Mode.Normal).toImage()
            ink = [(x, y) for x in range(image.width()) for y in range(image.height())
                   if image.pixelColor(x, y).alpha() > 100]
            assert ink
            xs, ys = zip(*ink)
            assert max(xs) - min(xs) + 1 >= image.width() * .7
            assert max(ys) - min(ys) + 1 >= image.height() * .7

        for key in ('ring', 'charge+', 'charge-'):
            check_symbol(toolbar._tool_buttons[key])

        charges, rings, tools = [], [], []
        toolbar.charge_tool_requested.connect(charges.append)
        toolbar.ring_type_changed.connect(rings.append)
        toolbar.tool_changed.connect(tools.append)
        toolbar._tool_buttons['charge+'].click()
        toolbar._tool_buttons['charge-'].click()
        assert charges == [1, -1]
        assert toolbar._tool_buttons['charge-'].isChecked()
        assert not toolbar._tool_buttons['charge+'].isChecked()

        icons = []
        for action, (label, key, _, _) in zip(toolbar._ring_btn.menu().actions(), RING_TYPES):
            assert action.text() == label
            action.trigger()
            assert rings[-1] == key and tools[-1] == 'ring'
            assert toolbar._ring_btn.isChecked()
            assert not toolbar._tool_buttons['charge-'].isChecked()
            assert toolbar._ring_btn.text() == label
            assert toolbar._ring_btn.icon().cacheKey() == action.icon().cacheKey()
            check_symbol(toolbar._ring_btn)
            icons.append(toolbar._ring_btn.icon().pixmap(QSize(24,24)).toImage())
        assert all(a != b for i, a in enumerate(icons) for b in icons[i+1:])

        # Clicking the ring face must use the selected ring, not open a menu.
        toolbar._ring_btn.click()
        assert tools[-1] == 'ring' and not toolbar._ring_btn.menu().isVisible()
        option = QStyleOptionToolButton()
        toolbar._ring_btn.initStyleOption(option)
        arrow = toolbar._ring_btn.style().subControlRect(QStyle.ComplexControl.CC_ToolButton,
                option, QStyle.SubControl.SC_ToolButtonMenu, toolbar._ring_btn)
        assert arrow.left() > size and toolbar._ring_btn.rect().contains(arrow)
        toolbar._ring_btn.menu().actions()[0].trigger()
        toolbar.grab().save(str(Path(sys.argv[1]) / 'toolbar.png'))
        window.close()
    ''')
