"""Screen capture and region selection.

Capture strategy (tries in order, uses the first that succeeds):

1. PowerShell via WSL interop — captures the Windows monitor under the cursor.
2. Qt ``QScreen.grabWindow`` — captures the Qt monitor under the cursor.
3. ``grim`` — Wayland-native tool (``apt install grim``).
4. ``scrot`` — X11 tool (``apt install scrot``).
5. ``gnome-screenshot`` — GNOME tool.

Windows/WSL use the native overlay in ``native_capture``. Other desktops use
``ScreenshotDialog`` as a borderless, monitor-sized selection overlay.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile

from PySide6.QtCore import (
    QBuffer, QByteArray, QCoreApplication, QIODevice, QObject, QPoint, QRect,
    QTimer, Qt, Signal,
)
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QPushButton, QVBoxLayout, QWidget,
)


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
    """Capture the monitor currently under the mouse cursor."""
    screen = QGuiApplication.screenAt(QCursor.pos())
    if screen is None:
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


def windows_monitor_under_cursor() -> tuple[str, int, int] | None:
    """Return the Windows monitor name and physical size under the cursor."""
    if not is_wsl():
        return None
    powershell = _find_powershell()
    if not powershell:
        return None
    command = (
        "Add-Type -TypeDefinition 'using System; "
        "using System.Runtime.InteropServices; "
        "public static class MRDpi { "
        "[DllImport(\"user32.dll\")] public static extern bool "
        "SetProcessDpiAwarenessContext(IntPtr value); }'; "
        "[MRDpi]::SetProcessDpiAwarenessContext([IntPtr](-4)) | Out-Null; "
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$p=[System.Windows.Forms.Cursor]::Position; "
        "$s=[System.Windows.Forms.Screen]::FromPoint($p); "
        "Write-Output ($s.DeviceName+'|'+$s.Bounds.Width+'|'+"
        "$s.Bounds.Height)"
    )
    try:
        result = subprocess.run(
            [powershell, "-NoProfile", "-Command", command],
            capture_output=True, timeout=8,
        )
        output = result.stdout.decode("utf-8", errors="replace").strip()
        name, width, height = output.rsplit("|", 2)
        return name, int(width), int(height)
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Global screenshot hotkey (Windows/WSL)
# ---------------------------------------------------------------------------

_HOTKEY_SCRIPT = r"""
param([int]$Port)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @"
using System;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

