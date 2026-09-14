"""SMILES ↔ Molecule conversion utilities."""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import Molecule
from .stereo import with_drawing_stereo


def molecule_to_smiles(mol: Molecule) -> str:
    """Convert a Molecule to a canonical SMILES string.

    Builds a fresh RDKit mol from the connectivity, bond types, and
    formal charges so that RDKit can derive implicit hydrogens cleanly
    — the editor's ``NoImplicit`` flags and stale explicit-H counts are
    not carried over.  Explicit Hs on aromatic atoms (e.g. pyrrole
    ``[nH]``) are preserved because they affect aromaticity perception.

    For common octet-rule atoms whose bond-order sum exceeds the neutral
    count (e.g. N with 4 bonds), the formal charge is auto-inferred so
    that the SMILES correctly reflects the charged species.
    """
    from .valence import infer_formal_charge

    # Pre-compute inferred charges
    inferred: dict[int, int] = {}
    for i in range(mol.num_atoms):
        info = mol.get_atom_info(i)
        bos = mol.bond_order_sum(i)
        inferred[i] = infer_formal_charge(info.element, bos,
                                          info.formal_charge)

    src = with_drawing_stereo(mol.to_rdkit())
    fresh = Chem.RWMol()
    for i in range(src.GetNumAtoms()):
        a = src.GetAtomWithIdx(i)
        na = Chem.Atom(a.GetAtomicNum())
        na.SetFormalCharge(inferred.get(i, a.GetFormalCharge()))
        na.SetChiralTag(a.GetChiralTag())
        na.SetIsotope(a.GetIsotope())
        if a.HasProp("_chiralPermutation"):
            na.SetIntProp("_chiralPermutation", a.GetIntProp("_chiralPermutation"))
        # Keep explicit Hs that are required for aromaticity (pyrrole N, etc.)
        if a.GetNumExplicitHs() > 0:
            na.SetNumExplicitHs(a.GetNumExplicitHs())
        fresh.AddAtom(na)
    for bond in src.GetBonds():
        bi = fresh.AddBond(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx(),
                           bond.GetBondType()) - 1
        new_bond = fresh.GetBondWithIdx(bi)
        new_bond.SetBondDir(bond.GetBondDir())
        stereo = bond.GetStereo()
        if stereo != Chem.BondStereo.STEREONONE:
            new_bond.SetStereo(stereo)
    try:
        Chem.SanitizeMol(fresh)
    except Exception:
        # Full sanitization failed (hypervalent atom?) — do partial
        # sanitization skipping strict valence check, then compute
        # implicit valence per-atom with strict=False.
        try:
            Chem.SanitizeMol(
                fresh,
                Chem.SanitizeFlags.SANITIZE_ALL
                ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES,
            )
        except Exception:
            pass
        for i in range(fresh.GetNumAtoms()):
            try:
                fresh.GetAtomWithIdx(i).UpdatePropertyCache(strict=False)
            except Exception:
                pass
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
    # Generate wedge/dash bonds from stereo tags + 2D coordinates
    try:
        Chem.WedgeMolBonds(rdmol, rdmol.GetConformer())
    except Exception:
        pass
    return Molecule.from_rdkit(rdmol)
