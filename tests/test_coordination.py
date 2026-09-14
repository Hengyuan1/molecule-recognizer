"""Metal bonds, manual confirmation and safe unsupported-geometry handling."""
import pytest
from rdkit import Chem
from rdkit.Chem import AllChem

from molrecognizer.core.molecule import Molecule, BondType
from molrecognizer.core.coordination import reviewed_labels, review_warnings
from molrecognizer.core.smiles import smiles_to_molecule, molecule_to_smiles
from molrecognizer.core.layout import format_2d
from molrecognizer.core.xyz import generate_3d
from molrecognizer.editor.history import (
    HistoryManager, ChangeBondTypeCommand, ChangeElementCommand,
    RemoveAtomCommand, ReplaceMoleculeCommand,
)
from tests.test_history import _molecular_state
from tests.test_shutdown import _run
from molrecognizer.gui.metal_picker import COMMON_METAL_CENTERS


def complex_molecule():
    return smiles_to_molecule("[NH3]->[Sc](<-[NH3])(<-[NH3])Br")


@pytest.mark.parametrize("symbol", [symbol for symbol, _ in COMMON_METAL_CENTERS])
def test_common_metals_allow_explicit_label_review_and_dative_export(symbol):
    from molrecognizer.core.coordination import METALS
    from molrecognizer.editor.canvas import ELEMENT_COLORS
    mol = Molecule()
    metal = mol.add_atom("*", 0, 0)
    donor = mol.add_atom("N", 1, 0)
    mol.add_bond(metal, donor)
    confirmed = reviewed_labels(mol, {metal: (symbol, 2), donor: ("NH3", 0)}, True)
    assert mol.get_atom_info(metal).element == "*"
    assert confirmed.get_atom_info(metal).element == symbol
    assert Chem.GetPeriodicTable().GetAtomicNumber(symbol) in METALS
    assert symbol in ELEMENT_COLORS
    restored = Chem.MolFromSmiles(molecule_to_smiles(confirmed))
    assert restored is not None
    center = next(a for a in restored.GetAtoms() if a.GetSymbol() == symbol)
    assert center.GetFormalCharge() == 2
    bond = center.GetBonds()[0]
    assert bond.GetBondType() == Chem.BondType.DATIVE
    assert bond.GetEndAtomIdx() == center.GetIdx()
    assert any("not validated" in w for w in review_warnings(confirmed))


@pytest.mark.parametrize("embedded", [False, True])
def test_common_metal_picker_select_place_replace_cancel_and_close(tmp_path, embedded):
    _run(tmp_path, f"""
        from types import SimpleNamespace
        from PySide6.QtCore import QPointF
        from tests.test_history import _molecular_state
        patch('molrecognizer.gui.window_placement.is_wsl', return_value={embedded}).start()
        toolbar = window._editor._toolbar
        assert toolbar._metal_btn.text() == 'Metal'
        assert 'Select metal center…' in window._menu_actions
        before = _molecular_state(window._editor.molecule)
        toolbar._metal_btn.click()
        dialog = window._metal_picker
        assert dialog is not None and dialog._embedded is {embedded}
        window._on_common_metal()
        assert window._metal_picker is dialog  # No duplicate picker.
        window._on_screenshot()
        assert not window._screenshot_pending
        dialog._buttons['Co'].click()
        app.processEvents()
        assert window._metal_picker is None
        assert window._editor._current_element == 'Co'
        assert window._editor._current_tool.name == 'atom'
        assert toolbar._pt_btn.text() == 'Co'
        assert not any(b.isChecked() for b in window._palette._buttons.values())
        assert _molecular_state(window._editor.molecule) == before
        event = SimpleNamespace(scenePos=lambda: QPointF(0, 0))
        window._editor._current_tool.mouse_press(event)
        window._editor._current_tool.mouse_release(event)
        mol = window._editor.molecule
        assert mol.num_atoms == 1 and mol.get_atom_info(0).element == 'Co'
        assert mol.get_atom_info(0).formal_charge == 0 and mol.num_bonds == 0
        for symbol in ('Pt', 'Cr'):
            window._menu_actions['Select metal center…'].trigger()
            window._metal_picker._buttons[symbol].click()
            app.processEvents()
            window._editor._current_tool.mouse_press(event)
            window._editor._current_tool.mouse_release(event)
            assert mol.num_atoms == 1 and mol.get_atom_info(0).element == symbol
        window._editor._undo()
        assert mol.get_atom_info(0).element == 'Pt'
        window._editor._redo()
        assert mol.get_atom_info(0).element == 'Cr'
        before = _molecular_state(mol)
        window._on_common_metal()
        window._metal_picker.reject()
        assert window._editor._current_element == 'Cr'
        assert _molecular_state(mol) == before
        window._on_common_metal()
        window.close()
        assert window._metal_picker is None
    """)


