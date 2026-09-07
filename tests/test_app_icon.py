"""App icon frames, window identity and Windows branding startup."""

import ctypes
from unittest.mock import Mock

from PIL import Image
import pytest

from molrecognizer.gui import app_icon
from tests.test_monitor_readability import _run


SIZES = {16, 20, 24, 32, 40, 48, 64, 96, 128, 256}


def test_windows_icon_contains_all_sizes_and_transparent_corners():
    with Image.open(app_icon.ICON_PATH) as icon:
        assert icon.format == "ICO"
        assert icon.ico.sizes() == {(size, size) for size in SIZES}
        for size in SIZES:
            frame = icon.ico.getimage((size, size)).convert("RGBA")
            assert frame.size == (size, size)
            for corner in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)):
                assert frame.getpixel(corner)[3] == 0
            # No white background is baked into the export; the tile interior
            # stays opaque and blue, including between the ring's bond strokes.
            center = frame.getpixel((size // 2, size // 2))
            assert center[3] == 255
            assert center[2] > center[1] > center[0]


def test_png_master_has_alpha_and_matches_approved_palette():
    with Image.open(app_icon.ICON_PATH.with_suffix(".png")) as image:
        assert image.mode == "RGBA" and image.size == (1024, 1024)
        assert image.getpixel((0, 0))[3] == 0
        assert image.getpixel((512, 512)) == (40, 90, 137, 255)
        assert image.getpixel((240, 168)) == (112, 217, 236, 255)
        assert image.getpixel((297, 512)) == (255, 255, 255, 255)


def test_source_and_child_window_use_brand_icon_outside_project_cwd(tmp_path):
    _run(tmp_path, "native", '''
        import os
        from PySide6.QtWidgets import QDialog
        from molrecognizer.gui.app_icon import application_icon
        os.chdir(sys.argv[1])
        icon = application_icon()
        app.setWindowIcon(icon)
        assert not icon.isNull()
        assert len(icon.availableSizes()) == 10
        expected = icon.pixmap(32, 32).toImage()
        assert window.windowIcon().pixmap(32, 32).toImage() == expected
        assert QDialog(window).windowIcon().pixmap(32, 32).toImage() == expected
        window.close()
        app.processEvents()
    ''')


def test_no_windows_identity_calls_on_linux(monkeypatch):
    monkeypatch.setattr(app_icon.sys, "platform", "linux")
    loader = Mock(side_effect=AssertionError("Windows only"))
    monkeypatch.setattr(ctypes, "WinDLL", loader, raising=False)
    app_icon.set_windows_app_id()
    loader.assert_not_called()


def test_stable_windows_app_id(monkeypatch):
    monkeypatch.setattr(app_icon.sys, "platform", "win32")
    function = Mock(return_value=0)
    library = Mock(SetCurrentProcessExplicitAppUserModelID=function)
    monkeypatch.setattr(ctypes, "WinDLL", Mock(return_value=library), raising=False)
    app_icon.set_windows_app_id()
    function.assert_called_once_with("Hengyuan.MolRecognizer.Desktop")
    assert function.argtypes == [ctypes.c_wchar_p]
    assert function.restype == ctypes.c_long


@pytest.mark.parametrize("error", [OSError("unavailable"), AttributeError("unavailable")])
def test_branding_failure_does_not_stop_startup(monkeypatch, error, caplog):
    monkeypatch.setattr(app_icon.sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "WinDLL", Mock(side_effect=error), raising=False)
    app_icon.set_windows_app_id()
    assert "Could not set Windows taskbar identity" in caplog.text


def test_windows_identity_hresult_failure_is_logged(monkeypatch, caplog):
    monkeypatch.setattr(app_icon.sys, "platform", "win32")
    library = Mock(SetCurrentProcessExplicitAppUserModelID=Mock(return_value=-1))
    monkeypatch.setattr(ctypes, "WinDLL", Mock(return_value=library), raising=False)
    app_icon.set_windows_app_id()
    assert "Could not set Windows taskbar identity" in caplog.text
