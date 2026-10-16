# MolRecognizer canvas-fix preview — Windows x64 with OSRA

Tag: `v0.3.0-canvas-fix.1`. This is a preview from
`agent/metal-coordination-wip`, not a merge into `main` or a replacement for
stable v0.3.0. The application still reports base version 0.3.0.

## Download and run

Download **[MolRecognizer-0.3.0-canvas-fix-windows-x64.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0-canvas-fix.1/MolRecognizer-0.3.0-canvas-fix-windows-x64.zip)**
(about 161 MiB). Extract the entire ZIP into a short, user-writable folder,
then open `MolRecognizer.exe` inside `MolRecognizer`. Keep all companion files
and folders together. No Python, Conda, WSL or separate OSRA installation is needed.
Close an older running copy before launching the new one.

Target: Windows 10/11 x64; .NET Framework 4.x is used for screen capture.
The app is unsigned. Follow your organization's software/security policies;
do not disable security protections to run it.

## Included changes

- Adding/deleting atoms and bonds, changing labels, and undo/redo preserve
  the canvas zoom and position. Manual zoom, pan and Fit structure remain
  available; loading a new structure still fits it normally.
- Includes all earlier picker-fix changes: readable common-metal buttons,
  coordinate-bond editing/export, explicit label/metal review, and 2×/4× OCR
  retry inputs.
- Includes the adaptive-threshold white-margin fix to reduce false frames.

Metal/coordination work is experimental. **No new metal 3D-generation method
is included**; automatic metal reformatting and metal/unknown-label 3D
generation remain disabled. OSRA can still misrecognize ring connections,
labels and stereochemistry. Check the graph and SMILES before using results.

## Verification

- 417 native Windows regression tests passed; three Git-dependent tests were
  skipped and five optional slow tests were deselected.
- The packaged EXE and a freshly extracted copy both passed automated checks
  for stable editing zoom/pan, undo/redo, organic 3D/XYZ, the comparison pane,
  metal picker, coordinate bonds, and bundled OSRA recognition/adaptive retry.
- Verified 8,953 ZIP files and import closure for 330 native binaries.
  All 264 application DLL/PYD dependencies are byte-identical to stable 0.3.0;
  bundled OSRA and its notices are unchanged.
- These are automated checks, not clean-machine interactive testing. Screen
  capture testing uses synthetic pixels. No new Defender scan was run.

SHA-256 of the Windows ZIP:

```text
dd2e9185307ffedaece787ac485312733c46c72681d24156e5c988a8a9bc7002
```

The matching `.zip.sha256` is attached. In PowerShell, use
`Get-FileHash .\MolRecognizer-0.3.0-canvas-fix-windows-x64.zip -Algorithm SHA256`
and compare the value. A checksum is not a digital signature or security guarantee.

## Exact sources and build provenance

The attached **[LOCAL-TEST-SOURCE.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0-canvas-fix.1/LOCAL-TEST-SOURCE.zip)**
contains the exact application source snapshot, tests and local build recipe.
It is also inside the Windows bundle, with `SOURCE-MANIFEST.json`. It is for
developers, not the ZIP to run. Its SHA-256 is:

```text
23d250dcd7451a99639308922f4324d9fded910845c67d88c297b3a554293942
```

The build used source base `3177b7ccc8c65cbda246794bd4848c270de35b41` plus the
canvas fix. Its application source and tests match this preview's tag;
release/download documentation was added afterwards. The tested binary ZIP
has not been repacked. Its `LOCAL-TEST.txt` and `BUILD-INFO.json` retain the
historical "not published" status recorded at build time; this release page
records its subsequent publication as a preview.

Unchanged OSRA/native dependency sources, patches and build recipes are in
**[MolRecognizer-0.3.0-sources.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-sources.zip)**
on the stable release, with its checksum. Use that archive for dependency
sources and `LOCAL-TEST-SOURCE.zip` for this preview's application sources.
License notices and source-access instructions remain included in the app.
