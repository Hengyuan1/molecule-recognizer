# MolRecognizer v0.3.0 — Windows portable application

The first standalone Windows release includes **OSRA 2.2.4** for local image
recognition. No Python, Conda, uv, WSL or separate OSRA installation is needed.

## Download and run

1. Download [MolRecognizer-0.3.0-windows-x64.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-windows-x64.zip) (159 MiB).
2. Extract the **entire ZIP** into a short, permanent, user-writable folder,
   such as `C:\Users\YourName\Apps`.
3. Open `MolRecognizer.exe` inside the extracted `MolRecognizer` folder.
   Keep `_internal`, `tools`, the worker EXE and all companion files together.
   Do not run it inside the ZIP or move only the main EXE.

Target: **Windows 10/11 x64**, with .NET Framework 4.x for screen capture.
For installation, screenshots and editing instructions, see the
[Windows and Linux usage guide](https://github.com/Hengyuan1/molecule-recognizer/blob/main/README.md).

The application processes images locally. It does not upload structures to a
recognition website. A shortcut may point to the EXE in a permanent user-writable
folder; moving the folder later requires updating that shortcut.

The `.zip.sha256` files let you check each ZIP's integrity.
[MolRecognizer-0.3.0-sources.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-sources.zip)
(941 MiB) is the companion source/patch/build-recipe archive, not the runnable application.
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

## Exact build and verification

The `v0.3.0` tag identifies the built source revision
`ae2877a6bd93a724cc3cc87ac63ee1d61368ec6a`. Both ZIPs are unchanged from the
final archives tested by the owner; newer README/audit-only commits are on
`main`, not a different executable build.

| Archive | SHA-256 |
| --- | --- |
| `MolRecognizer-0.3.0-windows-x64.zip` | `6d82c73696eea6a1a56294668c19df79b44d62377446fa703631e1aac9b2b199` |
| `MolRecognizer-0.3.0-sources.zip` | `90e6b1804afce3679ad009b7ff4e65fd20e9b59785f56a8bcae4ef2e8089be33` |

The [validation record](https://github.com/Hengyuan1/molecule-recognizer/blob/main/packaging/windows/audits/0.3.0-final/VALIDATION.md)
documents 358 passing WSL tests and 355 passing native Windows tests (three
Git-dependent Windows skips; five optional MolScribe tests deselected on each),
extracted-EXE smoke checks, source pairing and native dependency checks.
Defender scans of the extracted app and Windows ZIP reported no threats;
these results are not a digital signature or safety guarantee.

**Build-time status notes:** the archives retain their original preparation
documents and validation metadata, including statements such as "not published"
and `publication_cleared: false`. Those record the state before the owner
authorized this release. They are kept unchanged to preserve the exact tested
files and hashes; this GitHub release page records their subsequent publication.
The [scoped CImg permission](https://github.com/Hengyuan1/molecule-recognizer/blob/v0.3.0/packaging/windows/CIMG-PERMISSION.md)
and original third-party notices are included. Publication does not change any
component's license or grant rights beyond the recorded permission.

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
- The owner reports successful initial testing on their Windows setup;
  automated checks and that feedback are not a completed clean-machine test.
  See the [test checklist](https://github.com/Hengyuan1/molecule-recognizer/blob/v0.3.0/packaging/windows/TEST-CHECKLIST.md).

Report bugs at https://github.com/Hengyuan1/molecule-recognizer/issues with the
app/Windows versions, display scaling, steps and an example you may legally
share. Do not attach proprietary research screenshots or private logs.
