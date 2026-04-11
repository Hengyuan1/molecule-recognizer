"""Editing tools for the molecular canvas (Strategy pattern)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QGraphicsSceneMouseEvent

from ..core.molecule import BondType, Molecule
from .canvas import SCALE, AtomItem, BondItem, MoleculeScene
from .history import (
    AddAtomCommand,
    AddBondCommand,
    ChangeBondTypeCommand,
    ChangeElementCommand,
    HistoryManager,
    RemoveAtomCommand,
    RemoveBondCommand,
)

if TYPE_CHECKING:
    from .canvas import MoleculeCanvas


class Tool(ABC):
    """Base class for canvas editing tools."""

    name: str = "tool"

    def __init__(self, scene: MoleculeScene, history: HistoryManager):
        self._scene = scene
        self._history = history

    @abstractmethod
    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None: ...

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        pass

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        pass

    def deactivate(self) -> None:
        """Called when switching away from this tool."""
        pass


class SelectTool(Tool):
    """Click to select atoms/bonds. Drag atoms to move them."""

    name = "select"

    def __init__(self, scene: MoleculeScene, history: HistoryManager):
        super().__init__(scene, history)
        self._dragging: Optional[AtomItem] = None
        self._drag_start: QPointF = QPointF()

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        atom = self._scene.atom_at_pos(pos)
        if atom:
            self._dragging = atom
            self._drag_start = atom.pos()
            atom.set_highlighted(True)
            return

        bond = self._scene.bond_at_pos(pos)
        if bond:
            bond.set_highlighted(True)
            return

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._dragging:
            self._dragging.setPos(event.scenePos())

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._dragging:
            new_pos = event.scenePos()
            # Update molecule coordinates
            idx = self._dragging.atom_idx
            self._history.molecule.set_atom_position(idx, new_pos.x() / SCALE, new_pos.y() / SCALE)
            self._dragging.set_highlighted(False)
            self._dragging = None

    def deactivate(self) -> None:
        self._dragging = None


class BondTool(Tool):
    """Click two atoms to add or modify a bond between them."""

    name = "bond"

    def __init__(self, scene: MoleculeScene, history: HistoryManager,
                 bond_type: BondType = BondType.SINGLE):
        super().__init__(scene, history)
        self.bond_type = bond_type
        self._first_atom: Optional[AtomItem] = None

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        atom = self._scene.atom_at_pos(pos)
        if not atom:
            self._reset()
            return

        if self._first_atom is None:
            self._first_atom = atom
            atom.set_highlighted(True)
        else:
            if atom.atom_idx == self._first_atom.atom_idx:
                self._reset()
                return
            a1 = self._first_atom.atom_idx
            a2 = atom.atom_idx
            existing = self._history.molecule.get_bond_info(a1, a2)
            if existing:
                # Change bond type if different
                if existing.bond_type != self.bond_type:
                    cmd = ChangeBondTypeCommand(a1, a2, self.bond_type)
                    self._history.execute(cmd)
            else:
                cmd = AddBondCommand(a1, a2, self.bond_type)
                self._history.execute(cmd)
            self._reset()

    def _reset(self):
        if self._first_atom:
            self._first_atom.set_highlighted(False)
        self._first_atom = None

    def deactivate(self) -> None:
        self._reset()


class AtomTool(Tool):
    """Click empty space to add an atom. Click existing atom to change its element."""

    name = "atom"

    def __init__(self, scene: MoleculeScene, history: HistoryManager,
                 element: str = "C"):
        super().__init__(scene, history)
        self.element = element

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        atom = self._scene.atom_at_pos(pos)
        if atom:
            # Change existing atom's element
            if atom.element != self.element:
                cmd = ChangeElementCommand(atom.atom_idx, self.element)
                self._history.execute(cmd)
        else:
            # Add new atom at click position
            x = pos.x() / SCALE
            y = pos.y() / SCALE
            cmd = AddAtomCommand(self.element, x, y)
            self._history.execute(cmd)


class EraseTool(Tool):
    """Click an atom or bond to delete it."""

    name = "eraser"

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        atom = self._scene.atom_at_pos(pos)
        if atom:
            cmd = RemoveAtomCommand(atom.atom_idx)
            self._history.execute(cmd)
            return

        bond = self._scene.bond_at_pos(pos)
        if bond:
            cmd = RemoveBondCommand(bond.a1_idx, bond.a2_idx)
            self._history.execute(cmd)
