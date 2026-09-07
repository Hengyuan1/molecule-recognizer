"""Compact nitrogen labels preserve hydrogen counts, chemistry and editing."""

import textwrap

import pytest

from tests.test_hydroxyl_display import _run_label_qt


def test_nh_labels_count_explicit_and_implicit_hydrogens_once(tmp_path):
    _run_label_qt('''
        # Separate H atoms (SDF/OCR), bracket H counts, and implicit Hs can
        # coexist. Counts in the label must include each exactly once.
        cases = [
            ('CN([H])C', 'NH', 1),
            ('CN([H])[H]', 'NH2', 2),
            ('CN[H]', 'NH2', 1),
            ('C[NH][H]', 'NH2', 1),
            ('CN', 'NH2', 0),
            ('CNC', 'NH', 0),
            ('CN(C)C', 'N', 0),
            ('CC(=O)N([H])[H]', 'NH2', 2),
            ('CC=N[H]', 'NH', 1),
            ('c1ccn([H])c1', 'NH', 1),
            ('C[N+]([H])([H])[H]', 'NH3+', 3),
            ('C[N-][H]', 'NH\u2212', 1),
            ('[H]N([H])[H]', 'NH3', 3),
            ('C[C@H](N([H])[H])F', 'NH2', 2),
        ]
        for smiles, expected, hidden_count in cases:
            mol = load(smiles)
            original = _molecular_state(mol)
            before_smiles = molecule_to_smiles(mol)
            editor.load_molecule(mol)
            nitrogen = next(a.GetIdx() for a in mol.to_rdkit().GetAtoms()
                            if a.GetAtomicNum() == 7)
            assert label(nitrogen) == expected, (smiles, label(nitrogen))
            assert len(scene._collapsed_hydrogens) == hidden_count, smiles
            assert len(scene._atom_items) == mol.num_atoms - hidden_count
            assert len(scene._bond_items) == mol.num_bonds - hidden_count
            for h, n in scene._collapsed_hydrogens.items():
                assert n == nitrogen
                assert h not in scene._atom_items
                assert scene.get_bond_item(n, h) is None
                assert mol.get_bond_info(n, h).bond_type == BondType.SINGLE
            assert molecule_to_smiles(mol) == before_smiles
            assert _molecular_state(mol) == original
            if '2' in expected:
                parts = scene._atom_items[nitrogen]._label_items
                assert parts[2].text() == '2'
                assert parts[2].font().pointSize() < parts[1].font().pointSize()
            editor._toolbar._format_btn.click()
            assert molecule_to_smiles(mol) == before_smiles
            assert label(nitrogen) == expected
            editor._toolbar._undo_btn.click()
            assert _molecular_state(mol) == original

            # Recognized structures arrive as SDF, preserving separate Hs.
            # Build the source before the editor disables implicit-H state.
            params = Chem.SmilesParserParams()
            params.removeHs = False
            source = Chem.MolFromSmiles(smiles, params)
            AllChem.Compute2DCoords(source)
            Chem.WedgeMolBonds(source, source.GetConformer())
            sdf = Chem.MolToMolBlock(source)
            restored = Chem.MolFromMolBlock(sdf, removeHs=False)
            assert restored is not None
            editor.load_molecule(Molecule.from_rdkit(restored))
            assert label(nitrogen) == expected, (smiles, label(nitrogen))
        editor.close()
    ''', tmp_path)


def test_special_nitrogen_hydrogens_remain_explicit(tmp_path):
    _run_label_qt('''
        for smiles in ['CN([2H])[H]', 'CN([H:7])[H]']:
            mol = load(smiles)
            assert scene._collapsed_hydrogens == {3: 1}
            assert label(1) == 'NH'  # Only the ordinary H joins the label.
            assert 2 in scene._atom_items
            assert scene.get_bond_item(1, 2) is not None
        for bond_type in (BondType.WEDGE, BondType.DASH):
            mol = load('CN([H])[H]')
            mol.set_bond_type(1, 2, bond_type)
            editor.load_molecule(mol)
            assert scene._collapsed_hydrogens == {3: 1}
            assert label(1) == 'NH'
            assert scene.get_bond_item(1, 2).bond_type == bond_type
        for prop in ('molFileAlias', 'atomLabel'):
            mol = load('CN([H])[H]')
            mol._mol.GetAtomWithIdx(2).SetProp(prop, 'special H')
            editor.load_molecule(mol)
            assert scene._collapsed_hydrogens == {3: 1}
            assert 2 in scene._atom_items
        editor.close()
    ''', tmp_path)


