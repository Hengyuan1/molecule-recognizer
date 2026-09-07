"""Small interactive 3D ball-and-stick molecular viewer (QPainter-based)."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .window_placement import OwnerDialog

# CPK-ish colours
_ELEM_COL = {
    "H": "#AAAAAA", "C": "#555555", "N": "#3355DD", "O": "#DD2222",
    "S": "#CCAA00", "P": "#DD8800", "F": "#22BB22", "Cl": "#22CC22",
    "Br": "#992222", "I": "#772299", "B": "#DD8899", "Si": "#AABB99",
    "Se": "#CC8800",
}

# Relative display radii (arbitrary units, scaled at paint time)
_ELEM_RAD: dict[str, float] = {
    "H": 3.5, "C": 5.5, "N": 5.0, "O": 5.0, "S": 6.5, "P": 6.5,
    "F": 4.5, "Cl": 5.5, "Br": 6.0, "I": 6.5, "B": 5.5, "Si": 6.5,
}
_DEFAULT_RAD = 5.5


def _rotate(x: float, y: float, z: float,
            pitch: float, yaw: float) -> tuple[float, float, float]:
    """Rotate *x, y, z* by *pitch* (X-axis) then *yaw* (Y-axis)."""
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    y1 = y * cp - z * sp
    z1 = y * sp + z * cp
    x2 = x * cy + z1 * sy
    z2 = -x * sy + z1 * cy
    return x2, y1, z2


class Viewer3DWidget(QWidget):
    """Interactive 3D ball-and-stick viewer.

    Left-drag to rotate, right-drag to pan, scroll wheel to zoom.
    Double-click to expand (a comparison pane in the main workbench).
    """

    expand_requested = Signal()

    def __init__(self, parent: QWidget | None = None, *,
                 open_on_dblclick: bool = True, expand_in_place: bool = False) -> None:
        super().__init__(parent)
        self._atoms: list[tuple[str, float, float, float]] = []
        self._bonds: list[tuple[int, int, int]] = []   # (i, j, order)
        self._pitch = math.radians(-20)
        self._yaw = math.radians(30)
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._bounding_r = 1.0         # bounding-sphere radius (constant)
        self._drag_start = None
        self._drag_rot: tuple[float, float] = (0.0, 0.0)
        self._pan_start = None
        self._pan_origin: tuple[float, float] = (0.0, 0.0)
        self._open_on_dblclick = open_on_dblclick
        self._expand_in_place = expand_in_place
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumSize(160, 140)
        self.setStyleSheet(
            "background: #ffffff;"
            "border: 1px solid #dde1e6;"
            "border-radius: 8px;"
        )

    # -- public API --------------------------------------------------------

    def set_molecule(self, atoms, bonds):
        """*atoms*: list of (element, x, y, z).
        *bonds*: list of (i, j) or (i, j, order)."""
        self._atoms = list(atoms)
        self._bonds = [(b[0], b[1], b[2] if len(b) > 2 else 1)
                       for b in bonds]
        self._zoom = 1.0
        self._pan_x = self._pan_y = 0.0
        # Pre-compute bounding-sphere radius so scale is rotation-invariant
        if self._atoms:
            n = len(self._atoms)
            mx = sum(a[1] for a in self._atoms) / n
            my = sum(a[2] for a in self._atoms) / n
            mz = sum(a[3] for a in self._atoms) / n
            self._bounding_r = max(
                math.sqrt((a[1] - mx) ** 2 + (a[2] - my) ** 2
                          + (a[3] - mz) ** 2)
                for a in self._atoms
            )
            self._bounding_r = max(self._bounding_r, 0.01)
        self.update()

    def clear(self):
        self._atoms.clear()
        self._bonds.clear()
        self._zoom = 1.0
        self._pan_x = self._pan_y = 0.0
        self._bounding_r = 1.0
        self.update()

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        if not self._atoms:
            painter.setPen(QColor("#8899aa"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "No 3D structure")
            painter.end()
            return

        # Centre molecule at geometric centre
        n = len(self._atoms)
        mx = sum(a[1] for a in self._atoms) / n
        my = sum(a[2] for a in self._atoms) / n
        mz = sum(a[3] for a in self._atoms) / n

        # Rotate
        rotated: list[tuple[str, float, float, float]] = []
        for elem, x, y, z in self._atoms:
            rx, ry, rz = _rotate(x - mx, y - my, z - mz,
                                 self._pitch, self._yaw)
            rotated.append((elem, rx, ry, rz))

        # Scale from bounding sphere (rotation-invariant) + zoom
        margin = 22
        avail = min(w, h) / 2 - margin
        scale = avail / self._bounding_r * self._zoom

        # Orthographic projection -> screen coords (with pan offset)
        ox = cx + self._pan_x
        oy = cy + self._pan_y
        projected: list[tuple[str, float, float, float]] = []
        for elem, rx, ry, rz in rotated:
            projected.append((elem, rx * scale + ox, -ry * scale + oy, rz))

        # Z range for depth shading
        z_vals = [rz for _, _, _, rz in rotated]
        z_min, z_max = min(z_vals), max(z_vals)
        z_range = max(z_max - z_min, 0.01)

        # Draw bonds (far first)
        bond_w = max(1.2, scale * 0.06)
        sorted_bonds = sorted(
            self._bonds,
            key=lambda b: (rotated[b[0]][3] + rotated[b[1]][3]) / 2,
        )
        bond_pen = QPen(QColor("#999999"), bond_w)
        bond_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bond_pen)

        for i, j, order in sorted_bonds:
            sx1, sy1 = projected[i][1], projected[i][2]
            sx2, sy2 = projected[j][1], projected[j][2]
            if order <= 1:
                painter.drawLine(QPointF(sx1, sy1), QPointF(sx2, sy2))
            else:
                dx = sx2 - sx1
                dy = sy2 - sy1
                length = math.sqrt(dx * dx + dy * dy)
                if length < 0.1:
                    painter.drawLine(QPointF(sx1, sy1), QPointF(sx2, sy2))
                    continue
                # Perpendicular unit vector
                nx = -dy / length
                ny = dx / length
                gap = bond_w * 1.6  # spacing between parallel lines
                if order == 2:
                    d = gap * 0.5
                    painter.drawLine(
                        QPointF(sx1 + nx * d, sy1 + ny * d),
                        QPointF(sx2 + nx * d, sy2 + ny * d))
                    painter.drawLine(
                        QPointF(sx1 - nx * d, sy1 - ny * d),
                        QPointF(sx2 - nx * d, sy2 - ny * d))
                else:  # triple
                    painter.drawLine(QPointF(sx1, sy1), QPointF(sx2, sy2))
                    painter.drawLine(
                        QPointF(sx1 + nx * gap, sy1 + ny * gap),
                        QPointF(sx2 + nx * gap, sy2 + ny * gap))
                    painter.drawLine(
                        QPointF(sx1 - nx * gap, sy1 - ny * gap),
                        QPointF(sx2 - nx * gap, sy2 - ny * gap))

        # Draw atoms (far first, so near atoms paint on top)
        for idx in sorted(range(len(projected)),
                          key=lambda i: projected[i][3]):
            elem, sx, sy, rz = projected[idx]
            r = _ELEM_RAD.get(elem, _DEFAULT_RAD) * 0.04 * scale
            r = max(r, 2.0)
            r = min(r, 30.0)

            base = QColor(_ELEM_COL.get(elem, "#888888"))
            shade = 0.65 + 0.35 * ((rz - z_min) / z_range)
            color = QColor(min(255, int(base.red() * shade)),
                           min(255, int(base.green() * shade)),
                           min(255, int(base.blue() * shade)))
            painter.setPen(QPen(color.darker(130), 0.5))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(sx, sy), r, r)

            # Element labels for heteroatoms in larger views
            if r > 6 and elem not in ("C", "H"):
                font = painter.font()
                font.setPixelSize(max(8, int(r * 1.1)))
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(QColor("#ffffff"))
                rect = QRectF(sx - r, sy - r, 2 * r, 2 * r)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, elem)

        painter.end()

    # -- mouse rotation / pan ----------------------------------------------

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
            self._drag_rot = (self._pitch, self._yaw)
        elif event.button() == Qt.MouseButton.RightButton:
            self._pan_start = event.pos()
            self._pan_origin = (self._pan_x, self._pan_y)

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag_start is not None:
            dx = event.pos().x() - self._drag_start.x()
            dy = event.pos().y() - self._drag_start.y()
            self._yaw = self._drag_rot[1] + math.radians(dx * 0.5)
            self._pitch = self._drag_rot[0] + math.radians(dy * 0.5)
            self.update()
        elif self._pan_start is not None:
            dx = event.pos().x() - self._pan_start.x()
            dy = event.pos().y() - self._pan_start.y()
            self._pan_x = self._pan_origin[0] + dx
            self._pan_y = self._pan_origin[1] + dy
            self.update()

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
        elif event.button() == Qt.MouseButton.RightButton:
            self._pan_start = None

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        if (self._open_on_dblclick
                and self._atoms
                and event.button() == Qt.MouseButton.LeftButton):
            self._drag_start = self._pan_start = None
            if self._expand_in_place:
                self.expand_requested.emit()
                return
            dlg = Viewer3DDialog(self._atoms, self._bonds,
                                 self._pitch, self._yaw, parent=self.window())
            dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dlg.open()

    def wheelEvent(self, event):  # noqa: N802
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        self._zoom = max(0.25, min(6.0, self._zoom * factor))
        self.update()


class Viewer3DPanel(QWidget):
    """Non-modal comparison pane; the adjacent 2D editor stays interactive."""

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('editor_workspace')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        header = QHBoxLayout()
        title = QLabel('3D structure')
        title.setObjectName('workspace_title')
        header.addWidget(title, 1)
        self._close = QPushButton('Close')
        self._close.setToolTip('Close comparison and restore the full 2D canvas')
        self._close.clicked.connect(self.close_requested.emit)
        header.addWidget(self._close)
        layout.addLayout(header)
        self._viewer = Viewer3DWidget(open_on_dblclick=False)
        self._viewer.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self._viewer, 1)
        hint = QLabel('Left-drag: rotate · Right-drag: pan · Scroll: zoom')
        hint.setObjectName('workspace_hint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self._status = QLabel()
        self._status.setObjectName('workspace_hint')
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self.set_stale(False)
        self._escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._escape.activated.connect(self.close_requested.emit)

    def copy_from(self, source: Viewer3DWidget):
        self._viewer.set_molecule(source._atoms, source._bonds)
        self._viewer._pitch, self._viewer._yaw = source._pitch, source._yaw
        self._viewer._zoom = source._zoom

    def set_stale(self, stale: bool):
        self._status.setText('2D structure changed. Click Render to update this 3D view.' if stale else '')
        self._status.setVisible(stale)


# ======================================================================
# Separate larger viewer dialog
# ======================================================================

class Viewer3DDialog(OwnerDialog):
    """Resizable window showing a 3D ball-and-stick view of a molecule."""

    def __init__(self, atoms, bonds, pitch=None, yaw=None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("3D Structure Viewer")
        self.resize(640, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._viewer = Viewer3DWidget(open_on_dblclick=False)
        self._viewer.set_molecule(atoms, bonds)
        if pitch is not None:
            self._viewer._pitch = pitch
        if yaw is not None:
            self._viewer._yaw = yaw
        layout.addWidget(self._viewer)
