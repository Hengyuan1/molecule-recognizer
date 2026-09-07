"""Side-by-side, read-only review of explicit OSRA retry results."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSplitter, QVBoxLayout, QWidget,
)
from rdkit import Chem

from ..core.molecule import Molecule
from ..core.recognition_retry import RecognitionCandidate, RETRY_PROFILES
from ..core.smiles import molecule_to_smiles
from ..core.valence import check_valence
from ..editor.canvas import MoleculeScene
from .window_placement import OwnerDialog, owner_screen


class ComparisonView(QGraphicsView):
    """Pan/zoom a source image or drawing, without editing either."""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing
                            | QPainter.RenderHint.SmoothPixmapTransform)
        self.setInteractive(False)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMinimumSize(160, 140)

    def fit_content(self):
        bounds = self.scene().itemsBoundingRect()
        if not bounds.isEmpty():
            self.setSceneRect(bounds.adjusted(-30, -30, 30, 30))
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_content()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        if 0.01 < self.transform().m11() * factor < 100:
            self.scale(factor, factor)
        event.accept()


class RecognitionReviewDialog(OwnerDialog):
    stop_requested = Signal()

    def __init__(self, source: QPixmap, current: Molecule | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare recognition results")
        self.setObjectName("recognition_review")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self._candidates: list[RecognitionCandidate] = []
        self._current_row = -1
        self._failure = ""

        layout = QVBoxLayout(self)
        instructions = QLabel(
            "Select a result to compare with the source. Only Use selected replaces your structure.\n"
            "Check ring connections, atom labels and stereochemistry: no result is guaranteed correct.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        source_scene = QGraphicsScene(self)
        original = QPixmap(source)
        original.setDevicePixelRatio(1.0)
        source_scene.addPixmap(original)
        self._source_view = ComparisonView(source_scene)
        self._molecule_scene = MoleculeScene(self)
        self._result_view = ComparisonView(self._molecule_scene)
        self._result_title = QLabel("Current structure")
        for title, view in (
            (QLabel(f"Source image — {source.width()} × {source.height()} pixels"), self._source_view),
            (self._result_title, self._result_view),
        ):
            panel = QWidget()
            column = QVBoxLayout(panel)
            column.setContentsMargins(0, 0, 0, 0)
            column.addWidget(title)
            column.addWidget(view, 1)
            splitter.addWidget(panel)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter, 1)

        self._summary = QLabel("Select an alternative when it becomes available.")
        self._summary.setTextFormat(Qt.TextFormat.PlainText)
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)
        self._smiles = QLineEdit()
        self._smiles.setReadOnly(True)
        self._smiles.setPlaceholderText("SMILES of the selected result")
        self._smiles.setObjectName("smiles_field")
        layout.addWidget(self._smiles)

        self._choices = QListWidget()
        self._choices.setObjectName("recognition_candidates")
        self._choices.setMaximumHeight(self.fontMetrics().height() * 7 + 20)
        self._choices.currentRowChanged.connect(self._select)
        layout.addWidget(self._choices)
        self._status = QLabel("Starting local OSRA retries (up to 75 seconds total)…")
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        buttons = QHBoxLayout()
        fit = QPushButton("Fit previews")
        fit.setToolTip("Scroll to zoom; drag to pan either preview independently")
        fit.clicked.connect(self._fit_previews)
        buttons.addWidget(fit)
        self._stop = QPushButton("Stop retries")
        self._stop.clicked.connect(self._request_stop)
        buttons.addWidget(self._stop)
        buttons.addStretch()
        cancel = QPushButton("Keep current")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        self._use = QPushButton("Use selected")
        self._use.setObjectName("action_btn")
        self._use.setEnabled(False)
        self._use.clicked.connect(self.accept)
        buttons.addWidget(self._use)
        # Enter must not accidentally replace a manually corrected molecule.
        for button in (fit, self._stop, cancel, self._use):
            button.setAutoDefault(False)
        layout.addLayout(buttons)

        if current is not None and current.num_atoms:
            snapshot = Molecule.from_rdkit(current.to_rdkit())
            self._current_row = 0
            self._append(RecognitionCandidate("Current structure (unchanged)", snapshot))
            self._choices.setCurrentRow(0)
        owner = self.parentWidget()
        available = (owner_screen(owner) if owner is not None else self.screen()).availableGeometry()
        width, height = round(available.width() * .85), round(available.height() * .85)
        if owner is not None:
            # WSLg can report the combined desktop as one screen. The main
            # window already has the correct per-monitor size; stay inside it.
            width = min(width, round(owner.width() * .95))
            height = min(height, round(owner.height() * .95))
        self.resize(width, height)
        QTimer.singleShot(0, self._fit_previews)

    @property
    def selected_candidate(self):
        row = self._choices.currentRow()
        if row < 0 or row == self._current_row:
            return None
        candidate = self._candidates[row]
        return candidate if candidate.molecule is not None and not candidate.error else None

    def _append(self, candidate):
        self._candidates.append(candidate)
        item = QListWidgetItem(candidate.name + (" — no usable result" if candidate.error else ""))
        description = next((p.description for p in RETRY_PROFILES if p.name == candidate.name), "")
        item.setToolTip(candidate.error or description)
        self._choices.addItem(item)

    def add_candidate(self, candidate):
        previous = self._choices.currentRow()
        self._append(candidate)
        # Arrival/order/confidence never changes the user's current selection.
        if previous < 0:
            self._choices.setCurrentRow(-1)

    def set_status(self, message):
        self._status.setText(message)

    def set_failure(self, message):
        self._failure = message
        self.set_status(f"Retry failed: {message}")

    def finish(self, cancelled=False):
        self._stop.setEnabled(False)
        if self._failure:
            return
        state = "Retries stopped." if cancelled else "Retries finished."
        usable = any(index != self._current_row and candidate.molecule is not None
                     and not candidate.error for index, candidate in enumerate(self._candidates))
        self.set_status(state + (" Review the available results or keep your current structure."
                                 if usable else " No usable alternatives; try a clearer source image."))

    def _request_stop(self):
        self._stop.setEnabled(False)
        self.set_status("Stopping retries; available results are kept for review…")
        self.stop_requested.emit()

    def _fit_previews(self):
        self._source_view.fit_content()
        self._result_view.fit_content()

    def _select(self, row):
        self._use.setEnabled(False)
        self._smiles.clear()
        self._molecule_scene.load_molecule(Molecule())
        if row < 0:
            return
        candidate = self._candidates[row]
        self._result_title.setText(candidate.name)
        if candidate.error or candidate.molecule is None:
            self._summary.setText(candidate.error or "No structure available")
            return
        try:
            mol = candidate.molecule
            self._molecule_scene.load_molecule(mol)
            self._result_view.fit_content()
            rd = mol.to_rdkit()
            sizes = sorted(len(ring) for ring in Chem.GetSymmSSSR(rd))
            unknown = sum(a.GetAtomicNum() == 0 for a in rd.GetAtoms())
            warnings = check_valence(mol)
            text = (f"Atoms: {mol.num_atoms} · Bonds: {mol.num_bonds} · Rings: {len(sizes)} "
                    f"(sizes: {', '.join(map(str, sizes)) or 'none'}) · "
                    f"Unknown atoms: {unknown} · Valence warnings: {len(warnings)}")
            if candidate.confidence is not None:
                text += f"\nOSRA score: {candidate.confidence:.3f} — not an accuracy percentage."
            self._summary.setText(text)
            self._summary.setToolTip("\n".join(map(str, warnings)))
            self._smiles.setText(molecule_to_smiles(mol))
            self._use.setEnabled(row != self._current_row)
        except Exception as error:
            self._summary.setText(f"Cannot preview this result: {error}")

    def accept(self):
        if self.selected_candidate is not None and self._use.isEnabled():
            super().accept()
