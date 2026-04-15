"""Editor widget combining canvas, toolbar, and editing tools."""

from __future__ import annotations

from typing import Union

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QDialog, QGraphicsSceneMouseEvent, QVBoxLayout, QWidget

from ..core.molecule import BondType, Molecule
from ..editor.canvas import AtomItem, BondItem, MoleculeCanvas, MoleculeScene
from ..editor.history import HistoryManager
from ..editor.tools import (
    AtomTool, BondTool, ChargeTool, EraseTool, RingTool, SelectTool, Tool,
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

        # Hover state
        self._hover_item: Union[AtomItem, BondItem, None] = None

        # Toolbar → tools
        self._toolbar.tool_changed.connect(self._set_tool)
        self._toolbar.element_changed.connect(self._on_element_changed)
        self._toolbar.bond_type_changed.connect(self._on_bond_type_changed)
        self._toolbar.ring_type_changed.connect(self._on_ring_type_changed)
        self._toolbar.cleanup_requested.connect(self._cleanup_layout)
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
        self._hover_item = None
        self._rebuild_tools()
        self._canvas.load_molecule(mol)
        self.molecule_changed.emit()

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def _rebuild_tools(self):
        # Remember which tool was active so we can re-point _current_tool
        active_name = self._current_tool.name if self._current_tool else "select"

        scene = self._canvas.mol_scene
        self._tools = {
            "select": SelectTool(scene, self._history),
            "bond": BondTool(scene, self._history),
            "atom": AtomTool(scene, self._history),
            "eraser": EraseTool(scene, self._history),
            "charge": ChargeTool(scene, self._history, self._charge_delta),
            "ring": RingTool(scene, self._history, 6, aromatic=True,
                             tool_name="ring"),
        }
        # Propagate current element / bond type to all tools
        self._sync_tools()
        # Re-point _current_tool to the new instance (the old one is orphaned)
        self._current_tool = self._tools.get(active_name, self._tools["select"])

    def _set_tool(self, name: str):
        if self._current_tool:
            self._current_tool.deactivate()
        self._current_tool = self._tools.get(name)

    def set_element(self, element: str):
        self._on_element_changed(element)

    def _on_element_changed(self, element: str):
        self._current_element = element
        self._sync_tools()

    def _on_bond_type_changed(self, bond_type: BondType):
        self._current_bond_type = bond_type
        self._sync_tools()

    def _sync_tools(self):
        """Push current element / bond type to every tool."""
        for tool in self._tools.values():
            tool.element = self._current_element
            tool.bond_type = self._current_bond_type

    def _on_ring_type_changed(self, key: str):
        """Reconfigure the ring tool when a different ring type is selected."""
        from .toolbar import RING_TYPES
        ring_tool = self._tools.get("ring")
        if isinstance(ring_tool, RingTool):
            for _label, rkey, n, aro in RING_TYPES:
                if rkey == key:
                    ring_tool._n = n
                    ring_tool._aromatic = aro
                    break

    def _on_charge_tool(self, delta: int):
        self._charge_delta = delta
        if isinstance(self._tools.get("charge"), ChargeTool):
            self._tools["charge"].delta = delta
        self._set_tool("charge")

    def _on_periodic_table(self):
        dlg = PeriodicTableDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_element:
            self.set_element(dlg.selected_element)
            self._toolbar.set_pt_label(dlg.selected_element)

    # ------------------------------------------------------------------
    # Hover highlighting
    # ------------------------------------------------------------------

    def _update_hover(self, scene_pos):
        """Highlight the atom or bond under the cursor.

        Uses a tight radius for atoms so that bonds in ring structures
        can still be reached.  If the cursor is close to both an atom
        and a bond, the atom wins only when it's very close.
        """
        from ..editor.canvas import HIT_RADIUS
        from ..editor.tools import SelectTool
        scene = self._canvas.mol_scene

        # Items that are part of the active selection stay highlighted
        sel_atoms: set[int] = set()
        sel_bonds: set[tuple[int, int]] = set()
        tool = self._current_tool
        if isinstance(tool, SelectTool):
            sel_atoms = tool._selected
            sel_bonds = tool._selected_bonds

        # Clear previous highlight (unless it's part of the selection)
        if self._hover_item is not None:
            keep = False
            try:
                from ..editor.canvas import AtomItem, BondItem
                if isinstance(self._hover_item, AtomItem):
                    keep = self._hover_item.atom_idx in sel_atoms
                elif isinstance(self._hover_item, BondItem):
                    key = (min(self._hover_item.a1_idx, self._hover_item.a2_idx),
                           max(self._hover_item.a1_idx, self._hover_item.a2_idx))
                    keep = key in sel_bonds
                if not keep:
                    self._hover_item.set_highlighted(False)
            except RuntimeError:
                pass  # item was deleted by canvas refresh
            self._hover_item = None

        # Find nearest atom (tight radius — roughly the visible label area)
        tight_r2 = HIT_RADIUS * HIT_RADIUS  # 12px, not the 18px used by tools
        nearest_atom = None
        for item in scene._atom_items.values():
            d = item.pos() - scene_pos
            if d.x() * d.x() + d.y() * d.y() < tight_r2:
                nearest_atom = item
                break

        if nearest_atom:
            nearest_atom.set_highlighted(True)
            self._hover_item = nearest_atom
            return

        # No atom very close — check for bonds
        bond = scene.bond_at_pos(scene_pos)
        if bond:
            bond.set_highlighted(True)
            self._hover_item = bond

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
            # Hover highlight only when no button is pressed
            if event.buttons() == Qt.MouseButton.NoButton:
                self._update_hover(event.scenePos())
            event.accept()
            return True

        if etype == QEvent.Type.GraphicsSceneMouseRelease:
            if self._current_tool:
                self._current_tool.mouse_release(event)
            event.accept()
            return True

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """Handle Delete/Backspace to delete the current selection."""
        from ..editor.tools import SelectTool
        key = event.key()
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            tool = self._current_tool
            if isinstance(tool, SelectTool) and tool._selected:
                tool.delete_selection()
                return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _cleanup_layout(self):
        """Recompute 2D coordinates using RDKit for a clean layout."""
        from rdkit.Chem import AllChem
        from ..editor.history import CompoundCommand, MoveAtomCommand

        mol = self._molecule
        if mol.num_atoms == 0:
            return

        # Save old positions
        old_coords = mol.get_2d_coords()

        # Use RDKit to compute optimal 2D layout
        rdmol = mol.to_rdkit()
        AllChem.Compute2DCoords(rdmol)
        conf = rdmol.GetConformer(0)

        # Build compound MoveAtomCommand for full undo
        cmds = []
        for i in range(mol.num_atoms):
            pos = conf.GetAtomPosition(i)
            ox, oy = old_coords[i]
            # RDKit coords are in Angstrom-like units; match our scale
            if ox != pos.x or oy != pos.y:
                cmds.append(MoveAtomCommand(i, ox, oy, pos.x, pos.y))

        if cmds:
            # Execute all moves
            for cmd in cmds:
                cmd.execute(mol)
            compound = CompoundCommand(cmds)
            self._history._undo_stack.append(compound)
            self._history._redo_stack.clear()
            self._hover_item = None
            self._refresh_canvas()
            self.molecule_changed.emit()

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
        self._hover_item = None  # canvas items are about to be destroyed
        self._refresh_canvas()
        self.molecule_changed.emit()

    def _refresh_canvas(self):
        self._canvas.load_molecule(self._molecule)
