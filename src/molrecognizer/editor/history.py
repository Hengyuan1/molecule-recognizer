"""Undo/redo command stack for molecule editing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from ..core.molecule import BondType, Molecule


class Command(ABC):
    """Base class for reversible editing commands."""

    @abstractmethod
    def execute(self, mol: Molecule) -> None: ...

    @abstractmethod
    def undo(self, mol: Molecule) -> None: ...

    @abstractmethod
    def description(self) -> str: ...


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


class RemoveAtomCommand(Command):
    def __init__(self, idx: int):
        self.idx = idx
        self._saved_element: str = ""
        self._saved_x: float = 0
        self._saved_y: float = 0
        self._saved_charge: int = 0
        self._saved_bonds: list[tuple[int, int, BondType]] = []

    def execute(self, mol: Molecule) -> None:
        # Save atom state for undo
        info = mol.get_atom_info(self.idx)
        self._saved_element = info.element
        self._saved_x = info.x
        self._saved_y = info.y
        self._saved_charge = info.formal_charge
        # Save bonds connected to this atom
        self._saved_bonds = []
        for bond in mol.get_all_bonds():
            if bond.begin_atom_idx == self.idx or bond.end_atom_idx == self.idx:
                self._saved_bonds.append(
                    (bond.begin_atom_idx, bond.end_atom_idx, bond.bond_type)
                )
        mol.remove_atom(self.idx)

    def undo(self, mol: Molecule) -> None:
        # Re-add atom at original index position
        new_idx = mol.add_atom(
            self._saved_element, self._saved_x, self._saved_y, self._saved_charge
        )
        # Re-add bonds (indices may have shifted — this is a best-effort restore)
        for a1, a2, bt in self._saved_bonds:
            try:
                mol.add_bond(a1, a2, bt)
            except Exception:
                pass  # Bond restore may fail if indices shifted

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


class RemoveBondCommand(Command):
    def __init__(self, a1: int, a2: int):
        self.a1 = a1
        self.a2 = a2
        self._saved_type: BondType = BondType.SINGLE

    def execute(self, mol: Molecule) -> None:
        info = mol.get_bond_info(self.a1, self.a2)
        if info:
            self._saved_type = info.bond_type
        mol.remove_bond(self.a1, self.a2)

    def undo(self, mol: Molecule) -> None:
        mol.add_bond(self.a1, self.a2, self._saved_type)

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

    def execute(self, mol: Molecule) -> None:
        info = mol.get_atom_info(self.idx)
        self._old_element = info.element
        mol.set_atom_element(self.idx, self.new_element)

    def undo(self, mol: Molecule) -> None:
        mol.set_atom_element(self.idx, self._old_element)

    def description(self) -> str:
        return f"Change atom {self.idx} to {self.new_element}"


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
