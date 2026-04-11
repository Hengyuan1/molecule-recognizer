"""Toolbar with editing tool buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
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

        # Tool buttons
        self._tool_group = QActionGroup(self)
        self._tool_group.setExclusive(True)

        self._select_act = self._add_tool("Select", "select", checked=True)
        self._bond_act = self._add_tool("Bond", "bond")
        self._atom_act = self._add_tool("Atom", "atom")
        self._erase_act = self._add_tool("Eraser", "eraser")

        self.addSeparator()

        # Bond type selector
        self._bond_combo = QComboBox()
        for label, bt in BOND_TYPES:
            self._bond_combo.addItem(label, bt)
        self._bond_combo.currentIndexChanged.connect(self._on_bond_type_changed)
        bond_widget = QWidget()
        bond_layout = QHBoxLayout(bond_widget)
        bond_layout.setContentsMargins(4, 0, 4, 0)
        bond_layout.addWidget(QLabel("Bond:"))
        bond_layout.addWidget(self._bond_combo)
        self.addWidget(bond_widget)

        # Element selector
        self._element_combo = QComboBox()
        for e in ELEMENTS:
            self._element_combo.addItem(e)
        self._element_combo.currentTextChanged.connect(self._on_element_changed)
        elem_widget = QWidget()
        elem_layout = QHBoxLayout(elem_widget)
        elem_layout.setContentsMargins(4, 0, 4, 0)
        elem_layout.addWidget(QLabel("Atom:"))
        elem_layout.addWidget(self._element_combo)
        self.addWidget(elem_widget)

        self.addSeparator()

        # Undo / Redo
        undo_act = QAction("Undo", self)
        undo_act.triggered.connect(self.undo_requested.emit)
        self.addAction(undo_act)

        redo_act = QAction("Redo", self)
        redo_act.triggered.connect(self.redo_requested.emit)
        self.addAction(redo_act)

    def _add_tool(self, label: str, tool_name: str, checked: bool = False) -> QAction:
        action = QAction(label, self)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(lambda: self.tool_changed.emit(tool_name))
        self._tool_group.addAction(action)
        self.addAction(action)
        return action

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
