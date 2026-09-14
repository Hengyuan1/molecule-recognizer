"""Metal names are never clipped by native Windows one-line button metrics."""

import pytest

from tests.test_monitor_readability import _run


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("scale", [.7, 1.0, 1.8])
def test_picker_is_light_and_labels_fit_even_with_dark_system_palette(tmp_path, embedded, scale):
    _run(tmp_path, "native", f"""
        from PySide6.QtGui import QColor, QPalette
        from molrecognizer.gui.metal_picker import MetalPickerDialog
        from molrecognizer.gui.metal_picker import COMMON_METAL_CENTERS
        # The Windows offscreen plugin does not discover native fonts by itself.
        if sys.platform == 'win32':
            from PySide6.QtGui import QFontDatabase
            for name in ('segoeui.ttf', 'segoeuib.ttf'):
                assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name) >= 0
        dark = app.palette()
        dark.setColor(QPalette.ColorRole.Window, QColor('#202020'))
        dark.setColor(QPalette.ColorRole.WindowText, QColor('#eeeeee'))
        dark.setColor(QPalette.ColorRole.Button, QColor('#202020'))
        dark.setColor(QPalette.ColorRole.ButtonText, QColor('#eeeeee'))
        app.setPalette(dark)
        patch('molrecognizer.gui.window_placement.is_wsl', return_value={embedded}).start()
        window._ui_scale = {scale}
        window.resize(1500, 1000)
        window._on_common_metal()
        dialog = window._metal_picker
        app.processEvents()
        QTest.qWait(100)
        image = dialog.grab().toImage()
        assert image.pixelColor(2, 2).name() == '#edf2f7'
        for symbol, name in COMMON_METAL_CENTERS:
            button = dialog._buttons[symbol]
            assert button.text() == ''  # No native multiline caption to clip.
            assert button.accessibleName() == f'{{name}} ({{symbol}})'
            for label, expected in ((button.symbol_label, symbol), (button.name_label, name)):
                assert label.text() == expected
                assert button.rect().contains(label.geometry())
                assert label.height() >= label.fontMetrics().height()
                assert label.width() >= label.fontMetrics().horizontalAdvance(expected)
                assert label.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            assert button.name_label.palette().color(QPalette.ColorRole.WindowText).name() == '#243b53'
            assert not button.symbol_label.geometry().intersects(button.name_label.geometry())
            assert button.parentWidget().rect().contains(button.geometry())
        buttons = list(dialog._buttons.values())
        for index, button in enumerate(buttons):
            assert not any(button.geometry().intersects(other.geometry()) for other in buttons[index + 1:]), button.accessibleName()
        from PySide6.QtWidgets import QPushButton
        cancel = dialog.findChild(QPushButton, 'metal_cancel')
        assert cancel.height() >= cancel.fontMetrics().height() + 16
        dialog.grab().save(str(__import__('pathlib').Path(sys.argv[1]) / 'metal-picker.png'))
        dialog._buttons['Pt'].click()
        app.processEvents()
        assert window._editor._current_element == 'Pt'
        window.close()
    """)
