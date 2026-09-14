"""Conservative metal/label review; never infer a metal or oxidation state."""

from rdkit import Chem

from .molecule import Molecule


METALS = frozenset({3, 4, 11, 12, 13, 19, 20, 31, 37, 38, 49, 50, 55, 56,
                    81, 82, 83, 87, 88, 113, 114, 115, 116}
                   | set(range(21, 31)) | set(range(39, 49))
                   | set(range(57, 81)) | set(range(89, 113)))


def has_coordination(mol: Chem.Mol) -> bool:
    return (any(a.GetAtomicNum() in METALS for a in mol.GetAtoms())
            or any(b.GetBondType() == Chem.BondType.DATIVE for b in mol.GetBonds()))


def review_warnings(mol: Molecule) -> list[str]:
    rd = mol.to_rdkit()
    warnings = []
    unknown = [a.GetProp("molFileAlias") if a.HasProp("molFileAlias") else "*"
               for a in rd.GetAtoms() if a.GetAtomicNum() == 0]
    if unknown:
        warnings.append("Unresolved labels: " + ", ".join(sorted(set(unknown)))
                        + ". Use Edit → Review atom labels / metal; do not assume carbon.")
    if has_coordination(rd):
        warnings.append("Metal/coordinate structure: verify metal identity, donor atoms, "
                        "bond types, charges and geometry. Metal valence is not validated.")
    return warnings


def reviewed_labels(mol: Molecule, replacements: dict[int, tuple[str, int]],
                    coordinate_donors: bool = False) -> Molecule:
    """Apply only user-confirmed elements/NH3 and charges on an independent copy.

    CO3 is deliberately not expanded: its donor atom and binding mode are not
    specified by that abbreviation. Coordinate conversion is a separate opt-in
    for N/O single bonds to confirmed metal atoms; carbon bonds are untouched.
    """
    result = Molecule.from_rdkit(mol.to_rdkit())
    for idx, (label, charge) in replacements.items():
        atom = result._mol.GetAtomWithIdx(idx)
        label = label.strip()
        if label:
            if label in ("NH3", "H3N"):
                hydrogen_neighbors = sum(a.GetAtomicNum() == 1 for a in atom.GetNeighbors())
                if hydrogen_neighbors > 3:
                    raise ValueError("NH3 cannot have more than three hydrogen neighbors")
                element, hs = "N", 3 - hydrogen_neighbors
            else:
                symbols = {Chem.GetPeriodicTable().GetElementSymbol(n) for n in range(1, 119)}
                if label not in symbols:
                    raise ValueError(f"Use an exact element symbol or NH3, not {label!r}. "
                                     "CO3 must be drawn explicitly after confirming its attachment.")
                element, hs = label, 0
            if atom.HasProp("molFileAlias"):
                atom.SetProp("_OriginalOCRLabel", atom.GetProp("molFileAlias"))
                atom.ClearProp("molFileAlias")
            atom.SetAtomicNum(Chem.GetPeriodicTable().GetAtomicNumber(element))
            atom.SetNumExplicitHs(hs)
            atom.SetNoImplicit(True)
        atom.SetFormalCharge(charge)
    if coordinate_donors:
        changes = []
        for bond in list(result._mol.GetBonds()):
            a, b = bond.GetBeginAtom(), bond.GetEndAtom()
            if a.GetAtomicNum() in METALS and b.GetAtomicNum() in (7, 8):
                donor, metal, reverse = b.GetIdx(), a.GetIdx(), True
            elif b.GetAtomicNum() in METALS and a.GetAtomicNum() in (7, 8):
                donor, metal, reverse = a.GetIdx(), b.GetIdx(), False
            else:
                continue
            if bond.GetBondType() != Chem.BondType.SINGLE:
                continue
            direction = bond.GetBondDir()
            changes.append((donor, metal, reverse, direction))
        for donor, metal, reverse, direction in changes:
            # Retain spatial ink without using it to assign metal stereochemistry.
            result._mol.RemoveBond(donor, metal)
            result._mol.AddBond(donor, metal, Chem.BondType.DATIVE)
            new_bond = result._mol.GetBondBetweenAtoms(donor, metal)
            new_bond.SetBondDir(direction)
            new_bond.SetBoolProp("_CoordinationDrawingReversed", reverse)
    result._mol.UpdatePropertyCache(strict=False)
    return result
