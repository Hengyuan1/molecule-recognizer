# Molecule Recognizer

Recognize molecular structures from images (screenshots, papers, web pages), convert them to SMILES strings, and interactively edit the recognized structure. Built for computational chemistry workflows.

## Features

- **Image recognition** — Uses [MolScribe](https://github.com/thomas0809/MolScribe) to extract molecular structures from images
- **Screenshot capture** — Built-in screen region selector for capturing molecules directly
- **Interactive editor** — Add/delete atoms and bonds, change bond types (single, double, triple, aromatic), change element types
- **Valence checking** — Automatic validation of common element valences (C, N, O, S, P, halogens) with warnings
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

### Dependencies

- Python >= 3.10
- RDKit (molecular toolkit)
- PySide6 (Qt GUI)
- MolScribe (structure recognition)
- PyTorch (MolScribe backend)
- Pillow, NumPy

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
- **Select** — Click to select atoms/bonds, drag to move atoms
- **Bond** — Click two atoms to add or change a bond; select bond type from the dropdown
- **Atom** — Click empty space to add an atom, click existing atom to change its element
- **Eraser** — Click an atom or bond to delete it

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
│   │   ├── canvas.py        # QGraphicsView molecular canvas
│   │   ├── tools.py         # Editing tools (Select, Bond, Atom, Eraser)
│   │   └── history.py       # Undo/redo command stack
│   └── gui/
│       ├── app.py           # Application entry point
│       ├── main_window.py   # Main window
│       ├── screenshot.py    # Screen capture overlay
│       ├── editor_widget.py # Editor integration
│       └── toolbar.py       # Tool palette
└── tests/
```

## License

MIT
