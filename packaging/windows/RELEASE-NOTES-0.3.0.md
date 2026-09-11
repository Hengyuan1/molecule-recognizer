# MolRecognizer v0.3.0 — Windows portable application

**Prepared for final verification. Not published.** David Tschumperlé's explicit
alternative-license permission for legacy CImg is recorded in
`CIMG-PERMISSION.md`. Final archive verification and owner publication approval
remain separate steps. Do not remove this status merely because tests pass.

## Download and run (after publication)

Download **MolRecognizer-0.3.0-windows-x64.zip**, extract the entire archive,
and open `MolRecognizer.exe` inside the `MolRecognizer` folder. Keep the
companion files together. No Python, Conda, uv, WSL or separate OSRA install
is needed. Target: Windows 10/11 x64 with .NET Framework 4.x.

The application processes images locally. It does not upload structures to a
recognition website. A shortcut may point to the EXE in a permanent user-writable
folder; moving the folder later requires updating that shortcut.

The `.zip.sha256` files verify each ZIP. `MolRecognizer-0.3.0-sources.zip` is
the companion source/patch/build-recipe archive, not the runnable application.
GitHub's automatic "Source code" downloads do not replace this dependency
source archive. Ordinary users need only the Windows application ZIP.

## Included

- Native OSRA 2.2.4 with dictionaries, raster image codecs and required DLLs.
- IQmol-inspired 2D editor, reviewable recognition retries and live SMILES.
- Interactive side-by-side 3D comparison; save/copy XYZ in Angstrom or Bohr.
- Adjustable full-resolution region capture on laptop or extended monitors.
- Native Windows mixed-DPI fitting, readable dropdown arrows and multi-size icon.
- Larger, font-independent ring and charge icons that follow interface scaling.
- Scoped upstream CImg permission with its request, permalink and license text.
- Original dependency notices, source-access instructions and build checksums.
  Help → Third-party licenses opens the bundled notice folder.

## Known limitations

- The app is unsigned. Windows may show an origin/SmartScreen warning; a
  malware detection is different. Do not disable antivirus or bypass workplace
  policies. Verify the publisher/source and checksum before running a download.
- OSRA recognition is not guaranteed. Review labels, rings, connectivity,
  bond orders and stereochemistry before collecting structures for ML training.
  The generated chiral lactic-acid regression drawing is a known OSRA error,
  also observed with Linux OSRA 2.2.4; packaging does not fix it.
- Native Windows Alt+Y works while the app has keyboard focus; it is not a
  system-wide Windows hotkey. The Screenshot button is also available.
- MolScribe/PyTorch/model weights are not bundled.
- Automated tests do not replace testing the exact final ZIP interactively
  on a clean Windows machine. See `TEST-CHECKLIST.md` with the release assets.

Report bugs at https://github.com/Hengyuan1/molecule-recognizer/issues with the
app/Windows versions, display scaling, steps and an example you may legally
share. Do not attach proprietary research screenshots or private logs.
