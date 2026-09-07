"""The 3D comparison must leave the 2D canvas usable, without extra windows."""

import pytest

from tests.test_shutdown import _run
from tests.test_monitor_readability import _run as _run_scaled


COMPARISON_CHECK = '''
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QShortcutEvent, QKeySequence, QWheelEvent
from molrecognizer.core.smiles import smiles_to_molecule
from molrecognizer.core.xyz import generate_3d
from molrecognizer.editor.history import ChangeElementCommand
from molrecognizer.gui.viewer3d import Viewer3DDialog, Viewer3DPanel
from tests.test_history import _molecular_state

window.setWindowTitle('3D comparison check (temporary)')
window._apply_ui_scale(.8)
window.resize(1344, 756)
window.activateWindow()
app.processEvents()
original_geometry = window.geometry()
native = window.windowHandle()
canvas = window._editor.canvas
full_width = canvas.width()
source = window._left_panel._viewer_3d
panel = window._comparison_panel

# No 3D data means there is nothing to expand.
QTest.mouseDClick(source, Qt.MouseButton.LeftButton)
assert panel.isHidden()
window._set_molecule(smiles_to_molecule('CCO'))
window._render_smiles = window._bottom_bar.smiles_text
window._on_render_done(generate_3d(window._render_smiles))
assert source._atoms
state = _molecular_state(window._molecule)
source._pitch, source._yaw = .3, .7
QTest.mouseDClick(source, Qt.MouseButton.LeftButton)
QTest.qWait(50)
assert panel.isVisible() and window._editor.isVisible()
assert panel._viewer._atoms == source._atoms
assert (panel._viewer._pitch, panel._viewer._yaw) == (.3, .7)
assert panel.windowHandle() is None and not panel.isWindow()
assert window.windowHandle() is native and window.geometry() == original_geometry
assert not window.findChildren(Viewer3DDialog)
assert len(window.findChildren(Viewer3DPanel)) == 1
assert window._bottom_bar.isVisible() and not panel._status.isVisible()
assert canvas.width() < full_width and canvas.width() > 200 and panel.width() > 200
editor_right = window._editor.mapTo(window, QPoint(window._editor.width(), 0)).x()
panel_left = panel.mapTo(window, QPoint(0, 0)).x()
assert editor_right <= panel_left  # Adjacent, never an overlay over the 2D drawing.
assert _molecular_state(window._molecule) == state

# 3D mouse input remains live without affecting the 2D graph.
view = panel._viewer
center = view.rect().center()
QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=center)
QTest.mouseMove(view, center + QPoint(35, 25))
QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=center + QPoint(35, 25))
assert (view._pitch, view._yaw) != (.3, .7)
old_pan = (view._pan_x, view._pan_y)
QTest.mousePress(view, Qt.MouseButton.RightButton, pos=center)
QTest.mouseMove(view, center + QPoint(20, 10))
QTest.mouseRelease(view, Qt.MouseButton.RightButton, pos=center + QPoint(20, 10))
assert (view._pan_x, view._pan_y) != old_pan
zoom = view._zoom
wheel = QWheelEvent(QPointF(center), QPointF(view.mapToGlobal(center)), QPoint(), QPoint(0, 120),
                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                    Qt.ScrollPhase.NoScrollPhase, False)
QApplication.sendEvent(view, wheel)
assert view._zoom > zoom
assert _molecular_state(window._molecule) == state

# Reopening an already visible comparison must not reset its camera or split.
split = window._comparison_splitter
split.setSizes([650, 300])
app.processEvents()
split_sizes = split.sizes()
camera = (view._pitch, view._yaw, view._zoom)
QTest.mouseDClick(source, Qt.MouseButton.LeftButton)
assert split.sizes() == split_sizes
assert (view._pitch, view._yaw, view._zoom) == camera

# Main-window editing and Undo remain enabled while comparing. Flag old 3D
# data until an actual successful render of the changed structure arrives.
atoms = list(view._atoms)
window._editor._history.execute(ChangeElementCommand(2, 'N'))
assert panel._status.isVisible() and 'Render' in panel._status.text()
assert view._atoms == atoms
undo = window._menu_actions['Undo']
QApplication.sendEvent(undo, QShortcutEvent(QKeySequence('Ctrl+Z'), 0))
assert _molecular_state(window._molecule) == state and not panel._status.isVisible()
window._editor._history.execute(ChangeElementCommand(2, 'N'))
window._render_smiles = window._bottom_bar.smiles_text
window._on_render_done(RuntimeError('Test render failure'))
assert panel._status.isVisible() and view._atoms == atoms
window._on_render_done(generate_3d(window._render_smiles))
assert not panel._status.isVisible()
assert view._atoms == source._atoms and view._atoms != atoms

QTest.mouseClick(panel._close, Qt.MouseButton.LeftButton)
QTest.qWait(50)
assert panel.isHidden() and canvas.width() == full_width
assert window.geometry() == original_geometry and window.windowHandle() is native
QTest.mouseDClick(source, Qt.MouseButton.LeftButton)
QTest.qWait(20)
assert split.sizes() == split_sizes
QTest.keyClick(view, Qt.Key.Key_Escape)
assert panel.isHidden()
QTest.mouseDClick(source, Qt.MouseButton.LeftButton)
window._on_clear_all()
assert panel.isHidden() and not view._atoms and not source._atoms
assert window._rendered_smiles is None
window.close()
'''


