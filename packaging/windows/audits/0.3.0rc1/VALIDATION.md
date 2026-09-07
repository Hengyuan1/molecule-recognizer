# Windows 0.3.0rc1 — local validation, 2026-09-07

**Not published or cleared for public distribution.** This records successful
engineering checks, not completion of the [release audit](../../RELEASE-AUDIT.md).

## Exact candidate

- Build revision: `cd5bf785d722901d9cc75fcc7ba060287086f0da`.
- File: `MolRecognizer-0.3.0rc1-windows-x64.zip`, 157,968,430 bytes (~151 MiB).
- Local output: `dist/windows-rc1/`; the old Downloads app was not replaced.
- SHA-256: `ee1f5e027c2e1d7ead217b7a0f1d1158ad868014295b36aca63e2733b3b82b6c`.
- Native OSRA 2.2.4 included; no separate Python/Conda/WSL required to run it.
- Python 3.11.16, PySide6 6.11.0, RDKit 2026.3.4, NumPy 1.26.4,
  Pillow 12.2.0, PyInstaller 6.22.2.
- Unsigned; `BUILD-INFO.json` explicitly marks publication clearance pending.

This documentation was recorded after the build. Its later commit does not
change the candidate's recorded source revision or ZIP contents.

## Completed checks

| Check | Result |
| --- | --- |
| Native Windows regression suite | 265 passed, 5 deselected; 98.80 s |
| WSL regression suite | 265 passed, 5 deselected; 39.99 s |
| Relocated frozen EXE smoke checks | Passed with external Python/OSRA paths removed |
| Required Qt platform/SVG payload | Present; unwanted optional Qt components absent |
| Static normal/delay DLL import-presence audit | 330 PE files; no unresolved imports |
| ZIP CRC/content and file-set verification | All 1,428 files match the tested extracted build |
| Windows Defender: extracted app | Completed, exit 0; reported “found no threats” |
| Windows Defender: exact ZIP | Completed, exit 0; reported “found no threats” |

The smoke checks cover icons, the Qt window/SMILES editor, the packaged 3D
worker, XYZ export, comparison pane, compiled capture helper with synthetic
pixels, and bundled OSRA PNG-to-SDF recognition. They do **not** exercise a real
interactive desktop selection or establish recognition accuracy.

The five deselected tests are optional slow MolScribe tests. The regression
command on both platforms was:

```text
python -m pytest -m "not slow" -q --junitxml=<platform-report.xml>
```

Defender reported platform `4.18.26080.3`, engine `1.1.26080.3`, signatures
`1.459.99.0`; antivirus and real-time protection were enabled. Each scan used:

```text
MpCmdRun.exe -Scan -ScanType 3 -File <exact-candidate-path> -DisableRemediation
```

For this custom scan, `-DisableRemediation` scans archives, ignores exclusions,
and reports detections without quarantine/deletion; it does not disable
antivirus. See [Microsoft's command reference](https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus).
No security settings or exclusions were changed. A clean scan is not a
guarantee of safety, a code signature, or protection against future warnings.

Detailed generated records are retained locally in `dist/windows-rc1/`:
`BUILD-INFO.json`, `SMOKE-TEST.json`, `PE-IMPORTS.json`, `VALIDATION.json`,
`TESTS-WINDOWS.xml`, `TESTS-WSL.xml` and the ZIP checksum sidecar.
The PE check tests imported DLL presence, not ABI compatibility or every
optional runtime `LoadLibrary` path.

## Still required before publication

1. Complete dependency notices/license selection and any required matching
   source/relink materials. See the concrete RDKit/NumPy provenance gaps in
   the release audit; the source collection is not yet a cleared source asset.
2. Rebuild/recheck the final distributable after those materials are added.
3. Test that exact build interactively on a clean Windows machine/account:
   recognition, adjustable capture, mixed-DPI monitors, edits/undo, 3D/XYZ,
   closing/cancellation. Do not use confidential images for a public report.
4. Package the reviewed source materials and publish the ZIP, checksums and
   release notes as Release assets. Verify a downloaded copy before promoting
   the release as stable. No tag or release has been created for this candidate.