def test_dative_direction_valence_and_smiles_survive_history():
    mol = complex_molecule()
    rd = mol.to_rdkit()
    assert sum(b.bond_type == BondType.DATIVE for b in mol.get_all_bonds()) == 3
    donor = next(a.GetIdx() for a in rd.GetAtoms() if a.GetAtomicNum() == 7)
    metal = next(a.GetIdx() for a in rd.GetAtoms() if a.GetAtomicNum() == 21)
    assert mol.bond_order_sum(donor) == 0
    assert mol.bond_order_sum(metal) == 4
    before = _molecular_state(mol)
    smiles = molecule_to_smiles(mol)
    restored = Chem.MolFromSmiles(smiles)
    assert restored is not None
    assert all(a.GetFormalCharge() == 0 and a.GetTotalNumHs() == 3
               for a in restored.GetAtoms() if a.GetAtomicNum() == 7)
    history = HistoryManager(mol)
    for command in (ChangeBondTypeCommand(metal, donor, BondType.DATIVE),
                    RemoveAtomCommand(donor), ChangeElementCommand(donor, "P")):
        history.execute(command)
        changed = _molecular_state(mol)
        assert changed != before
        history.undo()
        assert _molecular_state(mol) == before
        history.redo()
        assert _molecular_state(mol) == changed
        history.undo()


def test_dative_does_not_downgrade_pyridine_when_replacing_nitrogen():
    # Use a simpler standalone pyridine donor to avoid arbitrary ring stereo.
    rd = Chem.MolFromSmiles("n1(->[Sc])ccccc1")
    AllChem.Compute2DCoords(rd)
    mol = Molecule.from_rdkit(rd)
    nitrogen = next(a.GetIdx() for a in rd.GetAtoms() if a.GetAtomicNum() == 7)
    bonds = mol.get_all_bonds()
    mol.set_atom_element(nitrogen, "N")
    assert mol.get_all_bonds() == bonds
    assert "n+" not in molecule_to_smiles(mol)


def test_confirmed_labels_only_and_source_wedges_preserved():
    mol = Molecule()
    metal = mol.add_atom("*", 0, 0)
    donor = mol.add_atom("*", 1, 1)
    carbon = mol.add_atom("C", -1, 0)
    mol._mol.GetAtomWithIdx(metal).SetProp("molFileAlias", "SC")
    mol._mol.GetAtomWithIdx(donor).SetProp("molFileAlias", "H3N")
    mol.add_bond(metal, donor, BondType.WEDGE)
    mol.add_bond(metal, carbon)
    before = _molecular_state(mol)
    result = reviewed_labels(mol, {metal: ("Sc", 3), donor: ("NH3", 0)}, True)
    assert _molecular_state(mol) == before
    assert result.get_2d_coords() == mol.get_2d_coords()
    bond = result.get_bond_info(metal, donor)
    assert bond.bond_type == BondType.DATIVE
    assert (bond.begin_atom_idx, bond.end_atom_idx) == (donor, metal)
    assert bond.drawing_type == BondType.WEDGE and bond.drawing_reversed
    assert result.get_bond_info(metal, carbon).bond_type == BondType.SINGLE
    assert "NH3" in molecule_to_smiles(result)
    assert result.get_atom_info(metal).formal_charge == 3
    history = HistoryManager(mol)
    history.execute(ReplaceMoleculeCommand(result))
    history.undo()
    assert _molecular_state(mol) == before
    history.redo()
    assert _molecular_state(mol) == _molecular_state(result)
    with pytest.raises(ValueError, match="CO3"):
        reviewed_labels(mol, {donor: ("CO3", 0)})


def test_unknown_labels_and_metal_are_not_reported_as_verified():
    mol = complex_molecule()
    assert any("not validated" in warning for warning in review_warnings(mol))
    unknown = Molecule()
    idx = unknown.add_atom("*")
    unknown._mol.GetAtomWithIdx(idx).SetProp("molFileAlias", "CO3")
    assert "CO3" in review_warnings(unknown)[0]
    assert review_warnings(smiles_to_molecule("CCO")) == []
    with pytest.raises(ValueError, match="source geometry"):
        format_2d(mol)
    with pytest.raises(ValueError, match="metal/coordinate"):
        generate_3d(molecule_to_smiles(mol))


@pytest.mark.parametrize("smiles", ["N[Pt@SP1](Cl)(Cl)N", "N[Pt@SP2](Cl)(Cl)N",
                                   "N[Co@OH1](F)(Cl)(Br)(I)S"])
