"""Compact OH labels must preserve chemistry and act as one editing unit."""

import textwrap

import pytest

from tests.test_canvas_stereo import _run_qt


def _run_oh_qt(body, tmp_path):
    prelude = '''
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtWidgets import QApplication, QGraphicsSceneMouseEvent
        from rdkit import Chem
        from rdkit.Chem import AllChem
        from molrecognizer.core.molecule import BondType, Molecule
        from molrecognizer.core.smiles import molecule_to_smiles
        from molrecognizer.editor.canvas import molecule_to_scene
        from molrecognizer.gui.editor_widget import EditorWidget
        from tests.test_history import _molecular_state

        app = QApplication([])
        editor = EditorWidget()
        scene = editor.canvas.mol_scene

        def load(smiles):
            params = Chem.SmilesParserParams()
            params.removeHs = False
            rd = Chem.MolFromSmiles(smiles, params)
            AllChem.Compute2DCoords(rd)
            Chem.WedgeMolBonds(rd, rd.GetConformer())
            mol = Molecule.from_rdkit(rd)
            editor.load_molecule(mol)
            return mol

        def methanol():
            mol = Molecule()
            for element, x, y in [('C', 0, 0), ('O', 2, 1), ('H', 3, 2)]:
                mol.add_atom(element, x, y)
            mol.add_bond(0, 1)
            mol.add_bond(1, 2)
            editor.load_molecule(mol)
            return mol

        def mouse(kind, pos):
            events = {'press': QEvent.Type.GraphicsSceneMousePress,
                      'move': QEvent.Type.GraphicsSceneMouseMove,
                      'release': QEvent.Type.GraphicsSceneMouseRelease}
            event = QGraphicsSceneMouseEvent(events[kind])
            event.setScenePos(pos)
            event.setButton(Qt.MouseButton.LeftButton)
            getattr(editor._current_tool, 'mouse_' + kind)(event)

        def label(idx):
            return ''.join(item.text() for item in scene._atom_items[idx]._label_items)
    '''
    _run_qt(textwrap.dedent(prelude) + '\n' + textwrap.dedent(body), tmp_path)


def test_hydroxyl_label_does_not_change_molecule_or_stereo(tmp_path):
    _run_oh_qt('''
        from tests.test_label_recovery import recovered_mol
        for mol in [load('CO[H]'), load('c1ccccc1O[H]'), load('CC(=O)O[H]'),
                    load('C[C@H](O[H])F'), Molecule.from_rdkit(recovered_mol())]:
            original = _molecular_state(mol)
            smiles = molecule_to_smiles(mol)
            editor.load_molecule(mol)
            assert len(scene._collapsed_hydrogens) == 1
            for h, o in scene._collapsed_hydrogens.items():
                assert label(o) == 'OH'
                assert h not in scene._atom_items
                assert scene.get_bond_item(h, o) is None
                assert scene.expand_atom_group([o]) == {o, h}
                assert mol.get_bond_info(h, o).bond_type == BondType.SINGLE
            for bond in mol.get_all_bonds():
                if bond.bond_type in (BondType.WEDGE, BondType.DASH):
                    item = scene.get_bond_item(bond.begin_atom_idx, bond.end_atom_idx)
                    assert item.bond_type == bond.bond_type
            assert molecule_to_smiles(mol) == smiles
            assert _molecular_state(mol) == original
            editor._toolbar._format_btn.click()
            assert molecule_to_smiles(mol) == smiles
            assert all(label(o) == 'OH' for o in scene._collapsed_hydrogens.values())
            editor._toolbar._undo_btn.click()
            assert _molecular_state(mol) == original

        # Implicit OH was already compact and must not become OH2.
        load('CO')
        assert not scene._collapsed_hydrogens and label(1) == 'OH'
        editor.close()
    ''', tmp_path)


