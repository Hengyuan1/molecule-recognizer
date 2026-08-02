# Molecule Recognizer

Recognize molecular structures from images (screenshots, papers, web pages), convert them to SMILES strings, interactively edit the recognized structure, and save the 3D structure in xyz format. Built for computational chemistry workflows.

![UI Demo](docs/media/UI-demo.png)

## Features

- **Image recognition** — Uses [OSRA](https://sourceforge.net/projects/osra/) by default and preserves its recognized 2D coordinates and explicit single/double-bond placement via SDF output, making image-to-canvas comparison and manual correction easier; MolScribe remains available as an alternative
- **Screenshot capture** — On WSL, press the system-wide Alt+Y hotkey from any Windows application to capture the monitor under the mouse cursor, then draw and adjust a selection box (drag edges/corners to resize, ✓ to accept, ✗ to cancel); works with extended monitors through the Qt/grim/scrot/PowerShell fallback chain
- **Per-monitor UI scaling** — Automatically enlarges the interface on high-resolution laptop displays; use the `A−`, percentage, and `A+` controls in the status bar to tune and remember a separate size for each monitor
- **Monitor-aware window sizing** — Uses stable Qt-controlled sizing without clipping controls and remembers settings per display; `Fit` and UI-scale controls replace unreliable custom WSLg edge-resize gestures
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
- **XYZ export and clipboard** — After rendering, save or copy 3D coordinates in XYZ format; both controls offer Angstrom (default) or Bohr units
- **SMILES export** — Live SMILES conversion as you edit, copy to clipboard or save to file; auto-inferred charges reflected in SMILES (e.g. `[N+]`); chirality (`@`/`@@`) and E/Z geometry preserved
- **Logging** — All warnings/errors (Python and C++/RDKit/Qt) written to `~/.molrecognizer/molrecognizer.log` instead of the terminal; log refreshed on each run; C-level stderr redirected after display server init to avoid cursor issues on WSLg
- **Python API** — Use programmatically from other Python packages

## Installation

### Python application

```bash
# Clone the repository
git clone https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .

# Optional: also install the legacy MolScribe backend
uv sync --extra molscribe
# or: pip install -e ".[molscribe]"

# Optional: expose the editable checkout as a command from any directory
uv tool install --python 3.10 --editable .
```

### Python Dependencies

- Python >= 3.10
- RDKit >= 2023.9.1 (molecular toolkit; Linux, macOS, and Windows wheels)
- PySide6 (Qt GUI)
- Pillow, NumPy
- MolScribe and PyTorch (optional alternative recognition backend)

OSRA is a separate native executable, not a Python dependency.

### OSRA discovery

Molecule Recognizer searches for OSRA in this order:

1. The `OSRA_EXECUTABLE` environment variable.
2. `osra` or `osra.exe` on `PATH`.
3. A project-local executable at `.tools/osra/bin/osra` or
   `.tools/osra/bin/osra.exe`.

For a custom installation:

```bash
export OSRA_EXECUTABLE=/path/to/osra
```

In PowerShell:

```powershell
$env:OSRA_EXECUTABLE = "C:\path\to\osra.exe"
```

The app runs OSRA locally; images are not sent to the NCI OSRA web page.
OSRA may return several structures for a page or compound image. The editor
loads the first valid structure.

### Windows

#### Recommended: Windows 11 with WSL2/WSLg

Run the Python application and OSRA inside Ubuntu under WSL2. This is the
configuration currently tested by the project and provides:

- A system-wide Windows `Alt+Y` shortcut while Molecule Recognizer is running.
- Capture of the full-resolution monitor under the cursor.
- Mixed-DPI and extended-monitor support.
- Local OSRA recognition without uploading images.

Install OSRA in WSL, put its executable on the WSL `PATH`, then install the
editable application:

```bash
uv tool install --python /usr/bin/python3.10 --editable \
  /path/to/molecule-recognizer
molrecognizer
```

#### Native Windows

Native Windows can run the Python GUI because RDKit, PySide6, Pillow, and
NumPy provide Windows wheels. OSRA must still be obtained or compiled
separately.

##### 1. Install Git and uv

Open PowerShell and install Git and uv if they are not already available:

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
```

Close and reopen PowerShell, then verify:

```powershell
git --version
uv --version
```

##### 2. Obtain OSRA for Windows

Download an OSRA Windows distribution from the
[official OSRA download page](https://sourceforge.net/p/osra/wiki/Download/),
or compile the free OSRA source using the
[official Windows build instructions](https://sourceforge.net/p/osra/wiki/Compilation_on_Windows/).
The official project currently distributes source and prebuilt Windows
binaries separately.

Keep the complete distribution together. OSRA needs more than `osra.exe`:
retain its DLLs and the runtime dictionaries `chain.txt`, `spelling.txt`, and
`superatom.txt`.

Before configuring Molecule Recognizer, test OSRA itself:

```powershell
& "C:\path\to\OSRA\bin\osra.exe" --version
& "C:\path\to\OSRA\bin\osra.exe" -f smi "C:\path\to\molecule.png"
```

The second command should print a SMILES string. If it reports a missing DLL
or dictionary, repair the OSRA installation before continuing.

##### 3. Install Molecule Recognizer

Choose either the uv-tool method or the Conda method below.

**Option A — uv tool:**

```powershell
git clone https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer
uv tool install --python 3.11 --editable .
```

If uv needs to install Python 3.11 first:

```powershell
uv python install 3.11
uv tool install --python 3.11 --editable .
```

**Option B — existing Conda/Miniconda installation:**

This option does not require WSL or a system-wide Python installation:

```powershell
git clone https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer

conda create -n molrecognizer python=3.11 -y
conda activate molrecognizer
python -m pip install --upgrade pip
python -m pip install -e .
```

If Git is unavailable on a managed laptop, download the repository ZIP,
extract it, open PowerShell in the extracted directory, and run the Conda and
pip commands above without the `git clone` command.

##### 4. Tell Molecule Recognizer where OSRA is

Set the executable for the current PowerShell session:

```powershell
$env:OSRA_EXECUTABLE = "C:\path\to\OSRA\bin\osra.exe"
```

Persist it for future PowerShell sessions:

```powershell
[Environment]::SetEnvironmentVariable(
    "OSRA_EXECUTABLE",
    "C:\path\to\OSRA\bin\osra.exe",
    "User"
)
```

Close and reopen PowerShell after setting the persistent value.

For a Conda environment, OSRA can instead be associated only with that
environment:

```powershell
conda activate molrecognizer
conda env config vars set OSRA_EXECUTABLE="C:\path\to\OSRA\bin\osra.exe"
conda deactivate
conda activate molrecognizer
```

Verify the environment variable:

```powershell
$env:OSRA_EXECUTABLE
```

As an alternative to `OSRA_EXECUTABLE`, place a complete OSRA distribution
inside the cloned project using this layout:

```text
.tools/
└── osra/
    ├── bin/
    │   ├── osra.exe
    │   └── required OSRA DLLs...
    └── share/
        ├── chain.txt
        ├── spelling.txt
        └── superatom.txt
```

You may also add the OSRA `bin` directory to the Windows `PATH`.

##### 5. Verify the integration

From any directory in a newly opened PowerShell window:

```powershell
molrecognizer
```

With the Conda installation, activate the environment first:

```powershell
conda activate molrecognizer
molrecognizer
```

In the application:

1. Click **Open Image** and select a molecule image.
2. Wait for OSRA recognition.
3. Confirm that the structure appears on the canvas and SMILES appears in
   the bottom bar.
4. Click **Render** to generate 3D coordinates.
5. Use **Save xyz** or **Copy xyz** as needed.

You can also test the integration without opening the GUI:

```powershell
uv run --project "C:\path\to\molecule-recognizer" python -c "import molrecognizer; print(molrecognizer.recognize(r'C:\path\to\molecule.png'))"
```

##### Native Windows screenshot note

On native Windows, `Alt+Y` and `Ctrl+Shift+S` currently work while Molecule
Recognizer has focus. Move the cursor onto the desired monitor before using
the shortcut. The system-wide `Alt+Y` shortcut that works while another
Windows application has focus is currently provided only by the WSL2/WSLg
configuration.

##### Troubleshooting

- **`OSRA executable was not found`** — check `$env:OSRA_EXECUTABLE`, or run
  `Get-Command osra.exe`.
- **Missing `chain.txt`** — keep `chain.txt`, `spelling.txt`, and
  `superatom.txt` in the OSRA distribution's expected `share` directory.
- **Missing DLL error** — restore the DLLs distributed with OSRA or add their
  directory to `PATH`.
- **`molrecognizer` is not found** — run `uv tool update-shell`, reopen
  PowerShell, and retry. For Conda, activate the `molrecognizer` environment.
- **Recognition returns an incorrect molecule** — crop tightly around one
  chemical structure and manually review the generated structure and SMILES.

### Why OSRA is not installed by `uv sync`

OSRA is not published as a Python wheel. It is a C++ program requiring
GraphicsMagick, Open Babel, Poppler, Potrace, patched GOCR, OCRAD, and TCLAP.
The official project distributes free source code, while current prebuilt
Windows binaries are provided separately. Automatically downloading or
building OSRA during Python package installation would be slow, fragile, and
would require platform-specific binary and license handling.

A future Windows release can bundle an OSRA distribution under
`.tools/osra/`, but that should be built and tested as a separate release
artifact rather than performed by `pip` or `uv` at install time.

### Screenshot backends

The screenshot feature tries several capture backends in order and uses
the first that succeeds:

| Priority | Backend | Works on |
|---|---|---|
| 1 | PowerShell + Win32 (automatic) | WSL2/WSLg, including extended monitors |
| 2 | Qt `grabWindow` (built-in) | Native Linux X11, macOS, native Windows |
| 3 | `grim` (`sudo apt install grim`) | Native Linux Wayland |
| 4 | `scrot` (`sudo apt install scrot`) | Native Linux X11 |
| 5 | `gnome-screenshot` | GNOME desktops |

**Native Linux:** no extra packages needed on X11. On Wayland, install
`grim`: `sudo apt install grim`.

**WSL2 / WSLg:** the app uses Windows PowerShell first. Move the cursor onto
the desired monitor and press `Alt+Y`; capture uses that monitor's native
pixel bounds and handles different display scaling factors.

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
| Screenshot (quick) | Alt+Y |
| Export SMILES | Ctrl+E |
| Undo | Ctrl+Z |
| Redo | Ctrl+Shift+Z |
| Quit | Ctrl+Q |
| Delete selection | Delete / Backspace |
| Increase interface size | Ctrl+Alt++ |
| Decrease interface size | Ctrl+Alt+- |
| Reset interface size | Ctrl+Alt+0 |

**Editing tools:**
- **Select** — Click atom to substitute element; drag atom to move it; drag empty space to box-select; drag selection to move group; click bond to cycle type
- **Bond** (with ▾ dropdown: Single/Double/Triple/Wedge/Dash) — Click atom to add a bonded atom (VSEPR-aware direction); click bond to cycle type (or set to wedge/dash when selected); drag atom to create bond
- **Atom** — Click empty space to add an atom; click existing atom to change its element; drag atom to create bond
- **Eraser** — Click an atom or bond to delete it; drag empty space to box-select and bulk-delete
- **Ring** (⌬ with ▾ dropdown: Benzene/6-ring/5-ring/4-ring/3-ring) — Click atom or bond to attach ring; click empty space to place standalone ring; drag to orient
- **Charge ⊕/⊖** — Click an atom to increase or decrease its formal charge
- **Format** — Reformat structure with optimal 2D layout (undoable)
- **Clean** — Clear canvas, loaded images, and 3D viewer
- **Save xyz / Copy xyz** — After rendering the 3D structure, save it to a file or copy the complete XYZ text to the clipboard; use each button's dropdown for Angstrom or Bohr
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

# Use the legacy MolScribe backend explicitly
smiles = molrecognizer.recognize(
    "molecule.png", backend="molscribe", device="cuda"
)

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

### Using MolScribe with a GPU

If you have a CUDA-capable GPU, recognition runs faster:

```python
smiles = molrecognizer.recognize(
    "molecule.png", backend="molscribe", device="cuda"
)
```

## Testing

```bash
# Run fast tests (no model download or OSRA installation required)
uv run pytest tests/ -m "not slow"

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
│   │   └── recognizer.py    # OSRA (default) and MolScribe integrations
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
