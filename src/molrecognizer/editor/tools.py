"""Editing tools for the molecular canvas (Strategy pattern).

All tools share the same atom / bond interactions:

- **Click atom** (no drag): substitute with the selected element.
- **Drag from atom**: rubber-band → create a new bond (to existing atom
  or a new carbon atom).
- **Click bond**: cycle its type (single → double → triple).

The only difference between tools is what happens on empty-space clicks:

- **Select / Bond**: nothing.
- **Atom**: add a new atom.
- **Eraser**: separate — deletes atoms / bonds on click.
- **Charge**: separate — adjusts formal charge on click.
"""

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

_BOND_CYCLE = [BondType.SINGLE, BondType.DOUBLE, BondType.TRIPLE]
_MIN_DRAG_DIST_SQ = 20 * 20  # px² — minimum drag to create a bond


# ======================================================================
# Base tool with shared atom / bond interaction
# ======================================================================

class Tool(ABC):
    """Base class for canvas editing tools.

    Provides unified atom-click (substitute), atom-drag (create bond),
    and bond-click (cycle type) behaviour.  Subclasses override
    :meth:`_on_empty_press` for tool-specific empty-space actions.
    """

    name: str = "tool"

    def __init__(self, scene: MoleculeScene, history: HistoryManager):
        self._scene = scene
        self._history = history
        self.element: str = "C"
        self.bond_type: BondType = BondType.SINGLE

        self._source: Optional[AtomItem] = None
        self._rubber: Optional[QGraphicsLineItem] = None
        self._target_highlight: Optional[AtomItem] = None
        self._press_pos: QPointF = QPointF()
        self._did_drag: bool = False

    # -- public API (called by event filter) --------------------------------

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        self._press_pos = pos
        self._did_drag = False

        atom = self._scene.atom_at_pos(pos)
        if atom:
            self._start_drag(atom, pos)
            return

        bond = self._scene.bond_at_pos(pos)
        if bond:
            self._cycle_bond(bond)
            return

        self._on_empty_press(pos)

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._source or not self._rubber:
            return
        pos = event.scenePos()
        self._rubber.setLine(QLineF(self._source.pos(), pos))

        dx = pos.x() - self._press_pos.x()
        dy = pos.y() - self._press_pos.y()
        if dx * dx + dy * dy > _MIN_DRAG_DIST_SQ:
            self._did_drag = True

        # Highlight target atom while dragging
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
        source_idx = self._source.atom_idx
        source_pos = self._source.pos()
        target = self._scene.atom_at_pos(pos)
        target_idx = target.atom_idx if target else None
        did_drag = self._did_drag  # save before cleanup resets it

        self._cleanup()

        if did_drag:
            # Dragged — create bond
            if target_idx is not None and target_idx != source_idx:
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
                x = pos.x() / SCALE
                y = pos.y() / SCALE
                cmd = AddAtomCommand(self.element, x, y)
                self._history.execute(cmd)
                if cmd.created_idx is not None:
                    self._history.execute(
                        AddBondCommand(source_idx, cmd.created_idx, self.bond_type)
                    )
        else:
            # Clicked without drag — tool-specific action on atom
            if target_idx is not None:
                self._on_atom_click(source_idx)

    def deactivate(self) -> None:
        self._cleanup()

    # -- subclass hook ------------------------------------------------------

    def _on_atom_click(self, atom_idx: int) -> None:
        """Called when an atom is clicked without dragging.  Default:
        substitute with the selected element."""
        src_elem = self._history.molecule.get_atom_info(atom_idx).element
        if src_elem != self.element:
            self._history.execute(ChangeElementCommand(atom_idx, self.element))

    def _on_empty_press(self, pos: QPointF) -> None:
        """Called when the user clicks empty canvas. Override in subclasses."""
        pass

    # -- internals ----------------------------------------------------------

    def _start_drag(self, atom: AtomItem, pos: QPointF):
        self._source = atom
        self._rubber = QGraphicsLineItem()
        self._rubber.setPen(QPen(QColor("#4A90D9"), 2, Qt.PenStyle.DashLine))
        self._rubber.setZValue(100)
        self._rubber.setLine(QLineF(atom.pos(), pos))
        self._scene.addItem(self._rubber)

    def _cycle_bond(self, bond_item: BondItem):
        """Change a bond to the currently selected bond type.  If it already
        matches, cycle to the next type instead."""
        current = bond_item.bond_type
        if current != self.bond_type:
            next_type = self.bond_type
        else:
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
            try:
                self._source.set_highlighted(False)
            except RuntimeError:
                pass
            self._source = None
        if self._target_highlight:
            try:
                self._target_highlight.set_highlighted(False)
            except RuntimeError:
                pass
            self._target_highlight = None
        if self._rubber:
            try:
                self._scene.removeItem(self._rubber)
            except RuntimeError:
                pass
            self._rubber = None
        self._did_drag = False


