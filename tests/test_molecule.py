"""Tests for Molecule class."""

import pytest
from molrecognizer.core.molecule import BondType, Molecule


def test_add_atoms():
    mol = Molecule()
    idx0 = mol.add_atom("C", 0.0, 0.0)
    idx1 = mol.add_atom("O", 1.5, 0.0)
    assert mol.num_atoms == 2
    assert idx0 == 0
    assert idx1 == 1


def test_add_bond():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.add_atom("C", 1.5, 0.0)
    mol.add_bond(0, 1, BondType.SINGLE)
    assert mol.num_bonds == 1
    bond = mol.get_bond_info(0, 1)
    assert bond is not None
    assert bond.bond_type == BondType.SINGLE


def test_remove_atom_removes_bonds():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.add_atom("C", 1.5, 0.0)
    mol.add_atom("O", 3.0, 0.0)
    mol.add_bond(0, 1)
    mol.add_bond(1, 2)
    assert mol.num_bonds == 2
    mol.remove_atom(1)
    assert mol.num_atoms == 2
    assert mol.num_bonds == 0


def test_set_bond_type():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.add_atom("C", 1.5, 0.0)
    mol.add_bond(0, 1, BondType.SINGLE)
    mol.set_bond_type(0, 1, BondType.DOUBLE)
    bond = mol.get_bond_info(0, 1)
    assert bond.bond_type == BondType.DOUBLE


def test_set_atom_element():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    info = mol.get_atom_info(0)
    assert info.element == "C"
    mol.set_atom_element(0, "N")
    info = mol.get_atom_info(0)
    assert info.element == "N"


def test_get_2d_coords():
    mol = Molecule()
    mol.add_atom("C", 1.0, 2.0)
    mol.add_atom("O", 3.0, 4.0)
    coords = mol.get_2d_coords()
    assert len(coords) == 2
    assert coords[0] == pytest.approx((1.0, 2.0), abs=1e-6)
    assert coords[1] == pytest.approx((3.0, 4.0), abs=1e-6)


def test_set_atom_position():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.set_atom_position(0, 5.0, 6.0)
    coords = mol.get_2d_coords()
    assert coords[0] == pytest.approx((5.0, 6.0), abs=1e-6)


def test_get_atom_info_neighbors():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.add_atom("C", 1.5, 0.0)
    mol.add_atom("C", 0.0, 1.5)
    mol.add_bond(0, 1)
    mol.add_bond(0, 2)
    info = mol.get_atom_info(0)
    assert sorted(info.neighbors) == [1, 2]


def test_get_all_bonds():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.add_atom("O", 1.0, 0.0)
    mol.add_atom("N", 2.0, 0.0)
    mol.add_bond(0, 1, BondType.DOUBLE)
    mol.add_bond(1, 2, BondType.SINGLE)
    bonds = mol.get_all_bonds()
    assert len(bonds) == 2
    types = {b.bond_type for b in bonds}
    assert BondType.DOUBLE in types
    assert BondType.SINGLE in types


def test_remove_bond():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.add_atom("O", 1.0, 0.0)
    mol.add_bond(0, 1)
    assert mol.num_bonds == 1
    mol.remove_bond(0, 1)
    assert mol.num_bonds == 0


def test_set_bond_type_nonexistent_raises():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.add_atom("O", 1.0, 0.0)
    with pytest.raises(ValueError):
        mol.set_bond_type(0, 1, BondType.DOUBLE)


def test_from_rdkit_roundtrip():
    mol = Molecule()
    mol.add_atom("C", 0.0, 0.0)
    mol.add_atom("C", 1.5, 0.0)
    mol.add_bond(0, 1, BondType.DOUBLE)
    rdmol = mol.to_rdkit()
    mol2 = Molecule.from_rdkit(rdmol)
    assert mol2.num_atoms == 2
    assert mol2.num_bonds == 1
    bond = mol2.get_bond_info(0, 1)
    assert bond.bond_type == BondType.DOUBLE
