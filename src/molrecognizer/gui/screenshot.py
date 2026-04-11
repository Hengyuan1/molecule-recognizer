"""Screen capture and region selection.

Capture strategy (tries in order, uses the first that succeeds):

1. Qt ``QScreen.grabWindow`` — works on native Linux X11 and macOS.
2. ``grim`` — Wayland-native tool (``apt install grim``).
3. ``scrot`` — X11 tool (``apt install scrot``).
4. ``gnome-screenshot`` — GNOME tool.
5. PowerShell via WSL interop — WSL2 fallback when no Linux tool works.

Region selection is handled by :class:`ScreenshotDialog`, a normal
``QDialog`` (no fullscreen overlay tricks that break on WSLg).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QDialog


# ---------------------------------------------------------------------------
# WSL detection (cached)
# ---------------------------------------------------------------------------

_wsl_cached: bool | None = None


def is_wsl() -> bool:
    """Detect if running under WSL (cached)."""
    global _wsl_cached
    if _wsl_cached is None:
        try:
            with open("/proc/version", "r") as f:
                _wsl_cached = "microsoft" in f.read().lower()
        except OSError:
            _wsl_cached = False
    return _wsl_cached


# ---------------------------------------------------------------------------
# Screen capture backends
# ---------------------------------------------------------------------------

def _grab_qt() -> QPixmap | None:
    """Qt native capture (works on X11 and macOS)."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    pixmap = screen.grabWindow(0)
    if pixmap.isNull() or pixmap.width() == 0:
        return None
    return pixmap


def _grab_tool(cmd: list[str], output_path: str) -> QPixmap | None:
    """Run an external screenshot tool that saves to *output_path*."""
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return None
    if not os.path.isfile(output_path):
        return None
    pixmap = QPixmap(output_path)
    os.unlink(output_path)
    if pixmap.isNull():
        return None
    return pixmap


def _grab_grim() -> QPixmap | None:
    """Wayland-native capture via ``grim`` (apt install grim)."""
    if not shutil.which("grim"):
        return None
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    return _grab_tool(["grim", path], path)


def _grab_scrot() -> QPixmap | None:
    """X11 capture via ``scrot`` (apt install scrot)."""
    if not shutil.which("scrot"):
        return None
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    return _grab_tool(["scrot", "-o", path], path)


def _grab_gnome_screenshot() -> QPixmap | None:
    """GNOME capture via ``gnome-screenshot``."""
    if not shutil.which("gnome-screenshot"):
        return None
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    return _grab_tool(["gnome-screenshot", "-f", path], path)


def _find_powershell() -> str | None:
    candidates = [
        "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
        "/mnt/c/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _grab_wsl_powershell() -> QPixmap | None:
    """WSL2 fallback: capture the Windows desktop via PowerShell.

    Minimizes the Molecule Recognizer window on the Windows side (since
    Qt ``hide()`` doesn't propagate to the Windows desktop reliably on
    WSLg), then captures at physical resolution via ``SetProcessDPIAware``.
    """
    ps = _find_powershell()
    if not ps:
        return None

    # Write the script to a temp file to avoid shell-escaping issues
    # with nested quotes (C# attributes inside PowerShell strings).
    script = """\
Add-Type -MemberDefinition @"
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
"@ -Name User32 -Namespace Win32 -PassThru | Out-Null

# Minimize the Molecule Recognizer window so it doesn't appear in the capture
Get-Process | Where-Object { $_.MainWindowTitle -like "*Molecule*" } | ForEach-Object {
    [Win32.User32]::ShowWindow($_.MainWindowHandle, 6) | Out-Null
}
Start-Sleep -Milliseconds 400

[Win32.User32]::SetProcessDPIAware() | Out-Null
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

# Restore the Molecule Recognizer window (SW_RESTORE = 9)
Get-Process | Where-Object { $_.MainWindowTitle -like "*Molecule*" } | ForEach-Object {
    [Win32.User32]::ShowWindow($_.MainWindowHandle, 9) | Out-Null
}

Write-Output $tmpPath
"""
    # Save script to a temp .ps1 file to avoid encoding/escaping issues
    fd, script_path = tempfile.mkstemp(suffix=".ps1")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)
        result = subprocess.run(
            [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             script_path],
            capture_output=True, timeout=20,
        )
        win_path = result.stdout.decode("utf-8", errors="replace").strip()
        if not win_path:
            return None

        wsl_result = subprocess.run(
            ["wslpath", win_path], capture_output=True, timeout=5,
        )
        wsl_path = wsl_result.stdout.decode("utf-8", errors="replace").strip()
        if not wsl_path or not os.path.isfile(wsl_path):
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
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
    return None


# ---------------------------------------------------------------------------
# Public capture API
# ---------------------------------------------------------------------------

def grab_screen() -> QPixmap | None:
    """Capture the full screen using the best available method.

    Tries Linux-native methods first, then falls back to PowerShell on
    WSL2.  Returns ``None`` if all methods fail.
    """
    # 1. Qt native (X11, macOS)
    pixmap = _grab_qt()
    if pixmap:
        return pixmap

    # 2. grim (Wayland)
    pixmap = _grab_grim()
    if pixmap:
        return pixmap

    # 3. scrot (X11)
    pixmap = _grab_scrot()
    if pixmap:
        return pixmap

    # 4. gnome-screenshot
    pixmap = _grab_gnome_screenshot()
    if pixmap:
        return pixmap

    # 5. PowerShell (WSL2 only)
    if is_wsl():
        return _grab_wsl_powershell()

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pixmap_to_png_bytes(pixmap: QPixmap) -> bytes:
    """Convert a QPixmap to PNG bytes via QBuffer (BytesIO not supported)."""
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buf, "PNG")
    buf.close()
    return bytes(ba.data())


# ---------------------------------------------------------------------------
# Region-selection dialog
# ---------------------------------------------------------------------------

class ScreenshotDialog(QDialog):
    """Dialog showing a captured screenshot for region selection.

    The user draws a rectangle by clicking and dragging, then releases
    the mouse to confirm.  Press Escape to cancel.

    Usage::

        dlg = ScreenshotDialog(screenshot_pixmap, parent=window)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            cropped = dlg.result_pixmap
    """

    def __init__(self, screenshot: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select region to recognize  (Esc to cancel)")
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

        self._screenshot = screenshot
        self.result_pixmap: QPixmap | None = None

        self._selecting = False
        self._origin = QPoint()
        self._current = QPoint()

        # Scale screenshot to fit ~90% of available screen area
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            max_w = int(avail.width() * 0.92)
            max_h = int(avail.height() * 0.88)
        else:
            max_w, max_h = 1600, 900

        self._scale = min(
            max_w / screenshot.width(),
            max_h / screenshot.height(),
            1.0,
        )
        display_w = int(screenshot.width() * self._scale)
        display_h = int(screenshot.height() * self._scale)

        self._display_pixmap = screenshot.scaled(
            display_w, display_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setFixedSize(self._display_pixmap.width(),
                          self._display_pixmap.height())

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._display_pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 60))

        if self._selecting:
            rect = QRect(self._origin, self._current).normalized()
            painter.drawPixmap(rect, self._display_pixmap, rect)
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.drawRect(rect)

        painter.end()

    # -- mouse handling ----------------------------------------------------

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

            if rect.width() > 5 and rect.height() > 5:
                inv = 1.0 / self._scale
                src_rect = QRect(
                    int(rect.x() * inv), int(rect.y() * inv),
                    int(rect.width() * inv), int(rect.height() * inv),
                )
                self.result_pixmap = self._screenshot.copy(src_rect)

            self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