def test_existing_non_tetrahedral_stereo_is_preserved(smiles):
    expected = Chem.MolToSmiles(Chem.MolFromSmiles(smiles))
    actual = molecule_to_smiles(smiles_to_molecule(smiles))
    assert Chem.MolToSmiles(Chem.MolFromSmiles(actual)) == expected


def test_review_nh3_counts_existing_explicit_h_neighbors_once():
    mol = Molecule()
    metal = mol.add_atom("Sc")
    donor = mol.add_atom("N", 1, 0)
    mol.add_bond(metal, donor)
    for y in (-1, 1):
        hydrogen = mol.add_atom("H", 2, y)
        mol.add_bond(donor, hydrogen)
    result = reviewed_labels(mol, {donor: ("NH3", 0)}, True)
    restored = Chem.MolFromSmiles(molecule_to_smiles(result))
    nitrogen = next(a for a in restored.GetAtoms() if a.GetAtomicNum() == 7)
    assert nitrogen.GetTotalNumHs(includeNeighbors=True) == 3
    assert nitrogen.GetFormalCharge() == 0


def test_coordination_ui_and_review_are_explicit_and_undoable(tmp_path):
    _run(tmp_path, """
        from molrecognizer.core.molecule import BondType, Molecule
        from molrecognizer.core.coordination import reviewed_labels
        from tests.test_coordination import complex_molecule
        from tests.test_history import _molecular_state
        window._set_molecule(complex_molecule())
        scene = window._editor.canvas.mol_scene
        donors = [i for i in scene._atom_items.values() if i.element == 'N']
        assert all(i.n_hs == 3 and i.formal_charge == 0 for i in donors)
        bonds = [b for b in scene._bond_items.values() if b.bond_type == BondType.DATIVE]
        assert all(len(b._extra_lines) == 2 for b in bonds)
        assert 'not validated' in window._bottom_bar._valence_label.text()
        assert 'All valences OK' not in window._bottom_bar._valence_label.text()
        before = _molecular_state(window._molecule)
        window._on_review_labels()
        dialog = window._label_review_dialog
        window._on_screenshot()
        assert not window._screenshot_pending
        assert not dialog._coordinate.isChecked()
        metal = next(a.GetIdx() for a in window._molecule.to_rdkit().GetAtoms() if a.GetSymbol() == 'Sc')
        dialog._fields[metal][1].setValue(3)
        dialog._preview()
        assert _molecular_state(window._molecule) == before
        dialog.accept()
        app.processEvents()
        assert window._molecule.get_atom_info(metal).formal_charge == 3
        window._editor._undo()
        assert _molecular_state(window._molecule) == before
        window._on_review_labels()
        window._label_review_dialog.reject()
        app.processEvents()
        assert _molecular_state(window._molecule) == before
        window._on_review_labels()
        dialog = window._label_review_dialog
        dialog._fields[metal][0].setText('CO3')
        dialog.accept()
        assert window._label_review_dialog is dialog and dialog.replacement is None
        assert 'CO3' in dialog._error.text()
        window.close()
        assert window._label_review_dialog is None
    """)


def test_coordinate_tool_reverses_arrow_and_preserves_spatial_ink(tmp_path):
    _run(tmp_path, """
        from PySide6.QtCore import QPointF
        from molrecognizer.core.molecule import Molecule, BondType
        from molrecognizer.core.coordination import reviewed_labels
        from molrecognizer.editor.tools import BondTool
        mol = Molecule()
        metal = mol.add_atom('Sc', 0, 0)
        donor = mol.add_atom('N', 2, 0)
        mol.add_bond(metal, donor, BondType.WEDGE)
        mol = reviewed_labels(mol, {donor: ('NH3', 0)}, True)
        window._set_molecule(mol)
        scene = window._editor.canvas.mol_scene
        item = next(iter(scene._bond_items.values()))
        assert item._drawing_reversed
        assert item._p1 == scene.get_atom_item(metal).pos()
        assert item._p2 == scene.get_atom_item(donor).pos()
        item.update_positions(QPointF(80, 10), QPointF(10, 20))
        assert item._p1 == QPointF(10, 20) and item._p2 == QPointF(80, 10)
        tool = BondTool(scene, window._editor._history)
        tool.bond_type = BondType.DATIVE
        tool._cycle_bond(item)
        info = mol.get_bond_info(metal, donor)
        assert (info.begin_atom_idx, info.end_atom_idx) == (metal, donor)
        assert info.drawing_type is None
        item = next(iter(scene._bond_items.values()))
        assert len(item._extra_lines) == 2
        assert all(line.line().p2() == item.line().p2() for line in item._extra_lines)
        window._editor._undo()
        assert mol.get_bond_info(metal, donor).drawing_reversed
        window.close()
    """)
