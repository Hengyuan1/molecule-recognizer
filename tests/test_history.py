"""Tests for undo/redo history."""

import pytest
from rdkit import Chem

from molrecognizer.core.molecule import BondType, Molecule
from molrecognizer.editor.history import (
    AddAtomCommand,
    AddBondCommand,
    BulkDeleteCommand,
    ChangeBondTypeCommand,
    ChangeElementCommand,
    HistoryManager,
    MoveAtomCommand,
    RemoveAtomCommand,
    RemoveBondCommand,
)


def test_add_atom_undo():
    mol = Molecule()
    hm = HistoryManager(mol)
    cmd = AddAtomCommand("C", 1.0, 2.0)
    hm.execute(cmd)
    assert mol.num_atoms == 1
    hm.undo()
    assert mol.num_atoms == 0


def test_add_bond_undo():
    mol = Molecule()
    mol.add_atom("C", 0, 0)
    mol.add_atom("C", 1, 0)
    hm = HistoryManager(mol)
    cmd = AddBondCommand(0, 1, BondType.SINGLE)
    hm.execute(cmd)
    assert mol.num_bonds == 1
    hm.undo()
    assert mol.num_bonds == 0


def test_change_bond_type_undo():
    mol = Molecule()
    mol.add_atom("C", 0, 0)
    mol.add_atom("C", 1, 0)
    mol.add_bond(0, 1, BondType.SINGLE)
    hm = HistoryManager(mol)
    cmd = ChangeBondTypeCommand(0, 1, BondType.DOUBLE)
    hm.execute(cmd)
    assert mol.get_bond_info(0, 1).bond_type == BondType.DOUBLE
    hm.undo()
    assert mol.get_bond_info(0, 1).bond_type == BondType.SINGLE


def test_change_element_undo():
    mol = Molecule()
    mol.add_atom("C", 0, 0)
    hm = HistoryManager(mol)
    cmd = ChangeElementCommand(0, "N")
    hm.execute(cmd)
    assert mol.get_atom_info(0).element == "N"
    hm.undo()
    assert mol.get_atom_info(0).element == "C"


def test_remove_bond_undo():
    mol = Molecule()
    mol.add_atom("C", 0, 0)
    mol.add_atom("C", 1, 0)
    mol.add_bond(0, 1, BondType.DOUBLE)
    hm = HistoryManager(mol)
    cmd = RemoveBondCommand(0, 1)
    hm.execute(cmd)
    assert mol.num_bonds == 0
    hm.undo()
    assert mol.num_bonds == 1
    assert mol.get_bond_info(0, 1).bond_type == BondType.DOUBLE


def test_redo():
    mol = Molecule()
    hm = HistoryManager(mol)
    cmd = AddAtomCommand("O", 2.0, 3.0)
    hm.execute(cmd)
    assert mol.num_atoms == 1
    hm.undo()
    assert mol.num_atoms == 0
    hm.redo()
    assert mol.num_atoms == 1


def test_redo_cleared_after_new_command():
    mol = Molecule()
    hm = HistoryManager(mol)
    hm.execute(AddAtomCommand("C", 0, 0))
    hm.execute(AddAtomCommand("N", 1, 0))
    hm.undo()
    assert hm.can_redo
    hm.execute(AddAtomCommand("O", 2, 0))
    assert not hm.can_redo


def test_can_undo_redo():
    mol = Molecule()
    hm = HistoryManager(mol)
    assert not hm.can_undo
    assert not hm.can_redo
    hm.execute(AddAtomCommand("C", 0, 0))
    assert hm.can_undo
    assert not hm.can_redo
    hm.undo()
    assert not hm.can_undo
    assert hm.can_redo


def test_on_change_callback():
    mol = Molecule()
    hm = HistoryManager(mol)
    calls = []
    hm.set_on_change(lambda: calls.append(1))
    hm.execute(AddAtomCommand("C", 0, 0))
    assert len(calls) == 1
    hm.undo()
    assert len(calls) == 2
    hm.redo()
    assert len(calls) == 3


def test_set_molecule_clears_history():
    mol1 = Molecule()
    hm = HistoryManager(mol1)
    hm.execute(AddAtomCommand("C", 0, 0))
    assert hm.can_undo
    mol2 = Molecule()
    hm.molecule = mol2
    assert not hm.can_undo
    assert not hm.can_redo


