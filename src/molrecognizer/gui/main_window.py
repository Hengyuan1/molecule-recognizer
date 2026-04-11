"""Main application window — StoneMIND-inspired layout.

Layout:
    +---------+---------------------------+------+
    |  Left   |  Toolbar                  | Elem |
    |  Panel  |  Canvas (draw / edit)     | Pal- |
    |  image  |                           | ette |
    |  preview|                           |      |
    |  +btns  |                           |      |
    +---------+---------------------------+------+
    | SMILES: ...               [Copy] [Export]  |
    | Valence: All OK                            |
    +--------------------------------------------+
"""

from __future__ import annotations

import io
import os

from PIL import Image
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core.molecule import Molecule
from ..core.smiles import molecule_to_smiles, smiles_to_molecule
from ..core.valence import check_valence
from .editor_widget import EditorWidget
from .screenshot import ScreenshotDialog, grab_screen, is_wsl, pixmap_to_png_bytes

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Element palette colours (CPK-ish)
ELEMENT_PALETTE = [
    ("H",  "#888888"),
    ("C",  "#333333"),
    ("N",  "#3355DD"),
    ("O",  "#DD2222"),
    ("S",  "#CCAA00"),
    ("P",  "#DD8800"),
    ("F",  "#22BB22"),
    ("Cl", "#22CC22"),
    ("Br", "#992222"),
    ("I",  "#772299"),
    ("B",  "#DD8899"),
]


# ======================================================================
# Recognition worker (background thread)
# ======================================================================

class RecognitionWorker(QThread):
    finished = Signal(object)
    status = Signal(str)

    def __init__(self, image: Image.Image, parent=None):
        super().__init__(parent)
        self._image = image

    def run(self):
        try:
            from ..core.recognizer import MoleculeRecognizer, _model_cache
            if "cpu" not in _model_cache:
                self.status.emit("Loading model into memory (~6 s, once per session)…")
            else:
                self.status.emit("Recognizing structure…")
            recognizer = MoleculeRecognizer(device="cpu")
            self.status.emit("Recognizing structure…")
            mol = recognizer.recognize(self._image)
            self.finished.emit(mol)
        except Exception as e:
            self.finished.emit(e)


# ======================================================================
# Element palette (right sidebar)
# ======================================================================

class ElementPalette(QWidget):
    """Vertical strip of coloured element buttons."""

    element_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(56)
        self.setObjectName("element_palette")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(6)

        self._buttons: dict[str, QPushButton] = {}
        for symbol, colour in ELEMENT_PALETTE:
            btn = QPushButton(symbol)
            btn.setObjectName("element_btn")
            btn.setFixedSize(40, 40)
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"QPushButton#element_btn {{"
                f"  background-color: {colour};"
                f"  color: white;"
                f"  border-radius: 20px;"
                f"  font-size: 13px;"
                f"  font-weight: 700;"
                f"  border: 2px solid transparent;"
                f"}}"
                f"QPushButton#element_btn:hover {{"
                f"  border-color: #4A90D9;"
                f"}}"
                f"QPushButton#element_btn:checked {{"
                f"  border-color: #ffffff;"
                f"  outline: 2px solid #4A90D9;"
                f"}}"
            )
            btn.clicked.connect(lambda checked, s=symbol: self._on_click(s))
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)
            self._buttons[symbol] = btn

        layout.addStretch()

        # Default selection
        self._buttons["C"].setChecked(True)

    def _on_click(self, symbol: str):
        for s, btn in self._buttons.items():
            btn.setChecked(s == symbol)
        self.element_selected.emit(symbol)


# ======================================================================
# Left panel (image preview + action buttons)
# ======================================================================

class LeftPanel(QWidget):
    open_image = Signal()
    screenshot = Signal()
    load_smiles = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("left_panel")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Title
        title = QLabel("Source Image")
        title.setObjectName("panel_title")
        layout.addWidget(title)

        # Image preview
        self._preview = QLabel()
        self._preview.setObjectName("image_preview")
        self._preview.setFixedHeight(180)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setText("No image")
        self._preview.setStyleSheet(
            "QLabel#image_preview {"
            "  background: #ffffff;"
            "  border: 1px solid #dde1e6;"
            "  border-radius: 8px;"
            "  color: #8899aa;"
            "  font-size: 12px;"
            "}"
        )
        layout.addWidget(self._preview)

        # Action buttons
        btn_open = QPushButton("Open Image")
        btn_open.setObjectName("action_btn")
        btn_open.clicked.connect(self.open_image.emit)
        layout.addWidget(btn_open)

        btn_screen = QPushButton("Screenshot")
        btn_screen.setObjectName("action_btn")
        btn_screen.clicked.connect(self.screenshot.emit)
        layout.addWidget(btn_screen)

        btn_smiles = QPushButton("Load SMILES")
        btn_smiles.setObjectName("action_btn_secondary")
        btn_smiles.clicked.connect(self.load_smiles.emit)
        layout.addWidget(btn_smiles)

        layout.addStretch()

    def set_preview(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            self._preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)

    def clear_preview(self):
        self._preview.clear()
        self._preview.setText("No image")


