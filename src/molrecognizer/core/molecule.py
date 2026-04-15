"""Molecule representation wrapping RDKit RWMol with 2D coordinates."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from rdkit import Chem
from rdkit.Chem import AllChem, rdchem


class BondType(Enum):
    SINGLE = Chem.rdchem.BondType.SINGLE
    DOUBLE = Chem.rdchem.BondType.DOUBLE
    TRIPLE = Chem.rdchem.BondType.TRIPLE
    AROMATIC = Chem.rdchem.BondType.AROMATIC
    WEDGE = "wedge"    # stereo: filled triangle (single + BondDir.BEGINWEDGE)
    DASH = "dash"      # stereo: dashed wedge  (single + BondDir.BEGINDASH)


@dataclass
class AtomInfo:
    index: int
    element: str
    x: float
    y: float
    formal_charge: int
    implicit_hs: int
    explicit_hs: int
    total_valence: int
    neighbors: list[int]


@dataclass
class BondInfo:
    begin_atom_idx: int
    end_atom_idx: int
    bond_type: BondType


def _bond_type_to_rdkit(bt: BondType) -> tuple:
    """Map our BondType to (RDKit BondType, BondDir)."""
    if bt == BondType.WEDGE:
        return (rdchem.BondType.SINGLE, rdchem.BondDir.BEGINWEDGE)
    if bt == BondType.DASH:
        return (rdchem.BondType.SINGLE, rdchem.BondDir.BEGINDASH)
    return (bt.value, rdchem.BondDir.NONE)


def _rdkit_to_bond_type(bond) -> BondType:
    """Map an RDKit bond to our BondType, checking BondDir for stereo."""
    d = bond.GetBondDir()
    if bond.GetBondType() == rdchem.BondType.SINGLE:
        if d == rdchem.BondDir.BEGINWEDGE:
            return BondType.WEDGE
        if d == rdchem.BondDir.BEGINDASH:
            return BondType.DASH
    return BondType(bond.GetBondType())


class Molecule:
    """Editable molecule with 2D coordinates.

    Wraps an RDKit RWMol. All atom positions are stored in an associated
    conformer so that GUI rendering and round-trip serialization preserve
    layout.
    """

    def __init__(self) -> None:
        self._mol = Chem.RWMol()
        # Create a 2D conformer that grows as atoms are added
        conf = Chem.Conformer()
        conf.SetId(0)
        self._mol.AddConformer(conf, assignId=True)

    # ------------------------------------------------------------------
    # Atom operations
    # ------------------------------------------------------------------

    def add_atom(self, element: str, x: float = 0.0, y: float = 0.0,
                 formal_charge: int = 0) -> int:
        """Add an atom and return its index."""
        atom = Chem.Atom(element)
        atom.SetFormalCharge(formal_charge)
        atom.SetNoImplicit(True)
        atom.SetNumExplicitHs(0)
        idx = self._mol.AddAtom(atom)
        # Extend conformer with the new atom's position
        conf = self._mol.GetConformer(0)
        conf.SetAtomPosition(idx, (x, y, 0.0))
        return idx

    def remove_atom(self, idx: int) -> None:
        """Remove an atom (and all its bonds)."""
        self._mol.RemoveAtom(idx)

    def set_atom_element(self, idx: int, element: str) -> None:
        """Change an atom's element, downgrading bond orders if necessary.

        When the new element's max valence is lower than the current bond
        order sum, double/triple/aromatic bonds are reduced to single bonds
        until the valence fits.
        """
        from .valence import STANDARD_VALENCES

        atom = self._mol.GetAtomWithIdx(idx)
        atom.SetAtomicNum(Chem.GetPeriodicTable().GetAtomicNumber(element))

        # Use the smallest standard valence that fits the number of
        # neighbors.  E.g. S with 2 bonds → use valence 2 (not 6).
        if element not in STANDARD_VALENCES:
            return
        charge = atom.GetFormalCharge()
        n_neighbors = len(list(atom.GetBonds()))
        effective_max = max(STANDARD_VALENCES[element]) + charge
        for v in sorted(STANDARD_VALENCES[element]):
            if v + charge >= n_neighbors:
                effective_max = v + charge
                break

        _order = {
            rdchem.BondType.SINGLE: 1, rdchem.BondType.DOUBLE: 2,
            rdchem.BondType.TRIPLE: 3, rdchem.BondType.AROMATIC: 1.5,
        }
        _downgrade = {
            rdchem.BondType.TRIPLE: rdchem.BondType.DOUBLE,
            rdchem.BondType.DOUBLE: rdchem.BondType.SINGLE,
            rdchem.BondType.AROMATIC: rdchem.BondType.SINGLE,
        }

        # Collect bonds and sort: highest order first for downgrading
        import math as _math
        bonds = []
        bos = 0.0
        for bond in atom.GetBonds():
            bt = bond.GetBondType()
            bonds.append(bond)
            bos += _order.get(bt, 1)

        # Downgrade bonds until the valence fits
        bonds.sort(key=lambda b: _order.get(b.GetBondType(), 1), reverse=True)
        for bond in bonds:
            if _math.ceil(bos) <= effective_max:
                break
            bt = bond.GetBondType()
            new_bt = _downgrade.get(bt)
            if new_bt is not None:
                old_v = _order[bt]
                bond.SetBondType(new_bt)
                new_v = _order.get(new_bt, 1)
                bos -= (old_v - new_v)

    def set_atom_position(self, idx: int, x: float, y: float) -> None:
        conf = self._mol.GetConformer(0)
        conf.SetAtomPosition(idx, (x, y, 0.0))

    def set_formal_charge(self, idx: int, charge: int) -> None:
        self._mol.GetAtomWithIdx(idx).SetFormalCharge(charge)

    def get_atom_info(self, idx: int) -> AtomInfo:
        # Refresh property cache so valence queries work on manually-built mols
        try:
            self._mol.UpdatePropertyCache(strict=False)
        except Exception:
            pass
        atom = self._mol.GetAtomWithIdx(idx)
        conf = self._mol.GetConformer(0)
        pos = conf.GetAtomPosition(idx)
        neighbors = [n.GetIdx() for n in atom.GetNeighbors()]
        return AtomInfo(
            index=idx,
            element=atom.GetSymbol(),
            x=pos.x,
            y=pos.y,
            formal_charge=atom.GetFormalCharge(),
            implicit_hs=atom.GetNumImplicitHs(),
            explicit_hs=atom.GetNumExplicitHs(),
            total_valence=atom.GetTotalValence(),
            neighbors=neighbors,
        )

    @property
    def num_atoms(self) -> int:
        return self._mol.GetNumAtoms()

    # ------------------------------------------------------------------
    # Bond operations
    # ------------------------------------------------------------------

    def add_bond(self, a1: int, a2: int, bond_type: BondType = BondType.SINGLE) -> int:
        """Add a bond between two atoms. Returns the bond index."""
        rdkit_bt, bond_dir = _bond_type_to_rdkit(bond_type)
        idx = self._mol.AddBond(a1, a2, rdkit_bt) - 1  # RDKit returns 1-based
        if bond_dir != rdchem.BondDir.NONE:
            self._mol.GetBondWithIdx(idx).SetBondDir(bond_dir)
        return idx

    def remove_bond(self, a1: int, a2: int) -> None:
        self._mol.RemoveBond(a1, a2)

    def set_bond_type(self, a1: int, a2: int, bond_type: BondType) -> None:
        bond = self._mol.GetBondBetweenAtoms(a1, a2)
        if bond is None:
            raise ValueError(f"No bond between atoms {a1} and {a2}")
        rdkit_bt, bond_dir = _bond_type_to_rdkit(bond_type)
        bond.SetBondType(rdkit_bt)
        bond.SetBondDir(bond_dir)

    def get_bond_info(self, a1: int, a2: int) -> Optional[BondInfo]:
        bond = self._mol.GetBondBetweenAtoms(a1, a2)
        if bond is None:
            return None
        bt = _rdkit_to_bond_type(bond)
        return BondInfo(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx(), bt)

    def get_all_bonds(self) -> list[BondInfo]:
        bonds = []
        for bond in self._mol.GetBonds():
            bt = _rdkit_to_bond_type(bond)
            bonds.append(BondInfo(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx(), bt))
        return bonds

    @property
    def num_bonds(self) -> int:
        return self._mol.GetNumBonds()

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def get_2d_coords(self) -> list[tuple[float, float]]:
        """Return (x, y) for every atom, ordered by atom index."""
        conf = self._mol.GetConformer(0)
        coords = []
        for i in range(self._mol.GetNumAtoms()):
            pos = conf.GetAtomPosition(i)
            coords.append((pos.x, pos.y))
        return coords

    # ------------------------------------------------------------------
    # RDKit interop
    # ------------------------------------------------------------------

    def to_rdkit(self) -> Chem.Mol:
        """Return a frozen RDKit Mol copy."""
        return self._mol.GetMol()

    @classmethod
    def from_rdkit(cls, mol: Chem.Mol) -> "Molecule":
        """Create a Molecule from an RDKit Mol (must have a conformer or one is computed)."""
        m = cls.__new__(cls)
        m._mol = Chem.RWMol(mol)
        if m._mol.GetNumConformers() == 0:
            AllChem.Compute2DCoords(m._mol)
        # Kekulize: convert aromatic bonds to explicit single/double so the
        # editor always shows Kekulé form (easier to verify valence).
        try:
            Chem.Kekulize(m._mol, clearAromaticFlags=True)
        except Exception:
            pass  # partially aromatic mol — keep whatever bond types exist
        # Prevent RDKit from auto-adding implicit Hs (the editor controls
        # valence directly through bonds).
        for atom in m._mol.GetAtoms():
            atom.SetNoImplicit(True)
        return m

    def __repr__(self) -> str:
        return f"Molecule(atoms={self.num_atoms}, bonds={self.num_bonds})"
