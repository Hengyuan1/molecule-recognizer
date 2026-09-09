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
import logging
import os
import re
import sys

from PIL import Image
from PySide6.QtCore import QSettings, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QFont, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
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
from .viewer3d import Viewer3DPanel, Viewer3DWidget
from .workbench_icons import workbench_icon
from .app_icon import application_icon
from .inline_menu import InlineMenuBar
from .native_capture import NativeRegionCapture, native_capture_executable
from .workers import RecognitionWorker, RecognitionRetryWorker, Render3DWorker
from .recognition_review import RecognitionReviewDialog
from .window_placement import OwnerDialog
from .screen_layout import fitted_geometry, recommended_scale, recommended_size, screen_signature

_logger = logging.getLogger(__name__)

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
    retry_recognition = Signal()
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
        image_actions = QHBoxLayout()
        image_actions.addWidget(btn_open)
        layout.addLayout(image_actions)

        btn_screen = QPushButton("Screenshot")
        btn_screen.setObjectName("action_btn")
        btn_screen.setToolTip("Capture a structure from your screen (Alt+Y)")
        btn_screen.clicked.connect(self.screenshot.emit)
        layout.addWidget(btn_screen)

        btn_smiles = QPushButton("Load SMILES")
        btn_smiles.setObjectName("action_btn_secondary")
        btn_smiles.clicked.connect(self.load_smiles.emit)
        image_actions.addWidget(btn_smiles)

        self._retry_btn = QPushButton("Retry recognition")
        self._retry_btn.setObjectName("action_btn_secondary")
        self._retry_btn.setToolTip("Compare alternative OSRA results for the full-resolution source image")
        self._retry_btn.setEnabled(False)
        self._retry_btn.clicked.connect(self.retry_recognition.emit)
        layout.addWidget(self._retry_btn)

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

        self._viewer_3d = Viewer3DWidget(expand_in_place=True)
        self._viewer_3d.setToolTip('Double-click to compare the 3D structure beside the 2D canvas')
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
        self.setWindowIcon(application_icon())
        self.resize(1400, 880)

        self._molecule: Molecule | None = None
        self._worker: RecognitionWorker | None = None
        self._retry_worker: RecognitionRetryWorker | None = None
        self._retry_dialog: RecognitionReviewDialog | None = None
        self._recognition_image: Image.Image | None = None
        self._render_worker: Render3DWorker | None = None
        self._render_smiles = ""
        self._rendered_smiles = None  # Identity of the last successful render.
        self._comparison_sizes = None
        self._closing = False
        self._source_pixmap: QPixmap | None = None
        self._mol_3d = None  # RDKit Mol with 3D conformer (for xyz export)
        self._was_maximized_before_screenshot = False
        self._screenshot_pending = False
        self._native_capture = None
        self._capture_dialog = None
        self._capture_timer = QTimer(self)
        self._capture_timer.setSingleShot(True)
        self._capture_timer.setInterval(300)
        self._capture_timer.timeout.connect(self._do_screenshot)

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
        self._native_screen_signature = None
        self._native_last_normal_size = None
        self._native_geometry_busy = False
        self._native_fitting = False
        self._native_fit_timer = QTimer(self)
        self._native_fit_timer.setSingleShot(True)
        self._native_fit_timer.setInterval(180)
        self._native_fit_timer.timeout.connect(self._fit_native_monitor)
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
        action(file_menu, "Retry recognition…", self._on_retry_recognition).setEnabled(False)
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
            "Powered by OSRA, RDKit and Qt (LGPLv3).\n"
            "OSRA includes CImg image processing, copyright David Tschumperlé,\n"
            "under CeCILL-C. See Help → Third-party licenses for notices."))
        action(help_menu, "Third-party licenses…", self._open_third_party_licenses)

    def _open_third_party_licenses(self):
        from ..runtime import application_directory
        root = application_directory()
        directory = root / "licenses"
        if directory.is_dir() and QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory))):
            return
        QMessageBox.information(
            self, "Third-party licenses",
            "MolRecognizer's code is MIT-licensed. Dependencies retain their own licenses.\n\n"
            "Qt/PySide uses LGPLv3. OSRA includes CImg image processing, copyright "
            "David Tschumperlé, under CeCILL-C. RDKit, NumPy and Pillow retain "
            "their original third-party notices.\n\n"
            "Portable builds include a licenses folder and SOURCE-ACCESS.md beside the EXE. "
            "For a source installation, consult the installed packages' license files and "
            "packaging/windows/THIRD-PARTY-NOTICES.md in the project source.")

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
        if not self._closing:
            self._menu_refresh_timer.start()

    def _refresh_after_menu(self):
        if self._closing:
            return
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
        self._left_panel.retry_recognition.connect(self._on_retry_recognition)
        self._left_panel.load_smiles.connect(self._on_load_smiles)
        self._left_panel.render_3d.connect(self._on_render_3d)
        self._left_panel.save_xyz.connect(self._on_save_xyz)
        self._left_panel.copy_xyz.connect(self._on_copy_xyz)
        self._left_panel._viewer_3d.expand_requested.connect(self._show_3d_comparison)
        self._splitter.addWidget(self._left_panel)

        self._editor = EditorWidget()
        # Place the command toolbar above all three panels, like a desktop
        # chemistry workbench, while retaining its existing signal wiring.
        self._editor.layout().removeWidget(self._editor._toolbar)
        outer.addWidget(self._editor._toolbar)
        self._editor.molecule_changed.connect(self._on_editor_changed)
        self._editor.clear_all_requested.connect(self._on_clear_all)
        self._comparison_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._comparison_splitter.setChildrenCollapsible(False)
        self._comparison_splitter.setHandleWidth(6)
        self._comparison_splitter.addWidget(self._editor)
        self._comparison_panel = Viewer3DPanel()
        self._comparison_panel.close_requested.connect(self._hide_3d_comparison)
        self._comparison_splitter.addWidget(self._comparison_panel)
        self._comparison_splitter.setStretchFactor(0, 1)
        self._comparison_splitter.setStretchFactor(1, 1)
        self._comparison_panel.hide()
        self._splitter.addWidget(self._comparison_splitter)

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
        if self._closing:
            return
        handle = self.windowHandle()
        if handle is None:
            QTimer.singleShot(100, self._connect_screen_scaling)
            return
        if is_wsl():
            return
        if self._native_windows_layout():
            handle.screenChanged.connect(self._schedule_native_fit)
            self._schedule_native_fit()
        else:
            handle.screenChanged.connect(self._on_scale_screen_changed)
            self._on_scale_screen_changed(handle.screen())
        self._screen_poll_timer = QTimer(self)
        self._screen_poll_timer.setInterval(300)
        self._screen_poll_timer.timeout.connect(self._poll_window_screen)
        self._screen_poll_timer.start()

    def _poll_window_screen(self):
        """Detect monitor moves when WSLg omits QWindow.screenChanged."""
        if self._closing:
            return
        if self._native_windows_layout():
            # QWindow.screen() uses Windows' native monitor selection. Comparing
            # rectangles across mixed-DPI Qt "screen islands" can pick the
            # wrong monitor and cause repeated resize/move oscillations.
            screen = self.screen()
            if screen is not None:
                if screen_signature(screen) != self._native_screen_signature:
                    if not self._native_fit_timer.isActive():
                        self._schedule_native_fit()
                elif not self._native_geometry_busy and not self.isMaximized() and not self.isFullScreen():
                    self._native_last_normal_size = self.size()
            return
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
        if self._native_windows_layout() and not self._windows_monitor_name:
            self._schedule_native_fit()
            return
        if self._windows_monitor_name:
            self._on_windows_monitor_detected((
                self._windows_monitor_name,
                self._windows_monitor_width,
                self._windows_monitor_height,
            ))
        else:
            self._status_bar.showMessage(
                "Waiting for Windows monitor detection…", 3000)

    def _native_windows_layout(self):
        return sys.platform == "win32" and not is_wsl()

    def nativeEvent(self, event_type, message):  # noqa: N802
        # Observe the native drag lifecycle only. Let Windows/Qt handle every
        # cursor, mouse grab and resize; never move a HWND from this callback.
        if sys.platform == "win32" and bytes(event_type) == b"windows_generic_MSG":
            import ctypes
            from ctypes import wintypes
            event = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents.message
            if event == 0x0231:  # WM_ENTERSIZEMOVE
                self._native_geometry_busy = True
                self._native_last_normal_size = self.size()
            elif event == 0x0232:  # WM_EXITSIZEMOVE
                self._native_geometry_busy = False
                if hasattr(self, "_native_fit_timer"):
                    self._schedule_native_fit()
        return super().nativeEvent(event_type, message)

    def _schedule_native_fit(self, *_):
        if not self._closing and not self._native_fitting:
            self._native_fit_timer.start()

    def _fit_native_monitor(self):
        if self._closing or self._native_geometry_busy or self._native_fitting:
            return
        screen = self.screen()
        if screen is None:
            return
        signature = screen_signature(screen)
        if signature == self._native_screen_signature and not self._fit_window_requested:
            return  # A manual resize on the same monitor must stay manual.
        settings = QSettings()
        if (self._scale_screen_name and self._scale_screen_name != screen.name()
                and self._native_last_normal_size is not None):
            settings.setValue(f"window_size/{self._scale_screen_name}", self._native_last_normal_size)
        self._native_fitting = True
        try:
            self._scale_screen = screen
            self._scale_screen_name = screen.name()
            stored = settings.value(f"ui_scale/{screen.name()}")
            try:
                scale = float(stored) if stored is not None else recommended_scale(screen)
            except (TypeError, ValueError):
                scale = recommended_scale(screen)
            self._apply_ui_scale(scale)
            available = screen.availableGeometry()
            margins = self.windowHandle().frameMargins()
            client_area = available.marginsRemoved(margins)
            # Layout minimums, not width alone, determine the safe scale. This
            # includes the menu/status bars and a short high-DPI work area.
            while (self._ui_scale > self._minimum_ui_scale()
                   and (self.minimumSizeHint().width() > client_area.width()
                        or self.minimumSizeHint().height() > client_area.height())):
                self._apply_ui_scale(self._ui_scale - 0.1)
            default = recommended_size(screen)
            desired = settings.value(f"window_size/{screen.name()}", default)
            if self._fit_window_requested or not isinstance(desired, QSize) or not desired.isValid():
                desired = default
            desired = desired.boundedTo(default)
            if not self.isMaximized() and not self.isFullScreen():
                target = fitted_geometry(self.geometry(), desired, self.minimumSizeHint(), available, margins)
                self.setGeometry(target)
                self._native_last_normal_size = self.size()
            self._native_screen_signature = signature
            self._fit_window_requested = False
            self._status_bar.showMessage(f"Window fitted to {screen.name()}", 3000)
            # AnchorUnderMouse can otherwise leave the molecule outside the
            # viewport after a large DPI-driven resize. This changes only the
            # view, never the coordinates or chemistry.
            QTimer.singleShot(0, self._fit_structure)
        finally:
            self._native_fitting = False

    def _on_windows_monitor_detected(self, result):
        if self._closing:
            return
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
        if sys.platform == "win32" and not is_wsl() and screen is not None:
            return recommended_scale(screen)
        if screen is not None and screen.geometry().width() >= 2500:
            return 1.8
        return 1.0

    def _on_scale_screen_changed(self, screen):
        if self._closing:
            return
        if screen is None:
            return
        if self._native_windows_layout():
            self._schedule_native_fit()
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
        geometry = self.geometry()
        self._apply_ui_scale(self._ui_scale + amount, save=True)
        if self._native_windows_layout() and self.screen() is not None:
            available = self.screen().availableGeometry()
            margins = self.windowHandle().frameMargins()
            room = available.marginsRemoved(margins).size()
            minimum = self.minimumSizeHint()
            if amount > 0 and (minimum.width() > room.width() or minimum.height() > room.height()):
                self._apply_ui_scale(previous, save=True)
            if not self.isMaximized() and not self.isFullScreen():
                self.setGeometry(fitted_geometry(geometry, geometry.size(), self.minimumSizeHint(),
                                                 available, margins))
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
        if self._native_windows_layout():
            self._request_windows_monitor_fit()

    def _minimum_ui_scale(self):
        # 60% on a 250%-scaled panel is still 150% in physical pixels. The
        # old universal 80% floor prevented fitting short logical work areas.
        if (self._native_windows_layout() and not self._windows_monitor_width
                and self.screen() is not None and self.screen().devicePixelRatio() >= 1.5):
            return 0.6
        return 0.8

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
        scale = round(max(self._minimum_ui_scale(), min(self._maximum_ui_scale(), scale)), 1)
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

        if self._native_windows_layout() and not self._windows_monitor_width:
            # Keep sidebar whitespace proportional too; fixed margins alone
            # used up much of the laptop's short logical work area.
            for layout in self._left_panel.findChildren(QLayout):
                if not hasattr(layout, "_base_metrics"):
                    m = layout.contentsMargins()
                    layout._base_metrics = ((m.left(), m.top(), m.right(), m.bottom()), layout.spacing())
                margins, spacing = layout._base_metrics
                layout.setContentsMargins(*(round(value * scale) for value in margins))
                if spacing >= 0:
                    layout.setSpacing(round(spacing * scale))
            for button in self._left_panel.findChildren(QPushButton):
                button.setIconSize(QSize(round(16 * scale), round(16 * scale)))

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
        self._comparison_splitter.setHandleWidth(max(5, round(6 * scale)))
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
        if self._closing or self._retry_dialog is not None or self._retry_worker is not None:
            return
        if self._worker is not None:
            self._status_bar.showMessage("Recognition already in progress…", 3000)
            return
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
        if (self._closing or self._screenshot_pending
                or self._retry_dialog is not None or self._retry_worker is not None):
            return
        if any(dialog.isVisible() for dialog in self.findChildren(OwnerDialog)):
            return  # The global Windows hotkey bypasses Qt's shortcut guard.
        if self._worker is not None:
            self._status_bar.showMessage("Recognition already in progress…", 3000)
            return
        self._screenshot_pending = True
        self._update_retry_available()
        self._status_bar.showMessage("Capturing screen…")
        self._was_maximized_before_screenshot = self.isMaximized()
        self.hide()
        QApplication.processEvents()
        if not self._closing:
            self._capture_timer.start()

    def _do_screenshot(self):
        if self._closing:
            return
        executable = native_capture_executable()
        if executable:
            self._native_capture = NativeRegionCapture(executable, self)
            self._native_capture.completed.connect(
                self._on_native_capture_completed, Qt.ConnectionType.QueuedConnection)
            self._native_capture.stopped.connect(self._finish_shutdown)
            self._native_capture.start()
            return
        screenshot = grab_screen()

        if screenshot is None or screenshot.isNull():
            self._restore_after_screenshot()
            self._status_bar.showMessage("Screenshot failed", 5000)
            return

        # Show the dialog BEFORE restoring the main window so the dialog
        # is the focused window.  Restore the main window only AFTER the
        # dialog closes to avoid WSLg hide/show ordering issues.
        dlg = ScreenshotDialog(screenshot)  # no parent — independent window
        self._capture_dialog = dlg
        result = dlg.exec()
        crop = dlg.result_pixmap
        self._capture_dialog = None
        dlg.deleteLater()
        if self._closing:
            return

        # Always restore main window after dialog closes
        self._restore_after_screenshot()
        if self._closing:
            return

        if result == QDialog.DialogCode.Accepted and crop:
            self._recognize_capture(crop)
        else:
            self._status_bar.showMessage("Screenshot cancelled", 3000)

    def _on_native_capture_completed(self, png, error):
        capture, self._native_capture = self._native_capture, None
        if capture is not None:
            capture.deleteLater()
        if self._closing:
            self._finish_shutdown()
            return
        self._restore_after_screenshot()
        if self._closing:
            return
        if error:
            QMessageBox.warning(self, "Screen capture", error)
            self._status_bar.showMessage("Screenshot failed", 5000)
        elif not png:
            self._status_bar.showMessage("Screenshot cancelled", 3000)
        else:
            pixmap = QPixmap()
            if pixmap.loadFromData(png, "PNG"):
                self._recognize_capture(pixmap)
            else:
                self._status_bar.showMessage("Invalid screenshot image", 5000)

    def _recognize_capture(self, pixmap):
        if (self._closing or self._worker is not None
                or self._retry_dialog is not None or self._retry_worker is not None):
            return
        self._source_pixmap = pixmap
        self._left_panel.set_preview(pixmap)
        try:
            img = Image.open(io.BytesIO(pixmap_to_png_bytes(pixmap)))
            img.load()
            self._recognize_image(img)
        except Exception as error:
            self._status_bar.showMessage(f"Screenshot error: {error}", 5000)

    def _restore_after_screenshot(self):
        """Restore the window without losing its pre-capture state."""
        if self._closing:
            return
        if self._was_maximized_before_screenshot:
            self.showMaximized()
        else:
            self.showNormal()
        self.raise_()
        self.activateWindow()
        self.unsetCursor()
        QApplication.processEvents()
        if self._closing:
            return
        self._screenshot_pending = False
        self._update_retry_available()
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
        if self._closing:
            return
        if (self._worker is not None or self._retry_worker is not None
                or self._retry_dialog is not None):
            self._status_bar.showMessage("Recognition already in progress…")
            return
        # Keep the actual recognition input, not the scaled sidebar thumbnail.
        self._recognition_image = img.copy()
        self._status_bar.showMessage("Starting recognition…")
        self._worker = RecognitionWorker(img, parent=self)
        self._worker.status.connect(self._on_worker_status)
        self._worker.result_ready.connect(self._on_recognition_done)
        self._worker.finished.connect(self._on_worker_finished)
        self._update_retry_available()
        self._worker.start()

    def _on_recognition_done(self, result):
        if self._closing:
            return
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
        worker = self.sender()
        if worker is self._worker:
            self._worker = None
        if worker is not None:
            worker.deleteLater()
        self._update_retry_available()
        self._finish_shutdown()

    def _on_worker_status(self, message):
        if not self._closing:
            self._status_bar.showMessage(message)

    def _update_retry_available(self):
        enabled = (self._recognition_image is not None and not self._closing
                   and self._worker is None and self._retry_worker is None
                   and self._retry_dialog is None and not self._screenshot_pending)
        self._left_panel._retry_btn.setEnabled(enabled)
        self._menu_actions["Retry recognition…"].setEnabled(enabled)

    def _on_retry_recognition(self):
        if (self._closing or self._recognition_image is None or self._worker is not None
                or self._retry_worker is not None or self._retry_dialog is not None
                or self._screenshot_pending):
            return
        # Recreate the preview from the same input used for these retries, even
        # if the sidebar was subsequently refreshed by a rejected capture.
        stream = io.BytesIO()
        self._recognition_image.save(stream, format="PNG")
        source = QPixmap()
        source.loadFromData(stream.getvalue(), "PNG")
        dialog = RecognitionReviewDialog(source, self._molecule, self)
        self._retry_dialog = dialog
        dialog.stop_requested.connect(self._cancel_retry)
        dialog.finished.connect(self._on_retry_review_finished)
        worker = RecognitionRetryWorker(self._recognition_image.copy(), self)
        self._retry_worker = worker
        worker.candidate_ready.connect(self._on_retry_candidate)
        worker.status.connect(self._on_retry_status)
        worker.failed.connect(self._on_retry_failed)
        worker.finished.connect(self._on_retry_worker_finished)
        self._update_retry_available()
        dialog.open()  # No nested event loop; closing/cancellation stays responsive.
        worker.start()

    def _cancel_retry(self):
        if self._retry_worker is not None:
            self._retry_worker.cancel()

    def _on_retry_candidate(self, candidate):
        if not self._closing and self._retry_dialog is not None:
            self._retry_dialog.add_candidate(candidate)

    def _on_retry_status(self, message):
        if not self._closing and self._retry_dialog is not None:
            self._retry_dialog.set_status(message)

    def _on_retry_failed(self, message):
        if not self._closing and self._retry_dialog is not None:
            self._retry_dialog.set_failure(message)

    def _on_retry_worker_finished(self):
        worker = self.sender()
        if worker is self._retry_worker:
            self._retry_worker = None
            if not self._closing and self._retry_dialog is not None:
                self._retry_dialog.finish(worker.cancelled)
        if worker is not None:
            worker.deleteLater()
        self._update_retry_available()
        self._finish_shutdown()

    def _on_retry_review_finished(self, result):
        dialog, self._retry_dialog = self._retry_dialog, None
        self._cancel_retry()
        if dialog is None:
            return
        candidate = dialog.selected_candidate
        dialog.deleteLater()
        if not self._closing and result == QDialog.DialogCode.Accepted and candidate is not None:
            from ..editor.history import ReplaceMoleculeCommand
            # Old selections and drag/ghost items reference the previous graph.
            # Clear them while its scene items are still alive.
            if self._editor._current_tool is not None:
                self._editor._current_tool.deactivate()
            self._editor._history.execute(ReplaceMoleculeCommand(candidate.molecule))
            self._editor._rebuild_tools()
            if self._render_worker is not None:
                self._render_worker.cancel()
            self._mol_3d = None
            self._rendered_smiles = None
            self._left_panel._viewer_3d.clear()
            self._comparison_panel._viewer.clear()
            self._hide_3d_comparison()
            self._fit_structure()
            self._status_bar.showMessage(f"Applied {candidate.name}; Undo restores the previous structure", 5000)
        # Refresh after the review panel has hidden and the new scene has been
        # applied. This does not remap, resize or recreate the main surface.
        QTimer.singleShot(0, self._refresh_display)
        self._update_retry_available()

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
        if self._closing:
            return
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
        self._update_comparison_status()

    def _on_clear_all(self):
        """Clear the canvas, loaded images, 3D viewer, and SMILES."""
        if self._retry_dialog is not None:
            self._retry_dialog.reject()
        self._cancel_retry()
        self._recognition_image = None
        self._update_retry_available()
        if self._render_worker is not None:
            self._render_worker.cancel()
        self._molecule = None
        self._mol_3d = None
        self._rendered_smiles = None
        self._source_pixmap = None
        self._editor.load_molecule(Molecule())
        self._left_panel.clear_preview()
        self._left_panel._viewer_3d.clear()
        self._comparison_panel._viewer.clear()
        self._hide_3d_comparison()
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

    def _show_3d_comparison(self):
        source = self._left_panel._viewer_3d
        if self._closing or not source._atoms or self._retry_dialog is not None:
            return
        if not self._comparison_panel.isVisible():
            self._comparison_panel.copy_from(source)
            self._comparison_panel.show()
            half = max(1, (self._comparison_splitter.width()
                           - self._comparison_splitter.handleWidth()) // 2)
            self._comparison_splitter.setSizes(self._comparison_sizes or [half, half])
            self._update_comparison_status()
            # Fit the drawing to its narrower view, without changing atom
            # coordinates, stereo or the top-level window's geometry.
            QTimer.singleShot(0, self._fit_structure)
        self._comparison_panel._viewer.setFocus()

    def _hide_3d_comparison(self):
        if not self._comparison_panel.isHidden():
            self._comparison_sizes = self._comparison_splitter.sizes()
            self._comparison_panel.hide()
            if not self._closing:
                self._editor.canvas.setFocus()
                QTimer.singleShot(0, self._fit_structure)

    def _update_comparison_status(self):
        if self._comparison_panel.isHidden():
            return
        # _update_info already computed this; avoid another chemical conversion
        # on every mouse move while editing a large molecule.
        current = self._bottom_bar.smiles_text
        self._comparison_panel.set_stale(
            self._rendered_smiles is not None and current != self._rendered_smiles)

    def _on_render_3d(self):
        if self._closing:
            return
        if self._render_worker is not None:
            self._status_bar.showMessage("3D generation already in progress…", 3000)
            return
        if self._molecule is None or self._molecule.num_atoms == 0:
            self._status_bar.showMessage("No molecule to render", 3000)
            return
        try:
            smiles = molecule_to_smiles(self._molecule)
        except Exception:
            self._status_bar.showMessage("Cannot generate SMILES for 3D", 3000)
            return
        self._render_smiles = smiles
        self._render_worker = Render3DWorker(smiles, self)
        self._render_worker.result_ready.connect(self._on_render_done)
        self._render_worker.finished.connect(self._on_render_worker_finished)
        self._status_bar.showMessage("Generating 3D structure…")
        self._render_worker.start()

    def _on_render_done(self, result):
        if self._closing:
            return
        try:
            if (self._molecule is None
                    or molecule_to_smiles(self._molecule) != self._render_smiles):
                self._status_bar.showMessage("Structure changed; render 3D again", 3000)
                return
            if isinstance(result, Exception):
                raise result
            from ..core.xyz import mol_to_atoms_bonds
            atoms, bonds = mol_to_atoms_bonds(result)
            self._left_panel._viewer_3d.set_molecule(atoms, bonds)
            self._mol_3d = result
            self._rendered_smiles = self._render_smiles
            if not self._comparison_panel.isHidden():
                self._comparison_panel.copy_from(self._left_panel._viewer_3d)
                self._update_comparison_status()
            self._status_bar.showMessage("3D structure rendered", 3000)
        except Exception as e:
            self._status_bar.showMessage(f"3D generation failed: {e}", 5000)

    def _on_render_worker_finished(self):
        worker = self.sender()
        if worker is self._render_worker:
            self._render_worker = None
        if worker is not None:
            worker.deleteLater()
        self._finish_shutdown()

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
        if not self._closing:
            _logger.info("Window close requested (recognition=%s, render=%s, capture=%s)",
                         self._worker is not None, self._render_worker is not None,
                         self._native_capture is not None)
            self._closing = True
            self._capture_timer.stop()
            self._native_fit_timer.stop()
            self._menu_refresh_timer.stop()
            if hasattr(self, "_screen_poll_timer"):
                self._screen_poll_timer.stop()
            # A cached QScreen may already be deleted after a monitor change.
            # Saving preferences must never prevent an otherwise idle close.
            try:
                settings = QSettings()
                geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
                settings.setValue("main_window/normal_geometry", geometry)
                name = (f"windows:{self._windows_monitor_name}"
                        if self._windows_monitor_name else self._scale_screen_name)
                if name and not self.isMaximized():
                    settings.setValue(f"window_size/{name}", self.size())
            except Exception:
                _logger.exception("Could not save window settings during shutdown")
            self._global_hotkey.close()
            if isinstance(self._menu_bar, InlineMenuBar):
                self._menu_bar.close_menu(restore_focus=False)
            for menu in self._popup_menus:
                menu.close()
            if self._capture_dialog is not None:
                self._capture_dialog.reject()
            for dialog in self.findChildren(QDialog):
                dialog.reject()
            if self._worker is not None:
                self._worker.cancel()
            self._cancel_retry()
            if self._render_worker is not None:
                self._render_worker.cancel()
            if self._native_capture is not None:
                self._native_capture.abort()
        if self._has_running_jobs():
            # Keep the event loop and job owners alive until cancellation has
            # finished, without a blocking wait or an unresponsive window.
            event.ignore()
            self.hide()
        else:
            event.accept()
            # Closing a window already hidden for capture/cancellation does
            # not emit lastWindowClosed. Explicitly finish application exit.
            app = QApplication.instance()
            if app.quitOnLastWindowClosed():
                QTimer.singleShot(0, app.quit)

    def _has_running_jobs(self):
        return any(job is not None and job.isRunning() for job in (
            self._worker, self._retry_worker, self._render_worker, self._native_capture))

    def _finish_shutdown(self):
        if self._closing and not self._has_running_jobs():
            QTimer.singleShot(0, self.close)
