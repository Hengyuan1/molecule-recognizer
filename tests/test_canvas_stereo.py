"""Stereo depiction and mouse-coordinate regression tests (headless Qt)."""

import os
import subprocess
import sys
import textwrap


def _run_qt(script, tmp_path):
    result = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(script), str(tmp_path)],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'XDG_CONFIG_HOME': str(tmp_path)},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_recognized_stereo_is_drawn_without_mirroring(tmp_path):
    _run_qt('''
        import sys
        from pathlib import Path
        from subprocess import CompletedProcess
        from unittest.mock import patch
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QApplication
        from rdkit import Chem
        from rdkit.Chem import AllChem
        from molrecognizer.core.molecule import BondType
        from molrecognizer.core.recognizer import OSRARecognizer
        from molrecognizer.core.smiles import molecule_to_smiles
        from molrecognizer.editor.canvas import SCALE
        from molrecognizer.editor.history import RemoveAtomCommand
        from molrecognizer.gui.editor_widget import EditorWidget

        app = QApplication([])
        editor = EditorWidget()
        path = Path(sys.argv[1]) / 'stereo.png'
        path.write_bytes(b'image')
        drawn_types = set()
        for smiles in ['C[C@H](O)F', 'C[C@@H](O)F']:
            source = Chem.MolFromSmiles(smiles)
            AllChem.Compute2DCoords(source)
            Chem.WedgeBond(source.GetBondBetweenAtoms(1, 3), 1, source.GetConformer())
            sdf = (Chem.MolToMolBlock(source) + '\\n$$$$\\n').encode()
            with patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra'), \\
                 patch('molrecognizer.core.recognizer.subprocess.run',
                       return_value=CompletedProcess([], 0, sdf, b'')):
                mol = OSRARecognizer().recognize(path)
            editor.load_molecule(mol)
            scene = editor.canvas.mol_scene
            for repeat in range(2):
                for idx, (x, y) in enumerate(mol.get_2d_coords()):
                    # Chemistry Y is up; Qt Y is down. Do not mirror chirality.
                    assert scene._atom_items[idx].pos() == QPointF(x * SCALE, -y * SCALE)
                bond = scene.get_bond_item(1, 3)
                assert bond.a1_idx == 1  # Narrow end stays at the stereocenter.
                drawn_types.add(bond.bond_type)
                if bond.bond_type == BondType.WEDGE:
                    assert len(bond._extra_polys) == 1
                    assert bond._extra_polys[0].polygon()[0] == bond.line().p1()
                else:
                    assert bond.bond_type == BondType.DASH
                    assert len(bond._extra_lines) == 7
                    lengths = [line.line().length() for line in bond._extra_lines]
                    assert lengths == sorted(lengths)  # Dashes widen away from center.
                assert molecule_to_smiles(mol) == Chem.MolToSmiles(Chem.MolFromSmiles(smiles))
                if repeat == 0:
                    editor._history.execute(RemoveAtomCommand(1))
                    editor._toolbar._undo_btn.click()
        assert drawn_types == {BondType.WEDGE, BondType.DASH}
        editor.close()
    ''', tmp_path)


