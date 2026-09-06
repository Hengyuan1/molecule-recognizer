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
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
)

from ..core.molecule import BondType, Molecule
from .canvas import (
    HIT_RADIUS, AtomItem, BondItem, MoleculeScene,
    molecule_to_scene, scene_to_molecule,
)
from .history import (
    AddAtomCommand,
    AddBondCommand,
    BulkDeleteCommand,
    ChangeBondTypeCommand,
    ChangeChargeCommand,
    ChangeElementCommand,
    CompoundCommand,
    HistoryManager,
    MoveAtomCommand,
    RemoveAtomCommand,
    RemoveBondCommand,
)

if TYPE_CHECKING:
    from .canvas import MoleculeCanvas

_BOND_CYCLE = [BondType.SINGLE, BondType.DOUBLE, BondType.TRIPLE]
_MIN_DRAG_DIST_SQ = 20 * 20  # px² — minimum drag to create a bond
_BASE_DIST = 1.5              # default bond length in coordinate units
_MIN_ATOM_DIST = 0.8          # minimum distance between any two atoms


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
        bond = self._scene.bond_at_pos(pos)

        if atom and bond:
            # Both nearby — prefer atom only when very close to its centre
            d = atom.pos() - pos
            if d.x() * d.x() + d.y() * d.y() < HIT_RADIUS * HIT_RADIUS:
                self._start_drag(atom, pos)
            else:
                self._cycle_bond(bond)
            return

        if atom:
            self._start_drag(atom, pos)
            return

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
                x, y = scene_to_molecule(pos)
                atom_cmd = AddAtomCommand(self.element, x, y)
                bond_cmd = AddBondCommand(source_idx, -1, self.bond_type)
                # Execute as compound so undo removes both at once
                compound = CompoundCommand([atom_cmd, bond_cmd])
                # We need the created index before adding the bond,
                # so execute manually:
                atom_cmd.execute(self._history.molecule)
                if atom_cmd.created_idx is not None:
                    bond_cmd.a1 = source_idx
                    bond_cmd.a2 = atom_cmd.created_idx
                    bond_cmd.execute(self._history.molecule)
                    self._history._undo_stack.append(compound)
                    self._history._redo_stack.clear()
                    if self._history._on_change:
                        self._history._on_change()
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
        """Cycle a bond: single → double → triple → single."""
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

_SEL_PEN = QPen(QColor("#1a73e8"), 1.5, Qt.PenStyle.DashLine)
_SEL_BRUSH = QColor(26, 115, 232, 25)


