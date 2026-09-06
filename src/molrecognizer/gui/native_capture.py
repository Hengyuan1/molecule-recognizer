"""Asynchronous Windows selection overlay, usable from WSL and native Windows."""

import base64
from pathlib import Path
import shutil
import sys

from PySide6.QtCore import QCoreApplication, QObject, QProcess, QTimer, Signal

from .screenshot import _find_powershell, is_wsl


# Read C# from stdin, not a command-line argument or a screenshot temp file.
_LOADER = """
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    Add-Type -TypeDefinition ([Console]::In.ReadToEnd()) -ReferencedAssemblies System.Windows.Forms,System.Drawing
    [Console]::WriteLine([MolRecognizerCapture]::Run())
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
"""


def native_capture_executable():
    if is_wsl():
        return _find_powershell()
    if sys.platform == "win32":
        return shutil.which("powershell.exe")
    return None


class NativeRegionCapture(QObject):
    completed = Signal(bytes, str)  # PNG bytes, error; empty/empty means cancelled
    ready = Signal()
    stopped = Signal()  # Always emitted when the helper exits, including abort.

    def __init__(self, executable, parent=None):
        super().__init__(parent)
        self._executable = executable
        self._output = bytearray()
        self._error = ""
        self._done = False
        self._process = QProcess(self)
        self._process.started.connect(self._send_source)
        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self._finished)
        self._process.finished.connect(lambda *_: self.stopped.emit())
        self._process.errorOccurred.connect(self._process_error)
        self._startup = QTimer(self)
        self._startup.setSingleShot(True)
        self._startup.timeout.connect(self._startup_timeout)
        QCoreApplication.instance().aboutToQuit.connect(self.abort)

    def start(self):
        self._startup.start(30000)
        command = base64.b64encode(_LOADER.encode("utf-16-le")).decode("ascii")
        self._process.start(self._executable,
                            ["-NoLogo", "-NoProfile", "-NonInteractive", "-STA",
                             "-EncodedCommand", command])

    def _send_source(self):
        if self._done:
            self._process.kill()
            return
        try:
            source = Path(__file__).with_name("capture_overlay.cs").read_bytes()
        except OSError as error:
            self._error = str(error)
            self._process.kill()
            return
        self._process.write(source)
        self._process.closeWriteChannel()

    def _read_output(self):
        self._output.extend(bytes(self._process.readAllStandardOutput()))
        if self._output.startswith(b"READY\r\n") or self._output.startswith(b"READY\n"):
            _, _, remaining = self._output.partition(b"\n")
            self._output = bytearray(remaining)
            self._startup.stop()  # No time limit while the user adjusts a crop.
            self.ready.emit()
        if len(self._output) > 64 * 1024 * 1024:
            self._error = "Selected image is too large. Please capture a smaller area."
            self._process.kill()

    def _process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._complete(b"", "Could not start the Windows capture overlay: "
                           + self._process.errorString())
            self.stopped.emit()

    def _startup_timeout(self):
        self._error = "Windows capture overlay did not start within 30 seconds."
        self._process.kill()

    def _finished(self, exit_code, exit_status):
        self._read_output()
        output = bytes(self._output).strip()
        error = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace").strip()
        if self._error or exit_code != 0 or exit_status != QProcess.ExitStatus.NormalExit:
            self._complete(b"", self._error or error or "Windows capture overlay exited unexpectedly.")
        elif output == b"CANCEL":
            self._complete(b"", "")
        elif output.startswith(b"PNG:"):
            try:
                png = base64.b64decode(output[4:], validate=True)
                if not png.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("Not a PNG image")
                self._complete(png, "")
            except ValueError:
                self._complete(b"", "The capture overlay returned an invalid image.")
        else:
            self._complete(b"", error or "The capture overlay returned no result.")

    def _complete(self, png, error):
        if self._done:
            return
        self._done = True
        self._startup.stop()
        self._output.clear()
        self.completed.emit(png, error)

    def abort(self):
        self._done = True
        self._startup.stop()
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

    def isRunning(self):
        return self._process.state() != QProcess.ProcessState.NotRunning
