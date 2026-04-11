"""Editor widget combining canvas, toolbar, and editing tools."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Signal
from PySide6.QtWidgets import QDialog, QGraphicsSceneMouseEvent, QVBoxLayout, QWidget

from ..core.molecule import BondType, Molecule
from ..editor.canvas import MoleculeCanvas, MoleculeScene
from ..editor.history import HistoryManager
from ..editor.tools import (
    AtomTool, BondTool, ChargeTool, EraseTool, SelectTool, Tool,
)
from .periodic_table import PeriodicTableDialog
from .toolbar import EditorToolbar


class EditorWidget(QWidget):
    """Combines the molecular canvas with toolbar and editing tools.

    Signals:
        molecule_changed: emitted whenever the molecule is modified.
    """

    molecule_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._molecule = Molecule()
        self._history = HistoryManager(self._molecule)
        self._history.set_on_change(self._on_history_change)

        # UI
        self._toolbar = EditorToolbar()
        self._canvas = MoleculeCanvas()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._canvas)

        # Tools
        self._tools: dict[str, Tool] = {}
        self._current_tool: Tool | None = None
        self._current_bond_type = BondType.SINGLE
        self._current_element = "C"
        self._charge_delta = +1
        self._rebuild_tools()
        self._set_tool("select")

        # Toolbar → tools
        self._toolbar.tool_changed.connect(self._set_tool)
        self._toolbar.element_changed.connect(self._on_element_changed)
        self._toolbar.bond_type_changed.connect(self._on_bond_type_changed)
        self._toolbar.undo_requested.connect(self._undo)
        self._toolbar.redo_requested.connect(self._redo)
        self._toolbar.charge_tool_requested.connect(self._on_charge_tool)
        self._toolbar.periodic_table_requested.connect(self._on_periodic_table)

        # Scene event interception
        self._canvas.mol_scene.installEventFilter(self)

    @property
    def molecule(self) -> Molecule:
        return self._molecule

    @property
    def canvas(self) -> MoleculeCanvas:
        return self._canvas

    def load_molecule(self, mol: Molecule):
        self._molecule = mol
        self._history.molecule = mol
        self._rebuild_tools()
        self._canvas.load_molecule(mol)
        self.molecule_changed.emit()

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def _rebuild_tools(self):
        scene = self._canvas.mol_scene
        self._tools = {
            "select": SelectTool(scene, self._history),
            "bond": BondTool(scene, self._history, self._current_bond_type),
            "atom": AtomTool(scene, self._history, self._current_element),
            "eraser": EraseTool(scene, self._history),
            "charge": ChargeTool(scene, self._history, self._charge_delta),
        }

    def _set_tool(self, name: str):
        if self._current_tool:
            self._current_tool.deactivate()
        self._current_tool = self._tools.get(name)

    def set_element(self, element: str):
        self._on_element_changed(element)

    def _on_element_changed(self, element: str):
        self._current_element = element
        if isinstance(self._tools.get("atom"), AtomTool):
            self._tools["atom"].element = element

    def _on_bond_type_changed(self, bond_type: BondType):
        self._current_bond_type = bond_type
        if isinstance(self._tools.get("bond"), BondTool):
            self._tools["bond"].bond_type = bond_type

    def _on_charge_tool(self, delta: int):
        self._charge_delta = delta
        if isinstance(self._tools.get("charge"), ChargeTool):
            self._tools["charge"].delta = delta
        self._set_tool("charge")

    def _on_periodic_table(self):
        dlg = PeriodicTableDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_element:
            self.set_element(dlg.selected_element)

    # ------------------------------------------------------------------
    # Event filter — intercept scene mouse events for tool delegation
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is not self._canvas.mol_scene:
            return super().eventFilter(obj, event)

        etype = event.type()

        if etype == QEvent.Type.GraphicsSceneMousePress:
            if self._current_tool:
                self._current_tool.mouse_press(event)
            event.accept()
            return True

        if etype == QEvent.Type.GraphicsSceneMouseMove:
            if self._current_tool:
                self._current_tool.mouse_move(event)
            event.accept()
            return True

        if etype == QEvent.Type.GraphicsSceneMouseRelease:
            if self._current_tool:
                self._current_tool.mouse_release(event)
            event.accept()
            return True

        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _undo(self):
        if self._history.undo():
            self._refresh_canvas()

    def _redo(self):
        if self._history.redo():
            self._refresh_canvas()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_history_change(self):
        self._refresh_canvas()
        self.molecule_changed.emit()

    def _refresh_canvas(self):
        self._canvas.load_molecule(self._molecule)