class SelectTool(Tool):
    """Select tool — click atom to substitute / drag to move, click bond
    to cycle, drag on empty space to draw a selection box.

    Selected atoms and bonds can be moved as a group or deleted with
    the Delete key.  Click on empty space to clear the selection.
    """
    name = "select"

    def __init__(self, scene: MoleculeScene, history: HistoryManager):
        super().__init__(scene, history)
        # Single-atom drag
        self._drag_atom: Optional[AtomItem] = None
        self._drag_ox: float = 0.0
        self._drag_oy: float = 0.0
        # Selection box
        self._sel_rect: Optional[QGraphicsRectItem] = None
        # Current selection
        self._selected: set[int] = set()                     # atom indices
        self._selected_bonds: set[tuple[int, int]] = set()   # (min, max)
        # Group drag
        self._group_drag = False
        self._group_origins: dict[int, tuple[float, float]] = {}

    # -- selection highlighting --------------------------------------------

    def _highlight_selection(self):
        for idx in self._selected:
            item = self._scene.get_atom_item(idx)
            if item:
                item.set_highlighted(True)
        for key in self._selected_bonds:
            bi = self._scene._bond_items.get(key)
            if bi:
                bi.set_highlighted(True)

    def _clear_selection(self):
        for idx in self._selected:
            item = self._scene.get_atom_item(idx)
            if item:
                try:
                    item.set_highlighted(False)
                except RuntimeError:
                    pass
        for key in self._selected_bonds:
            bi = self._scene._bond_items.get(key)
            if bi:
                try:
                    bi.set_highlighted(False)
                except RuntimeError:
                    pass
        self._selected.clear()
        self._selected_bonds.clear()

    def _compute_selected_bonds(self):
        """Find bonds whose both endpoints are in the atom selection."""
        self._selected_bonds.clear()
        for key, bi in self._scene._bond_items.items():
            if bi.a1_idx in self._selected and bi.a2_idx in self._selected:
                self._selected_bonds.add(key)

    def _is_on_selection(self, pos) -> bool:
        """True if *pos* is on a selected atom or a selected bond."""
        atom = self._scene.atom_at_pos(pos)
        if atom and atom.atom_idx in self._selected:
            return True
        bond = self._scene.bond_at_pos(pos)
        if bond:
            key = (min(bond.a1_idx, bond.a2_idx), max(bond.a1_idx, bond.a2_idx))
            if key in self._selected_bonds:
                return True
        return False

    # -- public: delete selection (called by EditorWidget on Delete key) ----

    def delete_selection(self):
        if not self._selected:
            return
        indices = [i for i in self._selected
                   if i < self._history.molecule.num_atoms]
        if not indices:
            return
        cmd = BulkDeleteCommand(indices)
        cmd.execute(self._history.molecule)
        self._history._undo_stack.append(cmd)
        self._history._redo_stack.clear()
        self._selected.clear()
        self._selected_bonds.clear()
        if self._history._on_change:
            self._history._on_change()

    # -- mouse events ------------------------------------------------------

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        self._press_pos = pos
        self._did_drag = False
        self._drag_atom = None
        self._group_drag = False

        # Clicking on anything in the selection → start group drag
        if self._selected and self._is_on_selection(pos):
            self._group_drag = True
            self._group_origins.clear()
            for idx in self._selected:
                info = self._history.molecule.get_atom_info(idx)
                self._group_origins[idx] = (info.x, info.y)
            return

        # Clicking elsewhere clears the selection
        if self._selected:
            self._clear_selection()

        atom = self._scene.atom_at_pos(pos)
        bond = self._scene.bond_at_pos(pos)

        if atom and bond:
            d = atom.pos() - pos
            if d.x() * d.x() + d.y() * d.y() < HIT_RADIUS * HIT_RADIUS:
                self._begin_atom_drag(atom)
            else:
                self._cycle_bond(bond)
            return

        if atom:
            self._begin_atom_drag(atom)
            return
        if bond:
            self._cycle_bond(bond)
            return

        # Empty space → start selection box
        self._sel_rect = QGraphicsRectItem()
        self._sel_rect.setPen(_SEL_PEN)
        self._sel_rect.setBrush(_SEL_BRUSH)
        self._sel_rect.setZValue(100)
        self._scene.addItem(self._sel_rect)

    def _begin_atom_drag(self, atom: AtomItem):
        self._drag_atom = atom
        info = self._history.molecule.get_atom_info(atom.atom_idx)
        self._drag_ox = info.x
        self._drag_oy = info.y

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        dx = pos.x() - self._press_pos.x()
        dy = pos.y() - self._press_pos.y()
        if dx * dx + dy * dy > _MIN_DRAG_DIST_SQ:
            self._did_drag = True

        # Group drag
        if self._group_drag and self._did_drag:
            delta_x, delta_y = scene_to_molecule(pos - self._press_pos)
            moved: set[int] = set()
            for idx in self._selected:
                ox, oy = self._group_origins[idx]
                atom_item = self._scene.get_atom_item(idx)
                if atom_item:
                    atom_item.setPos(molecule_to_scene(ox + delta_x, oy + delta_y))
                moved.add(idx)
            # Update bonds that touch any moved atom
            for bi in self._scene._bond_items.values():
                if bi.a1_idx in moved or bi.a2_idx in moved:
                    p1 = self._scene.get_atom_item(bi.a1_idx)
                    p2 = self._scene.get_atom_item(bi.a2_idx)
                    if p1 and p2:
                        bi.update_positions(p1.pos(), p2.pos())
            return

        # Single-atom drag
        if self._drag_atom:
            self._drag_atom.setPos(pos)
            idx = self._drag_atom.atom_idx
            for bond_item in self._scene._bond_items.values():
                if bond_item.a1_idx == idx:
                    other = self._scene.get_atom_item(bond_item.a2_idx)
                    if other:
                        bond_item.update_positions(pos, other.pos())
                elif bond_item.a2_idx == idx:
                    other = self._scene.get_atom_item(bond_item.a1_idx)
                    if other:
                        bond_item.update_positions(other.pos(), pos)
            return

        # Selection box
        if self._sel_rect:
            from PySide6.QtCore import QRectF
            r = QRectF(self._press_pos, pos).normalized()
            self._sel_rect.setRect(r)

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()

        # Group drag release
        if self._group_drag:
            if self._did_drag:
                delta_x, delta_y = scene_to_molecule(pos - self._press_pos)
                cmds = []
                for idx in self._selected:
                    ox, oy = self._group_origins[idx]
                    cmds.append(MoveAtomCommand(idx, ox, oy,
                                                ox + delta_x, oy + delta_y))
                for cmd in cmds:
                    cmd.execute(self._history.molecule)
                compound = CompoundCommand(cmds)
                self._history._undo_stack.append(compound)
                self._history._redo_stack.clear()
                if self._history._on_change:
                    self._history._on_change()
                # Re-highlight after canvas refresh
                self._highlight_selection()
            self._group_drag = False
            self._group_origins.clear()
            return

        # Single-atom drag release
        if self._drag_atom:
            atom_idx = self._drag_atom.atom_idx
            did_drag = self._did_drag
            self._drag_atom = None
            self._did_drag = False
            if did_drag:
                new_x, new_y = scene_to_molecule(pos)
                self._history.execute(
                    MoveAtomCommand(atom_idx, self._drag_ox, self._drag_oy,
                                    new_x, new_y)
                )
            else:
                self._on_atom_click(atom_idx)
            return

        # Selection box release
        if self._sel_rect:
            rect = self._sel_rect.rect()
            self._scene.removeItem(self._sel_rect)
            self._sel_rect = None
            if self._did_drag:
                for idx, atom_item in self._scene._atom_items.items():
                    if rect.contains(atom_item.pos()):
                        self._selected.add(idx)
                self._compute_selected_bonds()
                self._highlight_selection()

    def deactivate(self) -> None:
        self._clear_selection()
        self._drag_atom = None
        self._did_drag = False
        self._group_drag = False
        if self._sel_rect:
            try:
                self._scene.removeItem(self._sel_rect)
            except RuntimeError:
                pass
            self._sel_rect = None


