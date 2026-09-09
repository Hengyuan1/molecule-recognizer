# Final Windows ZIP — interactive acceptance

Record the tested ZIP's SHA-256 and `BUILD-INFO.json` source revision. Previous
tests of 0.2.0/0.3.0rc1 do not automatically count as tests of this exact ZIP.

- ZIP / SHA-256:
- Windows version and CPU architecture:
- Python/Conda/WSL/OSRA absent (clean machine), or present (developer machine):
- Laptop and external-monitor resolution/scaling:
- Test date / tester:

1. Extract to a new local folder (including a space in the path). Open the EXE
   without installing Python or changing PATH. Do not run inside the ZIP.
2. Load SMILES; edit atoms and bonds; delete an atom; Undo/Redo must restore
   connectivity, bond orders and stereo. Check Bond/ring/XYZ dropdowns.
3. Open a reference structure image. Compare rings, labels, wedge/dash bonds
   and SMILES. Retry recognition; choose/keep/cancel candidates.
4. Capture on each monitor. Draw, move and resize the box; accept and cancel.
   Try Alt+Y with the app focused. No confidential screenshots are needed.
5. Render 3D, double-click for side-by-side comparison, rotate/pan/zoom,
   copy/save XYZ and verify Angstrom/Bohr choices.
6. Move/resize between displays. Use A−/A+/Fit; check menus and window closure.
   Close while idle and while recognition or 3D generation is running.
7. Help → Third-party licenses opens the local notices. Check source-access
   instructions and confirm the companion source ZIP is available at release.
8. Note any Windows warning exactly. Do not disable Defender or organizational
   restrictions. An unsigned-app warning is not an antivirus test result.

Results / failures:

Publication additionally requires resolution of the recorded CImg compatibility
question. Passing these checks is functional acceptance, not a legal opinion.
