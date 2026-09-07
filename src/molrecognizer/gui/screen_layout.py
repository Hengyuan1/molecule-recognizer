"""Native screen sizing: all window geometry stays in Qt logical pixels."""

from PySide6.QtCore import QMargins, QRect, QSize


def screen_signature(screen):
    return (screen.name(), screen.availableGeometry().getRect(), screen.devicePixelRatio())


def recommended_scale(screen):
    # Windows already applies DPR. A 2880px panel at 250% is only 1152 logical
    # pixels wide; adding the WSL 180% compensation would scale it twice.
    dpr = max(1.0, screen.devicePixelRatio())
    physical_width = screen.geometry().width() * dpr
    return round(max(0.6, 1.8 / dpr), 1) if physical_width >= 2500 else 0.8


def recommended_size(screen):
    available = screen.availableGeometry()
    fraction = 0.8 if screen.geometry().width() * screen.devicePixelRatio() >= 2500 else 0.7
    return QSize(round(available.width() * fraction), round(available.height() * fraction))


def fitted_geometry(current: QRect, desired: QSize, minimum: QSize,
                    available: QRect, margins: QMargins) -> QRect:
    """Clamp the entire native frame, including title bar, to the work area."""
    client_area = available.marginsRemoved(margins)
    size = desired.expandedTo(minimum).boundedTo(client_area.size())
    x = max(client_area.left(), min(current.x(), client_area.right() - size.width() + 1))
    y = max(client_area.top(), min(current.y(), client_area.bottom() - size.height() + 1))
    return QRect(x, y, size.width(), size.height())
