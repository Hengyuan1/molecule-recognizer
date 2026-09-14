"""Opt-in portable-build smoke checks; never capture the user's desktop."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import traceback


def smoke_test(report_path: Path, *, require_osra: bool = False) -> int:
    report = {"ok": False, "checks": [], "osra": "not tested"}
    window = None
    worker = None
    app = None
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    try:
        from PySide6.QtCore import QEventLoop, QSettings, QTimer, Qt
        from PySide6.QtGui import QAction, QFont, QIcon
        from PySide6.QtWidgets import QApplication
        from rdkit import Chem
        from rdkit.Chem import Draw

        from .core.smiles import molecule_to_smiles, smiles_to_molecule
        from .core.xyz import mol_to_xyz_string
        from .gui.app_icon import application_icon
        from .gui.main_window import MainWindow
        from .gui.theme import STYLESHEET
        from .gui.workers import Render3DWorker
        from .runtime import application_directory, capture_helper, subprocess_options

        with tempfile.TemporaryDirectory(prefix="molrecognizer-smoke-") as temporary:
            app = QApplication([])
            app.setWindowIcon(application_icon())
            app.setApplicationName("MolRecognizer packaging test")
            app.setOrganizationName("MolRecognizer packaging test")
            QSettings.setDefaultFormat(QSettings.Format.IniFormat)
            QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, temporary)
            app._base_stylesheet = STYLESHEET
            app._base_font = QFont("Segoe UI", 11)
            app.setStyleSheet(STYLESHEET)
            app.setFont(app._base_font)
            for name in ("wedge-bond.png", "dash-bond.png", "chevron-down.svg", "molrecognizer.ico"):
                if QIcon(str(Path(__file__).parent / "gui" / "icons" / name)).isNull():
                    raise RuntimeError(f"Missing packaged icon: {name}")
            window = MainWindow()
            window.show()
            window._set_molecule(smiles_to_molecule("CCO"))
            app.processEvents()
            icon = application_icon()
            expected_sizes = {16, 20, 24, 32, 40, 48, 64, 96, 128, 256}
            if {size.width() for size in icon.availableSizes()} != expected_sizes:
                raise RuntimeError("Packaged app icon is missing Windows size variants")
            if window.windowIcon().pixmap(32, 32).toImage() != icon.pixmap(32, 32).toImage():
                raise RuntimeError("Main window is not using the application icon")
            report["checks"].append("multi-size application icon and title-bar identity")
            report["checks"].append("Qt window, icons and SMILES editor")
            toolbar = window._editor._toolbar
            for key in ("ring", "charge+", "charge-"):
                button = toolbar._tool_buttons[key]
                if (button.icon().isNull()
                        or button.toolButtonStyle() != Qt.ToolButtonStyle.ToolButtonIconOnly
                        or button.iconSize().width() <= toolbar._tool_buttons["bond"].iconSize().width()):
                    raise RuntimeError(f"Missing large toolbar symbol: {key}")
            report["checks"].append("large ring and charge toolbar icons")
            material_index = application_directory() / "licenses/release-materials/MATERIALS.json"
            if material_index.is_file():
                if not any(action.text().startswith("Third-party licenses")
                           for action in window.findChildren(QAction)):
                    raise RuntimeError("Packaged license access action is missing")
                if not (application_directory() / "SOURCE-ACCESS.md").is_file():
                    raise RuntimeError("Packaged source-access instructions are missing")
                report["checks"].append("license menu and packaged source-access instructions")

            results = []
            loop = QEventLoop()
            watchdog = QTimer()
            watchdog.setSingleShot(True)
            watchdog.timeout.connect(loop.quit)
            worker = Render3DWorker("CCO")
            worker.result_ready.connect(results.append)
            worker.finished.connect(loop.quit)
            watchdog.start(30000)
            worker.start()
            loop.exec()
            watchdog.stop()
            if not results:
                raise RuntimeError("3D helper timed out")
            if isinstance(results[0], Exception):
                raise results[0]
            mol = results[0]
            if Chem.MolToSmiles(Chem.RemoveHs(mol)) != "CCO" or not mol.GetConformer().Is3D():
                raise RuntimeError("3D helper changed the molecule or returned no 3D coordinates")
            if len(mol_to_xyz_string(mol).splitlines()) != mol.GetNumAtoms() + 2:
                raise RuntimeError("XYZ export failed")
            window._render_smiles = window._bottom_bar.smiles_text
            window._on_render_done(mol)
            window._show_3d_comparison()
            app.processEvents()
            if not window._comparison_panel.isVisible():
                raise RuntimeError("3D comparison did not open")
            window._hide_3d_comparison()
            report["checks"].append("packaged 3D worker, XYZ export and comparison panel")

            from .core.molecule import BondType
            from .core.recognition_retry import RETRY_PROFILES
            window._set_molecule(smiles_to_molecule("[NH3]->[Sc](<-[NH3])Br"))
            scene = window._editor.canvas.mol_scene
            donors = [atom for atom in scene._atom_items.values() if atom.element == "N"]
            arrows = [bond for bond in scene._bond_items.values() if bond.bond_type == BondType.DATIVE]
            if (len(donors) != 2 or not all(atom.n_hs == 3 and atom.formal_charge == 0 for atom in donors)
                    or len(arrows) != 2 or not all(len(bond._extra_lines) == 2 for bond in arrows)
                    or "not validated" not in window._bottom_bar._valence_label.text()):
                raise RuntimeError("Coordinate bond display or metal review warning failed")
            exported = Chem.MolFromSmiles(molecule_to_smiles(window._molecule))
            if exported is None or sum(b.GetBondType() == Chem.BondType.DATIVE
                                       for b in exported.GetBonds()) != 2:
                raise RuntimeError("Coordinate bond SMILES export failed")
            before = molecule_to_smiles(window._molecule)
            window._on_review_labels()
            dialog = window._label_review_dialog
            if dialog is None or dialog._coordinate.isChecked() or not dialog._preview():
                raise RuntimeError("Explicit label review is unavailable or enabled implicitly")
            dialog.reject()
            app.processEvents()
            if molecule_to_smiles(window._molecule) != before:
                raise RuntimeError("Cancelling label review changed the molecule")
            if tuple(profile.scale for profile in RETRY_PROFILES) != (1, 1, 1, 2, 4):
                raise RuntimeError("Enlarged OCR retry profiles are missing")
            report["checks"].append("coordinate bonds, neutral donors and metal review warnings")

            for symbol in ("Co", "Pt", "Cr"):
                window._editor._toolbar._metal_btn.click()
                picker = window._metal_picker
                if picker is None or symbol not in picker._buttons:
                    raise RuntimeError("Common metal picker is missing " + symbol)
                app.processEvents()
                from PySide6.QtGui import QColor
                if picker.grab().toImage().pixelColor(2, 2) != QColor("#edf2f7"):
                    raise RuntimeError("Metal picker background is not explicitly light")
                button = picker._buttons[symbol]
                if (not button.parentWidget().rect().contains(button.geometry())
                        or any(button.geometry().intersects(other.geometry())
                               for other in picker._buttons.values() if other is not button)):
                    raise RuntimeError("Metal picker buttons overlap or extend outside their panel")
                for label in (button.symbol_label, button.name_label):
                    if (not button.rect().contains(label.geometry())
                            or label.height() < label.fontMetrics().height()
                            or label.width() < label.fontMetrics().horizontalAdvance(label.text())):
                        raise RuntimeError("Metal picker clips a symbol or element name")
                picker._buttons[symbol].click()
                app.processEvents()
                if (window._editor._current_element != symbol
                        or window._editor._current_tool.name != "atom"
                        or molecule_to_smiles(window._molecule) != before):
                    raise RuntimeError("Common metal selection changed the molecule or failed")
            report["checks"].append("common metal center picker: Co, Pt and Cr")
            report["checks"].append("light metal picker and unclipped two-line labels")

            helper = capture_helper()
            if helper is None:
                raise RuntimeError("Compiled Windows capture helper is missing")
            result = subprocess.run([str(helper), "--self-test"], capture_output=True,
                                    timeout=15, **subprocess_options())
            if result.returncode != 0 or result.stdout.strip() != b"OK":
                raise RuntimeError("Capture helper check failed: " + result.stderr.decode(errors="replace"))
            report["checks"].append("compiled capture helper (synthetic pixels only)")

            if require_osra:
                from .core.recognition_retry import _adaptive_retry_image, recognition_alternatives
                from .core.recognizer import OSRARecognizer
                recognizer = OSRARecognizer(timeout=30)
                # Exercise both PNG decoding and the coordinate-preserving SDF
                # route, not only --version or the SMILES fallback.
                path = Path(temporary) / "benzene test.png"
                source = Draw.MolToImage(Chem.MolFromSmiles("c1ccccc1"), size=(400, 400))
                source.save(path)
                recognized = recognizer._read_sdf(path)
                if recognized is None:
                    raise RuntimeError("Bundled OSRA returned no SDF structure")
                Chem.SanitizeMol(recognized)
                if Chem.MolToSmiles(Chem.RemoveHs(recognized)) != "c1ccccc1":
                    raise RuntimeError("Bundled OSRA failed the benzene recognition check")
                report["osra"] = recognizer.executable
                report["checks"].append("bundled OSRA PNG-to-SDF recognition")
                pixels = source.tobytes()
                padded = _adaptive_retry_image(source)
                if (padded.size != (448, 448)
                        or padded.crop((24, 24, 424, 424)).tobytes() != source.convert("RGB").tobytes()
                        or padded.getpixel((0, 0)) != (255, 255, 255)):
                    raise RuntimeError("Adaptive retry padding changed the source drawing")
                attempts = recognition_alternatives(source, recognizer)
                try:
                    candidate = next(attempts)
                    if candidate.error or candidate.molecule is None:
                        raise RuntimeError("Bundled OSRA adaptive retry failed: " + candidate.error)
                    # Use the same export as the UI: the editor's internal
                    # molecule deliberately disables implicit hydrogens.
                    if (candidate.name != "Adaptive threshold"
                            or molecule_to_smiles(candidate.molecule) != "c1ccccc1"
                            or source.tobytes() != pixels):
                        raise RuntimeError("Adaptive retry changed the molecule or source pixels")
                finally:
                    attempts.close()
                report["checks"].append("adaptive retry white margin and bundled OSRA recognition")
            else:
                report["osra"] = "NOT INCLUDED — image recognition unavailable without external OSRA"
            window.close()
            app.processEvents()
            report["ok"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    finally:
        if worker is not None and worker.isRunning():
            worker.cancel()
            # Diagnostic process only; never a wait in a production GUI callback.
            worker._process.waitForFinished(5000)
        if window is not None:
            window.close()
        if app is not None:
            app.processEvents()
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1
