"""Editing tools for the molecular canvas (Strategy pattern)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QLineF, QPointF, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsSceneMouseEvent

from ..core.molecule import BondType, Molecule
from .canvas import SCALE, AtomItem, BondItem, MoleculeScene
from .history import (
    AddAtomCommand,
    AddBondCommand,
    ChangeBondTypeCommand,
    ChangeChargeCommand,
    ChangeElementCommand,
    HistoryManager,
    RemoveAtomCommand,
    RemoveBondCommand,
)

if TYPE_CHECKING:
    from .canvas import MoleculeCanvas

# Bond-type cycle for click-on-bond behaviour
_BOND_CYCLE = [BondType.SINGLE, BondType.DOUBLE, BondType.TRIPLE]


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
        pass


# ------------------------------------------------------------------
# Select tool — click to highlight, drag atoms to move
# ------------------------------------------------------------------

class SelectTool(Tool):
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

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._dragging:
            self._dragging.setPos(event.scenePos())

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._dragging:
            new_pos = event.scenePos()
            idx = self._dragging.atom_idx
            self._history.molecule.set_atom_position(
                idx, new_pos.x() / SCALE, new_pos.y() / SCALE
            )
            self._dragging.set_highlighted(False)
            self._dragging = None

    def deactivate(self) -> None:
        self._dragging = None


# ------------------------------------------------------------------
# Bond tool — drag from atom to create bonds; click bond to cycle
# ------------------------------------------------------------------

class BondTool(Tool):
    """Drag from an atom to another atom (or empty space) to create bonds.

    - **Drag atom → atom**: create / change bond between the two atoms.
    - **Drag atom → empty**: create a new carbon atom and bond to it.
    - **Click on a bond**: cycle its type (single → double → triple → …).
    """

    name = "bond"

    def __init__(self, scene: MoleculeScene, history: HistoryManager,
                 bond_type: BondType = BondType.SINGLE):
        super().__init__(scene, history)
        self.bond_type = bond_type
        self._source: Optional[AtomItem] = None
        self._rubber: Optional[QGraphicsLineItem] = None
        self._target_highlight: Optional[AtomItem] = None

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        atom = self._scene.atom_at_pos(pos)

        if atom:
            # Start a rubber-band drag from this atom
            self._source = atom
            atom.set_highlighted(True)
            self._rubber = QGraphicsLineItem()
            self._rubber.setPen(
                QPen(QColor("#4A90D9"), 2, Qt.PenStyle.DashLine)
            )
            self._rubber.setZValue(100)
            self._rubber.setLine(QLineF(atom.pos(), pos))
            self._scene.addItem(self._rubber)
            return

        # No atom under cursor — check for bond click
        bond = self._scene.bond_at_pos(pos)
        if bond:
            self._cycle_bond(bond)

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._source or not self._rubber:
            return
        pos = event.scenePos()
        self._rubber.setLine(QLineF(self._source.pos(), pos))

        # Highlight the target atom if hovering over one
        target = self._scene.atom_at_pos(pos)
        if target and target.atom_idx != self._source.atom_idx:
            if self._target_highlight and self._target_highlight is not target:
                self._target_highlight.set_highlighted(False)
            target.set_highlighted(True)
            self._target_highlight = target
        elif self._target_highlight:
            self._target_highlight.set_highlighted(False)
            self._target_highlight = None

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._source:
            return

        pos = event.scenePos()
        target = self._scene.atom_at_pos(pos)

        # Save indices and positions BEFORE cleanup — the canvas refresh
        # triggered by history commands deletes all scene items.
        source_idx = self._source.atom_idx
        source_pos = self._source.pos()
        target_idx = target.atom_idx if target else None

        # Remove rubber band and highlights first
        self._cleanup()

        if target_idx is not None and target_idx != source_idx:
            # Released on a different atom → create or modify bond
            existing = self._history.molecule.get_bond_info(source_idx, target_idx)
            if existing:
                if existing.bond_type != self.bond_type:
                    self._history.execute(
                        ChangeBondTypeCommand(source_idx, target_idx, self.bond_type)
                    )
            else:
                self._history.execute(
                    AddBondCommand(source_idx, target_idx, self.bond_type)
                )
        elif target_idx is None:
            # Released on empty space → create new atom + bond
            x = pos.x() / SCALE
            y = pos.y() / SCALE
            # Only create if the user actually dragged (not just clicked)
            dx = pos.x() - source_pos.x()
            dy = pos.y() - source_pos.y()
            if dx * dx + dy * dy > 20 * 20:  # min drag distance
                cmd_atom = AddAtomCommand("C", x, y)
                self._history.execute(cmd_atom)
                if cmd_atom.created_idx is not None:
                    self._history.execute(
                        AddBondCommand(
                            source_idx,
                            cmd_atom.created_idx,
                            self.bond_type,
                        )
                    )

    def _cycle_bond(self, bond_item: BondItem):
        current = bond_item.bond_type
        try:
            idx = _BOND_CYCLE.index(current)
            next_type = _BOND_CYCLE[(idx + 1) % len(_BOND_CYCLE)]
        except ValueError:
            next_type = BondType.SINGLE
        self._history.execute(
            ChangeBondTypeCommand(bond_item.a1_idx, bond_item.a2_idx, next_type)
        )

    def _cleanup(self):
        if self._source:
            self._source.set_highlighted(False)
            self._source = None
        if self._target_highlight:
            self._target_highlight.set_highlighted(False)
            self._target_highlight = None
        if self._rubber:
            self._scene.removeItem(self._rubber)
            self._rubber = None

    def deactivate(self) -> None:
        self._cleanup()


# ------------------------------------------------------------------
# Atom tool — click to add / change atoms
# ------------------------------------------------------------------

class AtomTool(Tool):
    """Click empty space to add an atom. Click existing atom to change element."""

    name = "atom"

    def __init__(self, scene: MoleculeScene, history: HistoryManager,
                 element: str = "C"):
        super().__init__(scene, history)
        self.element = element

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        atom = self._scene.atom_at_pos(pos)
        if atom:
            if atom.element != self.element:
                self._history.execute(
                    ChangeElementCommand(atom.atom_idx, self.element)
                )
        else:
            x = pos.x() / SCALE
            y = pos.y() / SCALE
            self._history.execute(AddAtomCommand(self.element, x, y))


# ------------------------------------------------------------------
# Eraser tool — click to delete atoms or bonds
# ------------------------------------------------------------------

class EraseTool(Tool):
    """Click an atom or bond to delete it."""

    name = "eraser"

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        atom = self._scene.atom_at_pos(pos)
        if atom:
            self._history.execute(RemoveAtomCommand(atom.atom_idx))
            return
        bond = self._scene.bond_at_pos(pos)
        if bond:
            self._history.execute(RemoveBondCommand(bond.a1_idx, bond.a2_idx))


# ------------------------------------------------------------------
# Charge tool — click atom to increase / decrease formal charge
# ------------------------------------------------------------------

class ChargeTool(Tool):
    """Click an atom to adjust its formal charge by *delta* (+1 or −1)."""

    name = "charge"

    def __init__(self, scene: MoleculeScene, history: HistoryManager,
                 delta: int = +1):
        super().__init__(scene, history)
        self.delta = delta

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        atom = self._scene.atom_at_pos(event.scenePos())
        if atom:
            self._history.execute(ChangeChargeCommand(atom.atom_idx, self.delta))
