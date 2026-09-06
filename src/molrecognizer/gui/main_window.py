"""Main application window — IQmol-inspired chemistry workbench.

Layout:
    +---------+---------------------------+------+
    | File / Edit / Build / View / Help          |
    | Drawing tools                  Undo/Redo  |
    +---------+---------------------------+------+
    |  Left   |                           | Elem |
    |  Panel  |  Canvas (draw / edit)     | Pal- |
    |  image  |                           | ette |
    |  preview|                           |      |
    |  +btns  |                           |      |
    +---------+---------------------------+------+
    | SMILES: ...               [Copy] [Export]  |
    | Valence: All OK                            |
    +--------------------------------------------+
"""

from __future__ import annotations

import io
import os
import re

from PIL import Image
from PySide6.QtCore import QSettings, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QFont, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.molecule import Molecule
from ..core.smiles import molecule_to_smiles, smiles_to_molecule
from ..core.valence import check_valence
from .editor_widget import EditorWidget
from .screenshot import (
    GlobalScreenshotHotkey, ScreenshotDialog, grab_screen, is_wsl,
    pixmap_to_png_bytes,
)
from .viewer3d import Viewer3DWidget
from .workbench_icons import workbench_icon
from .inline_menu import InlineMenuBar

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Element palette colours (CPK-ish)
ELEMENT_PALETTE = [
    ("H",  "#888888"),
    ("C",  "#333333"),
    ("N",  "#3355DD"),
    ("O",  "#DD2222"),
    ("S",  "#CCAA00"),
    ("P",  "#DD8800"),
    ("F",  "#22BB22"),
    ("Cl", "#22CC22"),
    ("Br", "#992222"),
    ("I",  "#772299"),
    ("B",  "#DD8899"),
]


# ======================================================================
# Recognition worker (background thread)
# ======================================================================

class RecognitionWorker(QThread):
    result_ready = Signal(object)
    status = Signal(str)

    def __init__(self, image: Image.Image, parent=None):
        super().__init__(parent)
        self._image = image

    def run(self):
        try:
            from ..core.recognizer import MoleculeRecognizer
            self.status.emit("Recognizing structure with OSRA…")
            recognizer = MoleculeRecognizer()
            mol = recognizer.recognize(self._image)
            self.result_ready.emit(mol)
        except Exception as e:
            self.result_ready.emit(e)


# ======================================================================
# Element palette (right sidebar)
# ======================================================================

class ElementPalette(QWidget):
    """Vertical strip of coloured element buttons."""

    element_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(52)
        self.setMaximumWidth(80)
        self.setObjectName("element_palette")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(6)

        self._buttons: dict[str, QPushButton] = {}
        for symbol, colour in ELEMENT_PALETTE:
            btn = QPushButton(symbol)
            btn.setObjectName("element_btn")
            btn.setFixedSize(40, 40)
            btn.setCheckable(True)
            btn.setProperty("element_colour", colour)
            btn.clicked.connect(lambda checked, s=symbol: self._on_click(s))
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)
            self._buttons[symbol] = btn

        layout.addStretch()

        # Default selection
        self._buttons["C"].setChecked(True)
        self.apply_scale(1.0)

    def apply_scale(self, scale: float):
        """Keep palette buttons circular and legible at every UI scale."""
        size = round(40 * scale)
        for button in self._buttons.values():
            colour = button.property("element_colour")
            button.setFixedSize(size, size)
            button.setStyleSheet(
                "QPushButton#element_btn {"
                "  background-color: #ffffff;"
                f"  color: {colour};"
                "  padding: 0px;"
                f"  min-height: {size - 4}px; max-height: {size - 4}px;"
                f"  min-width: {size - 4}px; max-width: {size - 4}px;"
                f"  border-radius: {round(20 * scale)}px;"
                f"  font-size: {round(13 * scale)}px;"
                "  font-weight: 700;"
                "  border: 2px solid #dce5ef;"
                "}"
                "QPushButton#element_btn:hover { border-color: #4A90D9; }"
                "QPushButton#element_btn:checked {"
                "  background-color: #dceafb; border: 2px solid #4A90D9;"
                "}"
            )

    def _on_click(self, symbol: str):
        for s, btn in self._buttons.items():
            btn.setChecked(s == symbol)
        self.element_selected.emit(symbol)


# ======================================================================
# Left panel (image preview + action buttons)
# ======================================================================

