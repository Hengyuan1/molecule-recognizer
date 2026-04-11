# Molecule Recognizer

Recognize molecular structures from images (screenshots, papers, web pages), convert them to SMILES strings, and interactively edit the recognized structure. Built for computational chemistry workflows.

## Features

- **Image recognition** — Uses [MolScribe](https://github.com/thomas0809/MolScribe) to extract molecular structures from images
- **Screenshot capture** — Built-in screen region selector with cross-platform support (Qt/grim/scrot/PowerShell fallback chain)
- **Interactive editor** — Draw and edit molecular structures:
  - Drag from an atom to create new bonds and atoms
  - Click a bond to cycle its type (single/double/triple)
  - Click an atom to change its element
  - Formal charge tools (increase/decrease)
  - Periodic table dialog for element selection
  - Pan (middle/right-mouse drag) and zoom (scroll wheel)
  - Full undo/redo support
- **Skeletal structure display** — Chemistry-standard rendering with implicit Hs shown on heteroatoms (e.g. NH₂, OH, SH), subscript H counts, superscript charges
- **Valence checking** — Automatic validation with over-valence warnings; implicit hydrogen counts derived from standard valences and formal charge
- **SMILES export** — Live SMILES conversion as you edit, copy to clipboard or save to file
- **Python API** — Use programmatically from other Python packages

## Installation

```bash
# Clone the repository
git clone <repo-url>
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

**Editing tools:**
- **Select** — Click to highlight atoms/bonds, drag to move atoms
- **Bond** — Drag from an atom to another atom to create a bond, drag to empty space to create a new atom + bond, click an existing bond to cycle its type (single → double → triple)
- **Atom** — Click empty space to add an atom, click existing atom to change its element; select element from the right-side palette or the periodic table (PT button)
- **Eraser** — Click an atom or bond to delete it
- **Charge ⊕/⊛** — Click an atom to increase or decrease its formal charge
- **PT** — Opens a periodic table dialog to pick any element

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
│   │   ├── smiles.py        # SMILES ↔ Molecule conversion
│   │   ├── valence.py       # Valence checking
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
│       └── periodic_table.py # Periodic table dialog
└── tests/
```

## License

MIT
