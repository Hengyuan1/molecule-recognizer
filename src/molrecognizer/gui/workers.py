"""Cancellable background jobs; no blocking waits in GUI callbacks."""

import sys
from threading import Event

from PySide6.QtCore import QObject, QProcess, QThread, Signal
from rdkit import Chem


class RecognitionWorker(QThread):
    result_ready = Signal(object)
    status = Signal(str)

    def __init__(self, image, parent=None):
        super().__init__(parent)
        self._image = image
        self._cancelled = Event()

    def cancel(self):
        self._cancelled.set()

    def run(self):
        if self._cancelled.is_set():
            return
        try:
            from ..core.recognizer import MoleculeRecognizer
            self.status.emit("Recognizing structure with OSRA…")
            recognizer = MoleculeRecognizer(cancel_event=self._cancelled)
            result = recognizer.recognize(self._image)
        except Exception as error:
            result = error
        if not self._cancelled.is_set():
            self.result_ready.emit(result)


# 3D embedding/optimization is a native computation with no cooperative cancel
# API. Isolate it in a process that can safely be killed, never QThread.terminate().
_RENDER_3D = """
import sys
from molrecognizer.core.xyz import generate_3d
mol = generate_3d(sys.stdin.read())
sys.stdout.buffer.write(mol.ToBinary())
"""


class Render3DWorker(QObject):
    result_ready = Signal(object)
    finished = Signal()

    def __init__(self, smiles, parent=None):
        super().__init__(parent)
        self._smiles = smiles
        self._cancelled = False
        self._done = False
        self._process = QProcess(self)
        self._process.started.connect(self._send_input)
        self._process.finished.connect(self._finished)
        self._process.errorOccurred.connect(self._error)

    def start(self):
        self._process.start(sys.executable, ['-c', _RENDER_3D])

    def isRunning(self):
        return self._process.state() != QProcess.ProcessState.NotRunning

    def cancel(self):
        self._cancelled = True
        if self.isRunning():
            self._process.kill()

    def _send_input(self):
        if self._cancelled:
            self._process.kill()
            return
        self._process.write(self._smiles.encode('utf-8'))
        self._process.closeWriteChannel()

    def _error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._complete(RuntimeError(self._process.errorString()))

    def _finished(self, exit_code, exit_status):
        result = None
        if not self._cancelled:
            try:
                if exit_code != 0 or exit_status != QProcess.ExitStatus.NormalExit:
                    detail = bytes(self._process.readAllStandardError()).decode('utf-8', errors='replace')
                    raise RuntimeError(detail.strip() or '3D generation failed')
                result = Chem.Mol(bytes(self._process.readAllStandardOutput()))
                if result is None or result.GetNumConformers() == 0:
                    raise ValueError('3D generation returned no coordinates')
            except Exception as error:
                result = error
        self._complete(result)

    def _complete(self, result):
        if self._done:
            return
        self._done = True
        if not self._cancelled:
            self.result_ready.emit(result)
        self.finished.emit()