class BondTool(Tool):
    """Like Select, but clicking an atom adds a new bonded atom
    (of the selected element) if the atom's valence isn't full,
    rather than substituting.

    Bond direction follows VSEPR-like rules:
    - 120° (trigonal) when existing + new bond orders sum < 4
    - 180° (linear) when existing + new bond orders sum >= 4
      (e.g. triple+single, double+double, triple on existing atom)
    New atoms are placed to avoid clashing with existing atoms/bonds;
    bond length is extended if necessary.
    """

    name = "bond"

    def _cycle_bond(self, bond_item: BondItem):
        """When wedge/dash is selected, set the bond to that type
        (or toggle back to single).  Otherwise fall through to the
        normal single → double → triple cycle."""
        if self.bond_type in (BondType.WEDGE, BondType.DASH):
            current = bond_item.bond_type
            new_type = (BondType.SINGLE if current == self.bond_type
                        else self.bond_type)
            self._history.execute(
                ChangeBondTypeCommand(
                    bond_item.a1_idx, bond_item.a2_idx, new_type)
            )
        else:
            super()._cycle_bond(bond_item)

    def _on_atom_click(self, atom_idx: int) -> None:
        import math
        from ..core.valence import STANDARD_VALENCES

        mol = self._history.molecule
        info = mol.get_atom_info(atom_idx)

        # Bond-order lookup
        _bv = {BondType.SINGLE: 1, BondType.DOUBLE: 2,
               BondType.TRIPLE: 3, BondType.AROMATIC: 1.5,
               BondType.WEDGE: 1, BondType.DASH: 1}

        # Compute bond-order sum and max existing bond order
        bos = 0.0
        max_existing = 0.0
        for b in mol.get_all_bonds():
            if b.begin_atom_idx == atom_idx or b.end_atom_idx == atom_idx:
                order = _bv.get(b.bond_type, 1)
                bos += order
                if order > max_existing:
                    max_existing = order

        new_order = _bv.get(self.bond_type, 1)
        needed = math.ceil(bos) + new_order

        # Smallest standard valence that fits the current + new bonds
        max_val = 4  # fallback
        if info.element in STANDARD_VALENCES:
            for v in sorted(STANDARD_VALENCES[info.element]):
                if v + info.formal_charge >= needed:
                    max_val = v + info.formal_charge
                    break
            else:
                max_val = max(v + info.formal_charge
                              for v in STANDARD_VALENCES[info.element])

        if needed > max_val:
            # Valence full — fall back to element substitution
            super()._on_atom_click(atom_idx)
            return

        # Determine ideal angle ------------------------------------------------
        n_existing = len(info.neighbors)

        if max_existing + new_order >= 4:
            # sp / linear: triple+single, double+double, etc.
            ideal_angle = math.pi                       # 180°
        elif n_existing >= 3:
            # 4+ total bonds — distribute evenly (90° for 4, 72° for 5, …)
            ideal_angle = 2 * math.pi / (n_existing + 1)
        else:
            # 0–2 existing bonds — always 120° (zig-zag / trigonal)
            ideal_angle = 2 * math.pi / 3               # 120°

        nx, ny = _find_bond_position(mol, atom_idx, info, ideal_angle)

        atom_cmd = AddAtomCommand(self.element, nx, ny)
        bond_cmd = AddBondCommand(atom_idx, -1, self.bond_type)
        # Execute as compound so undo removes atom + bond together
        atom_cmd.execute(self._history.molecule)
        if atom_cmd.created_idx is not None:
            bond_cmd.a2 = atom_cmd.created_idx
            bond_cmd.execute(self._history.molecule)
            compound = CompoundCommand([atom_cmd, bond_cmd])
            self._history._undo_stack.append(compound)
            self._history._redo_stack.clear()
            if self._history._on_change:
                self._history._on_change()


class AtomTool(Tool):
    """Like Select, but clicking empty space adds a new atom."""

    name = "atom"

    def _on_empty_press(self, pos: QPointF) -> None:
        x, y = scene_to_molecule(pos)
        self._history.execute(AddAtomCommand(self.element, x, y))


# ======================================================================
# Eraser tool (separate — doesn't share base atom/bond behaviour)
# ======================================================================

