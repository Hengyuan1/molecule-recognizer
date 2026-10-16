"""Editing changes the drawing, not the user's zoom or pan position."""

import pytest

from tests.test_canvas_stereo import _run_qt
from tests.test_shutdown import _run as _run_window


@pytest.mark.parametrize('zoom', [.35, 1.8, 2.6])
def test_edits_and_history_preserve_view_even_when_scene_grows(tmp_path, zoom):
    _run_qt('''
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QApplication
        from molrecognizer.core.molecule import BondType
        from molrecognizer.core.smiles import smiles_to_molecule
        from molrecognizer.editor.history import (
            AddAtomCommand, AddBondCommand, BulkDeleteCommand,
            ChangeBondTypeCommand, ChangeElementCommand, MoveAtomCommand,
            RemoveAtomCommand, RemoveBondCommand,
        )
        from molrecognizer.gui.editor_widget import EditorWidget

        app = QApplication([])
        editor = EditorWidget()
        editor.resize(1000, 700)
        editor.show()
        editor.load_molecule(smiles_to_molecule('CC(=O)N'))
        app.processEvents()
        canvas = editor.canvas
        canvas.scale(ZOOM, ZOOM)
        canvas.centerOn(QPointF(170, -85))
        app.processEvents()
        transform = canvas.transform()
        # Sample scene points, including a point outside the molecule. This
        # detects panning/recentering as well as a reset zoom factor.
        points = [QPointF(0, 0), QPointF(50, -70), QPointF(-80, 130)]
        pixels = [canvas.viewportTransform().map(p) for p in points]

        def assert_view_unchanged():
            app.processEvents()
            assert canvas.transform() == transform, 'Editing reset the zoom'
            for point, pixel in zip(points, pixels):
                current = canvas.viewportTransform().map(point)
                assert abs(current.x() - pixel.x()) < 1, (current, pixel)
                assert abs(current.y() - pixel.y()) < 1, (current, pixel)

        commands = [
            AddAtomCommand('O', 3, -2),
            AddBondCommand(3, 4, BondType.SINGLE),
            RemoveBondCommand(3, 4),
            RemoveAtomCommand(4),
            ChangeElementCommand(3, 'O'),
            ChangeBondTypeCommand(1, 2, BondType.SINGLE),
            MoveAtomCommand(0, *editor.molecule.get_2d_coords()[0], 4, 3),
            # Grow the scrollable area in both directions without panning.
            AddAtomCommand('C', -60, 40),
            AddAtomCommand('C', 60, -40),
            # Deleting all atoms must not reset the working view either.
            BulkDeleteCommand(range(6)),
        ]
        for command in commands:
            editor._history.execute(command)
            assert_view_unchanged()
            # Repeated history redraws must not accumulate rounding drift.
            for _ in range(3):
                editor._undo()
                assert_view_unchanged()
                editor._redo()
                assert_view_unchanged()
        editor._history.execute(AddAtomCommand('N', 0, 0))
        assert_view_unchanged()
        editor.close()
    '''.replace('ZOOM', repr(zoom)), tmp_path)


def test_new_structure_still_resets_view_and_first_atom_stays_at_click(tmp_path):
    _run_qt('''
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from molrecognizer.core.molecule import Molecule
        from molrecognizer.core.smiles import smiles_to_molecule
        from molrecognizer.gui.editor_widget import EditorWidget

        app = QApplication([])
        editor = EditorWidget()
        editor.resize(1000, 700)
        editor.show()
        editor.load_molecule(Molecule())
        canvas = editor.canvas
        canvas.scale(2.0, 2.0)
        editor._set_tool('atom')
        app.processEvents()
        position = canvas.viewport().rect().center() + QPoint(90, -70)
        QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=position)
        app.processEvents()
        assert editor.molecule.num_atoms == 1
        assert canvas.transform().m11() == 2.0
        atom = canvas.mol_scene._atom_items[0]
        assert (canvas.mapFromScene(atom.pos()) - position).manhattanLength() <= 1

        editor.load_molecule(smiles_to_molecule('c1ccccc1'))
        app.processEvents()
        assert canvas.transform().isIdentity()
        center = canvas.mapFromScene(canvas.mol_scene.itemsBoundingRect().center())
        assert (center - canvas.viewport().rect().center()).manhattanLength() <= 2
        editor.close()
    ''', tmp_path)


def test_manual_zoom_pan_and_fit_keep_working(tmp_path):
    _run_window(tmp_path, '''
        from PySide6.QtCore import QPoint, QPointF
        from PySide6.QtGui import QWheelEvent
        from molrecognizer.core.smiles import smiles_to_molecule
        from molrecognizer.editor.history import AddAtomCommand

        window._set_molecule(smiles_to_molecule('CC(=O)N'))
        canvas = window._editor.canvas
        QTest.qWait(180)
        window._menu_actions['Fit structure'].trigger()
        QTest.qWait(180)
        fitted = canvas.transform().m11()
        position = canvas.viewport().rect().center()
        wheel = QWheelEvent(
            QPointF(position), QPointF(canvas.viewport().mapToGlobal(position)),
            QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(canvas.viewport(), wheel)
        assert abs(canvas.transform().m11() - fitted * 1.15) < 1e-9

        before_pan = canvas.mapToScene(0, 0)
        QTest.mousePress(canvas.viewport(), Qt.MouseButton.RightButton, pos=position)
        QTest.mouseMove(canvas.viewport(), position + QPoint(60, 30))
        QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.RightButton,
                           pos=position + QPoint(60, 30))
        app.processEvents()
        assert canvas.mapToScene(0, 0) != before_pan

        def camera():
            return canvas.transform(), canvas.viewportTransform().map(QPointF(0, 0))

        before_edit = camera()
        window._editor._history.execute(AddAtomCommand('O', 5, 3))
        QTest.qWait(180)
        assert camera() == before_edit
        window._menu_actions['Undo'].trigger()
        QTest.qWait(30)
        assert camera() == before_edit

        window._menu_actions['Fit structure'].trigger()
        app.processEvents()
        assert canvas.transform() != before_edit[0]
        drawing = canvas.mapFromScene(canvas.mol_scene.itemsBoundingRect()).boundingRect()
        assert canvas.viewport().rect().contains(drawing)

        window.close()
    ''')
