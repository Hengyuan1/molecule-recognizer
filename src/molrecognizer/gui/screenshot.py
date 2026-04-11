"""Fullscreen overlay for capturing a screen region.

On WSL2, Qt's grabWindow doesn't work — we use PowerShell to capture
the Windows desktop, then show the overlay for region selection.
On native Linux/macOS, Qt's grabWindow is used directly.
"""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


def _is_wsl() -> bool:
    """Detect if running under WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _find_powershell() -> str | None:
    """Find powershell.exe for Windows interop."""
    candidates = [
        "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
        "/mnt/c/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _grab_screen_wsl() -> QPixmap | None:
    """Use PowerShell to capture the Windows desktop from WSL."""
    ps = _find_powershell()
    if not ps:
        return None

    script = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bounds = $screen.Bounds
$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$tmpPath = [System.IO.Path]::GetTempPath() + 'molrecognizer_screenshot.png'
$bmp.Save($tmpPath, [System.Drawing.Imaging.ImageFormat]::Png)
$gfx.Dispose()
$bmp.Dispose()
Write-Output $tmpPath
"""
    try:
        result = subprocess.run(
            [ps, "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=10
        )
        win_path = result.stdout.strip()
        if not win_path:
            return None

        # Convert Windows path to WSL path
        wsl_result = subprocess.run(
            ["wslpath", win_path],
            capture_output=True, text=True, timeout=5
        )
        wsl_path = wsl_result.stdout.strip()
        if not wsl_path or not os.path.isfile(wsl_path):
            # Fallback: manual conversion
            wsl_path = win_path.replace("\\", "/")
            drive = wsl_path[0].lower()
            wsl_path = f"/mnt/{drive}{wsl_path[2:]}"

        if os.path.isfile(wsl_path):
            pixmap = QPixmap(wsl_path)
            os.unlink(wsl_path)
            if not pixmap.isNull():
                return pixmap
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def _grab_screen_native() -> QPixmap | None:
    """Use Qt to grab the screen (works on native Linux/macOS)."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    pixmap = screen.grabWindow(0)
    if pixmap.isNull() or pixmap.width() == 0:
        return None
    return pixmap


def grab_screen() -> QPixmap | None:
    """Capture the full screen, using the best available method."""
    if _is_wsl():
        return _grab_screen_wsl()
    return _grab_screen_native()


class ScreenshotOverlay(QWidget):
    """Semi-transparent fullscreen overlay.

    The user draws a rectangle by clicking and dragging.
    On mouse release the captured region is emitted as a QPixmap signal.
    Press Escape to cancel.
    """

    captured = Signal(QPixmap)  # emitted with the cropped screenshot
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._origin = QPoint()
        self._current = QPoint()
        self._selecting = False
        self._full_screenshot: QPixmap | None = None

    def start(self):
        """Grab the entire screen, then show the overlay for region selection."""
        self._full_screenshot = grab_screen()
        if self._full_screenshot is None or self._full_screenshot.isNull():
            self.cancelled.emit()
            return

        # Size the overlay to match the captured image
        w = self._full_screenshot.width()
        h = self._full_screenshot.height()

        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.setGeometry(geo)
        else:
            self.setGeometry(0, 0, w, h)

        self.showFullScreen()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw the screenshot as background, scaled to widget
        if self._full_screenshot:
            scaled = self._full_screenshot.scaled(
                self.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled)
        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._selecting:
            rect = QRect(self._origin, self._current).normalized()
            # Clear the selection area (show original screenshot)
            if self._full_screenshot:
                scaled = self._full_screenshot.scaled(
                    self.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                painter.drawPixmap(rect, scaled, rect)
            # Draw selection border
            pen = QPen(QColor(0, 120, 215), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            rect = QRect(self._origin, self._current).normalized()
            self.hide()
            if rect.width() > 5 and rect.height() > 5 and self._full_screenshot:
                # Map overlay coordinates to screenshot coordinates
                sx = self._full_screenshot.width() / self.width()
                sy = self._full_screenshot.height() / self.height()
                src_rect = QRect(
                    int(rect.x() * sx), int(rect.y() * sy),
                    int(rect.width() * sx), int(rect.height() * sy)
                )
                cropped = self._full_screenshot.copy(src_rect)
                self.captured.emit(cropped)
            else:
                self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._selecting = False
            self.hide()
            self.cancelled.emit()
