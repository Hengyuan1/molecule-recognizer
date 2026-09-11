# Portable distribution notices

Molecule Recognizer's own code is MIT-licensed. Bundled third-party components
retain their respective licenses; they are not relicensed under the project's
MIT license. Installed distribution metadata and available license files are
copied into `licenses/`; exact package versions are in `BUILD-INFO.json`.

For the prepared 0.3.0 Windows bundle, start with
`licenses/release-materials/DEPENDENCY-LICENSES.md`. It maps components to
original notices and records selected license alternatives. The matching
source/patch/build-recipe asset is `MolRecognizer-0.3.0-sources.zip`; see
`SOURCE-ACCESS.md` beside the EXE. The scoped CImg alternative-license permission
is preserved in `licenses/release-materials/CIMG-PERMISSION.md` and its JSON
record. Publication is a separate step; neither asset is claimed public yet.

This software uses the Qt libraries under LGPLv3 and includes OSRA's CImg
image-processing code, copyright David Tschumperlé. For the covered legacy
CImg code, this distribution elects the ordinary CeCILL 2.1 alternative granted
by David and its GPL-combination route. Original CeCILL-C notices, the scoped
permission and full license texts are retained and accessible through
Help → Third-party licenses. MolRecognizer's MIT terms do not replace them.

Upstream projects and corresponding source locations:

- Python: https://www.python.org/downloads/source/
- PySide6 / Shiboken / Qt for Python: https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt: https://download.qt.io/archive/qt/
- RDKit: https://github.com/rdkit/rdkit
- NumPy: https://github.com/numpy/numpy
- Pillow: https://github.com/python-pillow/Pillow
- PyInstaller bootloader: https://github.com/pyinstaller/pyinstaller

The Qt libraries remain separate DLLs in `_internal/`. Before public release,
the distributor must review the actual collected binaries, notices, exact
corresponding source availability and all applicable redistribution obligations.
Automated copying of license files is not a substitute for that review.

OSRA is optional in preview builds. When included, its own license/dependency
notices and source provenance must be under `tools/osra/licenses/` and
`tools/osra/SOURCE-NOTICE.txt`. The build does not download, buy, or grant rights
to redistribute any OSRA binary. OSRA sources/build information:
https://sourceforge.net/p/osra/wiki/Download/