def test_side_by_side_comparison_and_render_refresh(tmp_path):
    _run(tmp_path, COMPARISON_CHECK)


@pytest.mark.parametrize('platform', ['wsl', 'native'])
def test_comparison_does_not_enlarge_mixed_dpi_window(tmp_path, platform):
    _run_scaled(tmp_path, platform, '''
        from molrecognizer.core.smiles import smiles_to_molecule
        window._set_molecule(smiles_to_molecule('c1ccccc1'))
        source = window._left_panel._viewer_3d
        source.set_molecule([('C', 0, 0, 0), ('C', 1, 1, 1)], [(0, 1)])
        for name, width, height in [('external', 1920, 1080), ('laptop', 2880, 1800)] * 2:
            window._on_windows_monitor_detected((name, width, height))
            app.processEvents()
            before = window.geometry()
            window._show_3d_comparison()
            app.processEvents()
            assert window._comparison_panel.isVisible()
            assert window._editor.isVisible()
            assert window.geometry() == before
            assert window._comparison_panel._viewer.width() >= 160
            assert window._editor.canvas.width() >= 200
            assert window._comparison_panel.windowHandle() is None
            panel = window._comparison_panel
            assert panel.grab().toImage().pixelColor(1, 1).name() == '#285987'
            assert panel._viewer.grab().toImage().pixelColor(20, 20).name() == '#ffffff'
        window._hide_3d_comparison()
        window.close()
    ''')


def test_retry_overlay_and_idle_close_work_with_comparison_open(tmp_path):
    _run(tmp_path, '''
        from molrecognizer.core.smiles import smiles_to_molecule
        from molrecognizer.core.recognizer import OSRARecognizer
        from tests.test_recognition_retry import _source
        patch('molrecognizer.gui.window_placement.is_wsl', return_value=True).start()
        patch('molrecognizer.core.recognizer.shutil.which', return_value=sys.executable).start()
        patch.object(OSRARecognizer, '_read_sdf', side_effect=lambda *a, **k: _source()).start()
        window._set_molecule(smiles_to_molecule('CCO'))
        source = window._left_panel._viewer_3d
        source.set_molecule([('C', 0, 0, 0), ('O', 1, 1, 1)], [(0, 1)])
        window._show_3d_comparison()
        window._recognition_image = Image.new('RGB', (100, 100), 'white')
        for accept in [False, True]:
            window._on_retry_recognition()
            until(lambda: window._retry_worker is None)
            dialog = window._retry_dialog
            if accept:
                dialog._choices.setCurrentRow(1)
                dialog._use.click()
                assert window._comparison_panel.isHidden()
                assert not window._comparison_panel._viewer._atoms
            else:
                dialog.reject()
                assert window._comparison_panel.isVisible()
        source.set_molecule([('C', 0, 0, 0)], [])
        window._show_3d_comparison()
        assert window.close()
        assert not window.isVisible()
    ''')
