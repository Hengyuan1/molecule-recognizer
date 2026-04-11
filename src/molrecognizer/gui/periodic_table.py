"""Periodic table dialog for element selection."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QDialog, QGridLayout, QPushButton, QVBoxLayout, QLabel

# (symbol, row, col, category)
# row/col are 0-indexed; lanthanides/actinides omitted for simplicity.
_ELEMENTS = [
    ("H",  0, 0, "nonmetal"),    ("He", 0, 17, "noble"),
    ("Li", 1, 0, "alkali"),      ("Be", 1, 1, "alkaline"),
    ("B",  1, 12, "metalloid"),  ("C",  1, 13, "nonmetal"),
    ("N",  1, 14, "nonmetal"),   ("O",  1, 15, "nonmetal"),
    ("F",  1, 16, "halogen"),    ("Ne", 1, 17, "noble"),
    ("Na", 2, 0, "alkali"),      ("Mg", 2, 1, "alkaline"),
    ("Al", 2, 12, "post"),       ("Si", 2, 13, "metalloid"),
    ("P",  2, 14, "nonmetal"),   ("S",  2, 15, "nonmetal"),
    ("Cl", 2, 16, "halogen"),    ("Ar", 2, 17, "noble"),
    ("K",  3, 0, "alkali"),      ("Ca", 3, 1, "alkaline"),
    ("Sc", 3, 2, "transition"),  ("Ti", 3, 3, "transition"),
    ("V",  3, 4, "transition"),  ("Cr", 3, 5, "transition"),
    ("Mn", 3, 6, "transition"),  ("Fe", 3, 7, "transition"),
    ("Co", 3, 8, "transition"),  ("Ni", 3, 9, "transition"),
    ("Cu", 3, 10, "transition"), ("Zn", 3, 11, "transition"),
    ("Ga", 3, 12, "post"),       ("Ge", 3, 13, "metalloid"),
    ("As", 3, 14, "metalloid"),  ("Se", 3, 15, "nonmetal"),
    ("Br", 3, 16, "halogen"),    ("Kr", 3, 17, "noble"),
    ("Rb", 4, 0, "alkali"),      ("Sr", 4, 1, "alkaline"),
    ("Y",  4, 2, "transition"),  ("Zr", 4, 3, "transition"),
    ("Nb", 4, 4, "transition"),  ("Mo", 4, 5, "transition"),
    ("Tc", 4, 6, "transition"),  ("Ru", 4, 7, "transition"),
    ("Rh", 4, 8, "transition"),  ("Pd", 4, 9, "transition"),
    ("Ag", 4, 10, "transition"), ("Cd", 4, 11, "transition"),
    ("In", 4, 12, "post"),       ("Sn", 4, 13, "post"),
    ("Sb", 4, 14, "metalloid"),  ("Te", 4, 15, "metalloid"),
    ("I",  4, 16, "halogen"),    ("Xe", 4, 17, "noble"),
    ("Cs", 5, 0, "alkali"),      ("Ba", 5, 1, "alkaline"),
    ("La", 5, 2, "lanthanide"),
    ("Hf", 5, 3, "transition"),  ("Ta", 5, 4, "transition"),
    ("W",  5, 5, "transition"),  ("Re", 5, 6, "transition"),
    ("Os", 5, 7, "transition"),  ("Ir", 5, 8, "transition"),
    ("Pt", 5, 9, "transition"),  ("Au", 5, 10, "transition"),
    ("Hg", 5, 11, "transition"), ("Tl", 5, 12, "post"),
    ("Pb", 5, 13, "post"),       ("Bi", 5, 14, "post"),
    ("Po", 5, 15, "post"),       ("At", 5, 16, "halogen"),
    ("Rn", 5, 17, "noble"),
    ("Fr", 6, 0, "alkali"),      ("Ra", 6, 1, "alkaline"),
    ("Ac", 6, 2, "actinide"),
    ("Rf", 6, 3, "transition"),  ("Db", 6, 4, "transition"),
    ("Sg", 6, 5, "transition"),  ("Bh", 6, 6, "transition"),
    ("Hs", 6, 7, "transition"),
]

_CATEGORY_COLORS = {
    "alkali":     "#FF6666",
    "alkaline":   "#FFCC66",
    "transition": "#FFD9B3",
    "post":       "#CCCCCC",
    "metalloid":  "#99CCBB",
    "nonmetal":   "#99DD99",
    "halogen":    "#99DDFF",
    "noble":      "#CCBBFF",
    "lanthanide": "#FFBBCC",
    "actinide":   "#FFBB99",
}


class PeriodicTableDialog(QDialog):
    """Modal dialog showing a periodic table for element selection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Element")
        self.selected_element: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Click an element to select it")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 13px; color: #555; margin-bottom: 6px;")
        outer.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(2)

        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        for symbol, row, col, cat in _ELEMENTS:
            btn = QPushButton(symbol)
            btn.setFont(font)
            btn.setFixedSize(38, 34)
            bg = _CATEGORY_COLORS.get(cat, "#DDDDDD")
            btn.setStyleSheet(
                f"QPushButton {{ background: {bg}; border: 1px solid #bbb;"
                f"  border-radius: 3px; color: #222; }}"
                f"QPushButton:hover {{ border: 2px solid #1a73e8; }}"
            )
            btn.clicked.connect(lambda checked, s=symbol: self._pick(s))
            grid.addWidget(btn, row, col)

        outer.addLayout(grid)
        self.setFixedSize(self.sizeHint())

    def _pick(self, symbol: str):
        self.selected_element = symbol
        self.accept()
