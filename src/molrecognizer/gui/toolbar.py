"""Toolbar with editing tool buttons."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QToolBar,
    QToolButton,
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

# Unicode symbols for tool buttons
TOOL_LABELS = {
    "select":  ("\u25ed", "Select"),      # ◭ pointer-like
    "bond":    ("\u2500", "Bond"),         # ─ line
    "atom":    ("\u2b24", "Atom"),         # ⬤ filled circle
    "eraser":  ("\u2715", "Eraser"),       # ✕ cross
}


class EditorToolbar(QToolBar):
    """Toolbar for molecule editing tools."""

    tool_changed = Signal(str)           # "select", "bond", "atom", "eraser"
    element_changed = Signal(str)        # element symbol
    bond_type_changed = Signal(object)   # BondType
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Editor Tools", parent)
        self.setMovable(False)
        self.setIconSize(QSize(28, 28))

        # Tool buttons — use QToolButton directly for full styling control
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._select_btn = self._add_tool_button("select", checked=True)
        self._bond_btn = self._add_tool_button("bond")
        self._atom_btn = self._add_tool_button("atom")
        self._erase_btn = self._add_tool_button("eraser")

        self._add_separator()

        # Bond type selector
        bond_label = QLabel(" Bond type:")
        self.addWidget(bond_label)
        self._bond_combo = QComboBox()
        for label, bt in BOND_TYPES:
            self._bond_combo.addItem(label, bt)
        self._bond_combo.currentIndexChanged.connect(self._on_bond_type_changed)
        self.addWidget(self._bond_combo)

        self._add_separator()

        # Element selector
        elem_label = QLabel(" Element:")
        self.addWidget(elem_label)
        self._element_combo = QComboBox()
        for e in ELEMENTS:
            self._element_combo.addItem(e)
        self._element_combo.currentTextChanged.connect(self._on_element_changed)
        self.addWidget(self._element_combo)

        self._add_separator()

        # Undo / Redo buttons
        self._undo_btn = QToolButton()
        self._undo_btn.setText("\u21b6 Undo")
        self._undo_btn.setToolTip("Undo (Ctrl+Z)")
        self._undo_btn.clicked.connect(self.undo_requested.emit)
        self.addWidget(self._undo_btn)

        self._redo_btn = QToolButton()
        self._redo_btn.setText("\u21b7 Redo")
        self._redo_btn.setToolTip("Redo (Ctrl+Shift+Z)")
        self._redo_btn.clicked.connect(self.redo_requested.emit)
        self.addWidget(self._redo_btn)

    def _add_tool_button(self, tool_name: str, checked: bool = False) -> QToolButton:
        symbol, label = TOOL_LABELS[tool_name]
        btn = QToolButton()
        btn.setText(f" {symbol}  {label} ")
        btn.setToolTip(label)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        btn.clicked.connect(lambda: self.tool_changed.emit(tool_name))
        self._button_group.addButton(btn)
        self.addWidget(btn)
        return btn

    def _add_separator(self):
        sep = QWidget()
        sep.setFixedWidth(12)
        self.addWidget(sep)

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