def test_special_hydrogens_and_other_oxygen_groups_stay_explicit(tmp_path):
    _run_oh_qt('''
        for smiles in ['CO[2H]', 'CO[H:7]', 'C[O+]([H])C', '[H]O[H]',
                       'CN[H]', 'COC', 'C[O-]', 'C=O', '[H]C']:
            mol = load(smiles)
            assert not scene._collapsed_hydrogens, smiles
            assert len(scene._atom_items) == mol.num_atoms
            assert len(scene._bond_items) == mol.num_bonds
        mol = methanol()
        mol.set_bond_type(1, 2, BondType.WEDGE)
        editor.load_molecule(mol)
        assert not scene._collapsed_hydrogens
        assert scene.get_bond_item(1, 2).bond_type == BondType.WEDGE
        editor.close()
    ''', tmp_path)


@pytest.mark.parametrize('group', [False, True])
def test_dragging_oh_moves_its_hydrogen_and_undo_restores_it(tmp_path, group):
    _run_oh_qt(f'group = {group!r}\n' + textwrap.dedent('''
        mol = methanol()
        original = _molecular_state(mol)
        editor._set_tool('select')
        if group:
            editor._current_tool._selected = {0, 1}
            editor._current_tool._highlight_selection()
        before = scene._atom_items[1].pos()
        target = before + QPointF(40, -40)
        mouse('press', before)
        mouse('move', target)
        assert scene._atom_items[1].pos() == target
        mouse('release', target)
        assert scene._atom_items[1].pos() == target
        assert mol.get_2d_coords()[1:] == [(3, 2), (4, 3)]
        assert label(1) == 'OH' and scene._collapsed_hydrogens == {2: 1}
        moved = _molecular_state(mol)
        editor._toolbar._undo_btn.click()
        assert _molecular_state(mol) == original
        assert not editor._history.can_undo
        editor._toolbar._redo_btn.click()
        assert _molecular_state(mol) == moved
        editor.close()
    '''), tmp_path)


@pytest.mark.parametrize('mode', ['eraser', 'selection', 'box_eraser'])
def test_deleting_oh_does_not_leave_an_orphan_hydrogen(tmp_path, mode):
    _run_oh_qt(f'mode = {mode!r}\n' + textwrap.dedent('''
        mol = methanol()
        original = _molecular_state(mol)
        oxygen_pos = scene._atom_items[1].pos()
        # The invisible hydrogen must not remain a clickable canvas target.
        assert scene.atom_at_pos(molecule_to_scene(3, 2)) is None
        if mode == 'selection':
            editor._set_tool('select')
            editor._current_tool._selected = {1}
            editor._current_tool.delete_selection()
        else:
            editor._set_tool('eraser')
            if mode == 'eraser':
                mouse('press', oxygen_pos)
            else:
                start, end = oxygen_pos - QPointF(20, 20), oxygen_pos + QPointF(20, 20)
                mouse('press', start)
                mouse('move', end)
                mouse('release', end)
        assert mol.num_atoms == 1 and mol.num_bonds == 0
        assert mol.get_atom_info(0).element == 'C'
        for _ in range(3):
            editor._toolbar._undo_btn.click()
            assert _molecular_state(mol) == original
            assert label(1) == 'OH'
            assert scene._collapsed_hydrogens == {2: 1}
            assert not editor._history.can_undo
            editor._toolbar._redo_btn.click()
            assert mol.num_atoms == 1 and not scene._collapsed_hydrogens
        editor.close()
    '''), tmp_path)


def test_editing_oxygen_refreshes_compact_group_membership(tmp_path):
    _run_oh_qt('''
        from molrecognizer.editor.history import ChangeElementCommand, ChangeChargeCommand
        mol = methanol()
        original = _molecular_state(mol)
        for cmd in [ChangeElementCommand(1, 'N'), ChangeChargeCommand(1, 1)]:
            editor._history.execute(cmd)
            assert not scene._collapsed_hydrogens
            assert 2 in scene._atom_items and scene.get_bond_item(1, 2) is not None
            editor._toolbar._undo_btn.click()
            assert _molecular_state(mol) == original
            assert label(1) == 'OH' and scene._collapsed_hydrogens == {2: 1}
        editor.close()
    ''', tmp_path)
