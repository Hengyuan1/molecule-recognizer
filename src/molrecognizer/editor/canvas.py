"""QGraphicsScene-based molecular canvas with skeletal structure rendering.

Carbon atoms are drawn as invisible line junctions (no circle, no label).
Heteroatoms (N, O, S, B, etc.) are drawn with a colored label on a white
background that masks the bond lines.  This produces the standard chemical
structure diagram style used in papers.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from ..core.molecule import BondType, Molecule

# Heteroatom colors (CPK-ish)
ELEMENT_COLORS: dict[str, str] = {
    "N": "#2222DD",
    "O": "#DD0000",
    "S": "#CCAA00",
    "P": "#DD8800",
    "F": "#22AA22",
    "Cl": "#22CC22",
    "Br": "#882222",
    "I": "#772299",
    "B": "#DD8899",
    "Se": "#DD8800",
    "Si": "#CC9966",
}

BOND_COLOR = "#222222"
BOND_WIDTH = 2.0
DOUBLE_BOND_OFFSET = 3.0
SCALE = 40.0  # pixels per unit coordinate
HIT_RADIUS = 12.0  # click detection radius


class AtomItem(QGraphicsEllipseItem):
    """Visual representation of an atom.

    Carbon atoms: small invisible hit area (no visible circle or label).
    Heteroatoms: colored element label on white background.
    """

    def __init__(self, atom_idx: int, element: str, x: float, y: float):
        # Hit area for clicking — always present but invisible for C
        r = HIT_RADIUS
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.atom_idx = atom_idx
        self.element = element
        self.setPos(x * SCALE, y * SCALE)
        self.setZValue(10)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # No visible circle
        self.setBrush(QBrush(Qt.GlobalColor.transparent))
        self.setPen(QPen(Qt.PenStyle.NoPen))

        self._bg_rect: QGraphicsRectItem | None = None
        self._label: QGraphicsSimpleTextItem | None = None
        self._build_label()

    @property
    def is_heteroatom(self) -> bool:
        return self.element != "C"

    def _build_label(self):
        # Remove old label items
        if self._bg_rect:
            if self._bg_rect.scene():
                self._bg_rect.scene().removeItem(self._bg_rect)
            self._bg_rect = None
        if self._label:
            if self._label.scene():
                self._label.scene().removeItem(self._label)
            self._label = None

        if not self.is_heteroatom:
            return

        color = QColor(ELEMENT_COLORS.get(self.element, "#DD44AA"))
        font = QFont("Arial", 12, QFont.Weight.Bold)

        self._label = QGraphicsSimpleTextItem(self.element, self)
        self._label.setFont(font)
        self._label.setBrush(QBrush(color))
        br = self._label.boundingRect()
        self._label.setPos(-br.width() / 2, -br.height() / 2)
        self._label.setZValue(12)

        # White background to mask bond lines behind the label
        pad = 2
        self._bg_rect = QGraphicsRectItem(
            -br.width() / 2 - pad, -br.height() / 2 - pad,
            br.width() + 2 * pad, br.height() + 2 * pad,
            self
        )
        self._bg_rect.setBrush(QBrush(QColor("#FAFAFA")))
        self._bg_rect.setPen(QPen(Qt.PenStyle.NoPen))
        self._bg_rect.setZValue(11)

    def set_highlighted(self, highlighted: bool):
        if highlighted:
            r = HIT_RADIUS
            self.setPen(QPen(QColor("#00AAFF"), 2))
            self.setBrush(QBrush(QColor(0, 170, 255, 40)))
        else:
            self.setPen(QPen(Qt.PenStyle.NoPen))
            self.setBrush(QBrush(Qt.GlobalColor.transparent))

    def update_element(self, element: str):
        self.element = element
        self._build_label()


class BondItem(QGraphicsLineItem):
    """Visual representation of a bond — standard skeletal line drawing."""

    def __init__(self, a1_idx: int, a2_idx: int, bond_type: BondType,
                 p1: QPointF, p2: QPointF,
                 a1_hetero: bool = False, a2_hetero: bool = False):
        super().__init__()
        self.a1_idx = a1_idx
        self.a2_idx = a2_idx
        self.bond_type = bond_type
        self._p1 = p1
        self._p2 = p2
        self._a1_hetero = a1_hetero
        self._a2_hetero = a2_hetero
        self._extra_lines: list[QGraphicsLineItem] = []
        self.setZValue(1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._render()

    def _render(self):
        pen = QPen(QColor(BOND_COLOR), BOND_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            self.setLine(QLineF(self._p1, self._p2))
            return

        ux, uy = dx / length, dy / length

        # Shorten bonds that connect to heteroatoms (so lines don't poke through labels)
        shrink1 = 8.0 if self._a1_hetero else 0.0
        shrink2 = 8.0 if self._a2_hetero else 0.0
        start = QPointF(self._p1.x() + ux * shrink1, self._p1.y() + uy * shrink1)
        end = QPointF(self._p2.x() - ux * shrink2, self._p2.y() - uy * shrink2)

        if self.bond_type == BondType.SINGLE:
            self.setLine(QLineF(start, end))

        elif self.bond_type == BondType.DOUBLE:
            nx, ny = -uy * DOUBLE_BOND_OFFSET, ux * DOUBLE_BOND_OFFSET
            self.setLine(QLineF(
                start.x() + nx, start.y() + ny,
                end.x() + nx, end.y() + ny
            ))
            line2 = QGraphicsLineItem(
                start.x() - nx, start.y() - ny,
                end.x() - nx, end.y() - ny,
                self
            )
            line2.setPen(pen)
            self._extra_lines.append(line2)

        elif self.bond_type == BondType.TRIPLE:
            off = DOUBLE_BOND_OFFSET * 1.4
            nx, ny = -uy * off, ux * off
            self.setLine(QLineF(start, end))
            for sign in (1, -1):
                ln = QGraphicsLineItem(
                    start.x() + sign * nx, start.y() + sign * ny,
                    end.x() + sign * nx, end.y() + sign * ny,
                    self
                )
                ln.setPen(pen)
                self._extra_lines.append(ln)

        elif self.bond_type == BondType.AROMATIC:
            # Solid line + dashed line (standard representation)
            nx, ny = -uy * DOUBLE_BOND_OFFSET, ux * DOUBLE_BOND_OFFSET
            self.setLine(QLineF(
                start.x() + nx, start.y() + ny,
                end.x() + nx, end.y() + ny
            ))
            dashed = QPen(QColor(BOND_COLOR), BOND_WIDTH, Qt.PenStyle.DashLine)
            dashed.setCapStyle(Qt.PenCapStyle.RoundCap)
            line2 = QGraphicsLineItem(
                start.x() - nx, start.y() - ny,
                end.x() - nx, end.y() - ny,
                self
            )
            line2.setPen(dashed)
            self._extra_lines.append(line2)

    def set_highlighted(self, highlighted: bool):
        color = QColor("#00AAFF") if highlighted else QColor(BOND_COLOR)
        w = BOND_WIDTH + (1 if highlighted else 0)
        self.setPen(QPen(color, w))

    def update_positions(self, p1: QPointF, p2: QPointF):
        self._p1 = p1
        self._p2 = p2
        for line in self._extra_lines:
            scene = line.scene()
            if scene:
                scene.removeItem(line)
        self._extra_lines.clear()
        self._render()


class MoleculeScene(QGraphicsScene):
    """Scene holding atom and bond graphics items."""

    atom_clicked = Signal(int)
    bond_clicked = Signal(int, int)
    canvas_clicked = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._atom_items: dict[int, AtomItem] = {}
        self._bond_items: dict[tuple[int, int], BondItem] = {}

    def load_molecule(self, mol: Molecule):
        """Clear scene and render the given molecule."""
        self.clear()
        self._atom_items.clear()
        self._bond_items.clear()

        coords = mol.get_2d_coords()

        # Add atoms
        for i in range(mol.num_atoms):
            info = mol.get_atom_info(i)
            x, y = coords[i]
            item = AtomItem(i, info.element, x, y)
            self.addItem(item)
            self._atom_items[i] = item

        # Add bonds — pass heteroatom flags so bonds shorten near labels
        for bond in mol.get_all_bonds():
            a1, a2 = bond.begin_atom_idx, bond.end_atom_idx
            p1 = self._atom_items[a1].pos()
            p2 = self._atom_items[a2].pos()
            a1_het = self._atom_items[a1].is_heteroatom
            a2_het = self._atom_items[a2].is_heteroatom
            item = BondItem(a1, a2, bond.bond_type, p1, p2, a1_het, a2_het)
            self.addItem(item)
            key = (min(a1, a2), max(a1, a2))
            self._bond_items[key] = item

    def get_atom_item(self, idx: int) -> Optional[AtomItem]:
        return self._atom_items.get(idx)

    def get_bond_item(self, a1: int, a2: int) -> Optional[BondItem]:
        key = (min(a1, a2), max(a1, a2))
        return self._bond_items.get(key)

    def atom_at_pos(self, scene_pos: QPointF) -> Optional[AtomItem]:
        for item in self._atom_items.values():
            dist = item.pos() - scene_pos
            if dist.x() ** 2 + dist.y() ** 2 < (HIT_RADIUS * 1.5) ** 2:
                return item
        return None

    def bond_at_pos(self, scene_pos: QPointF) -> Optional[BondItem]:
        for item in self._bond_items.values():
            a1_pos = self._atom_items.get(item.a1_idx)
            a2_pos = self._atom_items.get(item.a2_idx)
            if a1_pos and a2_pos:
                d = _point_to_line_dist(scene_pos, a1_pos.pos(), a2_pos.pos())
                if d < 10:
                    return item
        return None


class MoleculeCanvas(QGraphicsView):
    """Interactive view for the molecular scene."""

    molecule_changed = Signal()

    def __init__(self, parent=None):
        self._scene = MoleculeScene()
        super().__init__(self._scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor("#FAFAFA")))
        self.setMinimumSize(400, 300)

    @property
    def mol_scene(self) -> MoleculeScene:
        return self._scene

    def load_molecule(self, mol: Molecule):
        self._scene.load_molecule(mol)
        self.fitInView(self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50),
                       Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


def _point_to_line_dist(p: QPointF, a: QPointF, b: QPointF) -> float:
    dx = b.x() - a.x()
    dy = b.y() - a.y()
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-10:
        return math.sqrt((p.x() - a.x()) ** 2 + (p.y() - a.y()) ** 2)
    t = max(0, min(1, ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / len_sq))
    proj_x = a.x() + t * dx
    proj_y = a.y() + t * dy
    return math.sqrt((p.x() - proj_x) ** 2 + (p.y() - proj_y) ** 2)
