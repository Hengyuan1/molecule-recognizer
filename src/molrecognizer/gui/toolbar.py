"""Toolbar with editing tool buttons, laid out in two rows to prevent overflow."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.molecule import BondType

ELEMENTS = ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "H", "B", "Si", "Se"]

BOND_TYPES = [
    ("Single", BondType.SINGLE),
    ("Double", BondType.DOUBLE),
    ("Triple", BondType.TRIPLE),
    ("Aromatic", BondType.AROMATIC),
]


class EditorToolbar(QWidget):
    """Two-row toolbar for molecule editing tools.

    Row 1: Tool buttons (Select, Bond, Atom, Eraser)
    Row 2: Bond type, Element selector, Undo/Redo
    """

    tool_changed = Signal(str)           # "select", "bond", "atom", "eraser"
    element_changed = Signal(str)        # element symbol
    bond_type_changed = Signal(object)   # BondType
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget#toolbar_container {
                background-color: #ecf0f1;
                border-bottom: 2px solid #bdc3c7;
            }
        """)
        self.setObjectName("toolbar_container")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(6)

        # ---- Row 1: Tool buttons ----
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._select_btn = self._make_tool_button("Select", "select", row1, checked=True)
        self._bond_btn = self._make_tool_button("Bond", "bond", row1)
        self._atom_btn = self._make_tool_button("Atom", "atom", row1)
        self._erase_btn = self._make_tool_button("Eraser", "eraser", row1)

        row1.addStretch()
        outer.addLayout(row1)

        # ---- Row 2: Selectors + Undo/Redo ----
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        # Bond type
        bond_label = QLabel("Bond:")
        bond_label.setStyleSheet("font-weight: 600; font-size: 12px;")
        row2.addWidget(bond_label)
        self._bond_combo = QComboBox()
        for label, bt in BOND_TYPES:
            self._bond_combo.addItem(label, bt)
        self._bond_combo.currentIndexChanged.connect(self._on_bond_type_changed)
        row2.addWidget(self._bond_combo)

        row2.addSpacing(12)

        # Element
        elem_label = QLabel("Element:")
        elem_label.setStyleSheet("font-weight: 600; font-size: 12px;")
        row2.addWidget(elem_label)
        self._element_combo = QComboBox()
        for e in ELEMENTS:
            self._element_combo.addItem(e)
        self._element_combo.currentTextChanged.connect(self._on_element_changed)
        row2.addWidget(self._element_combo)

        row2.addStretch()

        # Undo / Redo
        self._undo_btn = QToolButton()
        self._undo_btn.setText("Undo")
        self._undo_btn.setToolTip("Undo (Ctrl+Z)")
        self._undo_btn.clicked.connect(self.undo_requested.emit)
        row2.addWidget(self._undo_btn)

        self._redo_btn = QToolButton()
        self._redo_btn.setText("Redo")
        self._redo_btn.setToolTip("Redo (Ctrl+Shift+Z)")
        self._redo_btn.clicked.connect(self.redo_requested.emit)
        row2.addWidget(self._redo_btn)

        outer.addLayout(row2)

    def _make_tool_button(self, label: str, tool_name: str,
                          layout: QHBoxLayout, checked: bool = False) -> QToolButton:
        btn = QToolButton()
        btn.setText(f"  {label}  ")
        btn.setToolTip(label)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        btn.clicked.connect(lambda: self.tool_changed.emit(tool_name))
        self._button_group.addButton(btn)
        layout.addWidget(btn)
        return btn

    def _on_bond_type_changed(self, index: int):
        bt = self._bond_combo.itemData(index)
        self.bond_type_changed.emit(bt)

    def _on_element_changed(self, element: str):
        self.element_changed.emit(element)

    @property
    def current_bond_type(self) -> BondType:
        return self._bond_combo.currentData()

    @property
    def current_element(self) -> str:
        return self._element_combo.currentText()