def test_editing_tools_follow_screen_coordinates(tmp_path):
    _run_qt('''
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtWidgets import QApplication, QGraphicsSceneMouseEvent
        from molrecognizer.core.molecule import Molecule
        from molrecognizer.editor.canvas import SCALE
        from molrecognizer.gui.editor_widget import EditorWidget

        app = QApplication([])
        editor = EditorWidget()
        mol = Molecule()
        scene = editor.canvas.mol_scene
        editor.load_molecule(mol)

        def mouse(kind, pos):
            event = QGraphicsSceneMouseEvent(kind)
            event.setScenePos(pos)
            event.setButton(Qt.MouseButton.LeftButton)
            event.setButtons(Qt.MouseButton.LeftButton)
            method = {QEvent.Type.GraphicsSceneMousePress: 'mouse_press',
                      QEvent.Type.GraphicsSceneMouseMove: 'mouse_move',
                      QEvent.Type.GraphicsSceneMouseRelease: 'mouse_release'}[kind]
            getattr(editor._current_tool, method)(event)

        press = QEvent.Type.GraphicsSceneMousePress
        move = QEvent.Type.GraphicsSceneMouseMove
        release = QEvent.Type.GraphicsSceneMouseRelease

        # Empty-canvas atom placement and bond dragging use the inverse transform.
        editor._set_tool('atom')
        first = QPointF(40, 80)
        mouse(press, first)
        assert scene._atom_items[0].pos() == first
        assert mol.get_2d_coords()[0] == (1, -2)
        editor._set_tool('bond')
        end = QPointF(120, 160)
        mouse(press, first)
        mouse(move, end)
        mouse(release, end)
        assert scene._atom_items[1].pos() == end
        assert mol.get_2d_coords()[1] == (3, -4)

        # A single-atom drag must not jump on release or after Undo/Redo.
        editor._set_tool('select')
        target = end + QPointF(40, -80)
        mouse(press, end)
        mouse(move, target)
        assert scene._atom_items[1].pos() == target
        mouse(release, target)
        assert scene._atom_items[1].pos() == target
        assert mol.get_2d_coords()[1] == (4, -2)
        editor._toolbar._undo_btn.click()
        assert scene._atom_items[1].pos() == end
        editor._toolbar._redo_btn.click()
        assert scene._atom_items[1].pos() == target

        # Group-drag preview and committed positions must agree.
        tool = editor._current_tool
        tool._selected = {0, 1}
        tool._highlight_selection()
        before = [QPointF(scene._atom_items[i].pos()) for i in range(2)]
        delta = QPointF(40, 60)
        mouse(press, before[0])
        mouse(move, before[0] + delta)
        for i in range(2):
            assert scene._atom_items[i].pos() == before[i] + delta
        mouse(release, before[0] + delta)
        for i in range(2):
            assert scene._atom_items[i].pos() == before[i] + delta

        # Ring previews and drag direction must use the same coordinate mapping.
        editor.load_molecule(Molecule())
        editor._set_tool('atom')
        anchor = QPointF(-80, -40)
        mouse(press, anchor)
        editor._set_tool('ring')
        mouse(press, anchor)
        mouse(move, anchor + QPointF(0, -120))
        ghost = editor._current_tool._ghost_items
        preview = [QPointF(ghost[i].line().p1()) for i in range(0, len(ghost), 2)]
        assert min(p.y() for p in preview) < anchor.y()
        assert max(p.y() for p in preview) <= anchor.y() + 1e-8
        mouse(release, anchor + QPointF(0, -120))
        for i, p in enumerate(preview):
            assert (scene._atom_items[i].pos() - p).manhattanLength() < 1e-8

        editor.load_molecule(Molecule())
        editor._set_tool('ring')
        mouse(press, QPointF(100, 200))
        assert (scene._atom_items[0].pos() - QPointF(100, 200)).manhattanLength() < 1e-8
        assert abs(editor.molecule.get_2d_coords()[0][1] + 200 / SCALE) < 1e-8
        editor.close()
    ''', tmp_path)


def test_format_button_preserves_stereo_and_is_one_undo_step(tmp_path):
    _run_qt('''
        from unittest.mock import patch
        from PySide6.QtWidgets import QApplication
        from molrecognizer.core.molecule import Molecule
        from molrecognizer.core.smiles import molecule_to_smiles
        from molrecognizer.gui.editor_widget import EditorWidget
        from tests.test_history import _molecular_state
        from tests.test_label_recovery import recovered_mol

        app = QApplication([])
        editor = EditorWidget()
        mol = Molecule.from_rdkit(recovered_mol())
        editor.load_molecule(mol)
        before = _molecular_state(mol)
        smiles = molecule_to_smiles(mol)
        updates = []
        editor.molecule_changed.connect(lambda: updates.append(molecule_to_smiles(mol)))
        editor._toolbar._format_btn.click()
        assert updates == [smiles]
        formatted = _molecular_state(mol)
        assert formatted != before
        editor._toolbar._undo_btn.click()
        assert _molecular_state(mol) == before
        assert not editor._history.can_undo
        editor._toolbar._redo_btn.click()
        assert _molecular_state(mol) == formatted
        assert updates == [smiles, smiles, smiles]
        assert len(editor.canvas.mol_scene._bond_items) == mol.num_bonds

        with patch('molrecognizer.core.layout.format_2d', side_effect=ValueError('failed')), \\
             patch('molrecognizer.gui.editor_widget.QMessageBox.warning') as warning:
            editor._toolbar._format_btn.click()
        warning.assert_called_once()
        assert _molecular_state(mol) == formatted
        assert updates == [smiles, smiles, smiles]
        editor.close()
    ''', tmp_path)
