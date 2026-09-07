# Changelog

## 0.3.0rc1 — Windows release candidate (not published)

- Started a component/source audit, collected exact OSRA/MSYS2 and Qt source
  archives, and recovered Qt's missing open-source license/attribution texts.
- Exclude unused Qt Virtual Keyboard, PDF, QML/Quick and software OpenGL
  payloads; validate required Qt plugins and record source revision/build status.
- Added safe source collection/inspection, PE import-closure audit tools,
  release-preparation regression tests, draft release notes and a blocking
  publication checklist. No public release or signature is implied.

- Added the approved blue molecular-ring/recognition-frame app icon as a
  vector master, transparent PNG and ten-size Windows ICO. Applied it to
  application/title-bar icons, Windows taskbar identity and all packaged EXEs;
  portable builds include a standalone ICO for desktop shortcuts and validate
  their embedded icon resources.
- Icon-update validation: 247 tests passed on native Windows and WSL (five
  optional tests excluded); rebuilt and installed portable EXEs passed icon,
  editor, 3D/XYZ, capture-helper and bundled OSRA smoke checks.
- Compiled OSRA 2.2.4 locally for native Windows x64 with patched GOCR/Open
  Babel, OCRAD and relocatable dictionaries/data/image codecs. Added build,
  DLL-collection and recognition-check scripts with pinned source hashes,
  compatibility patches, available notices and package provenance.
- The runtime was tested with its compiler tree unavailable and a system-only
  PATH: six generated image tests matched expected graphs; one chiral
  lactic-acid drawing was misrecognized, identically to existing Linux OSRA
  2.2.4. Recognition still requires review.
- Built an OSRA-inclusive portable ZIP. Both the relocated EXE and the copied
  Downloads EXE passed workbench/3D/capture-helper/OSRA smoke checks. Verified
  all 1,202 copied files and the ZIP checksum. The updated regression suite
  passed 239 tests on native Windows and WSL (five optional tests excluded).
- Fixed the Bond, ring, Save xyz and Copy xyz split-button arrows with a
  scalable chevron and a separate dropdown hit area, without overlapping text.
- Native Windows fitting now accounts for per-monitor DPI, title bars and
  taskbars, clamps oversized saved profiles, and waits until native dragging
  ends. Fit works on Windows as well as WSL; same-monitor manual resizing and
  maximized state are preserved. Sidebar spacing scales with the controls.
- Refitting keeps the molecule visible without changing its coordinates.
  Native Windows Python on a WSL network share is no longer mistaken for WSL.
- Added an opt-in Windows x64 portable builder and a GitHub Actions preview
  workflow. Complete builds require a supplied Windows OSRA runtime; explicit
  `no-osra` previews are labelled as editor-only, not complete recognizers.
- Isolated frozen 3D generation in a separate console helper, preserving
  asynchronous cancellation and binary transport without relaunching the GUI.
- Added a compiled C# screenshot helper for portable builds, removing their
  runtime PowerShell/Add-Type dependency while keeping the source/WSL path.
- Added executable-relative OSRA discovery, relocatable dictionary arguments,
  and external-process DLL/path handling for portable builds.
- Added relocated-EXE smoke checks, build metadata, available dependency
  notices, ZIP checksums and build/clean-Windows testing instructions.
- No OSRA-bundled Windows release has been published. Redistribution review
  and clean-machine interactive Windows testing remain required before release.
- Validation: 233 tests passed on native Windows and WSL (five optional
  MolScribe tests excluded). A native Windows no-OSRA preview was built and
  passed relocated-EXE checks for the workbench, separate 3D worker, XYZ,
  comparison pane and compiled selector (synthetic images, no desktop capture).
- Native desktop checks moved an isolated test window between a 250%-scaled
  laptop and two 100%-scaled external monitors and back, verifying full-frame
  work-area containment and dropdown rendering. The updated ZIP passed its
  relocated-EXE smoke checks and checksum verification.

## 0.2.0 — 2026-09-06

### Added

- Side-by-side 2D/3D comparison: double-click the rendered XYZ preview to open
  an interactive 3D pane beside the editable 2D canvas. Resize the panes with
  their divider, and close the comparison to restore the full canvas.
- A notice when the 2D structure differs from the last successful 3D render;
  successful re-rendering updates the open comparison pane.
- Reviewable OSRA retries with three explicit recognition presets, full-size
  source-image comparison, molecule statistics, cancellation, and undoable
  acceptance. No candidate is selected automatically.
- Updated README demonstration of the large-structure comparison workflow.

### Improved and fixed

- Ordinary N–H and O–H groups display as compact NH/NH₂/OH labels, preserving
  the molecular graph and special, isotopic, or stereo-marked hydrogens.
- Terminal nitriles are straightened locally without redrawing the rest of
  the recognized structure. Format initializes imported atom hybridization
  so triple bonds remain linear.
- WSLg retry review uses an in-window panel. The 3D comparison also remains
  inside the main window, avoiding native frame repositioning and modal
  window handoffs while staying on the same monitor.
- Retry cancellation, repeated opening/closing, focus restoration, panel
  cleanup, and monitor-dependent readability have regression coverage.
- This version also includes the recent adjustable screen capture,
  stereo-preserving layout/undo fixes, small-image atom-label recovery, and
  responsive shutdown improvements.

### Validation and limitations

- 196 tests passed; five optional MolScribe model-loading tests were excluded.
- WSLg desktop checks exercised retry-panel lifecycles and interactive 2D/3D
  comparison without changing the main window's geometry.
- OSRA can still misrecognize complex or low-resolution structures. Review
  connectivity and stereochemistry before using a structure as training data.
- OSRA remains a separately installed native executable; this version does
  not bundle OSRA or provide a standalone Windows installer.
