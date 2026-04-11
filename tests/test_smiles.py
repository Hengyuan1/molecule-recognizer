"""Tests for SMILES conversion."""

import pytest
from molrecognizer.core.smiles import molecule_to_smiles, smiles_to_molecule


@pytest.mark.parametrize("smiles,expected_atoms", [
    ("C", 1),            # methane (Hs removed)
    ("CC", 2),           # ethane
    ("C=C", 2),          # ethylene
    ("C#C", 2),          # acetylene
    ("c1ccccc1", 6),     # benzene
    ("CCO", 3),          # ethanol
    ("CC(=O)O", 4),      # acetic acid
])
def test_smiles_to_molecule(smiles, expected_atoms):
    mol = smiles_to_molecule(smiles)
    assert mol.num_atoms == expected_atoms


def test_roundtrip_ethanol():
    mol = smiles_to_molecule("CCO")
    smi = molecule_to_smiles(mol)
    # Canonical SMILES should be the same
    assert smi == "CCO"


def test_roundtrip_benzene():
    mol = smiles_to_molecule("c1ccccc1")
    smi = molecule_to_smiles(mol)
    assert smi == "c1ccccc1"


def test_roundtrip_acetic_acid():
    mol = smiles_to_molecule("CC(=O)O")
    smi = molecule_to_smiles(mol)
    # After stripping implicit Hs, canonical form may reorder
    assert smi == "CC(O)=O"


def test_has_2d_coords():
    mol = smiles_to_molecule("CCO")
    coords = mol.get_2d_coords()
    assert len(coords) == 3
    # Coords should not all be at origin
    assert not all(x == 0 and y == 0 for x, y in coords)


def test_invalid_smiles_raises():
    with pytest.raises(ValueError, match="Invalid SMILES"):
        smiles_to_molecule("not_a_smiles!!!")