class EraseTool(Tool):
    """Click an atom or bond to delete it.  Drag on empty space to draw
    a selection box — everything inside is deleted on release."""
    name = "eraser"

    def __init__(self, scene: MoleculeScene, history: HistoryManager):
        super().__init__(scene, history)
        self._sel_rect: Optional[QGraphicsRectItem] = None
        self._box_mode = False

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        self._press_pos = pos
        self._did_drag = False
        self._box_mode = False

        atom = self._scene.atom_at_pos(pos)
        if atom:
            self._history.execute(RemoveAtomCommand(atom.atom_idx))
            return
        bond = self._scene.bond_at_pos(pos)
        if bond:
            self._history.execute(RemoveBondCommand(bond.a1_idx, bond.a2_idx))
            return

        # Empty space → start selection box for bulk erase
        self._box_mode = True
        self._sel_rect = QGraphicsRectItem()
        self._sel_rect.setPen(QPen(QColor("#DD0000"), 1.5, Qt.PenStyle.DashLine))
        self._sel_rect.setBrush(QColor(221, 0, 0, 25))
        self._sel_rect.setZValue(100)
        self._scene.addItem(self._sel_rect)

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._sel_rect:
            return
        pos = event.scenePos()
        dx = pos.x() - self._press_pos.x()
        dy = pos.y() - self._press_pos.y()
        if dx * dx + dy * dy > _MIN_DRAG_DIST_SQ:
            self._did_drag = True
        from PySide6.QtCore import QRectF
        r = QRectF(self._press_pos, pos).normalized()
        self._sel_rect.setRect(r)

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._sel_rect:
            return
        rect = self._sel_rect.rect()
        try:
            self._scene.removeItem(self._sel_rect)
        except RuntimeError:
            pass
        self._sel_rect = None

        if not self._did_drag:
            return

        # Collect atoms inside the box and bulk-delete
        to_delete = [idx for idx, item in self._scene._atom_items.items()
                     if rect.contains(item.pos())]
        if not to_delete:
            return
        cmd = BulkDeleteCommand(to_delete)
        cmd.execute(self._history.molecule)
        self._history._undo_stack.append(cmd)
        self._history._redo_stack.clear()
        if self._history._on_change:
            self._history._on_change()

    def deactivate(self) -> None:
        if self._sel_rect:
            try:
                self._scene.removeItem(self._sel_rect)
            except RuntimeError:
                pass
            self._sel_rect = None


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


# ======================================================================
# Ring tool (benzene, 6-ring, 5-ring)
# ======================================================================

_GHOST_PEN = QPen(QColor(0, 0, 0, 90), 1.5, Qt.PenStyle.DashLine)
_GHOST_BRUSH = QColor(0, 0, 0, 0)


def _ring_vertices(
    anchor_x: float, anchor_y: float, angle: float,
    n: int, bond_len: float = _BASE_DIST,
) -> list[tuple[float, float]]:
    """Return *n* ring vertex positions (coordinate units).

    *anchor_x/y* is the first vertex.  *angle* is the outgoing direction
    from the anchor (the ring extends in that direction).  Vertices are
    ordered around the ring starting from the anchor.
    """
    import math
    r = bond_len / (2 * math.sin(math.pi / n))      # circumradius
    cx = anchor_x + r * math.cos(angle)
    cy = anchor_y + r * math.sin(angle)
    # anchor is at angle (angle + pi) from center
    start = angle + math.pi
    verts = []
    for i in range(n):
        a = start + 2 * math.pi * i / n
        vx = cx + r * math.cos(a)
        vy = cy + r * math.sin(a)
        verts.append((vx, vy))
    return verts


