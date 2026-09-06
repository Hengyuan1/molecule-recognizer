"""Close regressions, using isolated Qt processes and no desktop capture."""

import os
import subprocess
import sys
import textwrap
from threading import Event, Timer
from unittest.mock import patch

import pytest

from molrecognizer.core.recognizer import OSRARecognizer, RecognitionCancelled


_BOOTSTRAP = """
import sys, time
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from molrecognizer.gui.main_window import MainWindow
from molrecognizer.gui.workers import Render3DWorker
from molrecognizer.gui.native_capture import NativeRegionCapture

app = QApplication([])
app.setOrganizationName("shutdown-test")
app.setApplicationName("shutdown-test")
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, sys.argv[1])
patch("molrecognizer.gui.screenshot.is_wsl", return_value=False).start()
patch("molrecognizer.gui.main_window.is_wsl", return_value=True).start()
patch.object(MainWindow, "_connect_screen_scaling", lambda self: None).start()
errors = patch.object(QMessageBox, "critical").start()
warnings = patch.object(QMessageBox, "warning").start()
window = MainWindow()
window.show()
app.processEvents()

def until(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert predicate(), "Timed out waiting for background job"
"""


def _run(tmp_path, script):
    result = subprocess.run(
        [sys.executable, "-c", _BOOTSTRAP + textwrap.dedent(script), str(tmp_path)],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "QThread: Destroyed while thread" not in result.stderr
    assert "QProcess: Destroyed while process" not in result.stderr


@pytest.mark.parametrize("settings_error", [False, True])
def test_idle_close_with_stale_monitor_or_settings_failure(tmp_path, settings_error):
    _run(tmp_path, f"""
        window._scale_screen = Mock()
        window._scale_screen.name.side_effect = RuntimeError("QScreen already deleted")
        window._scale_screen_name = "external"
        window._menu_bar.open_menu(0)
        if {settings_error!r}:
            patch("molrecognizer.gui.main_window.QSettings",
                  side_effect=RuntimeError("Settings unavailable")).start()
        start = time.monotonic()
        assert window.close()
        assert time.monotonic() - start < .5
        assert not window.isVisible()
        assert not window._menu_bar._panel.isVisible()
        assert window._closing
        window._scale_screen.name.assert_not_called()
        assert window.close()  # Idempotent, even if settings are still broken.
        if not {settings_error!r}:
            assert QSettings().value("window_size/external") == window.size()
    """)


def test_pending_capture_and_late_callbacks_cannot_reopen_window(tmp_path):
    _run(tmp_path, """
        capture = patch("molrecognizer.gui.main_window.native_capture_executable").start()
        window._on_screenshot()
        assert window._capture_timer.isActive()
        assert window.close()
        QTest.qWait(400)
        assert not window._capture_timer.isActive()
        capture.assert_not_called()
        window._on_native_capture_completed(b"", "Late capture error")
        window._on_recognition_done(RuntimeError("Late recognition error"))
        window._restore_after_screenshot()
        window._on_screenshot()
        window._on_windows_monitor_detected(("other-monitor", 3000, 2000))
        app.processEvents()
        assert not window.isVisible()
        capture.assert_not_called()
        errors.assert_not_called()
        warnings.assert_not_called()
    """)


def test_title_bar_events_never_get_consumed_by_inline_menu(tmp_path):
    _run(tmp_path, """
        from PySide6.QtCore import QEvent
        bar = window._menu_bar
        bar.open_menu(0)
        bar._eat_release = True  # A mouse release lost to native decorations.
        event = QEvent(QEvent.Type.NonClientAreaMouseButtonPress)
        assert not bar.eventFilter(window.windowHandle(), event)
        assert not bar._eat_release and bar._current is None
        bar.open_menu(0)
        bar._eat_release = True
        assert window.close()
        assert not bar._eat_release and not window.isVisible()
    """)


def test_recognition_close_cancels_child_and_deletes_temporary_image(tmp_path):
    _run(tmp_path, """
        import subprocess
        from molrecognizer.core.recognizer import OSRARecognizer
        original_popen = subprocess.Popen
        children, images = [], []
        def slow_osra(command, **kwargs):
            images.append(Path(command[-1]))
            process = original_popen([sys.executable, '-c',
                                     'import time; time.sleep(60)'], **kwargs)
            children.append(process)
            return process
        patch('molrecognizer.core.recognizer.shutil.which',
              return_value=sys.executable).start()
        patch('molrecognizer.core.recognizer.subprocess.Popen', slow_osra).start()
        window._recognize_image(Image.new('RGB', (30, 30), 'white'))
        until(lambda: bool(children))
        assert images[0].is_file()
        start = time.monotonic()
        window.close()
        window.close()
        assert time.monotonic() - start < .5
        assert not window.isVisible()
        until(lambda: window._worker is None)
        assert children[0].poll() is not None
        assert not images[0].exists()
        errors.assert_not_called()
        window.close()
    """)


def test_render_process_roundtrip_and_error(tmp_path):
    _run(tmp_path, """
        from rdkit import Chem
        from molrecognizer.core.smiles import smiles_to_molecule
        window._set_molecule(smiles_to_molecule('CCO'))
        window._on_render_3d()
        assert window._render_worker is not None
        until(lambda: window._render_worker is None)
        assert window._mol_3d.GetConformer().Is3D()
        assert Chem.MolToSmiles(Chem.RemoveHs(window._mol_3d)) == 'CCO'
        worker = Render3DWorker('not-a-smiles')
        results, finished = [], []
        worker.result_ready.connect(results.append)
        worker.finished.connect(lambda: finished.append(True))
        worker.start()
        until(lambda: bool(finished))
        assert len(results) == 1 and isinstance(results[0], Exception)
        window.close()
    """)


@pytest.mark.parametrize("close_during_startup", [False, True])
def test_close_while_rendering_exits_real_event_loop(tmp_path, close_during_startup):
    _run(tmp_path, f"""
        from molrecognizer.core.smiles import smiles_to_molecule
        patch('molrecognizer.gui.workers._RENDER_3D',
              'import time; time.sleep(60)').start()
        window._set_molecule(smiles_to_molecule('CCO'))
        window._on_render_3d()
        if not {close_during_startup!r}:
            until(lambda: window._render_worker._process.processId() != 0)
        timed_out = []
        watchdog = QTimer()
        watchdog.setSingleShot(True)
        watchdog.timeout.connect(lambda: (timed_out.append(True), app.quit()))
        watchdog.start(3000)
        QTimer.singleShot(0, window.close)
        start = time.monotonic()
        app.exec()
        assert not timed_out, "Closing a busy window must exit after cancellation"
        assert time.monotonic() - start < 2
        assert not window._has_running_jobs()
        assert not window.isVisible()
        assert window._mol_3d is None
    """)


def test_changed_structure_discards_stale_render_result(tmp_path):
    _run(tmp_path, """
        from molrecognizer.core.smiles import smiles_to_molecule
        for clear in (False, True):
            window._set_molecule(smiles_to_molecule('CCO'))
            window._on_render_3d()
            if clear:
                window._on_clear_all()
            else:
                window._set_molecule(smiles_to_molecule('CCC'))
            until(lambda: window._render_worker is None)
            assert window._mol_3d is None
        window.close()
    """)


def test_render_failed_to_start_finishes_cleanly(tmp_path):
    _run(tmp_path, """
        worker = Render3DWorker('CCO')
        results, finished = [], []
        worker.result_ready.connect(results.append)
        worker.finished.connect(lambda: finished.append(True))
        with patch('molrecognizer.gui.workers.sys.executable', '/missing/python'):
            worker.start()
        until(lambda: bool(finished))
        assert len(results) == 1 and isinstance(results[0], Exception)
        assert not worker.isRunning()
        window.close()
    """)


def test_close_cancels_native_capture_without_waiting(tmp_path):
    _run(tmp_path, """
        capture = NativeRegionCapture(sys.executable, window)
        window._native_capture = capture
        results = []
        capture.completed.connect(lambda *args: results.append(args))
        capture.stopped.connect(window._finish_shutdown)
        capture._process.start(sys.executable, ['-c', 'import sys,time; sys.stdin.read(); time.sleep(60)'])
        until(lambda: capture._process.processId() != 0)
        start = time.monotonic()
        window.close()
        assert time.monotonic() - start < .5
        assert not window.isVisible()
        until(lambda: not capture.isRunning())
        assert results == []
        assert window.close()
    """)


def test_osra_cancellation_and_timeout_reap_process():
    cancelled = Event()
    recognizer = OSRARecognizer(executable=sys.executable, cancel_event=cancelled)
    original_popen = subprocess.Popen
    children = []
    def spawn(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        children.append(process)
        return process
    with patch('molrecognizer.core.recognizer.subprocess.Popen', spawn):
        timer = Timer(.15, cancelled.set)
        timer.start()
        try:
            with pytest.raises(RecognitionCancelled):
                recognizer._run_osra([sys.executable, '-c', 'import time; time.sleep(60)'], timeout=10)
        finally:
            timer.cancel()
            timer.join()
        assert len(children) == 1 and children[-1].poll() is not None
        with pytest.raises(RecognitionCancelled):
            recognizer._run_osra([sys.executable], timeout=10)
        assert len(children) == 1  # Pre-cancelled jobs do not start a process.
        cancelled.clear()
        with pytest.raises(subprocess.TimeoutExpired):
            recognizer._run_osra([sys.executable, '-c', 'import time; time.sleep(60)'], timeout=.1)
        assert len(children) == 2 and children[-1].poll() is not None


@pytest.mark.parametrize("as_text", [False, True])
def test_cancellable_osra_preserves_output_across_poll_intervals(as_text):
    recognizer = OSRARecognizer(executable=sys.executable, cancel_event=Event())
    result = recognizer._run_osra([
        sys.executable, '-c',
        "import sys,time; sys.stdout.write('a' * 100000); sys.stdout.flush(); "
        "time.sleep(.2); sys.stderr.write('b' * 100000); "
        "sys.stdout.write('c' * 100000); sys.exit(15)",
    ], timeout=5, text=as_text)
    assert result.returncode == 15
    expected = 'a' * 100000 + 'c' * 100000
    assert result.stdout == (expected if as_text else expected.encode())
    assert result.stderr == ('b' * 100000 if as_text else b'b' * 100000)


def test_hotkey_cleanup_tolerates_helper_exit_race(tmp_path):
    _run(tmp_path, """
        hotkey = window._global_hotkey
        process = Mock()
        process.poll.return_value = None
        process.terminate.side_effect = ProcessLookupError()
        hotkey._process = process
        connection = hotkey._connection = Mock()
        server = hotkey._server = Mock()
        assert window.close()
        connection.close.assert_called_once()
        server.close.assert_called_once()
        hotkey.close()
        process.terminate.assert_called_once()
    """)
