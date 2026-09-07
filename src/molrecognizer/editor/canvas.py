"""QGraphicsScene-based molecular canvas with skeletal structure rendering.

Carbon atoms are drawn as invisible line junctions (no circle, no label).
Heteroatoms (N, O, S, B, etc.) are drawn with a colored label on a white
background that masks the bond lines.  This produces the standard chemical
structure diagram style used in papers.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Optional

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from rdkit import Chem

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


def molecule_to_scene(x: float, y: float) -> QPointF:
    """Map chemistry's Y-up coordinates to Qt's Y-down scene, without mirroring."""
    return QPointF(x * SCALE, -y * SCALE)


def scene_to_molecule(pos: QPointF) -> tuple[float, float]:
    """Inverse mapping for mouse positions and drag deltas."""
    return pos.x() / SCALE, -pos.y() / SCALE


class AtomItem(QGraphicsEllipseItem):
    """Visual representation of an atom.

    Carbon atoms: invisible (skeletal style), unless they carry a charge.
    Heteroatoms: colored label showing element + implicit Hs + charge,
    e.g. ``NH2``, ``OH``, ``N+``, ``NH3+``.
    """

    def __init__(self, atom_idx: int, element: str, x: float, y: float,
                 n_hs: int = 0, formal_charge: int = 0):
        r = HIT_RADIUS
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.atom_idx = atom_idx
        self.element = element
        self.n_hs = n_hs
        self.formal_charge = formal_charge
        self.setPos(molecule_to_scene(x, y))
        self.setZValue(10)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.setBrush(QBrush(Qt.GlobalColor.transparent))
        self.setPen(QPen(Qt.PenStyle.NoPen))

        self._bg_rect: QGraphicsRectItem | None = None
        self._label_items: list[QGraphicsSimpleTextItem] = []
        self.label_width: float = 0.0   # used by BondItem for shortening
        # Highlight overlay — child item above bg rect and text
        self._highlight = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r, self)
        self._highlight.setPen(QPen(Qt.PenStyle.NoPen))
        self._highlight.setBrush(QBrush(Qt.GlobalColor.transparent))
        self._highlight.setZValue(15)   # above bg (11) and text (12)
        self._build_label()

    @property
    def is_heteroatom(self) -> bool:
        return self.element != "C"

    @property
    def show_label(self) -> bool:
        """Whether this atom should display a visible label."""
        return self.is_heteroatom or self.formal_charge != 0 or self.n_hs > 0

    def _build_label(self):
        # Remove old items
        if self._bg_rect:
            if self._bg_rect.scene():
                self._bg_rect.scene().removeItem(self._bg_rect)
            self._bg_rect = None
        for item in self._label_items:
            if item.scene():
                item.scene().removeItem(item)
        self._label_items.clear()

        self.label_width = 0.0
        if not self.show_label:
            return

        color = QColor(ELEMENT_COLORS.get(self.element, "#DD44AA"))
        main_font = QFont("Arial", 16, QFont.Weight.Bold)
        small_font = QFont("Arial", 11, QFont.Weight.Bold)

        # Measure main font metrics for vertical positioning
        # (use a throwaway item to get bounding rect height)
        ref = QGraphicsSimpleTextItem("X")
        ref.setFont(main_font)
        main_h = ref.boundingRect().height()

        # Build label parts left-to-right: Element, H, subscript, superscript
        # Positions are relative; we'll center the whole group afterwards.
        parts: list[tuple[str, QFont, float]] = []  # (text, font, y_offset)

        # Element symbol (normal)
        parts.append((self.element, main_font, 0.0))

        # "H" in normal size (if any Hs)
        if self.n_hs >= 1:
            parts.append(("H", main_font, 0.0))

        # H-count subscript (only if >1)
        if self.n_hs > 1:
            parts.append((str(self.n_hs), small_font, main_h * 0.30))

        # Charge superscript
        if self.formal_charge != 0:
            if self.formal_charge > 0:
                ctxt = f"{self.formal_charge}+" if self.formal_charge > 1 else "+"
            else:
                mag = abs(self.formal_charge)
                ctxt = f"{mag}\u2212" if mag > 1 else "\u2212"
            parts.append((ctxt, small_font, -main_h * 0.35))

        # Create the text items and measure total width
        x_cursor = 0.0
        items_with_x: list[tuple[QGraphicsSimpleTextItem, float, float]] = []
        for text, font, y_off in parts:
            ti = QGraphicsSimpleTextItem(text, self)
            ti.setFont(font)
            ti.setBrush(QBrush(color))
            ti.setZValue(12)
            w = ti.boundingRect().width()
            items_with_x.append((ti, x_cursor, y_off))
            self._label_items.append(ti)
            x_cursor += w

        total_w = x_cursor
        self.label_width = total_w

        # Position everything centred on the atom
        for ti, x, y_off in items_with_x:
            h = ti.boundingRect().height()
            ti.setPos(x - total_w / 2, -main_h / 2 + y_off)

        # White background to mask bond lines
        pad = 2
        self._bg_rect = QGraphicsRectItem(
            -total_w / 2 - pad, -main_h / 2 - pad,
            total_w + 2 * pad, main_h + 2 * pad,
            self,
        )
        self._bg_rect.setBrush(QBrush(QColor("#FAFAFA")))
        self._bg_rect.setPen(QPen(Qt.PenStyle.NoPen))
        self._bg_rect.setZValue(11)

    def set_highlighted(self, highlighted: bool):
        if highlighted:
            self._highlight.setPen(QPen(QColor("#00AAFF"), 2))
            self._highlight.setBrush(QBrush(QColor(0, 170, 255, 40)))
        else:
            self._highlight.setPen(QPen(Qt.PenStyle.NoPen))
            self._highlight.setBrush(QBrush(Qt.GlobalColor.transparent))

    def update_element(self, element: str):
        self.element = element
        self._build_label()


class BondItem(QGraphicsLineItem):
    """Visual representation of a bond — standard skeletal line drawing."""

    def __init__(self, a1_idx: int, a2_idx: int, bond_type: BondType,
                 p1: QPointF, p2: QPointF,
                 a1_label: bool = False, a2_label: bool = False,
                 a1_lw: float = 0.0, a2_lw: float = 0.0):
        super().__init__()
        self.a1_idx = a1_idx
        self.a2_idx = a2_idx
        self.bond_type = bond_type
        self._p1 = p1
        self._p2 = p2
        self._a1_hetero = a1_label
        self._a2_hetero = a2_label
        self._a1_lw = a1_lw
        self._a2_lw = a2_lw
        self._extra_lines: list[QGraphicsLineItem] = []
        self._extra_polys: list[QGraphicsPolygonItem] = []
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

        # Shorten bonds near labelled atoms so lines don't poke through
        shrink1 = (self._a1_lw / 2 + 3) if self._a1_hetero else 0.0
        shrink2 = (self._a2_lw / 2 + 3) if self._a2_hetero else 0.0
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

        elif self.bond_type == BondType.WEDGE:
            # Filled black triangle: narrow at start, wide at end
            self.setLine(QLineF(start, end))  # invisible backbone for hit-test
            self.setPen(QPen(Qt.PenStyle.NoPen))
            wedge_w = 5.0  # half-width at the wide end
            nx, ny = -uy * wedge_w, ux * wedge_w
            tri = QPolygonF([
                start,
                QPointF(end.x() + nx, end.y() + ny),
                QPointF(end.x() - nx, end.y() - ny),
            ])
            poly = QGraphicsPolygonItem(tri, self)
            poly.setBrush(QBrush(QColor(BOND_COLOR)))
            poly.setPen(QPen(Qt.PenStyle.NoPen))
            self._extra_polys.append(poly)

        elif self.bond_type == BondType.DASH:
            # Dashed wedge: series of short lines perpendicular to the bond,
            # getting wider from start to end
            self.setLine(QLineF(start, end))
            self.setPen(QPen(Qt.PenStyle.NoPen))
            n_dashes = 7
            dash_pen = QPen(QColor(BOND_COLOR), BOND_WIDTH)
            dash_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            max_w = 5.0
            for i in range(n_dashes):
                t = (i + 0.5) / n_dashes
                cx = start.x() + (end.x() - start.x()) * t
                cy = start.y() + (end.y() - start.y()) * t
                hw = max_w * t  # half-width grows with t
                ln = QGraphicsLineItem(
                    cx - uy * hw, cy + ux * hw,
                    cx + uy * hw, cy - ux * hw,
                    self,
                )
                ln.setPen(dash_pen)
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
        if self.bond_type in (BondType.WEDGE, BondType.DASH):
            # Wedge/dash: highlight the child shapes, keep parent NoPen
            if highlighted:
                hl_pen = QPen(QColor("#00AAFF"), BOND_WIDTH + 1)
                for poly in self._extra_polys:
                    poly.setPen(hl_pen)
                for ln in self._extra_lines:
                    ln.setPen(hl_pen)
            else:
                for poly in self._extra_polys:
                    poly.setPen(QPen(Qt.PenStyle.NoPen))
                dash_pen = QPen(QColor(BOND_COLOR), BOND_WIDTH)
                dash_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
                for ln in self._extra_lines:
                    ln.setPen(dash_pen)
            self.setPen(QPen(Qt.PenStyle.NoPen))
        else:
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
        for poly in self._extra_polys:
            scene = poly.scene()
            if scene:
                scene.removeItem(poly)
        self._extra_polys.clear()
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
        self._collapsed_hydrogens: dict[int, int] = {}  # H index -> N/O index

    def load_molecule(self, mol: Molecule):
        """Clear scene and render the given molecule."""
        self.clear()
        self._atom_items.clear()
        self._bond_items.clear()
        self._collapsed_hydrogens = self._label_hydrogens(mol)

        coords = mol.get_2d_coords()
        all_bonds = mol.get_all_bonds()

        # Auto-infer formal charges (e.g. N with 4 bonds → N+)
        display_charges = self._compute_display_charges(mol)
        # Build a clean RDKit mol to get accurate H counts,
        # using inferred charges so sanitization succeeds.
        display_hs = self._compute_display_hs(mol, display_charges)
        # GetTotalNumHs excludes separate H atoms. Include the ones represented
        # in OH/NH/NH2 labels, keeping their atoms/bonds in the molecular model.
        for parent_idx in self._collapsed_hydrogens.values():
            display_hs[parent_idx] = display_hs.get(parent_idx, 0) + 1

        # Add atoms with H-count and (possibly inferred) charge
        for i in range(mol.num_atoms):
            if i in self._collapsed_hydrogens:
                continue
            info = mol.get_atom_info(i)
            x, y = coords[i]
            n_hs = display_hs.get(i, 0)
            charge = display_charges.get(i, 0)
            item = AtomItem(i, info.element, x, y, n_hs, charge)
            self.addItem(item)
            self._atom_items[i] = item

        # Add bonds — shorten near labelled atoms proportional to label width
        for bond in all_bonds:
            a1, a2 = bond.begin_atom_idx, bond.end_atom_idx
            if a1 in self._collapsed_hydrogens or a2 in self._collapsed_hydrogens:
                continue
            ai1, ai2 = self._atom_items[a1], self._atom_items[a2]
            item = BondItem(a1, a2, bond.bond_type,
                            ai1.pos(), ai2.pos(),
                            ai1.show_label, ai2.show_label,
                            ai1.label_width, ai2.label_width)
            self.addItem(item)
            key = (min(a1, a2), max(a1, a2))
            self._bond_items[key] = item

    @staticmethod
    def _label_hydrogens(mol: Molecule) -> dict[int, int]:
        """Fold ordinary N-H/O-H into labels, keeping special Hs explicit."""
        result = {}
        for hydrogen in mol.to_rdkit().GetAtoms():
            if (hydrogen.GetAtomicNum() != 1 or hydrogen.GetDegree() != 1
                    or hydrogen.GetIsotope() or hydrogen.GetAtomMapNum()
                    or hydrogen.GetFormalCharge() or hydrogen.GetNumRadicalElectrons()
                    or hydrogen.HasQuery() or hydrogen.HasProp("molFileAlias")
                    or hydrogen.HasProp("atomLabel")):
                continue
            bond = hydrogen.GetBonds()[0]
            parent = bond.GetOtherAtom(hydrogen)
            if (parent.GetAtomicNum() not in (7, 8) or parent.GetNumRadicalElectrons()
                    or parent.HasQuery() or bond.GetBondDir() != Chem.BondDir.NONE
                    or bond.GetBondType() != Chem.BondType.SINGLE):
                continue
            # Preserve the existing OH rule. Nitrogen also supports several
            # H neighbors, bracket H counts, charges, and imine/aromatic bonds.
            if parent.GetAtomicNum() == 8 and (
                    parent.GetDegree() != 2 or parent.GetFormalCharge()
                    or parent.GetNumExplicitHs()
                    or any(b.GetBondType() != Chem.BondType.SINGLE for b in parent.GetBonds())
                    or not any(a.GetAtomicNum() > 1 for a in parent.GetNeighbors())):
                continue
            result[hydrogen.GetIdx()] = parent.GetIdx()
        return result

    def expand_atom_group(self, indices: Iterable[int]) -> set[int]:
        """Include hidden Hs when moving/deleting a visible OH/NH/NH2 group."""
        result = set(indices)
        result.update(h for h, parent in self._collapsed_hydrogens.items() if parent in result)
        return result

    @staticmethod
    def _compute_display_charges(mol: Molecule) -> dict[int, int]:
        """Infer formal charges for display.

        Atoms that already carry an explicit charge keep it.  For common
        octet-rule elements (N, O, B, halogens) whose bond-order sum
        exceeds the neutral count, the charge is inferred automatically
        (e.g. N with 4 bonds → +1).
        """
        from ..core.valence import infer_formal_charge

        _bv = {BondType.SINGLE: 1, BondType.DOUBLE: 2,
               BondType.TRIPLE: 3, BondType.AROMATIC: 1.5,
               BondType.WEDGE: 1, BondType.DASH: 1}
        all_bonds = mol.get_all_bonds()
        result: dict[int, int] = {}
        for i in range(mol.num_atoms):
            info = mol.get_atom_info(i)
            bos = 0.0
            for b in all_bonds:
                if b.begin_atom_idx == i or b.end_atom_idx == i:
                    bos += _bv.get(b.bond_type, 1)
            result[i] = infer_formal_charge(info.element, bos,
                                            info.formal_charge)
        return result

    @staticmethod
    def _compute_display_hs(
        mol: Molecule,
        display_charges: dict[int, int] | None = None,
    ) -> dict[int, int]:
        """Use RDKit sanitization to get accurate H counts for display.

        Builds a fresh mol (no stale NoImplicit / explicit-H state),
        sanitizes it, and reads back the total Hs.  Neutral carbons
        with bonds get 0 (skeletal style); isolated atoms get full Hs.

        When sanitization fails (e.g. hypervalent atom), individual atoms
        that can't report their H count fall back to a valence-table
        computation so that *other* atoms in the molecule still display
        correctly.

        *display_charges*, if given, overrides the atom's stored formal
        charge in the fresh mol so that RDKit sanitization succeeds for
        atoms with auto-inferred charges (e.g. N with 4 bonds + charge +1).
        """
        from ..core.valence import compute_display_hs as _valence_hs

        src = mol.to_rdkit()
        fresh = Chem.RWMol()
        for i in range(src.GetNumAtoms()):
            a = src.GetAtomWithIdx(i)
            na = Chem.Atom(a.GetAtomicNum())
            charge = (display_charges.get(i, a.GetFormalCharge())
                      if display_charges else a.GetFormalCharge())
            na.SetFormalCharge(charge)
            if a.GetNumExplicitHs() > 0:
                na.SetNumExplicitHs(a.GetNumExplicitHs())
            fresh.AddAtom(na)
        for bond in src.GetBonds():
            fresh.AddBond(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx(),
                          bond.GetBondType())
        try:
            Chem.SanitizeMol(fresh)
        except Exception:
            # Full sanitization failed (hypervalent atom?) — do partial
            # sanitization then compute implicit valence per-atom.
            try:
                Chem.SanitizeMol(
                    fresh,
                    Chem.SanitizeFlags.SANITIZE_ALL
                    ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES,
                )
            except Exception:
                pass
            for j in range(fresh.GetNumAtoms()):
                try:
                    fresh.GetAtomWithIdx(j).UpdatePropertyCache(strict=False)
                except Exception:
                    pass

        result: dict[int, int] = {}
        for i in range(fresh.GetNumAtoms()):
            a = fresh.GetAtomWithIdx(i)
            elem = a.GetSymbol()
            charge = a.GetFormalCharge()
            degree = a.GetDegree()

            try:
                n_hs = a.GetTotalNumHs()
            except Exception:
                # RDKit couldn't compute Hs (sanitization failed for this
                # atom or the whole mol) — fall back to valence table.
                bos = sum(b.GetBondTypeAsDouble() for b in a.GetBonds())
                n_hs = _valence_hs(elem, bos, charge)

            # Skeletal convention: neutral C with bonds hides Hs
            if elem == "C" and charge == 0 and degree > 0:
                n_hs = 0
            result[i] = n_hs
        return result

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
        best: Optional[BondItem] = None
        best_d = 15.0  # max detection distance in pixels
        for item in self._bond_items.values():
            a1_pos = self._atom_items.get(item.a1_idx)
            a2_pos = self._atom_items.get(item.a2_idx)
            if a1_pos and a2_pos:
                d = _point_to_line_dist(scene_pos, a1_pos.pos(), a2_pos.pos())
                if d < best_d:
                    best_d = d
                    best = item
        return best


class MoleculeCanvas(QGraphicsView):
    """Interactive view for the molecular scene.

    - **Scroll wheel**: zoom in / out.
    - **Middle-mouse drag** (or **right-mouse drag**): pan the canvas.
    - **Left-mouse**: forwarded to the current editing tool.
    """

    molecule_changed = Signal()

    def __init__(self, parent=None):
        self._scene = MoleculeScene()
        super().__init__(self._scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor("#FAFAFA")))
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)  # receive hover moves without button press
        # Allow the view to scroll beyond the content
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self._panning = False
        self._pan_start = QPointF()

    @property
    def mol_scene(self) -> MoleculeScene:
        return self._scene

    def load_molecule(self, mol: Molecule):
        self._scene.load_molecule(mol)
        # Expand scene rect so there is room to pan/scroll around
        br = self._scene.itemsBoundingRect().adjusted(-500, -500, 500, 500)
        self._scene.setSceneRect(br)
        # Use 1:1 pixel scale (SCALE px per coordinate unit) and centre
        # on the molecule.  This gives a comfortable default size; the
        # user can zoom with the scroll wheel.
        self.resetTransform()
        items_br = self._scene.itemsBoundingRect()
        if not items_br.isEmpty():
            self.centerOn(items_br.center())

    # -- zoom --------------------------------------------------------------

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    # -- pan (middle-mouse or right-mouse drag) ----------------------------

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.MiddleButton,
                               Qt.MouseButton.RightButton):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MouseButton.MiddleButton,
                               Qt.MouseButton.RightButton):
            self._panning = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)


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
