"""SMILES ↔ Molecule conversion utilities."""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import Molecule


def molecule_to_smiles(mol: Molecule) -> str:
    """Convert a Molecule to a canonical SMILES string.

    Builds a fresh RDKit mol from the connectivity, bond types, and
    formal charges so that RDKit can derive implicit hydrogens cleanly
    — the editor's ``NoImplicit`` flags and stale explicit-H counts are
    not carried over.  Explicit Hs on aromatic atoms (e.g. pyrrole
    ``[nH]``) are preserved because they affect aromaticity perception.
    """
    src = mol.to_rdkit()
    fresh = Chem.RWMol()
    for i in range(src.GetNumAtoms()):
        a = src.GetAtomWithIdx(i)
        na = Chem.Atom(a.GetAtomicNum())
        na.SetFormalCharge(a.GetFormalCharge())
        # Keep explicit Hs that are required for aromaticity (pyrrole N, etc.)
        if a.GetNumExplicitHs() > 0:
            na.SetNumExplicitHs(a.GetNumExplicitHs())
        fresh.AddAtom(na)
    for bond in src.GetBonds():
        fresh.AddBond(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx(),
                      bond.GetBondType())
    try:
        Chem.SanitizeMol(fresh)
    except Exception:
        pass  # best-effort for partially-edited molecules
    smiles = Chem.MolToSmiles(fresh)
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
