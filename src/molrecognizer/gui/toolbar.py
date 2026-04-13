"""Compact single-row toolbar for molecule editing tools."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QMenu,
    QToolButton,
    QWidget,
)

from ..core.molecule import BondType

ELEMENTS = ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "H", "B", "Si", "Se"]

BOND_TYPES = [
    ("Single", BondType.SINGLE),
    ("Double", BondType.DOUBLE),
    ("Triple", BondType.TRIPLE),
]


class EditorToolbar(QWidget):
    """Single-row toolbar: tools | bond dropdown | charge | PT | undo/redo."""

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
        self.setFixedHeight(52)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(6)

        # -- Tool button group (exclusive) --
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._tool_buttons: dict[str, QToolButton] = {}

        self._make_tool_button("Select", "select", row, checked=True)

        # Bond button with dropdown arrow for bond-type selection
        bond_btn = QToolButton()
        bond_btn.setText("Bond")
        bond_btn.setCheckable(True)
        bond_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        bond_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        bond_btn.clicked.connect(lambda: self._on_tool_click("bond"))

        bond_menu = QMenu(self)
        self._bond_action_group = QActionGroup(self)
        self._bond_action_group.setExclusive(True)
        for label, bt in BOND_TYPES:
            action = bond_menu.addAction(label)
            action.setCheckable(True)
            action.setData(bt)
            self._bond_action_group.addAction(action)
            if bt == BondType.SINGLE:
                action.setChecked(True)
        bond_menu.triggered.connect(self._on_bond_menu_triggered)
        bond_btn.setMenu(bond_menu)

        self._button_group.addButton(bond_btn)
        self._tool_buttons["bond"] = bond_btn
        row.addWidget(bond_btn)

        self._make_tool_button("Atom", "atom", row)
        self._make_tool_button("Eraser", "eraser", row)

        row.addWidget(self._sep())

        # Charge buttons (in the exclusive group so they act as tools)
        self._make_tool_button("\u2295", "charge+", row)   # ⊕
        self._make_tool_button("\u2296", "charge-", row)   # ⊖

        row.addWidget(self._sep())

        # Periodic table button (not in exclusive group — it opens a dialog)
        self._pt_btn = QToolButton()
        self._pt_btn.setText("PT")
        self._pt_btn.setToolTip("Periodic Table")
        self._pt_btn.clicked.connect(self.periodic_table_requested.emit)
        row.addWidget(self._pt_btn)

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

    def _on_bond_menu_triggered(self, action):
        bt = action.data()
        self.bond_type_changed.emit(bt)
        # Also activate the bond tool
        self._tool_buttons["bond"].setChecked(True)
        self.tool_changed.emit("bond")

    def set_pt_label(self, symbol: str):
        """Update the periodic-table button text to show the chosen element."""
        self._pt_btn.setText(symbol)
        self._pt_btn.setToolTip(f"Periodic Table ({symbol})")

    @property
    def current_bond_type(self) -> BondType:
        checked = self._bond_action_group.checkedAction()
        if checked:
            return checked.data()
        return BondType.SINGLE
