"""Compact single-row toolbar for molecule editing tools."""

from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QActionGroup, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QMenu,
    QToolButton,
    QWidget,
)

from ..core.molecule import BondType
from .workbench_icons import workbench_icon

ELEMENTS = ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "H", "B", "Si", "Se"]

BOND_TYPES = [
    ("Single", BondType.SINGLE),
    ("Double", BondType.DOUBLE),
    ("Triple", BondType.TRIPLE),
    ("Wedge", BondType.WEDGE),
    ("Dash", BondType.DASH),
]

# (label, tool_data_key, n_sides, aromatic)
RING_TYPES = [
    ("\u232C Benzene", "benzene", 6, True),     # ⌬
    ("\u2B21 6-ring", "ring6", 6, False),        # ⬡
    ("\u2B20 5-ring", "ring5", 5, False),        # ⬠
    ("\u25A1 4-ring", "ring4", 4, False),         # □
    ("\u25B3 3-ring", "ring3", 3, False),         # △
]

# Short labels for the button face
_RING_SHORT = {
    "benzene": "\u232C",
    "ring6": "\u2B21",
    "ring5": "\u2B20",
    "ring4": "\u25A1",
    "ring3": "\u25B3",
}


class EditorToolbar(QWidget):
    """Single-row toolbar: tools | bond dropdown | ring dropdown | charge | PT | undo/redo."""

    tool_changed = Signal(str)
    element_changed = Signal(str)       # kept for EditorWidget compat
    bond_type_changed = Signal(object)
    ring_type_changed = Signal(str)     # key like "benzene", "ring6", …
    undo_requested = Signal()
    redo_requested = Signal()
    cleanup_requested = Signal()   # reformat layout
    clear_requested = Signal()     # clear canvas + images
    charge_tool_requested = Signal(int)  # +1 or -1
    periodic_table_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbar_container")
        self.setMinimumHeight(46)

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
        bond_btn.setIcon(workbench_icon("bond"))
        bond_btn.setCheckable(True)
        bond_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        bond_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        bond_btn.clicked.connect(lambda: self._on_tool_click("bond"))

        bond_menu = QMenu(self)
        self._bond_action_group = QActionGroup(self)
        self._bond_action_group.setExclusive(True)
        _icons_dir = os.path.join(os.path.dirname(__file__), "icons")
        _bond_icons = {
            BondType.WEDGE: os.path.join(_icons_dir, "wedge-bond.png"),
            BondType.DASH: os.path.join(_icons_dir, "dash-bond.png"),
        }
        for label, bt in BOND_TYPES:
            icon_path = _bond_icons.get(bt)
            if icon_path and os.path.isfile(icon_path):
                action = bond_menu.addAction(QIcon(icon_path), label)
            else:
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

        # Ring button with dropdown for ring-type selection
        self._ring_btn = QToolButton()
        self._ring_btn.setText("\u232C")        # default: benzene ⌬
        self._ring_btn.setCheckable(True)
        self._ring_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._ring_btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self._ring_btn.clicked.connect(lambda: self._on_tool_click("ring"))

        ring_menu = QMenu(self)
        self._ring_action_group = QActionGroup(self)
        self._ring_action_group.setExclusive(True)
        for label, key, _n, _aro in RING_TYPES:
            action = ring_menu.addAction(label)
            action.setCheckable(True)
            action.setData(key)
            self._ring_action_group.addAction(action)
            if key == "benzene":
                action.setChecked(True)
        ring_menu.triggered.connect(self._on_ring_menu_triggered)
        self._ring_btn.setMenu(ring_menu)

        self._button_group.addButton(self._ring_btn)
        self._tool_buttons["ring"] = self._ring_btn
        row.addWidget(self._ring_btn)

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

        # Format (recompute 2D layout)
        self._format_btn = QToolButton()
        self._format_btn.setText("Format")
        self._format_btn.setToolTip("Reformat structure layout")
        self._format_btn.clicked.connect(self.cleanup_requested.emit)
        row.addWidget(self._format_btn)

        # Clean (clear canvas)
        self._clear_btn = QToolButton()
        self._clear_btn.setText("Clean")
        self._clear_btn.setToolTip("Clear canvas and loaded images")
        self._clear_btn.clicked.connect(self.clear_requested.emit)
        row.addWidget(self._clear_btn)

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

        for button, name in ((self._format_btn, "format"),
                             (self._clear_btn, "clear"),
                             (self._undo_btn, "undo"),
                             (self._redo_btn, "redo")):
            button.setIcon(workbench_icon(name))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        for button in self.findChildren(QToolButton):
            button.setIconSize(QSize(20, 20))
            button.setAccessibleName(button.text())

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
        if name in ("select", "atom", "eraser"):
            btn.setIcon(workbench_icon(name))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
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

    def _on_ring_menu_triggered(self, action):
        key = action.data()
        # Update button label to show selected ring
        self._ring_btn.setText(_RING_SHORT.get(key, "\u232C"))
        self.ring_type_changed.emit(key)
        # Also activate the ring tool
        self._ring_btn.setChecked(True)
        self.tool_changed.emit("ring")

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
