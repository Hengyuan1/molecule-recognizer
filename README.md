# Molecule Recognizer

Recognize molecular structures from images (screenshots, papers, web pages), convert them to SMILES strings, interactively edit the recognized structure, and save the 3D structure in xyz format. Built for computational chemistry workflows.

**Version [0.2.0](https://github.com/Hengyuan1/molecule-recognizer/tree/v0.2.0)** — Side-by-side 2D/3D comparison, reviewable OSRA retries, and WSLg stability improvements. See the [release notes](CHANGELOG.md).

![Molecule Recognizer 0.2.0 showing the source image, editable 2D structure, and interactive 3D comparison panel](docs/media/UI-demo.png)

Double-click the rendered XYZ preview to compare it beside the 2D canvas.
Drag the divider to adjust the view widths; the editor and SMILES remain
interactive. Close the 3D panel to return to the full canvas.

## Features

- **Desktop workbench** — IQmol-inspired menus and icon toolbar, separate source-image and 3D panels, and a blue workspace surround with a light canvas for readable chemical drawings. Menus and the bottom size controls scale with the rest of the interface. File/Edit/Build/View menus expose existing actions and shortcuts; **View → Fit structure** adjusts the view without changing molecular coordinates or bond placement (unlike Format, which regenerates the layout).
- **Image recognition** — Uses [OSRA](https://sourceforge.net/projects/osra/) by default and preserves its recognized 2D coordinates and explicit single/double-bond placement via SDF output, making image-to-canvas comparison and manual correction easier; MolScribe remains available as an alternative
- **Linear nitrile groups** — Recognized C–C≡N groups are straightened by moving only the terminal nitrogen, preserving the rest of the drawing and all bond assignments. Format also initializes imported atoms' hybridization so triple bonds remain linear during layout cleanup.
- **Small-image label recovery** — If OSRA leaves unrecognized atom labels in a small raster image (up to 1200 pixels on its longest side), the editor tries one 2× enlarged, padded copy. It transfers only unambiguous atom identities when the atom/bond counts, connections, known elements/charges, and specified stereochemistry agree. Original coordinates and wedge/dash markings stay unchanged. Intentional `*`/R-group placeholders are not assumed to be carbon; unresolved labels remain available for manual correction. The temporary retry image is deleted after use.
- **Reviewable recognition retries** — Click **Retry recognition** (or **File → Retry recognition…**) after opening/capturing an image to compare three local OSRA alternatives: adaptive thresholding, 100 dpi interpretation, and grayscale threshold 0.35. The full-resolution source and candidate drawings have independent pan/zoom; SMILES, ring sizes, unknown atoms, and valence warnings help comparison. Scores are not accuracy percentages and never choose a result automatically. **Use selected** applies the chosen drawing as one undoable change; **Keep current** or Escape leaves your edits intact. **Stop retries** keeps completed candidates available. Initial recognition defaults are unchanged.
- **Snip-style structure capture** — On WSL, press system-wide Alt+Y to select directly over the monitor under your cursor, including extended monitors. A borderless Windows overlay preserves the screen's original size: draw a rectangle, move it or adjust its edges/corners, then click **Recognize** or press **Enter**. **Esc**, right-click, or **Cancel** discards it. Arrow keys move the box by one pixel (Shift: ten). The full-resolution crop goes directly to local recognition, without a separate preview window or web upload.
- **Per-monitor UI scaling** — On WSL, uses a 180% interface target on high-resolution laptops. Native Windows accounts for Windows display scaling instead of applying it twice: for example, 70% in-app on a 250%-scaled laptop is about 175% in physical pixels. Window fitting includes the title bar, taskbar and minimum space needed by the controls. Use `A−` and `A+` to remember a separate size for each monitor, or click the percentage to restore that monitor's recommended scale. `Fit` restores the recommended window size even if an unsuitable size was saved.
- **Monitor-aware window sizing** — Uses stable Qt-controlled sizing without clipping controls and remembers settings per display; `Fit` and UI-scale controls replace unreliable custom WSLg edge-resize gestures
- **Monitor-aware retry review** — Retry recognition stays on the main window's monitor. On WSLg it opens inside the main window, avoiding native modal frames and Windows-side repositioning that can freeze or corrupt the display. Close the panel or press Esc to return to editing. Native Windows and other desktops retain a separate, parent-centered review dialog.
- **Side-by-side 2D/3D comparison** — Double-click the rendered XYZ preview to open an interactive 3D panel beside the 2D canvas. Drag the divider to adjust their widths; both views and the SMILES remain usable. Close the panel (or press Esc while focused in it) to restore the full canvas. Re-rendering updates the panel; a notice appears if the 2D structure has changed since the last successful render. No additional native window is created, including on WSLg.
- **WSLg menus** — File/Edit/Build/View/Help use a shared dropdown panel drawn inside the application, avoiding native-popup handoffs and cursor polling. Click a heading, then hover between headings; use arrow keys and Enter, Escape to dismiss, or Alt+letter/F10 to open a menu. Clicking outside, moving/resizing the window, or switching applications dismisses the panel. Native Windows and other platforms retain standard Qt menus. The Bond/Ring/XYZ dropdowns retain their separate WSLg popup-resource cleanup.
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
  - Format button — recompute 2D layout via RDKit, align it to the original orientation, and recalculate wedge/dash directions for the new coordinates so cleanup does not invert stereocenters. Coordinates and stereo markings undo/redo together in one step; if the stereochemical SMILES would change, the original drawing is retained.
  - Clean button — clear the canvas, loaded images, and 3D viewer to start fresh
  - Full undo/redo — adding a bonded atom undoes as a single step (atom + bond together); atom, bond, and bulk deletions use complete snapshots to restore original connections, bond types, stereochemistry, and coordinates exactly
- **Kekulé structure display** — Aromatic systems shown as conjugated single/double bonds (not aromatic notation) for easy valence verification. Implicit Hs displayed on heteroatoms with subscript counts and superscript charges (e.g. NH₂, OH, SH, N⁺, NH₃⁺). Isolated atoms show all Hs (e.g. CH₄, NH₃).
- **Compact hydrogen labels** — Ordinary O–H and N–H groups from image recognition display as `OH`, `NH`, or `NH₂` (also `NH₃⁺`, etc., as appropriate), without separate H atoms or bonds on the 2D canvas. The molecular data and SMILES remain unchanged. Moving/deleting a compact group includes its hidden hydrogens and supports Undo/Redo; isotopic, mapped, charged, or stereo-marked hydrogens remain explicit.
- **Smart element substitution** — Changing an atom to a lower-valence element automatically downgrades bond orders (e.g. C→S in a ring converts double bonds to single). Undo fully restores original bond types.
- **Valence checking** — Automatic validation with over-valence warnings; hydrogen counts derived via RDKit sanitization with valence-table fallback for robustness with hypervalent atoms
- **Stereochemistry** — OSRA's original SDF wedge/dash markings are restored on the same bonds, with their narrow ends at the original atoms; coordinates are mapped to the screen without mirroring the drawing. Stereo is also supported for SMILES-loaded and manually-drawn structures and preserved through SMILES export and 3D generation. Recognition errors or stereo markings absent from OSRA's output still need manual correction.
- **3D structure viewer** — Generate and view 3D conformers (RDKit ETKDG + MMFF optimization) in an interactive ball-and-stick viewer; left-drag to rotate, right-drag to pan, scroll to zoom; double-click the preview to compare it beside the 2D canvas; double/triple bonds drawn explicitly
- **XYZ export and clipboard** — After rendering, save or copy 3D coordinates in XYZ format; both controls offer Angstrom (default) or Bohr units
- **Responsive shutdown** — Closing cancels local recognition, 3D generation, and capture helpers without blocking the UI. Delayed screenshot results cannot reopen a closing window, and unavailable monitor/settings data cannot prevent closing. 3D generation runs in a separate background process so the interface stays responsive.
- **SMILES export** — Live SMILES conversion as you edit, copy to clipboard or save to file; auto-inferred charges reflected in SMILES (e.g. `[N+]`); chirality (`@`/`@@`) and E/Z geometry preserved
- **Logging** — All warnings/errors (Python and C++/RDKit/Qt) written to `~/.molrecognizer/molrecognizer.log` instead of the terminal; log refreshed on each run; C-level stderr redirected after display server init to avoid cursor issues on WSLg
- **Python API** — Use programmatically from other Python packages

## Installation

### Standalone Windows build (in development)

Windows portable packaging is being developed on the feature branch; the
published **v0.2.0 does not contain a standalone EXE**. The complete local
package is a ZIP you extract and run with `MolRecognizer.exe`, without Python,
Conda or WSL. Native **OSRA 2.2.4 has now been compiled and tested locally**;
complete builds bundle it under `tools/osra/` and discover it automatically.
Builds labelled **`no-osra` are editor-only previews**. No OSRA-bundled public
release has been published yet; redistribution review remains outstanding.
The next public version is planned as **0.3.0**. It is being prepared locally,
not published: the [release audit](packaging/windows/RELEASE-AUDIT.md) tracks
the recorded [upstream CImg permission](packaging/windows/CIMG-PERMISSION.md)
and final acceptance tests. David Tschumperlé granted the ordinary CeCILL
alternative for the covered legacy CImg code on September 10, 2026.
Prepared builds include original dependency notices accessible from
**Help → Third-party licenses**, source-access instructions, and a matching
source/patch/build-recipe archive. The latest build also includes larger ring
and charge icons that scale with the interface. See the [draft 0.3.0 release notes](packaging/windows/RELEASE-NOTES-0.3.0.md).
The [0.3.0 validation record](packaging/windows/audits/0.3.0/VALIDATION.md)
documents the locally built ZIP pair, exact checksums, regression results and
Defender scans. Public upload and clean-machine interactive acceptance remain
pending; this is not yet a downloadable GitHub release.

See [Windows build instructions and validation checklist](packaging/windows/README.md)
for the build script, OSRA runtime layout and GitHub Actions preview workflow.
The [native OSRA build recipe](packaging/windows/OSRA-BUILD.md) includes pinned
source archives, Windows compatibility patches, portable runtime collection
and the recognition-test results (including a known failed stereo test).
The 0.3.0rc1 OSRA-inclusive local ZIP passed relocated-executable checks;
265 regression tests passed on each of native Windows and WSL (five optional
tests deselected). See the [candidate validation record](packaging/windows/audits/0.3.0rc1/VALIDATION.md)
for its checksum, local antivirus results and outstanding release checks.
The portable build compiles the screenshot selector ahead of time, so capture
does not require running PowerShell scripts on the end user's machine.
The new molecular-ring/scan-frame icon is included in the EXE and application
windows, with ten sizes for Windows display scaling. A standalone
`MolRecognizer.ico` is also included for desktop shortcuts.

The development preview includes DPI-aware dropdown arrows and native Windows
monitor fitting. Moving between screens adjusts the interface after you finish
dragging; normal manual resizing on the same monitor remains manual. Laptop
windows target 80% of the work area and external 1080p monitors target 70%,
expanding as needed to keep controls visible. Click the bottom-right **Fit**
button to refit without restarting. Extract each updated preview into a new
folder and run its EXE, not the previous copy.

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
2. In a portable build, `tools/osra/bin/osra.exe` beside `MolRecognizer.exe`.
3. `osra` or `osra.exe` on `PATH`.
4. A project-local executable at `.tools/osra/bin/osra` or
   `.tools/osra/bin/osra.exe`.

When a complete dictionary set is found beside the selected OSRA installation
(`share/osra`, `share`, or its `bin` directory), the app supplies absolute paths
for `chain.txt`, `spelling.txt` and `superatom.txt`. This avoids compiled-in
build paths and keeps recognition independent of the current working folder.

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

An OSRA-inclusive portable MolRecognizer build already contains its runtime;
skip the separate OSRA/Python installation steps when using that bundle.
Developers can use the [tested native build recipe](packaging/windows/OSRA-BUILD.md)
to compile OSRA 2.2.4 and package it with the application.

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
5. Double-click the rendered preview for side-by-side 2D/3D comparison.
   Rotate with left-drag, pan with right-drag, and scroll to zoom. If you edit
   the 2D structure, click **Render** again to update the 3D view.
6. Use **Save xyz** or **Copy xyz** as needed.

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

The [Windows portable builder](packaging/windows/README.md) can include a
supplied Windows runtime under `tools/osra/`. Obtaining/building a suitable
OSRA runtime and reviewing its redistribution requirements are separate
release steps, not something `pip` or `uv` performs at install time.

### Screenshot backends

**Portable Windows builds:** use a precompiled Windows-native selector and
the .NET Framework 4.x runtime. No PowerShell or runtime compilation is needed.
The interaction and full-resolution crop are the same as below.

**Python installations on Windows and WSL2/WSLg:** a Windows-native selection overlay is launched through
Windows PowerShell and .NET Windows Forms (included with Windows). No additional
Python dependency or Snipaste installation is needed. Move the cursor onto the
desired monitor before pressing the shortcut. The overlay freezes that monitor
in memory while you adjust the selection, preserving physical pixels even with
mixed display scaling. Only the confirmed crop is returned to MolRecognizer;
the dimming, border and buttons are not included. Neither the full-screen image
nor the crop is saved to a screenshot file. The recognizer may create its own
temporary input file as part of local recognition.

PowerShell must be allowed to compile the bundled C# helper with `Add-Type`;
workplace application-control policies may block it. Errors restore the app
and are reported instead of silently opening the old preview workflow.

**Other desktops (or when Windows PowerShell is unavailable):** a borderless
Qt selection overlay uses the existing capture backends:

| Priority | Backend | Works on |
|---|---|---|
| 1 | Qt `grabWindow` (built-in) | Native Linux X11, macOS, native Windows |
| 2 | `grim` (`sudo apt install grim`) | Native Linux Wayland |
| 3 | `scrot` (`sudo apt install scrot`) | Native Linux X11 |
| 4 | `gnome-screenshot` | GNOME desktops |

**Native Linux:** no extra packages needed on X11. On Wayland, install
`grim`: `sudo apt install grim`.

Select one monitor per capture; to capture a different display, cancel, move
the cursor there, and press the shortcut again.

### Reviewing difficult recognition

For difficult ring systems, use **Retry recognition** after the initial attempt
finishes (also available if recognition failed). Select a candidate in the list,
compare its ring closures and stereochemistry with the source, then click
**Use selected** only if you want to replace the current structure. Undo restores
the previous drawing, including manual edits. Re-render 3D after accepting a new
result before saving/copying XYZ. All candidates may still be wrong; a larger
capture from the original PDF/vector drawing often provides more useful detail
than enlarging an existing small PNG.

Retries use the original image pixels held in memory until another image is
recognized, the workspace is cleared, or the app closes—not the sidebar
thumbnail. They create one temporary PNG, deleted after completion, failure, or
cancellation, and never upload the image. Each of the three attempts is limited
to 15 seconds of OSRA processing plus a 10-second process grace period (up to
75 seconds total); you can cancel at any time.

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
