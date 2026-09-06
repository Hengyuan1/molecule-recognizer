"""Capture transport and recognition integration without reading the desktop."""

import os
import subprocess
import sys
import textwrap


def test_async_capture_transport(tmp_path):
    script = r'''
        import base64
        import io
        import sys
        import time
        from unittest.mock import patch
        from PIL import Image
        from PySide6.QtCore import QTimer
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from molrecognizer.gui.native_capture import NativeRegionCapture

        app = QApplication([])
        stream = io.BytesIO()
        Image.new('RGB', (37, 21), (123, 45, 67)).save(stream, format='PNG')
        png = stream.getvalue()

        def run_output(output, exit_code=0):
            capture = NativeRegionCapture(sys.executable)
            results, ready = [], []
            capture.completed.connect(lambda data, error: results.append((data, error)))
            capture.ready.connect(lambda: ready.append(True))
            # A real asynchronous child process reads the source over stdin and
            # returns fragmented output, like the PowerShell transport.
            command = ('import sys,time; sys.stdin.buffer.read(); '
                       'sys.stdout.buffer.write(b"REA"); sys.stdout.flush(); time.sleep(.03); '
                       'sys.stdout.buffer.write(b"DY\\r\\n"); sys.stdout.flush(); time.sleep(.03); '
                       'sys.stdout.buffer.write(' + repr(output) + '); sys.stdout.flush(); '
                       'sys.exit(' + str(exit_code) + ')')
            # Replace the literal escaped CR/LF with Python escape sequences.
            command = command.replace('\\\\', '\\')
            capture._startup.start(3000)
            capture._process.start(sys.executable, ['-c', command])
            deadline = time.monotonic() + 5
            while not results and time.monotonic() < deadline:
                QTest.qWait(10)
            assert len(results) == 1, results
            assert ready == [True], ready
            assert not capture._startup.isActive()
            return results[0]

        data, error = run_output(b'PNG:' + base64.b64encode(png))
        assert data == png and not error
        assert run_output(b'CANCEL') == (b'', '')
        assert run_output(b'PNG:garbage')[1]
        assert run_output(b'', 1)[1]

        capture = NativeRegionCapture('/nonexistent/molrecognizer-test-executable')
        results = []
        capture.completed.connect(lambda data, error: results.append((data, error)))
        capture.start()
        QTest.qWait(100)
        assert len(results) == 1 and results[0][1]

        # A timed-out startup kills its child; it never leaves a hidden GUI.
        capture = NativeRegionCapture(sys.executable)
        results = []
        capture.completed.connect(lambda data, error: results.append((data, error)))
        capture._process.start(sys.executable, ['-c', 'import sys,time;sys.stdin.read();time.sleep(60)'])
        capture._startup.start(100)
        QTest.qWait(300)
        assert len(results) == 1 and 'did not start' in results[0][1]
    '''
    result = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(script)],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_capture_result_recognition_and_cancel(tmp_path):
    script = '''
        import io
        from unittest.mock import patch
        from PIL import Image
        from PySide6.QtWidgets import QApplication
        from molrecognizer.gui.main_window import MainWindow

        app = QApplication([])
        with patch('molrecognizer.gui.screenshot.is_wsl', return_value=False), \\
             patch.object(MainWindow, '_connect_screen_scaling', lambda self: None):
            window = MainWindow()
        recognized = []
        window._recognize_image = lambda image: recognized.append(image.copy())
        window._screenshot_pending = True
        stream = io.BytesIO()
        Image.new('RGB', (37, 21), (123, 45, 67)).save(stream, format='PNG')
        window._on_native_capture_completed(stream.getvalue(), '')
        assert window.isVisible() and not window._screenshot_pending
        assert recognized[0].size == (37, 21)
        assert recognized[0].getpixel((0, 0))[:3] == (123, 45, 67)
        assert window._source_pixmap.size().width() == 37
        window.hide()
        window._screenshot_pending = True
        window._on_native_capture_completed(b'', '')
        assert window.isVisible() and not window._screenshot_pending
        assert len(recognized) == 1  # Cancel preserves the current structure.
        with patch('molrecognizer.gui.main_window.QMessageBox.warning'):
            window.hide()
            window._on_native_capture_completed(b'', 'Test failure')
            assert window.isVisible()
        window.close()
    '''
    result = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(script)],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_qt_overlay_preserves_high_dpi_pixels(tmp_path):
    script = '''
        from PySide6.QtCore import QPoint, QRect, Qt
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QDialog
        from molrecognizer.gui.screenshot import ScreenshotDialog
        app = QApplication([])
        screen = app.primaryScreen()
        geometry = screen.geometry()
        original = QPixmap(geometry.width() * 2, geometry.height() * 2)
        original.fill(QColor(123, 45, 67))
        original.setDevicePixelRatio(2)
        dialog = ScreenshotDialog(original)
        dialog.show()
        app.processEvents()
        assert dialog.geometry() == geometry
        assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
        QTest.mousePress(dialog, Qt.MouseButton.LeftButton, pos=QPoint(120,120))
        QTest.mouseRelease(dialog, Qt.MouseButton.LeftButton, pos=QPoint(60,60))
        assert dialog._sel == QRect(QPoint(60,60), QPoint(120,120)), dialog._sel
        QTest.mousePress(dialog, Qt.MouseButton.LeftButton, pos=QPoint(90,90))
        QTest.mouseRelease(dialog, Qt.MouseButton.LeftButton, pos=QPoint(-100,-100))
        assert dialog.rect().contains(dialog._sel)
        dialog._sel = QRect(20,30,40,50)
        QTest.keyClick(dialog, Qt.Key.Key_Return)
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert dialog.result_pixmap.width() == 80
        assert dialog.result_pixmap.height() == 100
        assert dialog.result_pixmap.devicePixelRatio() == 1
        assert dialog.result_pixmap.toImage().pixelColor(0,0) == QColor(123,45,67)
        dialog.close()
    '''
    result = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(script)],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
