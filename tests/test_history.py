"""Tests for undo/redo history."""

from molrecognizer.core.molecule import BondType, Molecule
from molrecognizer.editor.history import (
    AddAtomCommand,
    AddBondCommand,
    ChangeBondTypeCommand,
    ChangeElementCommand,
    HistoryManager,
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
