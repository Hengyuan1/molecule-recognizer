"""QGraphicsScene-based molecular canvas for rendering and editing."""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from ..core.molecule import BondType, Molecule

# Element → color mapping
ELEMENT_COLORS: dict[str, str] = {
    "C": "#333333",
    "N": "#3050F8",
    "O": "#FF0D0D",
    "S": "#FFFF30",
    "P": "#FF8000",
    "F": "#90E050",
    "Cl": "#1FF01F",
    "Br": "#A62929",
    "I": "#940094",
    "H": "#FFFFFF",
    "Se": "#FFA100",
    "B": "#FFB5B5",
    "Si": "#F0C8A0",
}

DEFAULT_COLOR = "#FF69B4"  # for unknown elements

ATOM_RADIUS = 14.0
BOND_WIDTH = 2.5
DOUBLE_BOND_OFFSET = 4.0
SCALE = 40.0  # pixels per unit coordinate


class AtomItem(QGraphicsEllipseItem):
    """Visual representation of an atom on the canvas."""

    def __init__(self, atom_idx: int, element: str, x: float, y: float):
        r = ATOM_RADIUS
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.atom_idx = atom_idx
        self.element = element

        color = QColor(ELEMENT_COLORS.get(element, DEFAULT_COLOR))
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#222222"), 1.5))
        self.setPos(x * SCALE, y * SCALE)

        # Element label
        self._label = QGraphicsSimpleTextItem(element, self)
        font = QFont("Arial", 10, QFont.Weight.Bold)
        self._label.setFont(font)
        self._label.setBrush(QBrush(Qt.GlobalColor.white if color.lightness() < 128 else Qt.GlobalColor.black))
        # Center the label
        br = self._label.boundingRect()
        self._label.setPos(-br.width() / 2, -br.height() / 2)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(10)  # atoms on top of bonds

    def set_highlighted(self, highlighted: bool):
        if highlighted:
            self.setPen(QPen(QColor("#00AAFF"), 3))
        else:
            self.setPen(QPen(QColor("#222222"), 1.5))

    def update_element(self, element: str):
        self.element = element
        color = QColor(ELEMENT_COLORS.get(element, DEFAULT_COLOR))
        self.setBrush(QBrush(color))
        self._label.setText(element)
        self._label.setBrush(QBrush(Qt.GlobalColor.white if color.lightness() < 128 else Qt.GlobalColor.black))
        br = self._label.boundingRect()
        self._label.setPos(-br.width() / 2, -br.height() / 2)


class BondItem(QGraphicsLineItem):
    """Visual representation of a bond on the canvas."""

    def __init__(self, a1_idx: int, a2_idx: int, bond_type: BondType,
                 p1: QPointF, p2: QPointF):
        super().__init__()
        self.a1_idx = a1_idx
        self.a2_idx = a2_idx
        self.bond_type = bond_type
        self._p1 = p1
        self._p2 = p2
        self._extra_lines: list[QGraphicsLineItem] = []
        self.setZValue(1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._render()

    def _render(self):
        pen = QPen(QColor("#555555"), BOND_WIDTH)
        self.setPen(pen)

        # Shorten lines so they don't overlap atom circles
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            self.setLine(QLineF(self._p1, self._p2))
            return

        # Shorten by atom radius from each end
        ux, uy = dx / length, dy / length
        start = QPointF(self._p1.x() + ux * ATOM_RADIUS, self._p1.y() + uy * ATOM_RADIUS)
        end = QPointF(self._p2.x() - ux * ATOM_RADIUS, self._p2.y() - uy * ATOM_RADIUS)

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
            nx, ny = -uy * DOUBLE_BOND_OFFSET * 1.3, ux * DOUBLE_BOND_OFFSET * 1.3
            self.setLine(QLineF(start, end))
            line2 = QGraphicsLineItem(
                start.x() + nx, start.y() + ny,
                end.x() + nx, end.y() + ny,
                self
            )
            line2.setPen(pen)
            line3 = QGraphicsLineItem(
                start.x() - nx, start.y() - ny,
                end.x() - nx, end.y() - ny,
                self
            )
            line3.setPen(pen)
            self._extra_lines.extend([line2, line3])
        elif self.bond_type == BondType.AROMATIC:
            # Solid + dashed
            self.setLine(QLineF(
                start.x() + (-uy * DOUBLE_BOND_OFFSET), start.y() + (ux * DOUBLE_BOND_OFFSET),
                end.x() + (-uy * DOUBLE_BOND_OFFSET), end.y() + (ux * DOUBLE_BOND_OFFSET)
            ))
            dashed_pen = QPen(QColor("#555555"), BOND_WIDTH, Qt.PenStyle.DashLine)
            line2 = QGraphicsLineItem(
                start.x() - (-uy * DOUBLE_BOND_OFFSET), start.y() - (ux * DOUBLE_BOND_OFFSET),
                end.x() - (-uy * DOUBLE_BOND_OFFSET), end.y() - (ux * DOUBLE_BOND_OFFSET),
                self
            )
            line2.setPen(dashed_pen)
            self._extra_lines.append(line2)

    def set_highlighted(self, highlighted: bool):
        color = QColor("#00AAFF") if highlighted else QColor("#555555")
        self.setPen(QPen(color, BOND_WIDTH + (1 if highlighted else 0)))

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

    atom_clicked = Signal(int)       # atom index
    bond_clicked = Signal(int, int)  # atom indices
    canvas_clicked = Signal(float, float)  # scene coords

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

        # Add bonds
        for bond in mol.get_all_bonds():
            a1, a2 = bond.begin_atom_idx, bond.end_atom_idx
            p1 = self._atom_items[a1].pos()
            p2 = self._atom_items[a2].pos()
            item = BondItem(a1, a2, bond.bond_type, p1, p2)
            self.addItem(item)
            key = (min(a1, a2), max(a1, a2))
            self._bond_items[key] = item

    def get_atom_item(self, idx: int) -> Optional[AtomItem]:
        return self._atom_items.get(idx)

    def get_bond_item(self, a1: int, a2: int) -> Optional[BondItem]:
        key = (min(a1, a2), max(a1, a2))
        return self._bond_items.get(key)

    def atom_at_pos(self, scene_pos: QPointF) -> Optional[AtomItem]:
        """Find an atom item near the given scene position."""
        for item in self._atom_items.values():
            dist = (item.pos() - scene_pos)
            if dist.x() ** 2 + dist.y() ** 2 < (ATOM_RADIUS * 1.5) ** 2:
                return item
        return None

    def bond_at_pos(self, scene_pos: QPointF) -> Optional[BondItem]:
        """Find a bond item near the given scene position."""
        for item in self._bond_items.values():
            # Check distance from point to line segment
            line = item.line()
            p = scene_pos
            # Transform to item coordinates
            mapped = item.mapFromScene(p)
            # Use bounding rect as quick check
            br = item.boundingRect().adjusted(-10, -10, 10, 10)
            if br.contains(mapped):
                # More precise: distance to line
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
        # Fit the view to the content with some margin
        self.fitInView(self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50),
                       Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


def _point_to_line_dist(p: QPointF, a: QPointF, b: QPointF) -> float:
    """Distance from point p to line segment a-b."""
    dx = b.x() - a.x()
    dy = b.y() - a.y()
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-10:
        return math.sqrt((p.x() - a.x()) ** 2 + (p.y() - a.y()) ** 2)
    t = max(0, min(1, ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / len_sq))
    proj_x = a.x() + t * dx
    proj_y = a.y() + t * dy
    return math.sqrt((p.x() - proj_x) ** 2 + (p.y() - proj_y) ** 2)
