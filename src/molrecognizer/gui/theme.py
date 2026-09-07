"""Desktop chemistry workbench palette and widget styles."""

from pathlib import Path

STYLESHEET = """
QMainWindow { background: #e9eef4; }
QLabel { color: #32465b; font-size: 12px; }
QMenuBar { background: #ffffff; color: #263b50; padding: 4px 10px;
    border-bottom: 1px solid #d5dfe9; font-size: 13px; }
QMenuBar::item { padding: 5px 12px; background: transparent; }
QMenuBar::item:selected { background: #e9f1fc; border-radius: 4px; }
QMenu { background: #ffffff; color: #263b50; border: 1px solid #ced9e5;
    padding: 5px; font-size: 13px; }
QMenu::item { padding: 7px 26px; border-radius: 3px; }
QMenu::item:selected { background: #e9f1fc; color: #155fa9; }
QMenu::separator { height: 1px; background: #e1e8f0; margin: 5px; }
QWidget#inline_menu_bar { background: #ffffff; border-bottom: 1px solid #d5dfe9; }
QPushButton#inline_menu_heading { background: transparent; color: #263b50;
    border: none; border-radius: 4px; padding: 5px 12px; font-size: 13px; min-height: 0px; }
QPushButton#inline_menu_heading:hover, QPushButton#inline_menu_heading:checked {
    background: #e9f1fc; }
QFrame#inline_menu_panel { background: #ffffff; border: 1px solid #ced9e5; }
QFrame#inline_menu_panel QScrollArea, QWidget#inline_menu_contents { background: #ffffff; }
QPushButton#inline_menu_item { color: #263b50; text-align: left;
    border: none; padding: 7px 16px; font-size: 13px; min-height: 0px; }
QPushButton#inline_menu_item:hover, QPushButton#inline_menu_item:focus {
    background: #e9f1fc; color: #155fa9; }
QPushButton#inline_menu_item:disabled { color: #93a1af; }
QFrame#inline_menu_separator { background: #e1e8f0; }
QWidget#toolbar_container { background: #f7f9fc; border-bottom: 1px solid #cdd9e6; }
QToolButton { background: transparent; color: #354b62; border: 1px solid transparent;
    border-radius: 4px; padding: 4px 8px; font-size: 13px; font-weight: 600;
    min-height: 22px; }
QToolButton:hover { background: #e8eff8; border-color: #c0d3e8; }
QToolButton:checked { background: #dceafb; border-color: #7da6d3; color: #155fa9; }
QToolButton:pressed { background: #c8ddf3; }
QToolButton[popupMode="1"] { padding-right: 26px; }
QToolButton::menu-button { subcontrol-origin: padding; subcontrol-position: top right;
    width: 22px; border: none; border-left: 1px solid #c9d7e5;
    border-top-right-radius: 4px; border-bottom-right-radius: 4px;
    background: transparent; }
QToolButton::menu-button:hover { background: #dceafb; }
QToolButton::menu-button:pressed { background: #c8ddf3; }
QToolButton::menu-arrow { image: url("__CHEVRON_DOWN__"); width: 12px; height: 12px; }
QToolButton#save_xyz_btn, QToolButton#copy_xyz_btn {
    background: #ffffff; border: 1px solid #c9d7e5; font-size: 12px; }
QToolButton#save_xyz_btn:hover, QToolButton#copy_xyz_btn:hover { background: #e9f1fc; }
QWidget#left_panel, QWidget#element_palette { background: #edf2f7; }
QLabel#panel_title { color: #314b65; font-size: 12px; font-weight: 700;
    padding: 6px 0px; }
QLabel#sidebar_brand { font-size: 18px; font-weight: 700; color: #193e65; }
QLabel#sidebar_caption { color: #73879c; font-size: 11px; padding-bottom: 6px; }
QFrame#source_card, QFrame#viewer_card { background: #ffffff;
    border: 1px solid #d5e0eb; border-radius: 6px; }
QLabel#image_preview { background: #ffffff; color: #8092a6;
    border: 1px dashed #c5d4e3; border-radius: 4px; font-size: 12px; }
QPushButton { color: #36526e; background: #ffffff; border: 1px solid #c8d6e5;
    border-radius: 4px; padding: 5px 12px; font-size: 12px; min-height: 22px; }
QPushButton:hover { background: #edf4fc; border-color: #91b4da; }
QPushButton:pressed { background: #d9e9fa; }
QPushButton#action_btn { background: #2568ad; color: #ffffff;
    border-color: #2568ad; font-weight: 600; }
QPushButton#action_btn:hover { background: #1c5792; }
QPushButton#action_btn_secondary { background: #ffffff; color: #315e8b; }
QWidget#editor_workspace { background: #285987; }
QLabel#workspace_title { color: #ffffff; font-size: 12px; font-weight: 600; }
QLabel#workspace_hint { color: #c5daed; font-size: 11px; }
QLabel#canvas_empty_hint { color: #7b91a7; background: transparent;
    font-size: 14px; padding: 36px; }
QGraphicsView { background: #ffffff; border: 1px solid #d3e0ec; border-radius: 3px; }
QDialog#recognition_review { background: #edf2f7; }
QListWidget#recognition_candidates { background: #ffffff; color: #32465b;
    border: 1px solid #d3e0ec; border-radius: 3px; font-size: 13px; }
QListWidget#recognition_candidates::item { padding: 4px 8px; }
QListWidget#recognition_candidates::item:selected { background: #dceafb; color: #155fa9; }
QDialog#recognition_review QPushButton:disabled { color: #8c9bab;
    background: #f3f6f9; border-color: #dae2eb; }
QSplitter::handle { background: #d8e2ed; }
QSplitter::handle:hover { background: #98b7d7; }
QWidget#bottom_bar { background: #ffffff; border-top: 1px solid #cedbe8; }
QLabel#smiles_label { color: #48637e; font-size: 11px; font-weight: 700; }
QLineEdit { background: #f7f9fc; color: #293f55; border: 1px solid #d4e0ec;
    border-radius: 4px; padding: 6px 9px; }
QLineEdit#smiles_field { font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 12px; }
QPushButton#small_btn, QPushButton#small_btn_green { font-size: 12px; font-weight: 600; }
QPushButton#small_btn_green { background: #2568ad; border-color: #2568ad; color: white; }
QLabel#valence_label { color: #6f8397; font-size: 11px; }
QStatusBar { background: #e9eff6; color: #57718a; font-size: 11px;
    border-top: 1px solid #d6e1ec; padding: 2px 10px; }
QStatusBar::item { border: none; }
QPushButton#ui_scale_btn { padding: 1px 6px; min-height: 18px; font-size: 11px; }
QScrollBar:vertical { background: #f2f5f9; width: 9px; margin: 0px; }
QScrollBar:horizontal { background: #f2f5f9; height: 9px; margin: 0px; }
QScrollBar::handle { background: #c0cfdf; border-radius: 4px; min-width: 24px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip { color: #233d56; background: #f6f9fd; border: 1px solid #c4d5e6; padding: 5px; }
"""

# Absolute resource paths also work in a relocated portable _internal tree.
STYLESHEET = STYLESHEET.replace(
    "__CHEVRON_DOWN__", (Path(__file__).parent / "icons" / "chevron-down.svg").as_posix(),
)
