"""Read stereochemistry from the editor's current drawing, on a copy."""

from rdkit import Chem


def with_drawing_stereo(mol: Chem.Mol) -> Chem.RWMol:
    """Interpret current wedges before exporting or moving any coordinates."""
    result = Chem.RWMol(mol)
    for atom in result.GetAtoms():
        atom.SetNoImplicit(False)
    result.UpdatePropertyCache(strict=False)
    from .coordination import METALS
    metal_stereo = {a.GetIdx(): a.GetChiralTag() for a in result.GetAtoms()
                    if a.GetAtomicNum() in METALS}
    for bond in result.GetBonds():
        if (bond.GetBeginAtomIdx() in metal_stereo or bond.GetEndAtomIdx() in metal_stereo
                or bond.GetBondType() == Chem.BondType.DATIVE):
            bond.SetBondDir(Chem.BondDir.NONE)
    # With an implicit H, RDKit rejects a center carrying both wedge and
    # dash ("rule 1a"). One indicator suffices; keep the original drawing
    # untouched and use only the wedge on this perception copy.
    for atom in result.GetAtoms():
        outgoing = [b for b in atom.GetBonds() if b.GetBeginAtomIdx() == atom.GetIdx()]
        if any(b.GetBondDir() == Chem.BondDir.BEGINWEDGE for b in outgoing):
            for bond in outgoing:
                if bond.GetBondDir() == Chem.BondDir.BEGINDASH:
                    bond.SetBondDir(Chem.BondDir.NONE)
    Chem.AssignChiralTypesFromBondDirs(result)
    for idx, tag in metal_stereo.items():
        result.GetAtomWithIdx(idx).SetChiralTag(tag)
    return result
