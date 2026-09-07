# MolRecognizer v0.3.0-rc1 — Windows portable preview

Draft only. Do not publish until RELEASE-AUDIT.md's blocking items are resolved.

## Windows download

Choose **MolRecognizer-0.3.0rc1-windows-x64.zip** from the release assets, not
GitHub's automatically generated "Source code (zip)". Extract the whole ZIP
into a local folder and run `MolRecognizer.exe`. Keep its companion files
and folders together. No separate Python, Conda, WSL or OSRA installation is
needed. Target: Windows 10/11 x64; recognition is performed locally.

The `.zip.sha256` asset verifies the downloaded ZIP against the published
build. The separate corresponding-source archive is for developers and
license/source access; ordinary users do not need it to run the application.

## What's included

- Native OSRA 2.2.4 with relocatable dictionaries and image codecs.
- Editable recognized 2D structures and SMILES, plus side-by-side 3D comparison.
- Save/copy XYZ, native adjustable region capture, mixed-DPI monitor fitting.
- Clear dropdown arrows and the new multi-resolution molecular-ring app icon.

## Important limitations

- This preview is unsigned. Windows may warn or company policy may block it.
  Do not disable antivirus or bypass your organization's software policies.
- Recognition is not error-free. Check atom labels, ring connectivity, bond
  orders and stereochemistry before using structures for ML training.
- A generated chiral lactic-acid test is misrecognized by the bundled OSRA,
  identically to the existing Linux OSRA version. This is not fixed by packaging.
- On native Windows, Alt+Y is an application shortcut while MolRecognizer has
  focus, not a system-wide shortcut. The Screenshot button is also available.
- MolScribe and its model weights are not included in the portable ZIP.

For bugs, open a GitHub issue with the app version, Windows version, display
scaling and steps to reproduce. Include an example image only if you have
permission to share it; do not upload proprietary research or private logs.
