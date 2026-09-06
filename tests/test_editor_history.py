"""Eraser and toolbar undo/redo integration without opening a desktop window."""

import os
import subprocess
import sys
import textwrap


def test_eraser_undo_redo_restores_canvas_and_smiles(tmp_path):
    script = '''
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtWidgets import QApplication, QGraphicsSceneMouseEvent
        from molrecognizer.core.smiles import molecule_to_smiles, smiles_to_molecule
        from molrecognizer.gui.editor_widget import EditorWidget

        app = QApplication([])
        editor = EditorWidget()
        mol = smiles_to_molecule('CC(=O)N')
        editor.load_molecule(mol)
        editor._set_tool('eraser')
        scene = editor.canvas.mol_scene
        updates = []
        editor.molecule_changed.connect(lambda: updates.append(molecule_to_smiles(mol)))

        def state():
            atoms = {i: (a.element, a.pos().x(), a.pos().y())
                     for i, a in scene._atom_items.items()}
            bonds = {key: (b.a1_idx, b.a2_idx, b.bond_type)
                     for key, b in scene._bond_items.items()}
            return atoms, bonds, molecule_to_smiles(mol)

        def erase_at(pos):
            event = QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMousePress)
            event.setScenePos(pos)
            event.setButton(Qt.MouseButton.LeftButton)
            editor._current_tool.mouse_press(event)

        original = state()
        # Removing the middle atom deletes three attached bonds and renumbers N.
        erase_at(scene._atom_items[1].pos())
        assert mol.num_atoms == 3 and mol.num_bonds == 0
        deleted = state()
        for _ in range(3):
            editor._toolbar._undo_btn.click()
            assert state() == original
            assert updates[-1] == original[2]
            editor._toolbar._redo_btn.click()
            assert state() == deleted
            assert updates[-1] == deleted[2]

        # Start a new history branch by erasing the original double bond.
        editor._toolbar._undo_btn.click()
        midpoint = (scene._atom_items[1].pos() + scene._atom_items[2].pos()) / 2
        erase_at(midpoint)
        assert mol.num_atoms == 4 and mol.num_bonds == 2
        assert not editor._history.can_redo
        deleted_bond = state()
        editor._toolbar._undo_btn.click()
        assert state() == original
        editor._toolbar._redo_btn.click()
        assert state() == deleted_bond
        assert editor.molecule is mol and editor._history.molecule is mol
        editor.close()
    '''
    result = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(script)],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
