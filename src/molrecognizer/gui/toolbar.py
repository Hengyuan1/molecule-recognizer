"""Compact single-row toolbar for molecule editing tools."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
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


class EditorToolbar(QWidget):
    """Single-row toolbar: tools | bond type | charge | PT | undo/redo."""

    tool_changed = Signal(str)
    element_changed = Signal(str)       # kept for EditorWidget compat
    bond_type_changed = Signal(object)
    undo_requested = Signal()
    redo_requested = Signal()
    charge_tool_requested = Signal(int)  # +1 or -1
    periodic_table_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbar_container")
        self.setFixedHeight(44)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(4)

        # -- Tool button group (exclusive) --
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._tool_buttons: dict[str, QToolButton] = {}

        self._make_tool_button("Select", "select", row, checked=True)
        self._make_tool_button("Bond", "bond", row)
        self._make_tool_button("Atom", "atom", row)
        self._make_tool_button("Eraser", "eraser", row)

        row.addWidget(self._sep())

        # Bond type combo
        self._bond_combo = QComboBox()
        self._bond_combo.setFixedWidth(100)
        for label, bt in BOND_TYPES:
            self._bond_combo.addItem(label, bt)
        self._bond_combo.currentIndexChanged.connect(self._on_bond_type_changed)
        row.addWidget(self._bond_combo)

        row.addWidget(self._sep())

        # Charge buttons (in the exclusive group so they act as tools)
        self._make_tool_button("\u229a", "charge+", row)   # ⊕
        self._make_tool_button("\u229b", "charge-", row)   # ⊛ (using ⊖ is hard to see)

        row.addWidget(self._sep())

        # Periodic table button (not in exclusive group — it opens a dialog)
        pt_btn = QToolButton()
        pt_btn.setText("PT")
        pt_btn.setToolTip("Periodic Table")
        pt_btn.clicked.connect(self.periodic_table_requested.emit)
        row.addWidget(pt_btn)

        row.addStretch()

        # Undo / Redo
        self._undo_btn = QToolButton()
        self._undo_btn.setText("Undo")
        self._undo_btn.setToolTip("Undo (Ctrl+Z)")
        self._undo_btn.clicked.connect(self.undo_requested.emit)
        row.addWidget(self._undo_btn)

        self._redo_btn = QToolButton()
        self._redo_btn.setText("Redo")
        self._redo_btn.setToolTip("Redo (Ctrl+Shift+Z)")
        self._redo_btn.clicked.connect(self.redo_requested.emit)
        row.addWidget(self._redo_btn)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _sep() -> QFrame:
        s = QFrame()
        s.setFrameShape(QFrame.Shape.VLine)
        s.setFixedWidth(2)
        s.setStyleSheet("color: #ccd0d5;")
        return s

    def _make_tool_button(self, label: str, name: str,
                          layout: QHBoxLayout, checked: bool = False):
        btn = QToolButton()
        btn.setText(label)
        btn.setToolTip(name.replace("+", " +").replace("-", " −").capitalize())
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        btn.clicked.connect(lambda: self._on_tool_click(name))
        self._button_group.addButton(btn)
        self._tool_buttons[name] = btn
        layout.addWidget(btn)

    def _on_tool_click(self, name: str):
        if name == "charge+":
            self.charge_tool_requested.emit(+1)
        elif name == "charge-":
            self.charge_tool_requested.emit(-1)
        else:
            self.tool_changed.emit(name)

    def _activate_tool(self, name: str):
        btn = self._tool_buttons.get(name)
        if btn:
            btn.setChecked(True)
            self._on_tool_click(name)

    def _on_bond_type_changed(self, index: int):
        bt = self._bond_combo.itemData(index)
        self.bond_type_changed.emit(bt)

    @property
    def current_bond_type(self) -> BondType:
        return self._bond_combo.currentData()
