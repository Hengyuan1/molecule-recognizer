"""SMILES ↔ Molecule conversion utilities."""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import Molecule


def molecule_to_smiles(mol: Molecule) -> str:
    """Convert a Molecule to a canonical SMILES string."""
    rdmol = mol.to_rdkit()
    smiles = Chem.MolToSmiles(rdmol)
    if smiles is None:
        raise ValueError("Failed to generate SMILES from molecule")
    return smiles


def smiles_to_molecule(smiles: str) -> Molecule:
    """Parse a SMILES string into a Molecule with 2D coordinates."""
    rdmol = Chem.MolFromSmiles(smiles)
    if rdmol is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    # Remove all Hs so the editor shows skeletal structure
    rdmol = Chem.RemoveHs(rdmol)
    AllChem.Compute2DCoords(rdmol)
    return Molecule.from_rdkit(rdmol)
