# Changelog

## 0.3.0 — Windows portable release

- Publish the tested native Windows x64 ZIP with bundled OSRA 2.2.4, plus
  matching dependency sources/build recipes and SHA-256 checksums on
  [GitHub Releases](https://github.com/Hengyuan1/molecule-recognizer/releases/tag/v0.3.0).
  No Python, Conda, uv, WSL or separate OSRA installation is needed to run it.
- Include the application icon, readable ring/charge icons, native DPI-aware
  monitor fitting, adjustable capture, and side-by-side 2D/3D comparison.
- Preserve the scoped upstream legacy-CImg permission and original dependency
  notices. The release tag points to exact built source `ae2877a`; the tested
  ZIPs are unchanged. Build-time preparation records remain historical.
- Final validation: 358 passing WSL tests; 355 passing native Windows tests,
  three Git-dependent skips; five optional MolScribe tests deselected on each.
  Verified 8,950 extracted files, 330 native import tables and 90 source
  payloads. Extracted-EXE smoke checks passed and Defender scans of the Windows
  ZIP and extracted app reported no threats. These are not a security guarantee
  or clean-machine test; the app remains unsigned and OSRA needs manual review.
- Separate Windows and Linux setup/usage in the README, with direct Windows
  downloads and clear native PowerShell/Conda versus optional WSLg instructions.

### Historical preparation — 2026-09-08

- Prepare a stable-version Windows package while the OSRA/CImg compatibility
  inquiry remains open. No public upload or license exception is implied.
- Integrate original Qt and native wheel notices, including copyright-bearing
  CImg/GREYCstoration and Cairo headers, with a component/license-option map.
- Add Help → Third-party licenses, source-access/library-replacement
  instructions, final release notes and a clean-Windows acceptance checklist.
- Verify notice hashes against their exact source inventories and reject
  stale package versions, changed notices or unexpected material files.
- Add exact binary/source ZIP pairing, safe extraction, extracted-executable
  smoke tests, PE import checks and optional Defender scan reporting.
- Keep the existing installed app untouched; build/test in separate folders.
- Built the matching binary/source ZIP pair from `12e93ba`; verified 8,947
  extracted files, 330 native import tables and 90 source payload hashes.
  WSL: 349 tests passed. Native Windows: 346 passed, three Git-dependent skips.
  Five optional MolScribe tests were deselected on each platform. Extracted-EXE
  smoke checks passed; Defender reported no threats in the folder or ZIP.
  OSRA's known failed stereo drawing remains documented (six of seven matches).

## 0.3.0rc1 — Windows release candidate (not published)

- Started a component/source audit, collected exact OSRA/MSYS2 and Qt source
  archives, and recovered Qt's missing open-source license/attribution texts.
- Exclude unused Qt Virtual Keyboard, PDF, QML/Quick and software OpenGL
  payloads; validate required Qt plugins and record source revision/build status.
- Added safe source collection/inspection, PE import-closure audit tools,
  release-preparation regression tests, draft release notes and a blocking
  publication checklist. No public release or signature is implied.
- Built the reduced-Qt 0.3.0rc1 candidate from `cd5bf78`: 265 tests passed on
  each of native Windows and WSL (five optional tests deselected), relocated
  OSRA/editor/3D/XYZ/capture-helper smoke checks passed, and all 330 PE files
  passed the static DLL import-presence audit. Saved source collection and
  validation records; clean-machine interactive testing and the remaining
  third-party redistribution review are still pending.

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