class RingTool(Tool):
    """Draw a ring on an atom, a bond (fused), or empty canvas.

    - **Hover atom**: ghost preview extending away from the atom's bond.
    - **Hover bond**: ghost preview of a fused ring sharing that bond.
    - **Click atom + drag**: orient the ring, commit on release.
    - **Click bond**: commit a fused ring sharing that bond.
    - **Click empty canvas**: place a standalone ring.
    """

    def __init__(self, scene: MoleculeScene, history: HistoryManager,
                 n_sides: int = 6, aromatic: bool = False,
                 tool_name: str = "ring"):
        super().__init__(scene, history)
        self._n = n_sides
        self._aromatic = aromatic
        self.name = tool_name
        self._ghost_items: list[QGraphicsItem] = []
        self._anchor: Optional[AtomItem] = None
        self._anchor_bond: Optional[BondItem] = None
        self._ring_angle: float = 0.0

    # -- ghost preview -----------------------------------------------------

    def _clear_ghost(self):
        for item in self._ghost_items:
            try:
                if item.scene():
                    item.scene().removeItem(item)
            except RuntimeError:
                pass
        self._ghost_items.clear()

    def _draw_ghost(self, verts: list[tuple[float, float]]):
        self._clear_ghost()
        n = len(verts)
        for i in range(n):
            x1, y1 = verts[i]
            x2, y2 = verts[(i + 1) % n]
            p1, p2 = molecule_to_scene(x1, y1), molecule_to_scene(x2, y2)
            line = QGraphicsLineItem(QLineF(p1, p2))
            line.setPen(_GHOST_PEN)
            line.setZValue(50)
            self._scene.addItem(line)
            self._ghost_items.append(line)
            r = 3
            dot = QGraphicsEllipseItem(
                p1.x() - r, p1.y() - r, 2 * r, 2 * r
            )
            dot.setPen(_GHOST_PEN)
            dot.setBrush(_GHOST_BRUSH)
            dot.setZValue(50)
            self._scene.addItem(dot)
            self._ghost_items.append(dot)

    def _default_ring_angle(self, atom_idx: int) -> float:
        import math
        info = self._history.molecule.get_atom_info(atom_idx)
        if info.neighbors:
            ni = self._history.molecule.get_atom_info(info.neighbors[0])
            return math.atan2(ni.y - info.y, ni.x - info.x) + math.pi
        return 0.0

    def _fused_ring_verts(self, bond_item: BondItem):
        """Compute ring vertices that share the given bond.

        The shared edge is bond_item (a1→a2).  The ring extends to the
        side of the bond where the mouse is (or the side with more space).
        """
        import math
        mol = self._history.molecule
        a1 = mol.get_atom_info(bond_item.a1_idx)
        a2 = mol.get_atom_info(bond_item.a2_idx)
        mx = (a1.x + a2.x) / 2
        my = (a1.y + a2.y) / 2
        bond_angle = math.atan2(a2.y - a1.y, a2.x - a1.x)
        # Ring extends perpendicular to the bond from its midpoint
        perp = bond_angle + math.pi / 2
        bond_len = math.hypot(a2.x - a1.x, a2.y - a1.y)

        n = self._n
        r = bond_len / (2 * math.sin(math.pi / n))
        # Center on the perpendicular side
        # Try both sides, pick the one farther from existing neighbours
        cx1 = mx + (r * math.cos(math.pi / n)) * math.cos(perp)
        cy1 = my + (r * math.cos(math.pi / n)) * math.sin(perp)
        cx2 = mx - (r * math.cos(math.pi / n)) * math.cos(perp)
        cy2 = my - (r * math.cos(math.pi / n)) * math.sin(perp)

        # Pick the center that is farther from the average of existing
        # neighbours of a1 and a2 (so the ring goes to the "open" side).
        nbs = []
        for ni in a1.neighbors:
            if ni != bond_item.a2_idx:
                nbi = mol.get_atom_info(ni)
                nbs.append((nbi.x, nbi.y))
        for ni in a2.neighbors:
            if ni != bond_item.a1_idx:
                nbi = mol.get_atom_info(ni)
                nbs.append((nbi.x, nbi.y))
        if nbs:
            avg_x = sum(p[0] for p in nbs) / len(nbs)
            avg_y = sum(p[1] for p in nbs) / len(nbs)
            d1 = math.hypot(cx1 - avg_x, cy1 - avg_y)
            d2 = math.hypot(cx2 - avg_x, cy2 - avg_y)
            cx, cy = (cx1, cy1) if d1 >= d2 else (cx2, cy2)
        else:
            cx, cy = cx1, cy1

        # Generate vertices around the center; vertex 0 and 1 are the
        # shared bond endpoints (a1 and a2).
        angle_a1 = math.atan2(a1.y - cy, a1.x - cx)
        verts: list[tuple[float, float]] = []
        for i in range(n):
            a = angle_a1 + 2 * math.pi * i / n
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return verts

    # -- mouse events ------------------------------------------------------

    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        self._anchor_bond = None

        atom = self._scene.atom_at_pos(pos)
        bond = self._scene.bond_at_pos(pos)

        if atom and bond:
            d = atom.pos() - pos
            if d.x() * d.x() + d.y() * d.y() < HIT_RADIUS * HIT_RADIUS:
                # Atom takes priority
                self._anchor = atom
                self._anchor_bond = None
                self._ring_angle = self._default_ring_angle(atom.atom_idx)
            else:
                # Bond — fused ring, commit immediately on release
                self._anchor = None
                self._anchor_bond = bond
            return

        if atom:
            self._anchor = atom
            self._ring_angle = self._default_ring_angle(atom.atom_idx)
            info = self._history.molecule.get_atom_info(atom.atom_idx)
            verts = _ring_vertices(info.x, info.y, self._ring_angle, self._n)
            self._draw_ghost(verts)
            return

        if bond:
            self._anchor_bond = bond
            return

        # Empty canvas — place standalone ring
        self._anchor = None
        self._anchor_bond = None
        x, y = scene_to_molecule(pos)
        verts = _ring_vertices(x, y, 0.0, self._n)
        self._clear_ghost()
        self._commit_ring_verts(verts)

    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None:
        import math
        pos = event.scenePos()

        if self._anchor:
            # Dragging from atom — update ring direction
            ax, ay = self._anchor.pos().x(), self._anchor.pos().y()
            dx, dy = pos.x() - ax, pos.y() - ay
            if dx * dx + dy * dy > 100:
                mol_dx, mol_dy = scene_to_molecule(QPointF(dx, dy))
                self._ring_angle = math.atan2(mol_dy, mol_dx)
            info = self._history.molecule.get_atom_info(
                self._anchor.atom_idx)
            verts = _ring_vertices(info.x, info.y, self._ring_angle, self._n)
            self._draw_ghost(verts)
        elif self._anchor_bond:
            # Dragging from bond — just keep showing fused ghost
            verts = self._fused_ring_verts(self._anchor_bond)
            self._draw_ghost(verts)
        else:
            # Hover — show ghost on atom or bond under cursor
            atom = self._scene.atom_at_pos(pos)
            bond = self._scene.bond_at_pos(pos)
            if atom:
                angle = self._default_ring_angle(atom.atom_idx)
                info = self._history.molecule.get_atom_info(atom.atom_idx)
                verts = _ring_vertices(info.x, info.y, angle, self._n)
                self._draw_ghost(verts)
            elif bond:
                verts = self._fused_ring_verts(bond)
                self._draw_ghost(verts)
            else:
                self._clear_ghost()

    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._anchor:
            atom_idx = self._anchor.atom_idx
            info = self._history.molecule.get_atom_info(atom_idx)
            verts = _ring_vertices(info.x, info.y, self._ring_angle, self._n)
            self._clear_ghost()
            self._anchor = None
            self._commit_ring_verts(verts, pre_map={0: atom_idx})
        elif self._anchor_bond:
            bond = self._anchor_bond
            verts = self._fused_ring_verts(bond)
            # Pre-map the two bond endpoint atoms
            pre = self._fused_pre_map(bond, verts)
            self._clear_ghost()
            self._anchor_bond = None
            self._commit_ring_verts(verts, pre_map=pre)
        else:
            self._clear_ghost()

    def _fused_pre_map(self, bond_item: BondItem,
                       verts: list[tuple[float, float]]) -> dict[int, int]:
        """Map ring vertices to the bond's endpoints by proximity."""
        import math
        mol = self._history.molecule
        a1 = mol.get_atom_info(bond_item.a1_idx)
        a2 = mol.get_atom_info(bond_item.a2_idx)
        pre: dict[int, int] = {}
        for target_idx, tx, ty in [(bond_item.a1_idx, a1.x, a1.y),
                                   (bond_item.a2_idx, a2.x, a2.y)]:
            best_i, best_d = -1, 1e9
            for i, (vx, vy) in enumerate(verts):
                d = math.hypot(vx - tx, vy - ty)
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0 and best_d < _BASE_DIST:
                pre[best_i] = target_idx
        return pre

    def deactivate(self) -> None:
        self._clear_ghost()
        self._anchor = None
        self._anchor_bond = None

    # -- commit ring -------------------------------------------------------

    def _commit_ring_verts(self, verts,
                          pre_map: dict[int, int] | None = None):
        """Create ring atoms and bonds as a single compound command.

        *pre_map* maps vertex indices to known existing atom indices
        (e.g. ``{0: anchor_idx}``).  Non-pre-mapped vertices only reuse
        an existing atom if they are *very* close (< 0.3 units) to
        prevent unintended ring fusion.
        """
        mol = self._history.molecule
        n = len(verts)
        if pre_map is None:
            pre_map = {}

        # Tight threshold for non-pre-mapped vertices (0.3 vs 0.8)
        _TIGHT = 0.3 * 0.3

        vertex_map: list[int | None] = [None] * n
        for i in range(n):
            if i in pre_map:
                vertex_map[i] = pre_map[i]
                continue
            vx, vy = verts[i]
            for j in range(mol.num_atoms):
                ai = mol.get_atom_info(j)
                dx, dy = ai.x - vx, ai.y - vy
                if dx * dx + dy * dy < _TIGHT:
                    vertex_map[i] = j
                    break

        # Build atom commands
        cmds: list = []
        atom_cmds: list[tuple[int, AddAtomCommand | None]] = []
        for i in range(n):
            if vertex_map[i] is not None:
                atom_cmds.append((i, None))
            else:
                vx, vy = verts[i]
                cmd = AddAtomCommand("C", vx, vy)
                cmds.append(cmd)
                atom_cmds.append((i, cmd))

        # Bond types: aromatic rings get alternating double/single
        bond_types: list[BondType] = []
        for i in range(n):
            if self._aromatic and i % 2 == 0:
                bond_types.append(BondType.DOUBLE)
            else:
                bond_types.append(BondType.SINGLE)

        # Execute atom commands
        for cmd in cmds:
            cmd.execute(mol)

        # Resolve indices
        indices: list[int] = []
        for i, (vi, cmd) in enumerate(atom_cmds):
            if vertex_map[vi] is not None:
                indices.append(vertex_map[vi])
            else:
                assert cmd is not None and cmd.created_idx is not None
                indices.append(cmd.created_idx)

        # Create bond commands (skip existing bonds)
        bond_cmds: list = []
        for i in range(n):
            a1, a2 = indices[i], indices[(i + 1) % n]
            if mol.get_bond_info(a1, a2) is None:
                bt = bond_types[i]
                bcmd = AddBondCommand(a1, a2, bt)
                bcmd.execute(mol)
                bond_cmds.append(bcmd)

        all_cmds = cmds + bond_cmds
        if all_cmds:
            compound = CompoundCommand(all_cmds)
            self._history._undo_stack.append(compound)
            self._history._redo_stack.clear()
            if self._history._on_change:
                self._history._on_change()


