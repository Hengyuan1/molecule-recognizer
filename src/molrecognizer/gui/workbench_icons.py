"""Small vector icons for the workbench, rendered at high DPI by Qt."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


_SHAPES = {
    "open": '<path d="M3 7h7l2 3h9l-3 10H3z"/><path d="M3 10V4h7l2 3h7v3"/>',
    "capture": '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/><rect x="7" y="7" width="10" height="10" rx="1"/>',
    "select": '<path d="M5 3v17l5-5 4 7 3-2-4-7h7z"/>',
    "bond": '<path d="M4 18L18 4M7 21L21 7"/>',
    "benzene": '<path d="M12 2L21 7v10l-9 5-9-5V7zM12 5l6 3M18 15.5L12 19M6 15V9"/>',
    "ring6": '<path d="M12 2L21 7v10l-9 5-9-5V7z"/>',
    "ring5": '<path d="M12 2l9.5 7-3.6 11H6.1L2.5 9z"/>',
    "ring4": '<rect x="3" y="3" width="18" height="18"/>',
    "ring3": '<path d="M12 2L22 21H2z"/>',
    "charge+": '<circle cx="12" cy="12" r="9.5"/><path d="M7 12h10m-5-5v10"/>',
    "charge-": '<circle cx="12" cy="12" r="9.5"/><path d="M7 12h10"/>',
    "atom": '<circle cx="12" cy="12" r="7"/><path d="M10 9H8v6h2m6-6h-2v6h2"/>',
    "eraser": '<path d="M3 14l10-10 8 8-9 9H9zM8 9l8 8M12 21h9"/>',
    "undo": '<path d="M8 5L3 10l5 5M3 10h11a6 6 0 0 1 0 12"/>',
    "redo": '<path d="M16 5l5 5-5 5m5-5H10a6 6 0 0 0 0 12"/>',
    "format": '<path d="M4 20L16 8M13 5l6 6M5 3v6M2 6h6m11 9v6m-3-3h6"/>',
    "clear": '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>',
    "molecule": '<path d="M12 3l8 5v8l-8 5-8-5V8zM4 8l8 5 8-5m-8 5v8"/>',
}


def workbench_icon(name: str) -> QIcon:
    shape = _SHAPES[name]
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
           '<g fill="none" stroke="#356b9f" stroke-width="1.7" '
           'stroke-linecap="round" stroke-linejoin="round">'
           + shape + '</g></svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon
