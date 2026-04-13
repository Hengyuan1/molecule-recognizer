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
from .canvas import HIT_RADIUS, SCALE, AtomItem, BondItem, MoleculeScene
from .history import (
    AddAtomCommand,
    AddBondCommand,
    ChangeBondTypeCommand,
    ChangeChargeCommand,
    ChangeElementCommand,
    CompoundCommand,
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
                x = pos.x() / SCALE
                y = pos.y() / SCALE
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

class SelectTool(Tool):
    """Default tool — click atom to substitute, drag to create bond,
    click bond to cycle, click empty does nothing."""
    name = "select"


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

    def _on_atom_click(self, atom_idx: int) -> None:
        import math
        from ..core.valence import STANDARD_VALENCES

        mol = self._history.molecule
        info = mol.get_atom_info(atom_idx)

        # Bond-order lookup
        _bv = {BondType.SINGLE: 1, BondType.DOUBLE: 2,
               BondType.TRIPLE: 3, BondType.AROMATIC: 1.5}

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


# ======================================================================
# Geometry helpers for bond placement
# ======================================================================

_BASE_DIST = 1.5          # default bond length in coordinate units
_MIN_ATOM_DIST = 0.8      # minimum distance between any two atoms
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
