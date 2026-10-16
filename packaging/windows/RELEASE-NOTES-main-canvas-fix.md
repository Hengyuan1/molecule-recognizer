# MolRecognizer — main-branch canvas fix (Windows + OSRA)

Tag: `v0.3.0-main-canvas-fix.1`.

**Use this build for the canvas fix without the experimental metal-coordination
changes.** It is built from `main`, not `agent/metal-coordination-wip`.
The earlier `v0.3.0-canvas-fix.1` preview included that unfinished metal work;
this package intentionally excludes it. The application still reports base
version 0.3.0.

## Download and run

Download **[MolRecognizer-0.3.0-main-canvas-fix-windows-x64.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0-main-canvas-fix.1/MolRecognizer-0.3.0-main-canvas-fix-windows-x64.zip)**.
Extract the whole ZIP into a short, user-writable folder, then run
`MolRecognizer.exe` in the extracted `MolRecognizer` folder. Keep all companion
files together. Close the older app first and update any shortcut to this copy.

Windows 10/11 x64; .NET Framework 4.x is used for screen capture. Python,
Conda, WSL and a separate OSRA installation are not required. The app is
unsigned; follow your organization's software/security policies.

## Scope

- Atom/bond edits and undo/redo preserve the canvas zoom and pan position.
- The scrollable workspace grows as needed without recentering the drawing.
- Manual zoom, pan and Fit structure remain available; loading new structures
  still fits them normally.
- Main's recognition, chemistry, metal behavior and 3D-generation code are
  unchanged. The experimental metal picker, coordinate-bond changes, label
  review and retry changes have **not** been merged into this build.

OSRA output still requires manual review of atom labels, rings and
stereochemistry. This patch does not improve metal recognition or validate
metal coordination geometry.

## Verification and checksums

The main-branch regression suite passed all 363 tests on Linux/WSL and 360
tests on native Windows (three Git-dependent skips). Five optional slow tests
were deselected on each platform. Both the packaged EXE and a freshly extracted
copy passed checks for the editor, stable zoom/pan during edits and undo/redo,
organic 3D/XYZ/comparison, and bundled OSRA recognition. Verified 8,953 ZIP
files, all 330 native import tables, and 264 unchanged application DLL/PYD
dependencies. These are automated checks, not clean-machine interactive
testing; screenshot self-tests use synthetic pixels. The package is unsigned
and has not had a new Defender scan.

Windows ZIP SHA-256:

```text
9464883234b0b81a5ef25e4350f46437547cb9cf3dd8b5a0829cf078e342bfd6
```

Application source ZIP SHA-256:

```text
f85a199bb56d6bc1737b732db9b30af36b146a116daf0b9ab012d3f80f71c120
```

Each attached ZIP has a `.zip.sha256` file. Compare it with:

```powershell
Get-FileHash .\MolRecognizer-0.3.0-main-canvas-fix-windows-x64.zip -Algorithm SHA256
Get-Content .\MolRecognizer-0.3.0-main-canvas-fix-windows-x64.zip.sha256
```

A matching checksum verifies integrity, not trust or a digital signature.

## Sources and provenance

Built from main commit `343a81b304e0ef28475cea438544f9184f3e00a7`.
The release tag also includes subsequent download documentation; application
source and tests match that build commit.

**[MolRecognizer-0.3.0-main-canvas-fix-sources.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0-main-canvas-fix.1/MolRecognizer-0.3.0-main-canvas-fix-sources.zip)**
contains the exact application source and build recipe, not the runnable app.
The same archive and `SOURCE-MANIFEST.json` are included inside the Windows
bundle. `BUILD-INFO.json` records the source commit and that experimental
metal-coordination code is excluded. Its awaiting-publication status is a
historical build-time record; this page records the later upload.

OSRA 2.2.4, native dependencies and their notices are unchanged from stable
v0.3.0. Their matching source archives, patches and build recipes remain in
[MolRecognizer-0.3.0-sources.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-sources.zip)
on the stable release. Use that archive for dependency sources and the
main-canvas-fix source archive for this application's code. Old release notes
inside the bundle describe the base release; `MAIN-CANVAS-FIX.txt` describes
this patch.
