# Molecule Recognizer

Recognize molecular structures from images (screenshots, papers, web pages), convert them to SMILES strings, and interactively edit the recognized structure. Built for computational chemistry workflows.

![UI Demo](docs/media/UI-demo.png)

## Features

- **Image recognition** — Uses [MolScribe](https://github.com/thomas0809/MolScribe) to extract molecular structures from images
- **Screenshot capture** — Built-in screen region selector with adjustable selection box (drag edges/corners to resize, ✓ to accept, ✗ to cancel); cross-platform support (Qt/grim/scrot/PowerShell fallback chain)
- **Interactive editor** — Draw and edit molecular structures:
  - Click an atom to substitute its element; drag from an atom to create new bonds — works in Bond and Atom modes
  - In Bond mode, clicking an atom adds a new bonded atom with chemistry-aware geometry:
    - 120° angles for sp2/trigonal centres, 180° for linear (sp), 90° for sp3 (4-bond) centres
    - Zig-zag chain pattern when extending a chain of single bonds
    - Clash avoidance: angular sweep finds the best direction at normal bond length before resorting to longer bonds
  - Bond tool has a dropdown menu (▾) for selecting Single/Double/Triple/Wedge/Dash bond type
  - Wedge (▶ filled triangle) and Dash (dashed wedge) stereo bonds for stereochemistry display; stereo preserved from SMILES, image recognition, and manually-drawn wedge/dash bonds
  - In Bond mode with Wedge/Dash selected, clicking a bond sets it to that type (click again to toggle back to single)
  - Click a bond to cycle its type (single → double → triple → single)
  - Hover highlighting on atoms and bonds for visual feedback
  - Formal charge tools ⊕/⊖ (increase/decrease)
  - Auto-inferred formal charges: N with 4 bonds → N⁺, O with 3 bonds → O⁺, B with 4 bonds → B⁻
  - Periodic table dialog for any element; PT button shows the selected element
  - Resizable panels (drag splitter handles between left panel, canvas, element palette)
  - Pan (middle/right-mouse drag) and zoom (scroll wheel)
  - Ring tools (⌬ ⬡ ⬠ □ △) — draw benzene, 6/5/4/3-membered rings on atoms, bonds (fused), or empty canvas; dropdown selector with ghost preview on hover
  - Box selection — drag on empty space to select atoms and bonds; drag the selection to move it as a group; Delete key removes the selection
  - Format button — recompute 2D layout via RDKit for a tidy structure after manual edits
  - Clean button — clear the canvas, loaded images, and 3D viewer to start fresh
  - Full undo/redo — adding a bonded atom undoes as a single step (atom + bond together); bulk delete uses snapshot-based undo for correctness
- **Kekulé structure display** — Aromatic systems shown as conjugated single/double bonds (not aromatic notation) for easy valence verification. Implicit Hs displayed on heteroatoms with subscript counts and superscript charges (e.g. NH₂, OH, SH, N⁺, NH₃⁺). Isolated atoms show all Hs (e.g. CH₄, NH₃).
- **Smart element substitution** — Changing an atom to a lower-valence element automatically downgrades bond orders (e.g. C→S in a ring converts double bonds to single). Undo fully restores original bond types.
- **Valence checking** — Automatic validation with over-valence warnings; hydrogen counts derived via RDKit sanitization with valence-table fallback for robustness with hypervalent atoms
- **Stereochemistry** — Wedge/dash bonds correctly encode chirality for both SMILES-loaded and manually-drawn structures; chiral tags derived from 2D bond directions; stereo preserved through SMILES export and 3D generation
- **3D structure viewer** — Generate and view 3D conformers (RDKit ETKDG + MMFF optimization) in an interactive ball-and-stick viewer; left-drag to rotate, right-drag to pan, scroll to zoom; double-click the preview to open a larger viewer window; double/triple bonds drawn explicitly
- **XYZ export** — Save 3D coordinates in XYZ format; dropdown to choose Angstrom (default) or Bohr units
- **SMILES export** — Live SMILES conversion as you edit, copy to clipboard or save to file; auto-inferred charges reflected in SMILES (e.g. `[N+]`); chirality (`@`/`@@`) and E/Z geometry preserved
- **Logging** — All warnings/errors (Python and C++/RDKit/Qt) written to `~/.molrecognizer/molrecognizer.log` instead of the terminal; log refreshed on each run; C-level stderr redirected after display server init to avoid cursor issues on WSLg
- **Python API** — Use programmatically from other Python packages

## Installation

```bash
# Clone the repository
git clone https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

### Python Dependencies

- Python >= 3.10
- RDKit (molecular toolkit)
- PySide6 (Qt GUI)
- MolScribe (structure recognition)
- PyTorch (MolScribe backend)
- Pillow, NumPy

### System Dependencies (screenshot)

The screenshot feature tries several capture backends in order and uses
the first that succeeds:

| Priority | Backend | Works on |
|---|---|---|
| 1 | Qt `grabWindow` (built-in) | Native Linux X11, macOS |
| 2 | `grim` (`sudo apt install grim`) | Native Linux Wayland (Sway, etc.) |
| 3 | `scrot` (`sudo apt install scrot`) | Native Linux X11 |
| 4 | `gnome-screenshot` | GNOME desktops |
| 5 | PowerShell (automatic) | WSL2 — last-resort fallback |

**Native Linux:** no extra packages needed on X11. On Wayland, install
`grim`: `sudo apt install grim`.

**WSL2 / WSLg:** the actual screen is the Windows desktop, which no Linux
tool can capture. The app automatically falls back to PowerShell for
screenshots. No setup required — it just works.

## Usage

### GUI Application

```bash
# With uv
uv run molrecognizer

# Or if installed globally
molrecognizer
```

**Keyboard shortcuts:**
| Action | Shortcut |
|---|---|
| Open image | Ctrl+O |
| Screenshot | Ctrl+Shift+S |
| Export SMILES | Ctrl+E |
| Undo | Ctrl+Z |
| Redo | Ctrl+Shift+Z |
| Quit | Ctrl+Q |
| Delete selection | Delete / Backspace |

**Editing tools:**
- **Select** — Click atom to substitute element; drag atom to move it; drag empty space to box-select; drag selection to move group; click bond to cycle type
- **Bond** (with ▾ dropdown: Single/Double/Triple/Wedge/Dash) — Click atom to add a bonded atom (VSEPR-aware direction); click bond to cycle type (or set to wedge/dash when selected); drag atom to create bond
- **Atom** — Click empty space to add an atom; click existing atom to change its element; drag atom to create bond
- **Eraser** — Click an atom or bond to delete it; drag empty space to box-select and bulk-delete
- **Ring** (⌬ with ▾ dropdown: Benzene/6-ring/5-ring/4-ring/3-ring) — Click atom or bond to attach ring; click empty space to place standalone ring; drag to orient
- **Charge ⊕/⊖** — Click an atom to increase or decrease its formal charge
- **Format** — Reformat structure with optimal 2D layout (undoable)
- **Clean** — Clear canvas, loaded images, and 3D viewer
- **PT** — Opens a periodic table dialog to pick any element (button shows current selection)

**Canvas navigation:**
- **Scroll wheel** — Zoom in/out
- **Middle-mouse drag** or **right-mouse drag** — Pan the canvas

### Python API

```python
import molrecognizer

# Recognize structure from an image → SMILES string
smiles = molrecognizer.recognize("molecule.png")
print(smiles)  # e.g., "c1ccccc1"

# Get a full Molecule object with coordinates
mol = molrecognizer.recognize_to_molecule("molecule.png")
print(mol.num_atoms, mol.num_bonds)

# Work with SMILES
mol = molrecognizer.smiles_to_molecule("CCO")
smiles = molrecognizer.molecule_to_smiles(mol)

# Check valence
warnings = molrecognizer.check_valence(mol)
for w in warnings:
    print(w)  # e.g., "Atom 0 (C): valence 5, expected 4"

# Edit molecules programmatically
from molrecognizer import Molecule, BondType

mol = Molecule()
c1 = mol.add_atom("C", 0.0, 0.0)
c2 = mol.add_atom("C", 1.5, 0.0)
mol.add_bond(c1, c2, BondType.DOUBLE)
print(molrecognizer.molecule_to_smiles(mol))  # "C=C"
```

### Using with GPU

If you have a CUDA-capable GPU, recognition runs faster:

```python
smiles = molrecognizer.recognize("molecule.png", device="cuda")
```

## Testing

```bash
# Run fast tests (no model download required)
uv run pytest tests/ --ignore=tests/test_recognizer.py

# Run all tests including MolScribe integration (downloads ~400MB model on first run)
uv run pytest tests/ -m slow
```

## Project Structure

```
molecule-recognizer/
├── src/molrecognizer/
│   ├── __init__.py          # Public API
│   ├── core/
│   │   ├── molecule.py      # Molecule class (RDKit wrapper)
│   │   ├── smiles.py        # SMILES ↔ Molecule conversion (with stereo)
│   │   ├── valence.py       # Valence checking
│   │   ├── xyz.py           # 3D conformer generation & XYZ export
│   │   └── recognizer.py    # MolScribe integration
│   ├── editor/
│   │   ├── canvas.py        # QGraphicsView molecular canvas (skeletal rendering)
│   │   ├── tools.py         # Editing tools (Select, Bond, Atom, Eraser, Charge)
│   │   └── history.py       # Undo/redo command stack
│   └── gui/
│       ├── app.py           # Application entry point & stylesheet
│       ├── main_window.py   # Main window (3-panel layout + element palette)
│       ├── screenshot.py    # Screen capture (grim/Qt/PowerShell fallback)
│       ├── editor_widget.py # Editor integration
│       ├── toolbar.py       # Tool bar
│       ├── viewer3d.py      # Interactive 3D ball-and-stick viewer
│       └── periodic_table.py # Periodic table dialog
└── tests/
```

## License

MIT