def _molecular_state(mol):
    """Compare identities, ordered bonds, stereo, labels and every coordinate.

    SMILES equality alone misses changed atom indices and drawing geometry.
    Computed property caches aren't part of an editing operation's state.
    """
    rd = mol._mol
    return (
        [(a.GetAtomicNum(), a.GetIsotope(), a.GetFormalCharge(),
          a.GetNumExplicitHs(), a.GetNoImplicit(), a.GetChiralTag(),
          a.GetAtomMapNum(), a.GetIsAromatic(),
          a.GetPropsAsDict(includePrivate=False, includeComputed=False)) for a in rd.GetAtoms()],
        [(b.GetBeginAtomIdx(), b.GetEndAtomIdx(), b.GetBondType(),
          b.GetBondDir(), b.GetStereo(), tuple(b.GetStereoAtoms()),
          b.GetIsAromatic(), b.GetIsConjugated(),
          b.GetPropsAsDict(includePrivate=False, includeComputed=False)) for b in rd.GetBonds()],
        [(conf.GetId(), conf.Is3D(), tuple(tuple(conf.GetAtomPosition(i))
                                         for i in range(rd.GetNumAtoms())))
         for conf in rd.GetConformers()],
    )


@pytest.mark.parametrize("smiles", ["CC(=O)N", "c1ccccc1", "F/C=C/[C@H]([13CH3])[NH3+]"])
@pytest.mark.parametrize("index", [0, 1, 2, -1])
def test_delete_atom_undo_restores_exact_connections(smiles, index):
    mol = Molecule.from_rdkit(Chem.MolFromSmiles(smiles))
    for atom in mol._mol.GetAtoms():
        atom.SetProp("source_label", f"atom-{atom.GetIdx()}")
    index %= mol.num_atoms
    original = _molecular_state(mol)
    history = HistoryManager(mol)
    history.execute(RemoveAtomCommand(index))
    deleted = _molecular_state(mol)
    assert mol.num_atoms == len(original[0]) - 1
    for _ in range(3):
        assert history.undo()
        assert _molecular_state(mol) == original
        assert history.redo()
        assert _molecular_state(mol) == deleted


@pytest.mark.parametrize("bond_type", [BondType.SINGLE, BondType.DOUBLE, BondType.TRIPLE,
                                      BondType.WEDGE, BondType.DASH])
def test_delete_bond_preserves_direction_and_order(bond_type):
    mol = Molecule()
    for i, element in enumerate(["C", "N", "O"]):
        mol.add_atom(element, i * 1.5, i * -0.5)
    mol.add_bond(1, 0, bond_type)
    mol.add_bond(1, 2)
    mol._mol.GetBondWithIdx(0).SetProp("source_label", "original bond")
    original = _molecular_state(mol)
    history = HistoryManager(mol)
    history.execute(RemoveBondCommand(0, 1))  # Reverse of the stored orientation.
    deleted = _molecular_state(mol)
    for _ in range(3):
        history.undo()
        assert _molecular_state(mol) == original
        history.redo()
        assert _molecular_state(mol) == deleted


def test_delete_stereo_bond_restores_stereo_atoms():
    mol = Molecule.from_rdkit(Chem.MolFromSmiles("F/C=C/F"))
    original = _molecular_state(mol)
    history = HistoryManager(mol)
    history.execute(RemoveBondCommand(1, 2))
    history.undo()
    assert _molecular_state(mol) == original


def test_atom_deletion_does_not_break_earlier_history_indices():
    mol = Molecule.from_rdkit(Chem.MolFromSmiles("CC(=O)N"))
    original = _molecular_state(mol)
    history = HistoryManager(mol)
    x, y = mol.get_2d_coords()[3]
    history.execute(MoveAtomCommand(3, x, y, x + 2, y - 1))
    moved = _molecular_state(mol)
    history.execute(RemoveAtomCommand(1))
    deleted = _molecular_state(mol)
    history.undo()
    assert _molecular_state(mol) == moved
    history.undo()
    assert _molecular_state(mol) == original
    history.redo()
    assert _molecular_state(mol) == moved
    history.redo()
    assert _molecular_state(mol) == deleted


def test_bulk_delete_restores_exact_connections():
    mol = Molecule.from_rdkit(Chem.MolFromSmiles("F/C=C/[C@H]([13CH3])[NH3+]"))
    original = _molecular_state(mol)
    history = HistoryManager(mol)
    history.execute(BulkDeleteCommand([0, 2, 3]))
    deleted = _molecular_state(mol)
    for _ in range(3):
        history.undo()
        assert _molecular_state(mol) == original
        history.redo()
        assert _molecular_state(mol) == deleted
