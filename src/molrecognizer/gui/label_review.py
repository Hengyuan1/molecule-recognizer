"""Explicit atom/ligand confirmation without guessing OCR aliases."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ..core.coordination import reviewed_labels
from ..core.molecule import Molecule
from ..editor.canvas import MoleculeScene
from .recognition_review import ComparisonView
from .window_placement import OwnerDialog


class LabelReviewDialog(OwnerDialog):
    def __init__(self, molecule, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Review atom labels / metal")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self._original = Molecule.from_rdkit(molecule.to_rdkit())
        self.replacement = None
        self._fields = {}
        layout = QVBoxLayout(self)
        text = QLabel("Confirm labels against the source image. Blank replacement keeps the atom unchanged.\n"
                      "Use an exact element symbol (Sc, Ir, Co, Pt, Cr, N…) or NH3. Formal charges are your choice, "
                      "not inferred oxidation states. CO3 needs an explicit drawing and verified donor atom.")
        text.setWordWrap(True)
        layout.addWidget(text)
        body = QHBoxLayout()
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Atom", "Current / OCR label", "Replace with", "Formal charge"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for atom in molecule.to_rdkit().GetAtoms():
            if atom.GetAtomicNum() == 1:
                continue
            row = self._table.rowCount()
            self._table.insertRow(row)
            label = atom.GetProp("molFileAlias") if atom.HasProp("molFileAlias") else atom.GetSymbol()
            for column, value in enumerate((str(atom.GetIdx() + 1), label)):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row, column, item)
            element = QLineEdit()
            element.setPlaceholderText("Unchanged")
            charge = QSpinBox()
            charge.setRange(-8, 8)
            charge.setValue(atom.GetFormalCharge())
            self._table.setCellWidget(row, 2, element)
            self._table.setCellWidget(row, 3, charge)
            self._fields[atom.GetIdx()] = (element, charge)
        body.addWidget(self._table, 3)
        self._scene = MoleculeScene(self)
        self._scene.load_molecule(self._original)
        self._view = ComparisonView(self._scene)
        body.addWidget(self._view, 2)
        layout.addLayout(body, 1)
        self._coordinate = QCheckBox("Convert N/O–metal single bonds to donor → metal coordinate bonds")
        self._coordinate.setToolTip("Optional, user-confirmed convention. Metal–carbon bonds, charges "
                                    "and unknown centers are not changed. Original wedges remain visible.")
        layout.addWidget(self._coordinate)
        self._error = QLabel()
        self._error.setWordWrap(True)
        self._error.setStyleSheet("color: #b45309")
        layout.addWidget(self._error)
        row = QHBoxLayout()
        preview = QPushButton("Preview changes")
        preview.clicked.connect(self._preview)
        row.addWidget(preview)
        row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        apply = QPushButton("Apply reviewed changes")
        apply.clicked.connect(self.accept)
        row.addWidget(apply)
        for button in (preview, cancel, apply):
            button.setAutoDefault(False)
        layout.addLayout(row)
        self.resize(min(1000, round(parent.width() * .95)) if parent else 900,
                    min(650, round(parent.height() * .85)) if parent else 600)

    def _preview(self):
        try:
            replacements = {idx: (element.text(), charge.value())
                            for idx, (element, charge) in self._fields.items()}
            self.replacement = reviewed_labels(self._original, replacements, self._coordinate.isChecked())
            self._scene.load_molecule(self.replacement)
            self._view.fit_content()
            self._error.setText("Preview only. Verify labels, coordinate-bond direction and charges before applying.")
            return True
        except Exception as error:
            self.replacement = None
            self._error.setText(str(error))
            return False

    def accept(self):
        if self._preview():
            super().accept()