@pytest.mark.parametrize('group', [False, True])
def test_dragging_nh2_moves_both_hydrogens_and_undo_restores_them(tmp_path, group):
    _run_label_qt(f'group = {group!r}\n' + textwrap.dedent('''
        mol = load('CN([H])[H]')
        original = _molecular_state(mol)
        coords = mol.get_2d_coords()
        editor._set_tool('select')
        if group:
            editor._current_tool._selected = {0, 1}
            editor._current_tool._highlight_selection()
        before = scene._atom_items[1].pos()
        target = before + QPointF(40, -40)
        mouse('press', before)
        mouse('move', target)
        mouse('release', target)
        assert scene._atom_items[1].pos() == target
        for idx in ({0, 1, 2, 3} if group else {1, 2, 3}):
            x, y = coords[idx]
            actual_x, actual_y = mol.get_2d_coords()[idx]
            assert abs(actual_x - x - 1) < 1e-8
            assert abs(actual_y - y - 1) < 1e-8
        assert label(1) == 'NH2' and scene._collapsed_hydrogens == {2: 1, 3: 1}
        moved = _molecular_state(mol)
        editor._toolbar._undo_btn.click()
        assert _molecular_state(mol) == original
        assert not editor._history.can_undo
        editor._toolbar._redo_btn.click()
        assert _molecular_state(mol) == moved
        editor.close()
    '''), tmp_path)


@pytest.mark.parametrize('mode', ['eraser', 'selection', 'box_eraser'])
def test_deleting_nh2_removes_both_hydrogens_with_exact_undo(tmp_path, mode):
    _run_label_qt(f'mode = {mode!r}\n' + textwrap.dedent('''
        mol = load('CN([H])[H]')
        original = _molecular_state(mol)
        nitrogen_pos = scene._atom_items[1].pos()
        assert scene.expand_atom_group([1]) == {1, 2, 3}
        for h in (2, 3):
            assert scene.atom_at_pos(molecule_to_scene(*mol.get_2d_coords()[h])) is None
        if mode == 'selection':
            editor._set_tool('select')
            editor._current_tool._selected = {1}
            editor._current_tool.delete_selection()
        else:
            editor._set_tool('eraser')
            if mode == 'eraser':
                mouse('press', nitrogen_pos)
            else:
                start, end = nitrogen_pos - QPointF(20, 20), nitrogen_pos + QPointF(20, 20)
                mouse('press', start)
                mouse('move', end)
                mouse('release', end)
        assert mol.num_atoms == 1 and mol.num_bonds == 0
        assert mol.get_atom_info(0).element == 'C'
        for _ in range(3):
            editor._toolbar._undo_btn.click()
            assert _molecular_state(mol) == original
            assert label(1) == 'NH2'
            assert scene._collapsed_hydrogens == {2: 1, 3: 1}
            assert not editor._history.can_undo
            editor._toolbar._redo_btn.click()
            assert mol.num_atoms == 1 and not scene._collapsed_hydrogens
        editor.close()
    '''), tmp_path)


def test_editing_between_oh_and_nh2_refreshes_compact_labels(tmp_path):
    _run_label_qt('''
        from molrecognizer.editor.history import ChangeElementCommand, ChangeChargeCommand
        mol = methanol()
        original = _molecular_state(mol)
        editor._history.execute(ChangeElementCommand(1, 'N'))
        assert label(1) == 'NH2' and scene._collapsed_hydrogens == {2: 1}
        editor._history.execute(ChangeChargeCommand(1, 1))
        assert label(1) == 'NH3+' and scene._collapsed_hydrogens == {2: 1}
        editor._toolbar._undo_btn.click()
        assert label(1) == 'NH2'
        editor._toolbar._undo_btn.click()
        assert _molecular_state(mol) == original
        assert label(1) == 'OH'
        editor._toolbar._redo_btn.click()
        assert label(1) == 'NH2'
        editor._history.execute(ChangeElementCommand(1, 'C'))
        assert not scene._collapsed_hydrogens
        assert 2 in scene._atom_items and scene.get_bond_item(1, 2) is not None
        editor._toolbar._undo_btn.click()
        assert label(1) == 'NH2' and scene._collapsed_hydrogens == {2: 1}
        editor.close()
    ''', tmp_path)