# ======================================================================
# Geometry helpers for bond placement
# ======================================================================

_LENGTH_MULTS = [1.0, 1.3, 1.6, 2.0, 2.5, 3.0]


def _find_bond_position(
    mol, atom_idx: int, info, ideal_angle: float
) -> tuple[float, float]:
    """Find a clash-free position for a new bonded atom.

    *ideal_angle* is the angle (radians) between the existing bond and the
    new bond (pi for 180 deg, 2*pi/3 for 120 deg).  Candidate directions
    are tried at increasing bond lengths until one is clash-free.

    When the atom has exactly one neighbour, a *zig-zag* heuristic is used:
    the candidate that points away from the grandparent atom (the
    neighbour's other neighbour) is tried first so that chains grow in a
    zig-zag pattern.
    """
    import math

    # Gather neighbour directions
    neighbor_angles: list[float] = []
    for ni in info.neighbors:
        ni_info = mol.get_atom_info(ni)
        dx = ni_info.x - info.x
        dy = ni_info.y - info.y
        neighbor_angles.append(math.atan2(dy, dx))

    # Build candidate angle list (preferred order)
    if not neighbor_angles:
        candidates = [0.0]
    elif len(neighbor_angles) == 1:
        na = neighbor_angles[0]
        if abs(ideal_angle - math.pi) < 0.01:
            # 180° — only one candidate (opposite)
            candidates = [na + math.pi]
        else:
            c_plus = na + ideal_angle
            c_minus = na - ideal_angle

            # Zig-zag: prefer the direction AWAY from the grandparent so
            # that consecutive chain bonds alternate sides.
            ni = info.neighbors[0]
            ni_info = mol.get_atom_info(ni)
            gp_angle = None
            for gn in ni_info.neighbors:
                if gn != atom_idx:
                    gp_info = mol.get_atom_info(gn)
                    gp_angle = math.atan2(gp_info.y - info.y,
                                          gp_info.x - info.x)
                    break  # use first grandparent

            if gp_angle is not None:
                # Pick candidate farther from the grandparent direction
                def _adist(a, b):
                    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)

                if _adist(c_plus, gp_angle) >= _adist(c_minus, gp_angle):
                    candidates = [c_plus, c_minus]
                else:
                    candidates = [c_minus, c_plus]
            else:
                candidates = [c_plus, c_minus]
    else:
        # Multiple neighbours: ideal-angle offsets from each, then largest gap
        candidates = []
        for na in neighbor_angles:
            candidates.append(na + ideal_angle)
            if abs(ideal_angle - math.pi) > 0.01:
                candidates.append(na - ideal_angle)
        # Largest angular gap as last-resort direction
        sorted_a = sorted(neighbor_angles)
        max_gap = 0.0
        gap_mid = 0.0
        for i in range(len(sorted_a)):
            a1 = sorted_a[i]
            a2 = sorted_a[(i + 1) % len(sorted_a)]
            gap = (a2 - a1) % (2 * math.pi)
            if gap > max_gap:
                max_gap = gap
                gap_mid = a1 + gap / 2
        candidates.append(gap_mid)

    # Pre-compute existing atom positions and bond segments
    all_atoms: list[tuple[int, float, float]] = []
    for i in range(mol.num_atoms):
        ai = mol.get_atom_info(i)
        all_atoms.append((i, ai.x, ai.y))

    all_bonds: list[tuple[int, int, float, float, float, float]] = []
    for b in mol.get_all_bonds():
        b1 = mol.get_atom_info(b.begin_atom_idx)
        b2 = mol.get_atom_info(b.end_atom_idx)
        all_bonds.append((b.begin_atom_idx, b.end_atom_idx,
                          b1.x, b1.y, b2.x, b2.y))

    # --- Phase 1: preferred candidates at default length (strict) ----------
    for angle in candidates:
        nx = info.x + _BASE_DIST * math.cos(angle)
        ny = info.y + _BASE_DIST * math.sin(angle)
        if not _has_clash(info.x, info.y, nx, ny, atom_idx,
                          all_atoms, all_bonds):
            return (nx, ny)

    # --- Phase 2: fine sweep at default length (best clearance) ------------
    # Prefer a tighter angle at normal length over a long bond.
    best = _sweep_best_angle(
        info.x, info.y, _BASE_DIST, atom_idx, all_atoms, all_bonds,
    )
    if best is not None:
        return (info.x + _BASE_DIST * math.cos(best),
                info.y + _BASE_DIST * math.sin(best))

    # --- Phase 3: extended lengths -----------------------------------------
    for mult in _LENGTH_MULTS[1:]:          # skip 1.0, already tried
        dist = _BASE_DIST * mult
        for angle in candidates:
            nx = info.x + dist * math.cos(angle)
            ny = info.y + dist * math.sin(angle)
            if not _has_clash(info.x, info.y, nx, ny, atom_idx,
                              all_atoms, all_bonds):
                return (nx, ny)

    # Ultimate fallback: place to the right at base distance
    return (info.x + _BASE_DIST, info.y)


