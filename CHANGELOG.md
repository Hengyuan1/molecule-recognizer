# Changelog

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