public sealed class MoleculeRecognizerHotkey : NativeWindow, IDisposable {
    [DllImport("user32.dll")]
    private static extern bool RegisterHotKey(
        IntPtr hWnd, int id, uint modifiers, uint virtualKey);
    [DllImport("user32.dll")]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);
    [DllImport("user32.dll")]
    private static extern bool SetProcessDpiAwarenessContext(IntPtr value);
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr p);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(
        IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")]
    private static extern IntPtr MonitorFromWindow(IntPtr hWnd, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern bool GetMonitorInfo(
        IntPtr monitor, ref MONITORINFOEX info);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct MONITORINFOEX {
        public int size;
        public int left;
        public int top;
        public int right;
        public int bottom;
        public int workLeft;
        public int workTop;
        public int workRight;
        public int workBottom;
        public uint flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
        public string deviceName;
    }

    private const int WM_HOTKEY = 0x0312;
    private readonly TcpClient client;
    private readonly Timer heartbeat;
    private IntPtr appWindow = IntPtr.Zero;
    private string lastMonitorName = "";
    private string monitorCandidate = "";
    private int monitorCandidateCount = 0;

    public MoleculeRecognizerHotkey(int portNumber) {
        SetProcessDpiAwarenessContext(new IntPtr(-4));
        client = new TcpClient("127.0.0.1", portNumber);
        CreateHandle(new CreateParams());
        // MOD_ALT = 1, virtual-key Y = 0x59
        if (!RegisterHotKey(Handle, 1, 0x0001, 0x59))
            throw new InvalidOperationException(
                "Alt+Y is already registered by another application.");
        heartbeat = new Timer();
        heartbeat.Interval = 500;
        heartbeat.Tick += delegate { SendMonitor(); };
        heartbeat.Start();
    }

    private void Send(string value) {
        try {
            byte[] data = Encoding.UTF8.GetBytes(value);
            client.GetStream().Write(data, 0, data.Length);
        } catch {
            // The WSL GUI exited or crashed. Release Alt+Y instead of leaving
            // a detached Windows helper that blocks the next app instance.
            Application.ExitThread();
        }
    }

    private void SendMonitor() {
        appWindow = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr p) {
            StringBuilder title = new StringBuilder(256);
            GetWindowText(hWnd, title, title.Capacity);
            if (title.ToString().StartsWith("Molecule Recognizer")) {
                appWindow = hWnd;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        if (appWindow == IntPtr.Zero) {
            Send("P\n");
            return;
        }
        IntPtr monitor = MonitorFromWindow(appWindow, 2);
        MONITORINFOEX info = new MONITORINFOEX();
        info.size = Marshal.SizeOf(info);
        if (GetMonitorInfo(monitor, ref info)) {
            if (lastMonitorName.Length == 0) {
                lastMonitorName = info.deviceName;
            } else if (lastMonitorName != info.deviceName) {
                if (monitorCandidate == info.deviceName)
                    monitorCandidateCount++;
                else {
                    monitorCandidate = info.deviceName;
                    monitorCandidateCount = 1;
                }
                // Require 1.5 seconds on the new majority monitor so boundary
                // jitter cannot alternate UI scaling and sizing operations.
                if (monitorCandidateCount < 3) {
                    Send("P\n");
                    return;
                }
                lastMonitorName = info.deviceName;
                monitorCandidate = "";
                monitorCandidateCount = 0;
            } else {
                monitorCandidate = "";
                monitorCandidateCount = 0;
            }
            int width = info.right - info.left;
            int height = info.bottom - info.top;
            Send("M|" + info.deviceName + "|" + width + "|" + height + "\n");
        } else {
            Send("P\n");
        }
    }

    protected override void WndProc(ref Message message) {
        if (message.Msg == WM_HOTKEY && message.WParam.ToInt32() == 1)
            Send("H\n");
        base.WndProc(ref message);
    }

    public void Dispose() {
        heartbeat.Stop();
        heartbeat.Dispose();
        UnregisterHotKey(Handle, 1);
        DestroyHandle();
        client.Dispose();
    }
}
"@ -ReferencedAssemblies System.Windows.Forms

$hotkey = New-Object MoleculeRecognizerHotkey($Port)
try {
    [System.Windows.Forms.Application]::Run()
} finally {
    $hotkey.Dispose()
}
"""


class GlobalScreenshotHotkey(QObject):
    """Register Alt+Y with Windows and relay it to the WSL Qt application."""

    activated = Signal()
    monitor_changed = Signal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server: socket.socket | None = None
        self._connection: socket.socket | None = None
        self._process: subprocess.Popen | None = None
        self._script_path: str | None = None
        self._timer: QTimer | None = None
        self._receive_buffer = bytearray()
        self._last_monitor = None
        self.error: str | None = None

        if not is_wsl():
            return
        powershell = _find_powershell()
        if not powershell:
            return

        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind(("0.0.0.0", 0))
            self._server.listen(4)
            self._server.setblocking(False)
            port = self._server.getsockname()[1]

            fd, self._script_path = tempfile.mkstemp(suffix=".ps1")
            with os.fdopen(fd, "w", encoding="utf-8") as script_file:
                script_file.write(_HOTKEY_SCRIPT)
            self._process = subprocess.Popen(
                [
                    powershell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", self._script_path, "-Port", str(port),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self._timer = QTimer(self)
            self._timer.setInterval(50)
            self._timer.timeout.connect(self._poll)
            self._timer.start()
            app = QCoreApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self.close)
        except OSError as error:
            self.error = str(error)
            self.close()

    @property
    def available(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _poll(self):
        if self._server is None:
            return
        if self._connection is None:
            try:
                self._connection, _ = self._server.accept()
                self._connection.setblocking(False)
            except BlockingIOError:
                return
            except OSError:
                return
        try:
            data = self._connection.recv(64)
        except BlockingIOError:
            return
        except OSError:
            data = b""
        if not data:
            self._connection.close()
            self._connection = None
            return
        self._receive_buffer.extend(data)
        while b"\n" in self._receive_buffer:
            line, _, remainder = self._receive_buffer.partition(b"\n")
            self._receive_buffer = bytearray(remainder)
            if line == b"H":
                self.activated.emit()
            elif line.startswith(b"M|"):
                try:
                    name, width, height = line.decode("utf-8").split("|")[1:]
                    monitor = name, int(width), int(height)
                except (UnicodeDecodeError, ValueError):
                    continue
                if monitor != self._last_monitor:
                    self._last_monitor = monitor
                    self.monitor_changed.emit(*monitor)

    def close(self):
        if self._timer is not None:
            self._timer.stop()
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        self._process = None
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        if self._server is not None:
            self._server.close()
        self._server = None
        if self._script_path:
            try:
                os.unlink(self._script_path)
            except OSError:
                pass
        self._script_path = None


def _grab_wsl_powershell() -> QPixmap | None:
    """WSL2 fallback: capture the Windows desktop via PowerShell."""
    ps = _find_powershell()
    if not ps:
        return None

    script = """\
Add-Type -MemberDefinition @"
[DllImport("user32.dll")]
public static extern bool SetProcessDpiAwarenessContext(IntPtr value);
"@ -Name User32 -Namespace Win32 -PassThru | Out-Null

# Per-monitor-v2 awareness makes Screen.Bounds and CopyFromScreen use the same
# physical-pixel coordinate space on mixed-DPI multi-monitor systems.
[Win32.User32]::SetProcessDpiAwarenessContext([IntPtr](-4)) | Out-Null
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# The Qt application hides its own window before invoking this script. Do not
# manipulate that WSLg window through Win32 ShowWindow: doing so desynchronizes
# Qt's visibility state and can stall queued paint/result events until the user
# moves the window.
Start-Sleep -Milliseconds 150

# Capture only the monitor containing the cursor. This keeps the selection
# image large while allowing capture from any extended monitor.
$cursor = [System.Windows.Forms.Cursor]::Position
$screen = [System.Windows.Forms.Screen]::FromPoint($cursor)
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
    """Capture the monitor under the cursor using the best available method."""
    # WSLg's Qt screens do not necessarily represent the Windows monitor
    # containing the cursor, so capture Windows directly first.
    if is_wsl():
        pixmap = _grab_wsl_powershell()
        if pixmap:
            return pixmap
    pixmap = _grab_qt()
    if pixmap:
        return pixmap
    pixmap = _grab_grim()
    if pixmap:
        return pixmap
    pixmap = _grab_scrot()
    if pixmap:
        return pixmap
    pixmap = _grab_gnome_screenshot()
    if pixmap:
        return pixmap
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

_HANDLE = 8          # resize-handle half-size in pixels
_EDGE_MARGIN = 12    # hit-test margin for edges


class ScreenshotDialog(QDialog):
    """Borderless monitor-sized overlay for non-Windows region selection.

    The user draws a rectangle, then adjusts it by dragging edges or
    corners.  A small ✓ / ✗ toolbar appears below the selection.

    - **✓** (or Enter) — accept the selection.
    - **✗** (or Escape) — discard and return.

    Usage::

        dlg = ScreenshotDialog(screenshot_pixmap, parent=window)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            cropped = dlg.result_pixmap
    """

    def __init__(self, screenshot: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select structure region (Enter to recognize, Esc to cancel)")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

        self._screenshot = screenshot
        self.result_pixmap: QPixmap | None = None

        # Selection state
        self._sel: QRect | None = None      # current selection in display coords
        self._drawing = False               # user is drawing a NEW box
        self._dragging = False              # user is moving the box
        self._resizing = False              # user is resizing the box
        self._drag_edge = ""                # which edge/corner: "tl","t","tr",...
        self._drag_origin = QPoint()
        self._sel_origin = QRect()

        # Match the screen's logical geometry; retain the original physical
        # pixels for cropping. Never show a reduced preview in a normal window.
        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.geometry()
            max_w = avail.width()
            max_h = avail.height()
        else:
            max_w, max_h = 1600, 900

        self._scale = min(
            max_w / screenshot.width(),
            max_h / screenshot.height(),
        )
        display_w = int(screenshot.width() * self._scale)
        display_h = int(screenshot.height() * self._scale)

        self._display_pixmap = screenshot.scaled(
            display_w, display_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._display_pixmap.setDevicePixelRatio(1.0)
        self.setFixedSize(self._display_pixmap.width(),
                          self._display_pixmap.height())
        if screen:
            self.move(
                avail.x() + (avail.width() - self.width()) // 2,
                avail.y() + (avail.height() - self.height()) // 2,
            )

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._display_pixmap)
        # Dim the whole image
        painter.fillRect(self.rect(), QColor(0, 0, 0, 60))

        if not self._sel:
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRect(20, 20, self.width() - 40, 50),
                             Qt.AlignmentFlag.AlignCenter,
                             "Drag to select. Adjust edges/corners, then Enter to recognize. Esc cancels.")

        if self._sel and self._sel.width() > 0 and self._sel.height() > 0:
            r = self._sel.normalized()
            # Draw the clear (un-dimmed) region
            painter.drawPixmap(r, self._display_pixmap, r)
            # Blue border
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.drawRect(r)
            # Resize handles (small squares at corners and edge midpoints)
            painter.setBrush(QColor(0, 120, 215))
            painter.setPen(Qt.PenStyle.NoPen)
            for hx, hy in self._handle_positions(r):
                painter.drawRect(hx - _HANDLE // 2, hy - _HANDLE // 2,
                                 _HANDLE, _HANDLE)
            # ✓ / ✗ buttons drawn as text below the selection
            bar_y = r.bottom() + 8
            if bar_y + 28 > self.height():
                bar_y = max(0, r.top() - 36)
            bar_x = max(0, min(self.width() - 60, r.center().x() - 30))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(50, 50, 50, 200))
            painter.drawRoundedRect(bar_x, bar_y, 60, 28, 6, 6)
            painter.setPen(QColor(255, 255, 255))
            from PySide6.QtGui import QFont
            painter.setFont(QFont("Arial", 14))
            painter.drawText(bar_x + 6, bar_y + 21, "\u2717")   # ✗
            painter.drawText(bar_x + 36, bar_y + 21, "\u2713")  # ✓
            self._btn_bar = QRect(bar_x, bar_y, 60, 28)

        painter.end()

    @staticmethod
    def _handle_positions(r: QRect):
        """Yield (x, y) for the 8 resize handles."""
        mx, my = r.center().x(), r.center().y()
        return [
            (r.left(), r.top()), (mx, r.top()), (r.right(), r.top()),
            (r.left(), my),                       (r.right(), my),
            (r.left(), r.bottom()), (mx, r.bottom()), (r.right(), r.bottom()),
        ]

    # -- hit testing -------------------------------------------------------

    def _hit_edge(self, pos: QPoint) -> str:
        """Return which edge/corner the point is on, or '' for interior,
        or None if outside."""
        if not self._sel:
            return ""
        r = self._sel.normalized()
        m = _EDGE_MARGIN
        inside = r.adjusted(-m, -m, m, m).contains(pos)
        if not inside:
            return ""
        on_left = abs(pos.x() - r.left()) < m
        on_right = abs(pos.x() - r.right()) < m
        on_top = abs(pos.y() - r.top()) < m
        on_bottom = abs(pos.y() - r.bottom()) < m
        if on_top and on_left:
            return "tl"
        if on_top and on_right:
            return "tr"
        if on_bottom and on_left:
            return "bl"
        if on_bottom and on_right:
            return "br"
        if on_top:
            return "t"
        if on_bottom:
            return "b"
        if on_left:
            return "l"
        if on_right:
            return "r"
        if r.contains(pos):
            return "move"
        return ""

    def _hit_btn(self, pos: QPoint) -> str:
        """Return 'accept', 'reject', or '' based on ✓/✗ button click."""
        if not hasattr(self, "_btn_bar") or not self._sel:
            return ""
        bar = self._btn_bar
        if not bar.contains(pos):
            return ""
        if pos.x() < bar.center().x():
            return "reject"
        return "accept"

    # -- mouse handling ----------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = self._clamp_point(event.pos())

        # Check ✓/✗ buttons first
        btn = self._hit_btn(pos)
        if btn == "accept":
            self._accept_selection()
            return
        if btn == "reject":
            self.reject()
            return

        # If selection exists, check for resize / move
        if self._sel:
            edge = self._hit_edge(pos)
            if edge == "move":
                self._dragging = True
                self._drag_origin = pos
                self._sel_origin = QRect(self._sel)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
            if edge:
                self._resizing = True
                self._drag_edge = edge
                self._drag_origin = pos
                self._sel_origin = QRect(self._sel)
                return

        # Start drawing a new box
        self._sel = QRect(pos, pos)
        self._drag_origin = pos
        self._drawing = True
        self.update()

    def mouseMoveEvent(self, event):
        pos = self._clamp_point(event.pos())

        if self._drawing:
            self._sel = self._between(self._drag_origin, pos)
            self.update()
            return

        if self._dragging:
            delta = pos - self._drag_origin
            self._sel = self._sel_origin.translated(delta)
            self._sel.moveLeft(max(0, min(self.width() - self._sel.width(), self._sel.left())))
            self._sel.moveTop(max(0, min(self.height() - self._sel.height(), self._sel.top())))
            self.update()
            return

        if self._resizing:
            r = QRect(self._sel_origin)
            dx = pos.x() - self._drag_origin.x()
            dy = pos.y() - self._drag_origin.y()
            e = self._drag_edge
            if "l" in e:
                r.setLeft(r.left() + dx)
            if "r" in e:
                r.setRight(r.right() + dx)
            if "t" in e:
                r.setTop(r.top() + dy)
            if "b" in e:
                r.setBottom(r.bottom() + dy)
            self._sel = self._between(r.topLeft(), r.bottomRight()).intersected(self.rect())
            self.update()
            return

        # Update cursor based on hover position
        if self._sel:
            edge = self._hit_edge(pos)
            cursors = {
                "tl": Qt.CursorShape.SizeFDiagCursor,
                "br": Qt.CursorShape.SizeFDiagCursor,
                "tr": Qt.CursorShape.SizeBDiagCursor,
                "bl": Qt.CursorShape.SizeBDiagCursor,
                "t": Qt.CursorShape.SizeVerCursor,
                "b": Qt.CursorShape.SizeVerCursor,
                "l": Qt.CursorShape.SizeHorCursor,
                "r": Qt.CursorShape.SizeHorCursor,
                "move": Qt.CursorShape.OpenHandCursor,
            }
            # Cross inside box, resize on edges, arrow outside
            self.setCursor(cursors.get(edge, Qt.CursorShape.ArrowCursor))
        else:
            # No selection yet — cross cursor everywhere for initial draw
            self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.mouseMoveEvent(event)
        if self._drawing:
            self._drawing = False
            if self._sel:
                self._sel = self._sel.normalized()
            self.update()
        self._dragging = False
        self._resizing = False

    def _clamp_point(self, pos):
        return QPoint(max(0, min(self.width() - 1, pos.x())),
                      max(0, min(self.height() - 1, pos.y())))

    @staticmethod
    def _between(first, second):
        # Construct ordered inclusive endpoints directly. Normalizing a QRect
        # built from reversed endpoints otherwise loses the boundary pixels.
        return QRect(QPoint(min(first.x(), second.x()), min(first.y(), second.y())),
                     QPoint(max(first.x(), second.x()), max(first.y(), second.y())))

    def _accept_selection(self):
        if self._sel:
            rect = self._sel.normalized()
            if rect.width() > 5 and rect.height() > 5:
                inv = 1.0 / self._scale
                src_rect = QRect(
                    int(rect.x() * inv), int(rect.y() * inv),
                    int(rect.width() * inv), int(rect.height() * inv),
                )
                self.result_pixmap = self._screenshot.copy(src_rect)
                self.result_pixmap.setDevicePixelRatio(1.0)
                self.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._accept_selection()
        else:
            super().keyPressEvent(event)