_MIN_BOND_ANGLE = 0.50   # ~29 deg — minimum angle between adjacent bonds
_SWEEP_STEPS = 36        # 10° per step for fine angular sweep


def _sweep_best_angle(
    sx: float, sy: float, dist: float, source_idx: int,
    all_atoms: list[tuple[int, float, float]],
    all_bonds: list[tuple[int, int, float, float, float, float]],
) -> float | None:
    """Scan 360° in fine steps and return the angle with the best
    clearance that has no hard clashes (atom overlap / bond crossing).

    Returns *None* if every angle has a hard clash at *dist*.
    """
    import math

    best_angle: float | None = None
    best_clearance = -1.0

    for step in range(_SWEEP_STEPS):
        angle = 2 * math.pi * step / _SWEEP_STEPS
        nx = sx + dist * math.cos(angle)
        ny = sy + dist * math.sin(angle)

        # Hard clashes — these are non-negotiable
        hard = False
        for idx, ax, ay in all_atoms:
            if idx == source_idx:
                continue
            if math.hypot(nx - ax, ny - ay) < _MIN_ATOM_DIST:
                hard = True
                break
        if hard:
            continue

        for bi, bj, b1x, b1y, b2x, b2y in all_bonds:
            if bi == source_idx or bj == source_idx:
                continue
            if _segments_cross(sx, sy, nx, ny, b1x, b1y, b2x, b2y):
                hard = True
                break
        if hard:
            continue

        # Soft clearance: minimum angular distance to existing bonds
        # from the source atom (bigger = better).
        min_adist = math.pi  # best possible
        for bi, bj, b1x, b1y, b2x, b2y in all_bonds:
            if bi == source_idx:
                ea = math.atan2(b2y - b1y, b2x - b1x)
            elif bj == source_idx:
                ea = math.atan2(b1y - b2y, b1x - b2x)
            else:
                continue
            adist = abs((angle - ea + math.pi) % (2 * math.pi) - math.pi)
            min_adist = min(min_adist, adist)

        if min_adist > best_clearance:
            best_clearance = min_adist
            best_angle = angle

    # Accept if the best angle has at least some angular separation
    # (> ~15° = 0.26 rad) — tighter than the strict check but still
    # readable.
    if best_angle is not None and best_clearance > 0.26:
        return best_angle
    return None


