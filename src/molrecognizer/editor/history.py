"""Undo/redo command stack for molecule editing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from rdkit import Chem

from ..core.molecule import BondType, Molecule


class Command(ABC):
    """Base class for reversible editing commands."""

    @abstractmethod
    def execute(self, mol: Molecule) -> None: ...

    @abstractmethod
    def undo(self, mol: Molecule) -> None: ...

    @abstractmethod
    def description(self) -> str: ...


class _SnapshotCommand(Command):
    """Restore exact molecular state for edits that discard graph information.

    RDKit renumbers atoms after deletion. Rebuilding just the removed atoms
    and bonds would invalidate both their connections and earlier commands'
    indices. A deep copy also preserves bond orientation, stereo, properties,
    and conformers without regenerating the recognized layout.
    """

    def __init__(self):
        self._saved_rwmol: Chem.RWMol | None = None

    def execute(self, mol: Molecule) -> None:
        self._saved_rwmol = Chem.RWMol(mol._mol)
        self._apply(mol)

    @abstractmethod
    def _apply(self, mol: Molecule) -> None: ...

    def undo(self, mol: Molecule) -> None:
        if self._saved_rwmol is None:
            raise RuntimeError("Cannot undo a command before execution")
        # Keep the shared Molecule wrapper, but don't let later edits mutate
        # the snapshot itself (including on repeated undo/redo).
        mol._mol = Chem.RWMol(self._saved_rwmol)


class ReplaceMoleculeCommand(_SnapshotCommand):
    """Accept a reviewed recognition candidate as one undoable replacement."""

    def __init__(self, replacement: Molecule):
        super().__init__()
        self._replacement = Chem.RWMol(replacement.to_rdkit())

    def _apply(self, mol: Molecule) -> None:
        mol._mol = Chem.RWMol(self._replacement)

    def description(self) -> str:
        return "Use recognition alternative"


class CompoundCommand(Command):
    """Groups multiple commands into a single undoable step."""

    def __init__(self, commands: list[Command]):
        self._commands = commands

    def execute(self, mol: Molecule) -> None:
        for cmd in self._commands:
            cmd.execute(mol)

    def undo(self, mol: Molecule) -> None:
        for cmd in reversed(self._commands):
            cmd.undo(mol)

    def description(self) -> str:
        if self._commands:
            return self._commands[0].description()
        return "Compound"


class AddAtomCommand(Command):
    def __init__(self, element: str, x: float, y: float, formal_charge: int = 0):
        self.element = element
        self.x = x
        self.y = y
        self.formal_charge = formal_charge
        self.created_idx: int | None = None

    def execute(self, mol: Molecule) -> None:
        self.created_idx = mol.add_atom(self.element, self.x, self.y, self.formal_charge)

    def undo(self, mol: Molecule) -> None:
        if self.created_idx is not None:
            mol.remove_atom(self.created_idx)

    def description(self) -> str:
        return f"Add {self.element} at ({self.x:.1f}, {self.y:.1f})"


class RemoveAtomCommand(_SnapshotCommand):
    def __init__(self, idx: int):
        super().__init__()
        self.idx = idx

    def _apply(self, mol: Molecule) -> None:
        mol.remove_atom(self.idx)

    def description(self) -> str:
        return f"Remove atom {self.idx}"


class AddBondCommand(Command):
    def __init__(self, a1: int, a2: int, bond_type: BondType = BondType.SINGLE):
        self.a1 = a1
        self.a2 = a2
        self.bond_type = bond_type

    def execute(self, mol: Molecule) -> None:
        mol.add_bond(self.a1, self.a2, self.bond_type)

    def undo(self, mol: Molecule) -> None:
        mol.remove_bond(self.a1, self.a2)

    def description(self) -> str:
        return f"Add {self.bond_type.name.lower()} bond {self.a1}-{self.a2}"


class RemoveBondCommand(_SnapshotCommand):
    def __init__(self, a1: int, a2: int):
        super().__init__()
        self.a1 = a1
        self.a2 = a2

    def _apply(self, mol: Molecule) -> None:
        mol.remove_bond(self.a1, self.a2)

    def description(self) -> str:
        return f"Remove bond {self.a1}-{self.a2}"


class ChangeBondTypeCommand(Command):
    def __init__(self, a1: int, a2: int, new_type: BondType):
        self.a1 = a1
        self.a2 = a2
        self.new_type = new_type
        self._old_type: BondType = BondType.SINGLE

    def execute(self, mol: Molecule) -> None:
        info = mol.get_bond_info(self.a1, self.a2)
        if info:
            self._old_type = info.bond_type
        mol.set_bond_type(self.a1, self.a2, self.new_type)

    def undo(self, mol: Molecule) -> None:
        mol.set_bond_type(self.a1, self.a2, self._old_type)

    def description(self) -> str:
        return f"Change bond {self.a1}-{self.a2} to {self.new_type.name.lower()}"


class ChangeElementCommand(Command):
    def __init__(self, idx: int, new_element: str):
        self.idx = idx
        self.new_element = new_element
        self._old_element: str = "C"
        self._old_bonds: list[tuple[int, int, BondType]] = []

    def execute(self, mol: Molecule) -> None:
        info = mol.get_atom_info(self.idx)
        self._old_element = info.element
        # Save bond types before the element change (set_atom_element may
        # downgrade them to fit the new element's valence).
        self._old_bonds = []
        for bond in mol.get_all_bonds():
            if bond.begin_atom_idx == self.idx or bond.end_atom_idx == self.idx:
                self._old_bonds.append(
                    (bond.begin_atom_idx, bond.end_atom_idx, bond.bond_type)
                )
        mol.set_atom_element(self.idx, self.new_element)

    def undo(self, mol: Molecule) -> None:
        mol.set_atom_element(self.idx, self._old_element)
        # Restore original bond types that may have been downgraded
        for a1, a2, bt in self._old_bonds:
            try:
                mol.set_bond_type(a1, a2, bt)
            except Exception:
                pass

    def description(self) -> str:
        return f"Change atom {self.idx} to {self.new_element}"


class ChangeChargeCommand(Command):
    def __init__(self, idx: int, delta: int):
        self.idx = idx
        self.delta = delta
        self._old_charge: int = 0

    def execute(self, mol: Molecule) -> None:
        info = mol.get_atom_info(self.idx)
        self._old_charge = info.formal_charge
        mol.set_formal_charge(self.idx, self._old_charge + self.delta)

    def undo(self, mol: Molecule) -> None:
        mol.set_formal_charge(self.idx, self._old_charge)

    def description(self) -> str:
        sign = "+" if self.delta > 0 else ""
        return f"Change charge on atom {self.idx} by {sign}{self.delta}"


class MoveAtomCommand(Command):
    def __init__(self, idx: int, old_x: float, old_y: float,
                 new_x: float, new_y: float):
        self.idx = idx
        self.old_x = old_x
        self.old_y = old_y
        self.new_x = new_x
        self.new_y = new_y

    def execute(self, mol: Molecule) -> None:
        mol.set_atom_position(self.idx, self.new_x, self.new_y)

    def undo(self, mol: Molecule) -> None:
        mol.set_atom_position(self.idx, self.old_x, self.old_y)

    def description(self) -> str:
        return f"Move atom {self.idx}"


class BulkDeleteCommand(_SnapshotCommand):
    """Delete a set of atoms and their bonds with exact snapshot-based undo."""

    def __init__(self, indices: list[int]):
        super().__init__()
        self._indices = sorted(indices, reverse=True)

    def _apply(self, mol: Molecule) -> None:
        for idx in self._indices:
            mol.remove_atom(idx)

    def description(self) -> str:
        return f"Delete {len(self._indices)} atoms"


class FormatLayoutCommand(_SnapshotCommand):
    """Coordinates and their stereo markings are one atomic, undoable edit."""

    def _apply(self, mol: Molecule) -> None:
        from ..core.layout import format_2d
        mol._mol = format_2d(mol)._mol

    def description(self) -> str:
        return "Format 2D layout"


class HistoryManager:
    """Manages an undo/redo stack of commands against a Molecule."""

    def __init__(self, molecule: Molecule):
        self._molecule = molecule
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self._on_change: Callable[[], None] | None = None

    @property
    def molecule(self) -> Molecule:
        return self._molecule

    @molecule.setter
    def molecule(self, mol: Molecule) -> None:
        self._molecule = mol
        self._undo_stack.clear()
        self._redo_stack.clear()

    def set_on_change(self, callback: Callable[[], None]) -> None:
        self._on_change = callback

    def execute(self, cmd: Command) -> None:
        cmd.execute(self._molecule)
        self._undo_stack.append(cmd)
        self._redo_stack.clear()
        if self._on_change:
            self._on_change()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        cmd.undo(self._molecule)
        self._redo_stack.append(cmd)
        if self._on_change:
            self._on_change()
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.execute(self._molecule)
        self._undo_stack.append(cmd)
        if self._on_change:
            self._on_change()
        return True

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0
