"""Explicit selection of common metal centers, without guessing chemistry."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QGridLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ..editor.canvas import ELEMENT_COLORS
from .window_placement import OwnerDialog


COMMON_METAL_CENTERS = (
    ("Co", "Cobalt"), ("Pt", "Platinum"), ("Cr", "Chromium"), ("Sc", "Scandium"),
    ("Ir", "Iridium"), ("Fe", "Iron"), ("Ni", "Nickel"), ("Cu", "Copper"),
    ("Zn", "Zinc"), ("Mn", "Manganese"), ("Ru", "Ruthenium"), ("Pd", "Palladium"),
    ("Rh", "Rhodium"), ("Ag", "Silver"), ("Au", "Gold"), ("Ti", "Titanium"),
)


class MetalChoiceButton(QPushButton):
    """Two real labels, not a multiline native push-button caption.

    Windows styles size/clip a QPushButton's caption as a single line. A child
    layout gives both lines their own measured space at every font/DPI setting.
    """

    def __init__(self, symbol, name, scale, parent=None):
        super().__init__(parent)
        self.setObjectName("metal_choice")
        self.setAutoDefault(False)
        self.setAccessibleName(f"{name} ({symbol})")
        self.setToolTip(f"Select {name} ({symbol}); no charge or bonds are assigned")
        self._minimum_card_size = QSize(round(112 * scale), round(70 * scale))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(round(10 * scale), round(9 * scale),
                                  round(10 * scale), round(9 * scale))
        layout.setSpacing(round(3 * scale))
        self.symbol_label = QLabel(symbol, self)
        self.symbol_label.setObjectName("metal_symbol")
        self.symbol_label.setStyleSheet(f"color: {ELEMENT_COLORS[symbol]};")
        self.name_label = QLabel(name, self)
        self.name_label.setObjectName("metal_name")
        for label in (self.symbol_label, self.name_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(label)

    def sizeHint(self):  # noqa: N802
        # QPushButton's native size hint ignores child layouts. The grid must
        # reserve the complete two-label height, not just let the child widget
        # grow over the next row after layout has already finished.
        hint = super().sizeHint()
        if self.layout():
            hint = hint.expandedTo(self.layout().sizeHint())
        return hint.expandedTo(self._minimum_card_size)

    def minimumSizeHint(self):  # noqa: N802
        return self.sizeHint()


class MetalPickerDialog(OwnerDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select a metal center")
        self.setObjectName("metal_picker")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.selected_element = None
        self._buttons = {}
        # Native Windows already applies system DPI. Never shrink this dialog
        # below a readable logical size; WSL's larger in-app scale is retained.
        scale = max(1.0, min(2.0, getattr(self._owner, "_ui_scale", 1.0)))
        px = lambda value: round(value * scale)
        self.setStyleSheet(f"""
            QDialog#metal_picker, QWidget#metal_picker_content {{ background: #edf2f7; }}
            QLabel {{ color: #243b53; background: transparent; font-size: {px(14)}px; }}
            QLabel#metal_symbol {{ font-size: {px(20)}px; font-weight: 700; }}
            QLabel#metal_name {{ color: #243b53; font-size: {px(13)}px; font-weight: 500; }}
            QPushButton#metal_choice, QPushButton#metal_cancel {{
                background: #ffffff; color: #243b53; border: 1px solid #b8c9dc;
                border-radius: {px(6)}px; padding: 0px; min-height: 0px;
            }}
            QPushButton#metal_choice:hover, QPushButton#metal_choice:focus,
            QPushButton#metal_cancel:hover, QPushButton#metal_cancel:focus {{
                background: #e1edfb; border-color: #2568ad;
            }}
            QPushButton#metal_choice:pressed {{ background: #cbdff5; }}
            QPushButton#metal_cancel {{
                font-size: {px(14)}px; padding: {px(8)}px {px(18)}px;
                min-height: {px(22)}px; min-width: {px(60)}px;
            }}
        """)
        outer = QVBoxLayout(self)
        content = QWidget(self)
        content.setObjectName("metal_picker_content")
        content.setMaximumWidth(px(620))
        layout = QVBoxLayout(content)
        outer.addStretch()
        outer.addWidget(content, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()
        instructions = QLabel(
            "Choose a metal, then click the canvas to place it or an atom to replace it.\n"
            "This selects the element only, not its oxidation state or coordination geometry. "
            "Use PT for other elements.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        grid = QGridLayout()
        grid.setSpacing(px(8))
        for index, (symbol, name) in enumerate(COMMON_METAL_CENTERS):
            button = MetalChoiceButton(symbol, name, scale)
            button.clicked.connect(lambda checked=False, s=symbol: self._pick(s))
            grid.addWidget(button, index // 4, index % 4)
            self._buttons[symbol] = button
        layout.addLayout(grid)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("metal_cancel")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel, 0, Qt.AlignmentFlag.AlignRight)
        self.resize(px(620), px(470))

    def _pick(self, symbol):
        self.selected_element = symbol
        self.accept()
