# Portable distribution notices

Molecule Recognizer's own code is MIT-licensed. Bundled third-party components
retain their respective licenses; they are not relicensed under the project's
MIT license. Installed distribution metadata and available license files are
copied into `licenses/`; exact package versions are in `BUILD-INFO.json`.

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