# ======================================================================
# Concrete tools
# ======================================================================

class SelectTool(Tool):
    """Default tool — click atom to substitute, drag to create bond,
    click bond to cycle, click empty does nothing."""
    name = "select"


class BondTool(Tool):
    """Like Select, but clicking an atom adds a new bonded atom
    (of the selected element) if the atom's valence isn't full,
    rather than substituting."""

    name = "bond"

    def _on_atom_click(self, atom_idx: int) -> None:
        from ..core.valence import STANDARD_VALENCES
        import math

        mol = self._history.molecule
        info = mol.get_atom_info(atom_idx)

        # Compute bond-order sum (aromatic ≈ 1.5, not 2)
        _bv = {BondType.SINGLE: 1, BondType.DOUBLE: 2,
               BondType.TRIPLE: 3, BondType.AROMATIC: 1.5}
        bos = 0.0
        for b in mol.get_all_bonds():
            if b.begin_atom_idx == atom_idx or b.end_atom_idx == atom_idx:
                bos += _bv.get(b.bond_type, 1)

        # Effective max valence
        max_val = 4  # fallback
        if info.element in STANDARD_VALENCES:
            max_val = max(v + info.formal_charge
                         for v in STANDARD_VALENCES[info.element])

        bond_order = {BondType.SINGLE: 1, BondType.DOUBLE: 2,
                      BondType.TRIPLE: 3, BondType.AROMATIC: 1.5}.get(self.bond_type, 1)

        if math.ceil(bos) + bond_order <= max_val:
            # Room for a new bond — add atom + bond.
            # Place the new atom in the direction with least overlap
            # with existing bonds.
            import math
            dist = 1.5  # coordinate units
            neighbor_angles: list[float] = []
            for ni in info.neighbors:
                ni_info = mol.get_atom_info(ni)
                dx = ni_info.x - info.x
                dy = ni_info.y - info.y
                neighbor_angles.append(math.atan2(dy, dx))

            if not neighbor_angles:
                # No neighbors — point right
                best_angle = 0.0
            elif len(neighbor_angles) == 1:
                # One neighbor — go opposite + 60° offset for zig-zag
                best_angle = neighbor_angles[0] + math.pi * 2 / 3
            else:
                # Multiple neighbors — find the largest angular gap
                neighbor_angles.sort()
                best_angle = 0.0
                max_gap = 0.0
                for i in range(len(neighbor_angles)):
                    a1 = neighbor_angles[i]
                    a2 = neighbor_angles[(i + 1) % len(neighbor_angles)]
                    gap = (a2 - a1) % (2 * math.pi)
                    if gap > max_gap:
                        max_gap = gap
                        best_angle = a1 + gap / 2

            nx = info.x + dist * math.cos(best_angle)
            ny = info.y + dist * math.sin(best_angle)

            cmd = AddAtomCommand(self.element, nx, ny)
            self._history.execute(cmd)
            if cmd.created_idx is not None:
                self._history.execute(
                    AddBondCommand(atom_idx, cmd.created_idx, self.bond_type)
                )
        else:
            # Valence full — fall back to element substitution
            super()._on_atom_click(atom_idx)


class AtomTool(Tool):
    """Like Select, but clicking empty space adds a new atom."""

    name = "atom"

    def _on_empty_press(self, pos: QPointF) -> None:
        x = pos.x() / SCALE
        y = pos.y() / SCALE
        self._history.execute(AddAtomCommand(self.element, x, y))


# ======================================================================
# Eraser tool (separate — doesn't share base atom/bond behaviour)
# ======================================================================

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

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        pass

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        pass


# ======================================================================
# Charge tool (separate — adjusts formal charge)
# ======================================================================

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

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        pass

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        pass