class LeftPanel(QWidget):
    open_image = Signal()
    screenshot = Signal()
    load_smiles = Signal()
    render_3d = Signal()
    save_xyz = Signal(str)  # "angstrom" or "bohr"
    copy_xyz = Signal(str)  # "angstrom" or "bohr"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("left_panel")
        self.setMinimumWidth(180)
        self.setMaximumWidth(350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        outer = layout
        brand = QLabel("Molecule Recognizer")
        brand.setObjectName("sidebar_brand")
        outer.addWidget(brand)
        caption = QLabel("IMAGE  /  STRUCTURE  /  COORDINATES")
        caption.setObjectName("sidebar_caption")
        outer.addWidget(caption)
        source_card = QFrame()
        source_card.setObjectName("source_card")
        outer.addWidget(source_card)
        layout = QVBoxLayout(source_card)
        layout.setContentsMargins(12, 6, 12, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("01   SOURCE IMAGE")
        title.setObjectName("panel_title")
        layout.addWidget(title)

        # Image preview
        self._preview = QLabel()
        self._preview.setObjectName("image_preview")
        self._preview.setFixedHeight(150)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setText("Open an image or capture a structure")
        self._preview.setWordWrap(True)
        layout.addWidget(self._preview)

        # Action buttons
        btn_open = QPushButton("Open Image")
        btn_open.setObjectName("action_btn_secondary")
        btn_open.setIcon(workbench_icon("open"))
        btn_open.clicked.connect(self.open_image.emit)
        layout.addWidget(btn_open)

        btn_screen = QPushButton("Screenshot")
        btn_screen.setObjectName("action_btn")
        btn_screen.setToolTip("Capture a structure from your screen (Alt+Y)")
        btn_screen.clicked.connect(self.screenshot.emit)
        layout.addWidget(btn_screen)

        btn_smiles = QPushButton("Load SMILES")
        btn_smiles.setObjectName("action_btn_secondary")
        btn_smiles.clicked.connect(self.load_smiles.emit)
        layout.addWidget(btn_smiles)

        # ---- 3D Structure section ----
        viewer_card = QFrame()
        viewer_card.setObjectName("viewer_card")
        outer.addWidget(viewer_card)
        layout = QVBoxLayout(viewer_card)
        layout.setContentsMargins(12, 6, 12, 12)
        layout.setSpacing(8)
        title_3d = QLabel("02   3D STRUCTURE")
        title_3d.setObjectName("panel_title")
        layout.addWidget(title_3d)

        self._viewer_3d = Viewer3DWidget()
        self._viewer_3d.setMinimumHeight(100)
        self._viewer_3d.setFixedHeight(120)
        layout.addWidget(self._viewer_3d)

        # Render + XYZ actions
        row_3d = QHBoxLayout()
        row_3d.setSpacing(6)

        btn_render = QPushButton("Render")
        btn_render.setObjectName("action_btn_secondary")
        btn_render.setIcon(workbench_icon("molecule"))
        btn_render.clicked.connect(self.render_3d.emit)
        row_3d.addWidget(btn_render)

        xyz_actions = QVBoxLayout()
        xyz_actions.setSpacing(6)

        self._xyz_btn = QToolButton()
        self._xyz_btn.setText("Save xyz")
        self._xyz_btn.setObjectName("save_xyz_btn")
        self._xyz_btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        xyz_menu = QMenu(self)
        act_ang = xyz_menu.addAction("Angstrom")
        act_bohr = xyz_menu.addAction("Bohr")
        act_ang.triggered.connect(lambda: self.save_xyz.emit("angstrom"))
        act_bohr.triggered.connect(lambda: self.save_xyz.emit("bohr"))
        self._xyz_btn.setMenu(xyz_menu)
        self._xyz_btn.clicked.connect(lambda: self.save_xyz.emit("angstrom"))
        xyz_actions.addWidget(self._xyz_btn)

        self._copy_xyz_btn = QToolButton()
        self._copy_xyz_btn.setText("Copy xyz")
        self._copy_xyz_btn.setObjectName("copy_xyz_btn")
        self._copy_xyz_btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        copy_xyz_menu = QMenu(self)
        copy_ang = copy_xyz_menu.addAction("Angstrom")
        copy_bohr = copy_xyz_menu.addAction("Bohr")
        copy_ang.triggered.connect(lambda: self.copy_xyz.emit("angstrom"))
        copy_bohr.triggered.connect(lambda: self.copy_xyz.emit("bohr"))
        self._copy_xyz_btn.setMenu(copy_xyz_menu)
        self._copy_xyz_btn.clicked.connect(
            lambda: self.copy_xyz.emit("angstrom"))
        xyz_actions.addWidget(self._copy_xyz_btn)

        row_3d.addLayout(xyz_actions)

        layout.addLayout(row_3d)

        outer.addStretch()

    def set_preview(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            self._preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)

    def clear_preview(self):
        self._preview.clear()
        self._preview.setText("Open an image or capture a structure")


# ======================================================================
# Bottom bar (SMILES + actions + valence)
# ======================================================================

class BottomBar(QWidget):
    copy_smiles = Signal()
    export_smiles = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottom_bar")
        self.setMinimumHeight(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(4)

        # Row 1: SMILES
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        smiles_label = QLabel("SMILES")
        smiles_label.setObjectName("smiles_label")
        row1.addWidget(smiles_label)

        self._smiles_field = QLineEdit()
        self._smiles_field.setReadOnly(True)
        self._smiles_field.setPlaceholderText("Draw or recognise a structure…")
        self._smiles_field.setObjectName("smiles_field")
        row1.addWidget(self._smiles_field, 1)  # stretch to fill

        btn_copy = QPushButton("Copy")
        btn_copy.setObjectName("small_btn")
        btn_copy.setMinimumWidth(70)
        btn_copy.clicked.connect(self.copy_smiles.emit)
        row1.addWidget(btn_copy)

        btn_export = QPushButton("Export")
        btn_export.setObjectName("small_btn_green")
        btn_export.setMinimumWidth(70)
        btn_export.clicked.connect(self.export_smiles.emit)
        row1.addWidget(btn_export)

        layout.addLayout(row1)

        # Row 2: Valence status
        self._valence_label = QLabel("Valence: —")
        self._valence_label.setObjectName("valence_label")
        layout.addWidget(self._valence_label)

    @property
    def smiles_text(self) -> str:
        return self._smiles_field.text()

    def set_smiles(self, smiles: str):
        self._smiles_field.setText(smiles)

    def set_valence_ok(self):
        self._valence_label.setText("✓  All valences OK")
        self._valence_label.setStyleSheet("color: #27ae60; font-weight: 600;")

    def set_valence_warnings(self, warnings: list):
        n = len(warnings)
        details = "; ".join(str(w) for w in warnings[:3])
        suffix = f" … (+{n - 3} more)" if n > 3 else ""
        self._valence_label.setText(f"⚠  {details}{suffix}")
        self._valence_label.setStyleSheet("color: #e74c3c; font-weight: 500;")

    def clear(self):
        self._smiles_field.clear()
        self._valence_label.setText("Valence: —")
        self._valence_label.setStyleSheet("")


# ======================================================================
# Main window
# ======================================================================

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Molecule Recognizer")
        self.setWindowIcon(workbench_icon("molecule"))
        self.resize(1400, 880)

        self._molecule: Molecule | None = None
        self._worker: RecognitionWorker | None = None
        self._source_pixmap: QPixmap | None = None
        self._mol_3d = None  # RDKit Mol with 3D conformer (for xyz export)
        self._was_maximized_before_screenshot = False
        self._screenshot_pending = False

        self._setup_ui()
        self._setup_statusbar()
        self._setup_shortcuts()
        self._setup_menu_dismissal()
        self._global_hotkey = GlobalScreenshotHotkey(self)
        self._global_hotkey.activated.connect(self._on_screenshot)
        self._ui_scale = 1.0
        self._scale_screen_name = ""
        self._scale_screen = None
        self._windows_monitor_name = ""
        self._windows_monitor_width = 0
        self._windows_monitor_height = 0
        self._fit_window_requested = False
        self._setup_ui_scaling()
        self._global_hotkey.monitor_changed.connect(
            lambda name, width, height:
                self._on_windows_monitor_detected((name, width, height)))

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_shortcuts(self):
        """Menus and shortcuts share one action, avoiding duplicate bindings."""
        bar = self._menu_bar
        if isinstance(bar, QMenuBar):
            bar.setNativeMenuBar(False)
        self._menu_actions = {}

        def action(menu, text, callback, shortcut=None, icon=None):
            item = QAction(text, self)
            if icon:
                item.setIcon(workbench_icon(icon))
            if shortcut:
                item.setShortcut(QKeySequence(shortcut))
            item.triggered.connect(lambda checked=False: callback())
            self.addAction(item)  # Shortcuts also work without native QMenus.
            menu.addAction(item)
            self._menu_actions[text] = item
            return item

        file_menu = bar.addMenu("&File")
        action(file_menu, "Open image…", self._on_open_image, "Ctrl+O", "open")
        screenshot = action(file_menu, "Capture screenshot", self._on_screenshot,
                            "Alt+Y", "capture")
        screenshot.setShortcuts([QKeySequence("Alt+Y"),
                                QKeySequence("Ctrl+Shift+S")])
        action(file_menu, "Load SMILES…", self._on_load_smiles)
        file_menu.addSeparator()
        action(file_menu, "Export SMILES…", self._on_export_smiles, "Ctrl+E")
        action(file_menu, "Save XYZ…", lambda: self._on_save_xyz("angstrom"))
        file_menu.addSeparator()
        action(file_menu, "Quit", self.close, "Ctrl+Q")

        edit_menu = bar.addMenu("&Edit")
        action(edit_menu, "Undo", self._editor._undo, "Ctrl+Z", "undo")
        action(edit_menu, "Redo", self._editor._redo, "Ctrl+Shift+Z", "redo")
        edit_menu.addSeparator()
        action(edit_menu, "Copy SMILES", self._copy_smiles)
        action(edit_menu, "Copy XYZ", lambda: self._on_copy_xyz("angstrom"))
        edit_menu.addSeparator()
        action(edit_menu, "Clear workspace", self._on_clear_all, icon="clear")

        build_menu = bar.addMenu("&Build")
        for label, key in (("Select", "select"), ("Draw bonds", "bond"),
                           ("Place atoms", "atom"), ("Erase", "eraser")):
            action(build_menu, label,
                   lambda k=key: self._editor._toolbar._activate_tool(k))
        build_menu.addSeparator()
        action(build_menu, "Periodic table…", self._editor._on_periodic_table)
        action(build_menu, "Format 2D layout", self._editor._cleanup_layout,
               icon="format")
        action(build_menu, "Render 3D structure", self._on_render_3d,
               icon="molecule")

        view_menu = bar.addMenu("&View")
        action(view_menu, "Fit structure", self._fit_structure)
        action(view_menu, "Fit window to monitor", self._request_windows_monitor_fit)
        view_menu.addSeparator()
        larger = action(view_menu, "Larger interface",
                        lambda: self._change_ui_scale(0.1), "Ctrl+Alt++")
        larger.setShortcuts([QKeySequence("Ctrl+Alt++"), QKeySequence("Ctrl+Alt+=")])
        action(view_menu, "Smaller interface", lambda: self._change_ui_scale(-0.1),
               "Ctrl+Alt+-")
        action(view_menu, "Reset interface size", self._reset_ui_scale, "Ctrl+Alt+0")

        help_menu = bar.addMenu("&Help")
        action(help_menu, "Getting started", lambda: QMessageBox.information(
            self, "Getting started",
            "1. Open an image or press Alt+Y to capture a structure.\n"
            "2. Compare the recognition with the source and edit the drawing.\n"
            "3. Copy or export SMILES, or Render 3D to save/copy XYZ.\n\n"
            "Scroll to zoom; right-drag to pan. Format generates a new 2D layout."))
        action(help_menu, "About Molecule Recognizer", lambda: QMessageBox.about(
            self, "Molecule Recognizer",
            "Molecule Recognizer\n\n"
            "Image recognition, interactive structure editing and XYZ export.\n"
            "Powered by OSRA, RDKit and Qt."))

    def _fit_structure(self):
        canvas = self._editor.canvas
        bounds = canvas.mol_scene.itemsBoundingRect()
        if not bounds.isEmpty():
            canvas.fitInView(bounds.adjusted(-40, -40, 40, 40),
                             Qt.AspectRatioMode.KeepAspectRatio)

    def _setup_menu_dismissal(self):
        # Use one deferred refresh for the entire menu tree. In WSLg the
        # underlying surface can otherwise retain a popup's last pixels.
        self._menu_refresh_timer = QTimer(self)
        self._menu_refresh_timer.setSingleShot(True)
        self._menu_refresh_timer.setInterval(150)
        self._menu_refresh_timer.timeout.connect(self._refresh_after_menu)
        if is_wsl():
            QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateMenu, False)
            QApplication.setEffectEnabled(Qt.UIEffect.UI_FadeMenu, False)
        self._popup_menus = self.findChildren(QMenu)
        for menu in self._popup_menus:
            menu.aboutToShow.connect(self._menu_refresh_timer.stop)
            menu.aboutToHide.connect(self._queue_menu_refresh)

    def _queue_menu_refresh(self):
        # Moving across menu headings briefly hides one popup before showing
        # the next. Let that handoff finish; aboutToShow cancels this cleanup.
        self._menu_refresh_timer.start()

    def _refresh_after_menu(self):
        # Wait until the entire popup chain is closed. Destroying a parent
        # menu's surface while a submenu is active can disrupt its input grab.
        if (QApplication.activePopupWidget() is not None
                or any(menu.isVisible() for menu in self._popup_menus)):
            return
        if QApplication.mouseButtons() != Qt.MouseButton.NoButton:
            self._menu_refresh_timer.start()
            return
        if is_wsl():
            for menu in self._popup_menus:
                if (not menu.isVisible()
                        and menu.testAttribute(Qt.WidgetAttribute.WA_WState_Created)):
                    # A hidden native popup may leave a cached WSLg/RDP surface
                    # behind, even outside this window. Repainting our canvas
                    # cannot erase it. Release only that popup's window-system
                    # resources; the QMenu and QActions remain alive and Qt
                    # recreates the surface on the next popup().
                    menu.destroy(True, False)
        if not self.isVisible():
            return
        # Qt owns the active menu heading. Clearing it here can interrupt a
        # hover/keyboard transition even when no popup is momentarily active.
        self.centralWidget().update()
        self._editor.canvas.viewport().update()
        self.update()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Keep the bars inside the scaled content layout. Changing native
        # QMainWindow chrome metrics while maximized has caused WSLg surface
        # configure/buffer mismatches; these are ordinary child widgets instead.
        self._menu_bar = InlineMenuBar(central) if is_wsl() else QMenuBar(central)
        outer.addWidget(self._menu_bar)

        # ---- Top area: left panel | canvas | element palette ----
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(3)
        self._splitter.setChildrenCollapsible(False)

        self._left_panel = LeftPanel()
        self._left_panel.open_image.connect(self._on_open_image)
        self._left_panel.screenshot.connect(self._on_screenshot)
        self._left_panel.load_smiles.connect(self._on_load_smiles)
        self._left_panel.render_3d.connect(self._on_render_3d)
        self._left_panel.save_xyz.connect(self._on_save_xyz)
        self._left_panel.copy_xyz.connect(self._on_copy_xyz)
        self._splitter.addWidget(self._left_panel)

        self._editor = EditorWidget()
        # Place the command toolbar above all three panels, like a desktop
        # chemistry workbench, while retaining its existing signal wiring.
        self._editor.layout().removeWidget(self._editor._toolbar)
        outer.addWidget(self._editor._toolbar)
        self._editor.molecule_changed.connect(self._on_editor_changed)
        self._editor.clear_all_requested.connect(self._on_clear_all)
        self._splitter.addWidget(self._editor)

        self._palette = ElementPalette()
        self._palette.element_selected.connect(self._on_palette_element)
        self._splitter.addWidget(self._palette)

        # Centre panel stretches; side panels don't
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        self._splitter.setSizes([290, 1060, 50])

        outer.addWidget(self._splitter, 1)

        # ---- Bottom bar ----
        self._bottom_bar = BottomBar()
        self._bottom_bar.copy_smiles.connect(self._copy_smiles)
        self._bottom_bar.export_smiles.connect(self._on_export_smiles)
        outer.addWidget(self._bottom_bar)


    def _setup_statusbar(self):
        self._status_bar = QStatusBar(self.centralWidget())
        self.centralWidget().layout().addWidget(self._status_bar)
        self._status_bar.showMessage("Ready")

    def _setup_ui_scaling(self):
        """Add per-monitor UI zoom controls and watch for screen changes."""
        self._scale_down_btn = QPushButton("A−")
        self._scale_down_btn.setObjectName("ui_scale_btn")
        self._scale_down_btn.setToolTip("Make the interface smaller (Ctrl+Alt+-)")
        self._scale_down_btn.clicked.connect(
            lambda: self._change_ui_scale(-0.1))

        self._scale_reset_btn = QPushButton("100%")
        self._scale_reset_btn.setObjectName("ui_scale_btn")
        self._scale_reset_btn.setToolTip("Reset interface size (Ctrl+Alt+0)")
        self._scale_reset_btn.clicked.connect(self._reset_ui_scale)

        self._scale_up_btn = QPushButton("A+")
        self._scale_up_btn.setObjectName("ui_scale_btn")
        self._scale_up_btn.setToolTip("Make the interface larger (Ctrl+Alt++)")
        self._scale_up_btn.clicked.connect(
            lambda: self._change_ui_scale(0.1))

        self._status_bar.addPermanentWidget(self._scale_down_btn)
        self._status_bar.addPermanentWidget(self._scale_reset_btn)
        self._status_bar.addPermanentWidget(self._scale_up_btn)
        self._fit_window_btn = QPushButton("Fit")
        self._fit_window_btn.setObjectName("ui_scale_btn")
        self._fit_window_btn.setToolTip(
            "Fit the window to the recommended size for this monitor")
        self._fit_window_btn.clicked.connect(self._request_windows_monitor_fit)
        self._status_bar.addPermanentWidget(self._fit_window_btn)
        self._status_bar.setSizeGripEnabled(False)
        QTimer.singleShot(0, self._connect_screen_scaling)

    def _connect_screen_scaling(self):
        handle = self.windowHandle()
        if handle is None:
            QTimer.singleShot(100, self._connect_screen_scaling)
            return
        if is_wsl():
            return
        handle.screenChanged.connect(self._on_scale_screen_changed)
        self._on_scale_screen_changed(handle.screen())
        self._screen_poll_timer = QTimer(self)
        self._screen_poll_timer.setInterval(300)
        self._screen_poll_timer.timeout.connect(self._poll_window_screen)
        self._screen_poll_timer.start()

    def _poll_window_screen(self):
        """Detect monitor moves when WSLg omits QWindow.screenChanged."""
        window_rect = self.frameGeometry()
        best_screen = None
        best_area = -1
        for screen in QApplication.screens():
            intersection = window_rect.intersected(screen.geometry())
            area = intersection.width() * intersection.height()
            if area > best_area:
                best_area = area
                best_screen = screen
        if (best_screen is not None and self._scale_screen is not None
                and best_screen.name() != self._scale_screen.name()):
            self._on_scale_screen_changed(best_screen)

    def _request_windows_monitor_fit(self):
        self._fit_window_requested = True
        if self._windows_monitor_name:
            self._on_windows_monitor_detected((
                self._windows_monitor_name,
                self._windows_monitor_width,
                self._windows_monitor_height,
            ))
        else:
            self._status_bar.showMessage(
                "Waiting for Windows monitor detection…", 3000)

    def _on_windows_monitor_detected(self, result):
        if result is None:
            self._status_bar.showMessage(
                "Could not detect the Windows monitor", 3000)
            return
        name, width, height = result
        first_detection = not self._windows_monitor_name
        changed = bool(self._windows_monitor_name
                       and self._windows_monitor_name != name)
        settings = QSettings()
        if changed:
            settings.setValue(
                f"window_size/windows:{self._windows_monitor_name}",
                self.size(),
            )
        self._windows_monitor_name = name
        self._windows_monitor_width = width
        self._windows_monitor_height = height
        self._scale_screen_name = f"windows:{name}"
        stored_scale = settings.value(f"ui_scale/windows:{name}")
        readability_upgrade = False
        if width >= 2500:
            scale = float(stored_scale) if stored_scale is not None else 1.8
            # Older versions could save an external monitor's narrow window
            # on the laptop. Upgrade that profile once, then respect subsequent
            # manual adjustments instead of growing the window on every move.
            readable_key = f"high_resolution_readability_v1/{name}"
            if not settings.value(readable_key, False, type=bool):
                scale = max(scale, 1.8)
                settings.setValue(f"ui_scale/windows:{name}", scale)
                settings.setValue(f"window_size/windows:{name}", QSize(
                    round(width * 0.80), round(height * 0.80)))
                settings.setValue(readable_key, True)
                readability_upgrade = True
        else:
            # A 100% UI has a ~1260×760 minimum, preventing a genuinely
            # compact window on 1080p monitors. Use 80% there so both the
            # controls and the window can become materially smaller.
            compact_key = f"external_compact_scale/{name}"
            if not settings.value(compact_key, False, type=bool):
                scale = 0.8
                settings.setValue(f"ui_scale/windows:{name}", scale)
                settings.setValue(compact_key, True)
            else:
                scale = (float(stored_scale)
                         if stored_scale is not None else 0.8)
        self._apply_ui_scale(scale)

        if (changed or self._fit_window_requested or readability_upgrade
                or (first_detection and width >= 2500)):
            # Use a compact target, but never make the frame smaller than its
            # contents. WSLg otherwise clips whole panels, then expands the
            # window unpredictably on the next drag.
            fit_fraction = 0.70 if width < 2500 else 0.80
            maximum = QSize(
                round(width * fit_fraction),
                round(height * fit_fraction),
            )
            stored_size = settings.value(
                f"window_size/windows:{name}", maximum)
            if self._fit_window_requested:
                stored_size = maximum
            if not isinstance(stored_size, QSize) or not stored_size.isValid():
                stored_size = maximum
            target = QSize(
                min(stored_size.width(), maximum.width()),
                min(stored_size.height(), maximum.height()),
            )
            target = target.expandedTo(self.minimumSizeHint())
            if not self.isMaximized() and not self.isFullScreen():
                # Only Qt may resize its WSLg surface. Resizing the outer
                # Windows msrdc HWND directly desynchronizes the frame from
                # Qt's content, clipping panels and sometimes freezing input.
                self.resize(target)
            self._status_bar.showMessage(
                f"Window fitted to {name} ({target.width()}×{target.height()})",
                3000,
            )
        self._fit_window_requested = False

    @staticmethod
    def _default_scale_for_screen(screen) -> float:
        """Compensate when WSLg hides Windows' high-DPI scale from Qt."""
        if screen is not None and screen.geometry().width() >= 2500:
            return 1.8
        return 1.0

    def _on_scale_screen_changed(self, screen):
        if screen is None:
            return
        previous_screen = self._scale_screen
        changed = (previous_screen is not None
                   and previous_screen.name() != screen.name())
        target_size = None
        if changed:
            settings = QSettings()
            settings.setValue(
                f"window_size/{previous_screen.name()}", self.size())
            available = screen.availableGeometry()
            default_size = QSize(
                round(available.width() * 0.80),
                round(available.height() * 0.80),
            )
            stored_size = settings.value(
                f"window_size/{screen.name()}", default_size)
            if not isinstance(stored_size, QSize) or not stored_size.isValid():
                stored_size = default_size
            target_size = QSize(
                min(stored_size.width(), default_size.width()),
                min(stored_size.height(), default_size.height()),
            )
        self._scale_screen = screen
        self._scale_screen_name = screen.name()
        stored = QSettings().value(f"ui_scale/{screen.name()}")
        scale = (float(stored) if stored is not None
                 else self._default_scale_for_screen(screen))
        self._apply_ui_scale(scale)
        if (target_size is not None and not self.isMaximized()
                and not self.isFullScreen()):
            self.resize(target_size)

    def _change_ui_scale(self, amount: float):
        previous = self._ui_scale
        self._apply_ui_scale(self._ui_scale + amount, save=True)
        if amount > 0 and self._ui_scale == previous:
            self._status_bar.showMessage(
                "Maximum safe size for this monitor", 3000)
        elif amount < 0 and self._ui_scale == previous:
            self._status_bar.showMessage("Minimum interface size", 3000)

    def _reset_ui_scale(self):
        if self._windows_monitor_width:
            scale = 1.8 if self._windows_monitor_width >= 2500 else 0.8
        else:
            scale = self._default_scale_for_screen(self._scale_screen)
        self._apply_ui_scale(scale, save=True)

    def _maximum_ui_scale(self) -> float:
        """Keep maximized WSLg windows within the monitor's configured size."""
        if self._windows_monitor_width:
            width = self._windows_monitor_width
        else:
            handle = self.windowHandle()
            screen = handle.screen() if handle is not None else None
            width = (screen.availableGeometry().width()
                     if screen is not None else 1920)
        if width <= 2000:
            return 1.3
        if width <= 2560:
            return 1.6
        return 2.0

    def _apply_ui_scale(self, scale: float, save: bool = False):
        scale = round(max(0.8, min(self._maximum_ui_scale(), scale)), 1)
        if scale == self._ui_scale:
            if save and self._scale_screen_name:
                QSettings().setValue(
                    f"ui_scale/{self._scale_screen_name}", scale)
            return
        self._ui_scale = scale
        self.setMinimumSize(0, 0)

        app = QApplication.instance()
        base_css = getattr(app, "_base_stylesheet", app.styleSheet())
        scaled_css = re.sub(
            r"(?<![\w.])(\d+(?:\.\d+)?)px",
            lambda match: f"{max(1, round(float(match.group(1)) * scale))}px",
            base_css,
        )
        # Do not replace QApplication's stylesheet while a maximized WSLg
        # window is visible. Changing status-bar metrics can make Qt submit a
        # buffer with a different height before Wayland sends a new configure,
        # which is a fatal xdg_surface protocol error. Scale only the central
        # content, which now also contains the menu and status bars.
        self.centralWidget().setStyleSheet(scaled_css)

        base_font = getattr(app, "_base_font", app.font())
        font = QFont(base_font)
        font.setPointSizeF(base_font.pointSizeF() * scale)
        self.centralWidget().setFont(font)

        self._left_panel.setMinimumWidth(round(280 * scale))
        self._left_panel.setMaximumWidth(round(350 * scale))
        self._left_panel._preview.setFixedHeight(round(150 * scale))
        self._left_panel._viewer_3d.setFixedHeight(round(120 * scale))
        self._palette.setMinimumWidth(round(52 * scale))
        self._palette.setMaximumWidth(round(80 * scale))
        self._palette.apply_scale(scale)
        self._editor._toolbar.setMinimumHeight(round(46 * scale))
        for button in self._editor._toolbar.findChildren(QToolButton):
            button.setIconSize(QSize(round(20 * scale), round(20 * scale)))
        self._bottom_bar.setMinimumHeight(round(80 * scale))
        self._splitter.setHandleWidth(max(3, round(3 * scale)))
        self._scale_reset_btn.setText(f"{round(scale * 100)}%")

        if save and self._scale_screen_name:
            QSettings().setValue(
                f"ui_scale/{self._scale_screen_name}", scale)
        if self.centralWidget().layout() is not None:
            self.centralWidget().layout().activate()

    # ------------------------------------------------------------------
    # Element palette → editor
    # ------------------------------------------------------------------

    def _on_palette_element(self, element: str):
        self._editor.set_element(element)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Molecule Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)",
        )
        if path:
            self._source_pixmap = QPixmap(path)
            self._left_panel.set_preview(self._source_pixmap)
            img = Image.open(path)
            self._recognize_image(img)

    def _on_screenshot(self):
        # A focused WSL window can receive both Qt's shortcut and Windows'
        # registered hotkey for the same keypress.
        if self._screenshot_pending:
            return
        self._screenshot_pending = True
        self._status_bar.showMessage("Capturing screen…")
        self._was_maximized_before_screenshot = self.isMaximized()
        self.hide()
        QApplication.processEvents()
        QTimer.singleShot(300, self._do_screenshot)

    def _do_screenshot(self):
        screenshot = grab_screen()

        if screenshot is None or screenshot.isNull():
            self._restore_after_screenshot()
            self._status_bar.showMessage("Screenshot failed", 5000)
            return

        # Show the dialog BEFORE restoring the main window so the dialog
        # is the focused window.  Restore the main window only AFTER the
        # dialog closes to avoid WSLg hide/show ordering issues.
        dlg = ScreenshotDialog(screenshot)  # no parent — independent window
        result = dlg.exec()

        # Always restore main window after dialog closes
        self._restore_after_screenshot()

        if result == QDialog.DialogCode.Accepted and dlg.result_pixmap:
            self._source_pixmap = dlg.result_pixmap
            self._left_panel.set_preview(self._source_pixmap)
            try:
                png_data = pixmap_to_png_bytes(dlg.result_pixmap)
                img = Image.open(io.BytesIO(png_data))
                img.load()
                self._recognize_image(img)
            except Exception as e:
                self._status_bar.showMessage(f"Screenshot error: {e}", 5000)
        else:
            self._status_bar.showMessage("Screenshot cancelled", 3000)

    def _restore_after_screenshot(self):
        """Restore the window without losing its pre-capture state."""
        if self._was_maximized_before_screenshot:
            self.showMaximized()
        else:
            self.showNormal()
        self.raise_()
        self.activateWindow()
        self.unsetCursor()
        QApplication.processEvents()
        self._screenshot_pending = False
        QTimer.singleShot(0, self._refresh_display)
        QTimer.singleShot(150, self._refresh_display)

    def _on_load_smiles(self):
        smiles, ok = QInputDialog.getText(
            self, "Load SMILES", "Enter SMILES string:"
        )
        if ok and smiles.strip():
            try:
                mol = smiles_to_molecule(smiles.strip())
                self._set_molecule(mol)
                self._status_bar.showMessage("Loaded from SMILES", 3000)
            except ValueError as e:
                QMessageBox.warning(self, "Invalid SMILES", str(e))

    def _on_export_smiles(self):
        if self._molecule is None:
            self._status_bar.showMessage("No molecule to export", 3000)
            return
        smiles = self._bottom_bar.smiles_text
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SMILES", "molecule.smi",
            "SMILES Files (*.smi);;Text Files (*.txt);;All Files (*)",
        )
        if path:
            with open(path, "w") as f:
                f.write(smiles + "\n")
            self._status_bar.showMessage(f"Exported to {path}", 3000)

    def _copy_smiles(self):
        text = self._bottom_bar.smiles_text
        if text:
            QApplication.clipboard().setText(text)
            self._status_bar.showMessage("SMILES copied to clipboard", 3000)

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------

    def _recognize_image(self, img: Image.Image):
        if self._worker is not None and self._worker.isRunning():
            self._status_bar.showMessage("Recognition already in progress…")
            return
        self._status_bar.showMessage("Starting recognition…")
        self._worker = RecognitionWorker(img, parent=self)
        self._worker.status.connect(
            lambda msg: self._status_bar.showMessage(msg)
        )
        self._worker.result_ready.connect(self._on_recognition_done)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_recognition_done(self, result):
        if isinstance(result, Exception):
            self._status_bar.showMessage("Recognition failed", 5000)
            QMessageBox.critical(
                self, "Recognition Error",
                f"Failed to recognize structure:\n{result}",
            )
            return
        self._set_molecule(result)
        self._status_bar.showMessage("Structure recognized", 3000)

    def _on_worker_finished(self):
        """Release the completed worker after its result has been delivered."""
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    # ------------------------------------------------------------------
    # Molecule state
    # ------------------------------------------------------------------

    def _set_molecule(self, mol: Molecule):
        self._molecule = mol
        self._editor.load_molecule(mol)
        self._update_info()
        # WSLg can miss the first paint request after a hidden maximized
        # window is restored. A deferred refresh runs after the queued
        # recognition result and window-exposure events have settled.
        QTimer.singleShot(0, self._refresh_display)
        QTimer.singleShot(150, self._refresh_display)

    def _refresh_display(self):
        """Force WSLg/Qt to paint newly loaded recognition results."""
        central = self.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().activate()
        canvas = self._editor.canvas
        canvas.mol_scene.update()
        canvas.viewport().update()
        canvas.viewport().repaint()
        self._editor.update()
        self._bottom_bar.update()
        self.update()

    def _on_editor_changed(self):
        self._molecule = self._editor.molecule
        self._update_info()

    def _on_clear_all(self):
        """Clear the canvas, loaded images, 3D viewer, and SMILES."""
        self._molecule = None
        self._mol_3d = None
        self._source_pixmap = None
        self._editor.load_molecule(Molecule())
        self._left_panel.clear_preview()
        self._left_panel._viewer_3d.clear()
        self._bottom_bar.clear()
        self._status_bar.showMessage("Canvas cleared", 3000)

    def _update_info(self):
        if self._molecule is None:
            self._bottom_bar.clear()
            return
        # SMILES
        try:
            smiles = molecule_to_smiles(self._molecule)
            self._bottom_bar.set_smiles(smiles)
        except Exception:
            self._bottom_bar.set_smiles("[Error generating SMILES]")
        # Valence
        warnings = check_valence(self._molecule)
        if warnings:
            self._bottom_bar.set_valence_warnings(warnings)
        else:
            self._bottom_bar.set_valence_ok()

    # ------------------------------------------------------------------
    # 3D rendering / XYZ export
    # ------------------------------------------------------------------

    def _on_render_3d(self):
        if self._molecule is None or self._molecule.num_atoms == 0:
            self._status_bar.showMessage("No molecule to render", 3000)
            return
        try:
            smiles = molecule_to_smiles(self._molecule)
        except Exception:
            self._status_bar.showMessage("Cannot generate SMILES for 3D", 3000)
            return
        try:
            from ..core.xyz import generate_3d, mol_to_atoms_bonds
            self._mol_3d = generate_3d(smiles)
            atoms, bonds = mol_to_atoms_bonds(self._mol_3d)
            self._left_panel._viewer_3d.set_molecule(atoms, bonds)
            self._status_bar.showMessage("3D structure rendered", 3000)
        except Exception as e:
            self._status_bar.showMessage(f"3D generation failed: {e}", 5000)

    def _on_save_xyz(self, unit: str):
        if self._mol_3d is None:
            self._status_bar.showMessage(
                "Render 3D first before saving xyz", 3000)
            return
        default_name = "molecule.xyz"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save XYZ", default_name,
            "XYZ Files (*.xyz);;All Files (*)",
        )
        if path:
            try:
                from ..core.xyz import mol_to_xyz_string
                xyz_str = mol_to_xyz_string(self._mol_3d, unit=unit)
                with open(path, "w") as f:
                    f.write(xyz_str)
                self._status_bar.showMessage(
                    f"Saved xyz ({unit}) to {path}", 3000)
            except Exception as e:
                self._status_bar.showMessage(f"Save failed: {e}", 5000)

    def _on_copy_xyz(self, unit: str):
        if self._mol_3d is None:
            self._status_bar.showMessage(
                "Render 3D first before copying xyz", 3000)
            return
        try:
            from ..core.xyz import mol_to_xyz_string
            xyz_text = mol_to_xyz_string(self._mol_3d, unit=unit)
            QApplication.clipboard().setText(xyz_text)
            self._status_bar.showMessage(
                f"XYZ structure copied ({unit})", 3000)
        except Exception as e:
            self._status_bar.showMessage(f"Copy failed: {e}", 5000)

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        QSettings().setValue("main_window/normal_geometry", geometry)
        if self._scale_screen is not None and not self.isMaximized():
            QSettings().setValue(
                f"window_size/{self._scale_screen.name()}", self.size())
        if self._windows_monitor_name and not self.isMaximized():
            QSettings().setValue(
                f"window_size/windows:{self._windows_monitor_name}",
                self.size(),
            )
        if self._worker is not None and self._worker.isRunning():
            self._worker.finished.disconnect()
            self._worker.quit()
            self._worker.wait(5000)
        event.accept()
