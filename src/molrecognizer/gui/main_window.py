"""Main application window."""

from __future__ import annotations

import io

from PIL import Image
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from ..core.molecule import Molecule
from ..core.smiles import molecule_to_smiles, smiles_to_molecule
from ..core.valence import check_valence
from .editor_widget import EditorWidget
from .screenshot import ScreenshotOverlay


class RecognitionWorker(QThread):
    """Run MolScribe recognition in a background thread."""
    finished = Signal(object)  # Molecule or Exception
    status = Signal(str)

    def __init__(self, image: Image.Image, parent=None):
        super().__init__(parent)
        self._image = image

    def run(self):
        try:
            self.status.emit("Loading MolScribe model...")
            from ..core.recognizer import MoleculeRecognizer
            recognizer = MoleculeRecognizer(device="cpu")
            self.status.emit("Recognizing structure...")
            mol = recognizer.recognize(self._image)
            self.finished.emit(mol)
        except Exception as e:
            self.finished.emit(e)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Molecule Recognizer")
        self.resize(1200, 800)

        self._molecule: Molecule | None = None
        self._screenshot_overlay = ScreenshotOverlay()
        self._screenshot_overlay.captured.connect(self._on_screenshot_captured)
        self._screenshot_overlay.cancelled.connect(self._on_screenshot_cancelled)
        self._worker: RecognitionWorker | None = None

        self._setup_menu()
        self._setup_central()
        self._setup_info_panel()
        self._setup_statusbar()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        open_act = QAction("&Open Image...", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._on_open_image)
        file_menu.addAction(open_act)

        screenshot_act = QAction("&Screenshot", self)
        screenshot_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        screenshot_act.triggered.connect(self._on_screenshot)
        file_menu.addAction(screenshot_act)

        file_menu.addSeparator()

        load_smiles_act = QAction("Load from S&MILES...", self)
        load_smiles_act.triggered.connect(self._on_load_smiles)
        file_menu.addAction(load_smiles_act)

        export_act = QAction("&Export SMILES...", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.triggered.connect(self._on_export_smiles)
        file_menu.addAction(export_act)

        file_menu.addSeparator()

        quit_act = QAction("&Quit", self)
        quit_act.setShortcut(QKeySequence.StandardKey.Quit)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        edit_menu = menu.addMenu("&Edit")
        self._undo_act = QAction("&Undo", self)
        self._undo_act.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_act.setEnabled(False)
        edit_menu.addAction(self._undo_act)

        self._redo_act = QAction("&Redo", self)
        self._redo_act.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_act.setEnabled(False)
        edit_menu.addAction(self._redo_act)

    def _setup_central(self):
        self._editor = EditorWidget()
        self._editor.molecule_changed.connect(self._on_editor_changed)
        self.setCentralWidget(self._editor)

        # Wire menu undo/redo to editor
        self._undo_act.triggered.connect(self._editor._undo)
        self._redo_act.triggered.connect(self._editor._redo)

    def _setup_info_panel(self):
        dock = QDockWidget("Info", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        dock.setMinimumWidth(260)

        panel = QWidget()
        panel.setStyleSheet("QWidget { background-color: #f5f6fa; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # SMILES display
        smiles_label = QLabel("SMILES")
        layout.addWidget(smiles_label)

        self._smiles_edit = QPlainTextEdit()
        self._smiles_edit.setReadOnly(True)
        self._smiles_edit.setMaximumHeight(72)
        self._smiles_edit.setPlaceholderText("No molecule loaded")
        layout.addWidget(self._smiles_edit)

        copy_btn = QPushButton("Copy SMILES")
        copy_btn.clicked.connect(self._copy_smiles)
        layout.addWidget(copy_btn)

        layout.addSpacing(8)

        # Valence warnings
        warn_label = QLabel("Valence Warnings")
        layout.addWidget(warn_label)

        self._warnings_list = QListWidget()
        self._warnings_list.setMinimumHeight(120)
        layout.addWidget(self._warnings_list)

        layout.addStretch()
        dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _setup_statusbar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Molecule Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"
        )
        if path:
            img = Image.open(path)
            self._recognize_image(img)

    def _on_screenshot(self):
        self.statusBar().showMessage("Select a screen region...")
        # Hide the window so it doesn't appear in the screenshot
        self.hide()
        # Small delay to let the window fully disappear before grabbing
        QTimer.singleShot(300, self._screenshot_overlay.start)

    def _on_screenshot_captured(self, pixmap: QPixmap):
        # Show the window again
        self.show()
        self.activateWindow()
        # Convert QPixmap → PIL Image
        buffer = io.BytesIO()
        pixmap.save(buffer, "PNG")
        buffer.seek(0)
        img = Image.open(buffer)
        self._recognize_image(img)

    def _on_screenshot_cancelled(self):
        self.show()
        self.activateWindow()
        self.statusBar().showMessage("Screenshot cancelled", 3000)

    def _on_load_smiles(self):
        from PySide6.QtWidgets import QInputDialog
        smiles, ok = QInputDialog.getText(self, "Load SMILES", "Enter SMILES string:")
        if ok and smiles.strip():
            try:
                mol = smiles_to_molecule(smiles.strip())
                self._set_molecule(mol)
                self.statusBar().showMessage("Loaded from SMILES", 3000)
            except ValueError as e:
                QMessageBox.warning(self, "Invalid SMILES", str(e))

    def _on_export_smiles(self):
        if self._molecule is None:
            self.statusBar().showMessage("No molecule to export", 3000)
            return
        smiles = self._smiles_edit.toPlainText()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SMILES", "molecule.smi",
            "SMILES Files (*.smi);;Text Files (*.txt);;All Files (*)"
        )
        if path:
            with open(path, "w") as f:
                f.write(smiles + "\n")
            self.statusBar().showMessage(f"Exported to {path}", 3000)

    def _copy_smiles(self):
        text = self._smiles_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("SMILES copied to clipboard", 3000)

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------

    def _recognize_image(self, img: Image.Image):
        self.statusBar().showMessage("Starting recognition...")
        self._worker = RecognitionWorker(img, parent=self)
        self._worker.status.connect(lambda msg: self.statusBar().showMessage(msg))
        self._worker.finished.connect(self._on_recognition_done)
        self._worker.start()

    def _on_recognition_done(self, result):
        self._worker = None
        if isinstance(result, Exception):
            self.statusBar().showMessage("Recognition failed", 5000)
            QMessageBox.critical(
                self, "Recognition Error",
                f"Failed to recognize structure:\n{result}"
            )
            return
        self._set_molecule(result)
        self.statusBar().showMessage("Structure recognized", 3000)

    # ------------------------------------------------------------------
    # Molecule state
    # ------------------------------------------------------------------

    def _set_molecule(self, mol: Molecule):
        """Set the current molecule and update all displays."""
        self._molecule = mol
        self._editor.load_molecule(mol)
        self._update_smiles()
        self._update_valence()
        self._undo_act.setEnabled(True)
        self._redo_act.setEnabled(True)

    def _on_editor_changed(self):
        """Called when the editor modifies the molecule."""
        self._molecule = self._editor.molecule
        self._update_smiles()
        self._update_valence()

    def _update_smiles(self):
        if self._molecule is None:
            self._smiles_edit.setPlainText("")
            return
        try:
            smiles = molecule_to_smiles(self._molecule)
            self._smiles_edit.setPlainText(smiles)
        except Exception:
            self._smiles_edit.setPlainText("[Error generating SMILES]")

    def _update_valence(self):
        self._warnings_list.clear()
        if self._molecule is None:
            return
        warnings = check_valence(self._molecule)
        for w in warnings:
            item = QListWidgetItem(str(w))
            item.setForeground(Qt.GlobalColor.red)
            self._warnings_list.addItem(item)
        if not warnings:
            item = QListWidgetItem("All valences OK")
            item.setForeground(Qt.GlobalColor.darkGreen)
            self._warnings_list.addItem(item)