def _has_clash(
    sx: float, sy: float, nx: float, ny: float, source_idx: int,
    all_atoms: list[tuple[int, float, float]],
    all_bonds: list[tuple[int, int, float, float, float, float]],
) -> bool:
    """Return True if placing a new atom at (nx, ny) with a bond from
    (sx, sy) clashes with existing atoms, crosses existing bonds, or
    points in nearly the same direction as an existing bond from the
    source atom."""
    import math

    # 1. Atom–atom distance
    for idx, ax, ay in all_atoms:
        if idx == source_idx:
            continue
        if math.hypot(nx - ax, ny - ay) < _MIN_ATOM_DIST:
            return True

    new_angle = math.atan2(ny - sy, nx - sx)

    for bi, bj, b1x, b1y, b2x, b2y in all_bonds:
        if bi == source_idx or bj == source_idx:
            # 2. Angular overlap: new bond too close in direction to an
            #    existing bond from the source atom.
            if bi == source_idx:
                ea = math.atan2(b2y - b1y, b2x - b1x)
            else:
                ea = math.atan2(b1y - b2y, b1x - b2x)
            adist = abs((new_angle - ea + math.pi) % (2 * math.pi) - math.pi)
            if adist < _MIN_BOND_ANGLE:
                return True
        else:
            # 3. Segment crossing with bonds not connected to source
            if _segments_cross(sx, sy, nx, ny, b1x, b1y, b2x, b2y):
                return True

    return False


def _segments_cross(
    ax: float, ay: float, bx: float, by: float,
    cx: float, cy: float, dx: float, dy: float,
) -> bool:
    """Return True if line segments AB and CD properly cross each other."""
    def _cross(ox, oy, px, py, qx, qy):
        return (px - ox) * (qy - oy) - (py - oy) * (qx - ox)

    d1 = _cross(cx, cy, dx, dy, ax, ay)
    d2 = _cross(cx, cy, dx, dy, bx, by)
    d3 = _cross(ax, ay, bx, by, cx, cy)
    d4 = _cross(ax, ay, bx, by, dx, dy)

    return (((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and
            ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)))
