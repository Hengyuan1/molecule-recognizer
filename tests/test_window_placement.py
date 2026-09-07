"""Auxiliary dialogs belong to the main window and open on its monitor."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QRect, QSize

from molrecognizer.gui.window_placement import centered_geometry, owner_screen
from tests.test_canvas_stereo import _run_qt
from tests.test_shutdown import _run


@pytest.mark.parametrize('available, owner', [
    (QRect(2880, 0, 1920, 1040), QRect(3100, 100, 1344, 756)),
    (QRect(-1920, -400, 1920, 1040), QRect(-1800, -300, 1344, 756)),
    (QRect(0, -1080, 1920, 1040), QRect(100, -1000, 1344, 756)),
    (QRect(2880, 0, 1920, 1040), QRect(2600, 900, 1344, 756)),
])
def test_centering_and_work_area_clamping(available, owner):
    target = centered_geometry(owner, QSize(640, 520), available)
    assert available.contains(target)
    assert target.size() == QSize(640, 520)
    if available.contains(owner):
        assert target.center() == owner.center()
    assert centered_geometry(owner, QSize(9000, 5000), available) == available


def test_monitor_selection_uses_majority_not_cursor_or_stale_screen():
    laptop = Mock()
    laptop.geometry.return_value = QRect(0, 0, 2880, 1800)
    external = Mock()
    external.geometry.return_value = QRect(-1920, 0, 1920, 1080)
    owner = Mock()
    owner.screen.return_value = laptop  # screenChanged may arrive late.
    owner.frameGeometry.return_value = QRect(-1000, 100, 1344, 756)
    with patch('molrecognizer.gui.window_placement.QApplication') as app:
        app.screens.return_value = [laptop, external]
        app.platformName.return_value = 'windows'
        assert owner_screen(owner) is external
        app.platformName.return_value = 'wayland'
        assert owner_screen(owner) is laptop  # Do not use fake Wayland globals.


def test_retry_and_double_click_viewer_are_owned_and_centered(tmp_path):
    _run_qt('''
        from unittest.mock import patch
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QPixmap
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
        from molrecognizer.gui.recognition_review import RecognitionReviewDialog
        from molrecognizer.gui.viewer3d import Viewer3DWidget, Viewer3DDialog
        from molrecognizer.gui.window_placement import centered_geometry

        app = QApplication([])
        patch('molrecognizer.gui.window_placement.is_wsl', return_value=False).start()
        owner = QWidget()
        layout = QVBoxLayout(owner)
        viewer = Viewer3DWidget()
        layout.addWidget(viewer)
        owner.resize(700, 650)
        owner.move(60, 70)
        owner.show()
        app.processEvents()
        original = owner.geometry()
        pixmap = QPixmap(30, 30)
        pixmap.fill(Qt.GlobalColor.white)
        review = RecognitionReviewDialog(pixmap, None, owner)
        review.open()
        app.processEvents()
        assert review.parentWidget() is owner
        assert review.windowHandle().transientParent() is owner.windowHandle()
        expected = centered_geometry(owner.frameGeometry(), review.frameGeometry().size(),
                                     owner.screen().availableGeometry())
        assert (review.frameGeometry().center() - expected.center()).manhattanLength() <= 6
        review.reject()
        review.deleteLater()
        QTest.qWait(20)

        viewer.set_molecule([('C', 0, 0, 0), ('N', 1, 0, 0)], [(0, 1, 3)])
        for _ in range(2):
            # This returns without a nested exec() event loop.
            QTest.mouseDClick(viewer, Qt.MouseButton.LeftButton)
            QTest.qWait(20)
            dialogs = owner.findChildren(Viewer3DDialog)
            assert len(dialogs) == 1
            dialog = dialogs[0]
            assert dialog.isVisible() and dialog.parentWidget() is owner
            assert dialog.windowHandle().transientParent() is owner.windowHandle()
            expected = centered_geometry(owner.frameGeometry(), dialog.frameGeometry().size(),
                                         owner.screen().availableGeometry())
            assert (dialog.frameGeometry().center() - expected.center()).manhattanLength() <= 6
            assert dialog._viewer._atoms == viewer._atoms
            # No persistent positioning timer fights the user's subsequent move.
            dialog.move(5, 5)
            QTest.qWait(30)
            assert dialog.pos() == QPoint(5, 5)
            dialog.close()
            QTest.qWait(20)
            assert not owner.findChildren(Viewer3DDialog)
        assert owner.geometry() == original
        owner.close()
    ''', tmp_path)


# Shared with the real WSLg smoke check: these operations must leave the one
# native main-window surface enabled, interactive and unchanged after closing.
WSL_PANEL_STRESS = '''
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QShortcutEvent, QKeySequence
from PySide6.QtWidgets import QFrame, QPushButton, QWidget
from molrecognizer.core.recognizer import OSRARecognizer
from molrecognizer.core.smiles import smiles_to_molecule
from molrecognizer.editor.history import ChangeElementCommand
from molrecognizer.gui.viewer3d import Viewer3DDialog
from molrecognizer.gui.window_placement import OwnerDialog
from tests.test_recognition_retry import _source
from tests.test_history import _molecular_state

patch('molrecognizer.gui.window_placement.is_wsl', return_value=True).start()
patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra').start()
patch.object(OSRARecognizer, '_read_sdf', side_effect=lambda *a, **k: _source()).start()
window.setWindowTitle('Panel regression test (temporary)')
window._apply_ui_scale(0.8)
window.resize(1344, 756)
window._set_molecule(smiles_to_molecule('CCO'))
window._recognition_image = Image.new('RGB', (400, 300), 'white')
window._editor._history.execute(ChangeElementCommand(2, 'N'))
window.activateWindow()
QTest.qWait(50)
original_geometry = window.geometry()
native = window.windowHandle()
ticks = []
heartbeat = QTimer()
heartbeat.timeout.connect(lambda: ticks.append(True))
heartbeat.start(10)

for mode in ['apply', 'keep', 'escape', 'close'] * 3:
    before = _molecular_state(window._molecule)
    window._on_retry_recognition()
    dialog = window._retry_dialog
    until(lambda: window._retry_worker is None)
    assert dialog._embedded and dialog.isVisible()
    assert not dialog.isWindow() and dialog.windowHandle() is None
    assert not dialog._panel_host.isWindow() and dialog._panel_host.windowHandle() is None
    assert dialog.windowModality() == Qt.WindowModality.NonModal
    assert QApplication.activeModalWidget() is None
    assert dialog._panel_host.geometry() == window.centralWidget().rect()
    assert window.windowHandle() is native and window.isEnabled()
    assert window.geometry() == original_geometry
    for direction in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
        for _ in range(10):
            QTest.keyClick(QApplication.focusWidget() or dialog, direction)
            assert dialog._panel_host.isAncestorOf(QApplication.focusWidget())
    # Shortcuts must not edit the hidden main canvas while reviewing.
    undo = window._menu_actions['Undo']
    QApplication.sendEvent(undo, QShortcutEvent(QKeySequence('Ctrl+Z'), 0))
    assert _molecular_state(window._molecule) == before
    # A title-bar close is deliberately NOT intercepted by the input guard.
    assert not dialog.eventFilter(window, QEvent(QEvent.Type.Close))
    assert not dialog.eventFilter(native, QEvent(QEvent.Type.NonClientAreaMouseButtonPress))
    if mode == 'apply':
        dialog._choices.setCurrentRow(1)
        selected = _molecular_state(dialog.selected_candidate.molecule)
        QTest.mouseClick(dialog._use, Qt.MouseButton.LeftButton)
        assert _molecular_state(window._molecule) == selected
        window._editor._undo()
        assert _molecular_state(window._molecule) == before
    elif mode == 'keep':
        dialog.reject()
    elif mode == 'escape':
        QTest.keyClick(dialog._smiles, Qt.Key.Key_Escape)
    else:
        close = next(b for b in dialog._panel_host.findChildren(QPushButton) if b.text() == 'Close')
        QTest.mouseClick(close, Qt.MouseButton.LeftButton)
    assert window._retry_dialog is None
    assert not dialog._panel_host.isVisible()
    assert _molecular_state(window._molecule) == before
    until(lambda: not window.findChildren(QFrame, 'owner_dialog_panel'))
    assert window.geometry() == original_geometry and window.windowHandle() is native
    assert window.isEnabled() and window.isVisible()
    # Exercise the main-window keyboard path again after the panel is gone.
    window._editor._history.execute(ChangeElementCommand(2, 'O'))
    QApplication.sendEvent(undo, QShortcutEvent(QKeySequence('Ctrl+Z'), 0))
    assert _molecular_state(window._molecule) == before

viewer = window._left_panel._viewer_3d
viewer.set_molecule([('C', 0, 0, 0), ('N', 1, 0, 0)], [(0, 1, 3)])
for mode in ['escape', 'close'] * 3:
    QTest.mouseDClick(viewer, Qt.MouseButton.LeftButton)
    QTest.qWait(20)
    panel = window._comparison_panel
    assert panel.isVisible() and not panel.isWindow() and panel.windowHandle() is None
    assert window._editor.isVisible() and not window.findChildren(Viewer3DDialog)
    if mode == 'escape':
        QTest.keyClick(panel._viewer, Qt.Key.Key_Escape)
    else:
        QTest.mouseClick(panel._close, Qt.MouseButton.LeftButton)
    until(panel.isHidden)
    assert not window.findChildren(QFrame, 'owner_dialog_panel')
    assert window.geometry() == original_geometry and window.windowHandle() is native
assert len(ticks) > 20, 'The GUI heartbeat must continue during all panel operations'
assert not any(w.isVisible() and w is not window for w in QApplication.topLevelWidgets())
window.close()
assert not window.isVisible()
'''


def test_wsl_retry_and_xyz_repeated_open_close_keep_one_responsive_surface(tmp_path):
    _run(tmp_path, WSL_PANEL_STRESS)


def test_wsl_panel_tracks_owner_resize_and_idle_main_close(tmp_path):
    _run(tmp_path, '''
        from PySide6.QtGui import QPixmap
        from molrecognizer.gui.recognition_review import RecognitionReviewDialog
        from molrecognizer.gui.viewer3d import Viewer3DDialog
        patch('molrecognizer.gui.window_placement.is_wsl', return_value=True).start()
        window._apply_ui_scale(.8)
        window.resize(1344, 756)
        app.processEvents()
        original_minimum = window.minimumSizeHint()
        source = QPixmap(100, 100)
        source.fill(Qt.GlobalColor.white)
        dialog = RecognitionReviewDialog(source, None, window)
        dialog.open()
        app.processEvents()
        assert window.minimumSizeHint() == original_minimum
        for scale, width, height in [(1.8, 2304, 1440), (.8, 1344, 756)] * 2:
            window._apply_ui_scale(scale)
            window.resize(width, height)
            app.processEvents()
            assert dialog._panel_host.geometry() == window.centralWidget().rect()
            assert dialog._panel_host.font().pointSizeF() == window.centralWidget().font().pointSizeF()
            assert dialog.font().pointSizeF() == window.centralWidget().font().pointSizeF()
            assert dialog.windowHandle() is None
            assert window.width() == width and window.height() == height
        dialog.reject()
        dialog.deleteLater()
        QTest.qWait(20)
        # Closing the main window with an idle 3D panel must work too.
        viewer = Viewer3DDialog([('C', 0, 0, 0)], [], parent=window)
        viewer.open()
        app.processEvents()
        assert viewer.isVisible() and viewer.windowHandle() is None
        assert window.close()
        assert not window.isVisible() and not viewer.isVisible()
    ''')
