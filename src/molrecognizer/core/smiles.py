"""SMILES ↔ Molecule conversion utilities."""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import Molecule


def molecule_to_smiles(mol: Molecule) -> str:
    """Convert a Molecule to a canonical SMILES string."""
    rdmol = Chem.RWMol(mol.to_rdkit())
    # The editor stores atoms with NoImplicit=True to control valence
    # directly through bonds.  Before generating SMILES we need to let RDKit
    # re-derive implicit hydrogens so the output is chemically correct.
    # Preserve existing NumExplicitHs (e.g. pyrrole [nH]).
    for atom in rdmol.GetAtoms():
        atom.SetNoImplicit(False)
    try:
        Chem.SanitizeMol(rdmol)
    except Exception:
        pass  # best-effort for partially-edited molecules
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