# ======================================================================
# Bottom bar (SMILES + actions + valence)
# ======================================================================

class BottomBar(QWidget):
    copy_smiles = Signal()
    export_smiles = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottom_bar")
        self.setFixedHeight(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(4)

        # Row 1: SMILES
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        smiles_label = QLabel("SMILES")
        smiles_label.setObjectName("smiles_label")
        smiles_label.setFixedWidth(54)
        row1.addWidget(smiles_label)

        self._smiles_field = QLineEdit()
        self._smiles_field.setReadOnly(True)
        self._smiles_field.setPlaceholderText("Draw or recognise a structure…")
        self._smiles_field.setObjectName("smiles_field")
        row1.addWidget(self._smiles_field)

        btn_copy = QPushButton("Copy")
        btn_copy.setObjectName("small_btn")
        btn_copy.setFixedWidth(60)
        btn_copy.clicked.connect(self.copy_smiles.emit)
        row1.addWidget(btn_copy)

        btn_export = QPushButton("Export")
        btn_export.setObjectName("small_btn_green")
        btn_export.setFixedWidth(60)
        btn_export.clicked.connect(self.export_smiles.emit)
        row1.addWidget(btn_export)

        layout.addLayout(row1)

        # Row 2: Valence status
        self._valence_label = QLabel("Valence: —")
        self._valence_label.setObjectName("valence_label")
        layout.addWidget(self._valence_label)

    @property
    def smiles_text(self) -> str:
        return self._smiles_field.text()

    def set_smiles(self, smiles: str):
        self._smiles_field.setText(smiles)

    def set_valence_ok(self):
        self._valence_label.setText("✓  All valences OK")
        self._valence_label.setStyleSheet("color: #27ae60; font-weight: 600;")

    def set_valence_warnings(self, warnings: list):
        n = len(warnings)
        details = "; ".join(str(w) for w in warnings[:3])
        suffix = f" … (+{n - 3} more)" if n > 3 else ""
        self._valence_label.setText(f"⚠  {details}{suffix}")
        self._valence_label.setStyleSheet("color: #e74c3c; font-weight: 500;")

    def clear(self):
        self._smiles_field.clear()
        self._valence_label.setText("Valence: —")
        self._valence_label.setStyleSheet("")


# ======================================================================
# Main window
# ======================================================================

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Molecule Recognizer")
        self.resize(1200, 800)

        self._molecule: Molecule | None = None
        self._worker: RecognitionWorker | None = None
        self._source_pixmap: QPixmap | None = None

        self._setup_menu()
        self._setup_ui()
        self._setup_statusbar()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        open_act = QAction("&Open Image…", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._on_open_image)
        file_menu.addAction(open_act)

        screenshot_act = QAction("&Screenshot", self)
        screenshot_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        screenshot_act.triggered.connect(self._on_screenshot)
        file_menu.addAction(screenshot_act)

        file_menu.addSeparator()

        load_smiles_act = QAction("Load from S&MILES…", self)
        load_smiles_act.triggered.connect(self._on_load_smiles)
        file_menu.addAction(load_smiles_act)

        export_act = QAction("&Export SMILES…", self)
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

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- Top area: left panel | canvas | element palette ----
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Left panel
        self._left_panel = LeftPanel()
        self._left_panel.open_image.connect(self._on_open_image)
        self._left_panel.screenshot.connect(self._on_screenshot)
        self._left_panel.load_smiles.connect(self._on_load_smiles)
        body.addWidget(self._left_panel)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #dde1e6;")
        body.addWidget(sep1)

        # Editor (toolbar + canvas)
        self._editor = EditorWidget()
        self._editor.molecule_changed.connect(self._on_editor_changed)
        body.addWidget(self._editor, 1)  # stretch=1 → takes remaining space

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #dde1e6;")
        body.addWidget(sep2)

        # Element palette
        self._palette = ElementPalette()
        self._palette.element_selected.connect(self._on_palette_element)
        body.addWidget(self._palette)

        outer.addLayout(body, 1)

        # Horizontal rule
        hr = QFrame()
        hr.setFrameShape(QFrame.Shape.HLine)
        hr.setStyleSheet("color: #dde1e6;")
        outer.addWidget(hr)

        # ---- Bottom bar ----
        self._bottom_bar = BottomBar()
        self._bottom_bar.copy_smiles.connect(self._copy_smiles)
        self._bottom_bar.export_smiles.connect(self._on_export_smiles)
        outer.addWidget(self._bottom_bar)

        # Wire undo/redo from menu to editor
        self._undo_act.triggered.connect(self._editor._undo)
        self._redo_act.triggered.connect(self._editor._redo)

    def _setup_statusbar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------
    # Element palette → editor
    # ------------------------------------------------------------------

    def _on_palette_element(self, element: str):
        self._editor.set_element(element)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Molecule Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)",
        )
        if path:
            self._source_pixmap = QPixmap(path)
            self._left_panel.set_preview(self._source_pixmap)
            img = Image.open(path)
            self._recognize_image(img)

    def _on_screenshot(self):
        self.statusBar().showMessage("Capturing screen…")
        self.hide()
        QApplication.processEvents()
        QTimer.singleShot(300, self._do_screenshot)

    def _do_screenshot(self):
        screenshot = grab_screen()
        self.show()
        self.raise_()
        self.activateWindow()

        if screenshot is None or screenshot.isNull():
            self.statusBar().showMessage("Screenshot failed", 5000)
            return

        dlg = ScreenshotDialog(screenshot, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_pixmap:
            self._source_pixmap = dlg.result_pixmap
            self._left_panel.set_preview(self._source_pixmap)
            try:
                png_data = pixmap_to_png_bytes(dlg.result_pixmap)
                img = Image.open(io.BytesIO(png_data))
                img.load()
                self._recognize_image(img)
            except Exception as e:
                self.statusBar().showMessage(f"Screenshot error: {e}", 5000)
        else:
            self.statusBar().showMessage("Screenshot cancelled", 3000)

    def _on_load_smiles(self):
        smiles, ok = QInputDialog.getText(
            self, "Load SMILES", "Enter SMILES string:"
        )
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
        smiles = self._bottom_bar.smiles_text
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SMILES", "molecule.smi",
            "SMILES Files (*.smi);;Text Files (*.txt);;All Files (*)",
        )
        if path:
            with open(path, "w") as f:
                f.write(smiles + "\n")
            self.statusBar().showMessage(f"Exported to {path}", 3000)

    def _copy_smiles(self):
        text = self._bottom_bar.smiles_text
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("SMILES copied to clipboard", 3000)

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------

    def _recognize_image(self, img: Image.Image):
        if self._worker is not None and self._worker.isRunning():
            self.statusBar().showMessage("Recognition already in progress…")
            return
        self.statusBar().showMessage("Starting recognition…")
        self._worker = RecognitionWorker(img, parent=self)
        self._worker.status.connect(
            lambda msg: self.statusBar().showMessage(msg)
        )
        self._worker.finished.connect(self._on_recognition_done)
        self._worker.start()

    def _on_recognition_done(self, result):
        if isinstance(result, Exception):
            self.statusBar().showMessage("Recognition failed", 5000)
            QMessageBox.critical(
                self, "Recognition Error",
                f"Failed to recognize structure:\n{result}",
            )
            return
        self._set_molecule(result)
        self.statusBar().showMessage("Structure recognized", 3000)

    # ------------------------------------------------------------------
    # Molecule state
    # ------------------------------------------------------------------

    def _set_molecule(self, mol: Molecule):
        self._molecule = mol
        self._editor.load_molecule(mol)
        self._update_info()
        self._undo_act.setEnabled(True)
        self._redo_act.setEnabled(True)

    def _on_editor_changed(self):
        self._molecule = self._editor.molecule
        self._update_info()

    def _update_info(self):
        if self._molecule is None:
            self._bottom_bar.clear()
            return
        # SMILES
        try:
            smiles = molecule_to_smiles(self._molecule)
            self._bottom_bar.set_smiles(smiles)
        except Exception:
            self._bottom_bar.set_smiles("[Error generating SMILES]")
        # Valence
        warnings = check_valence(self._molecule)
        if warnings:
            self._bottom_bar.set_valence_warnings(warnings)
        else:
            self._bottom_bar.set_valence_ok()

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            self._worker.finished.disconnect()
            self._worker.quit()
            self._worker.wait(5000)
        event.accept()
