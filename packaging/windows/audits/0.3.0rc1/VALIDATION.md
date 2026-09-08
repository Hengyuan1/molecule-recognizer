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

## Runtime signature check after Visual Studio installation

After the owner installed stable Visual Studio Community 2026, a read-only
PowerShell `Get-AuthenticodeSignature` check returned `Valid` for all 12 DLLs
whose names matched `^(msvcp|vcruntime|ucrtbase|concrt|vcomp)` under the tested
candidate's `_internal` folder. This check did not replace or modify any DLL.
Paths below are relative to `_internal`:

| DLL | File version | Signer |
| --- | --- | --- |
| `ucrtbase.dll` | 10.0.10240.16384 | Microsoft Corporation |
| `VCRUNTIME140.dll` | 14.44.35211.0 | Microsoft Windows |
| `VCRUNTIME140_1.dll` | 14.44.35211.0 | Microsoft Windows |
| `PySide6/MSVCP140.dll` | 14.44.35211.0 | Microsoft Windows |
| `PySide6/MSVCP140_1.dll` | 14.44.35211.0 | The QT Company Oy |
| `PySide6/MSVCP140_2.dll` | 14.44.35211.0 | The QT Company Oy |
| `PySide6/VCRUNTIME140.dll` | 14.44.35211.0 | Microsoft Windows |
| `PySide6/VCRUNTIME140_1.dll` | 14.44.35211.0 | Microsoft Windows |
| `rdkit.libs/msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll` | 14.40.33810.0 | Microsoft Windows Software Compatibility Publisher |
| `shiboken6/MSVCP140.dll` | 14.44.35211.0 | Microsoft Windows |
| `shiboken6/VCRUNTIME140.dll` | 14.44.35211.0 | Microsoft Windows |
| `shiboken6/VCRUNTIME140_1.dll` | 14.44.35211.0 | Microsoft Windows |

Individual file hashes are recorded in the existing `PE-IMPORTS.json` report.
This was a signature/version check, not a finding that every runtime is
Microsoft-signed or that its redistribution terms are satisfied. It does not
sign the application or establish that Windows reputation warnings will stop.

## Still required before publication

The owner subsequently confirmed that the candidate works well on their
Windows setup. This is a successful user-reported test; it does not establish
that the setup was a clean machine or enumerate each exercised workflow.

1. Resolve the OSRA/CImg license-compatibility question, then finish notice
   integration and any remaining source/relink requirements. The previously
   unidentified RDKit/NumPy inputs are now recorded in WHEEL-PROVENANCE.md;
   the source collection is not yet a cleared source asset.
2. Rebuild/recheck the final distributable after those materials are added.
3. Test that exact build interactively on a clean Windows machine/account:
   recognition, adjustable capture, mixed-DPI monitors, edits/undo, 3D/XYZ,
   closing/cancellation. Do not use confidential images for a public report.
4. Package the reviewed source materials and publish the ZIP, checksums and
   release notes as Release assets. Verify a downloaded copy before promoting
   the release as stable. No tag or release has been created for this candidate.

## Additional source-preparation validation — 2026-09-07

These are checks of the later working-tree preparation tools, not a rebuild
or a new antivirus scan of the candidate ZIP.

- WSL full suite after all source-preparation changes: **314 passed,
  5 optional MolScribe tests deselected**.
- Native Windows full suite before the final two path-validation tests were
  added: **309 passed, 3 skipped, 5 deselected**. The three Git-dependent
  packaging tests were skipped because Git was not on that environment's PATH.
- Native Windows rerun of both source-preparation test modules after those
  last changes: **64 passed, 3 skipped** for the same Git prerequisite.
- All three Git-dependent cases pass under WSL: the source ZIP uses committed
  files only, archived Git config/hooks are ignored, and object alternates
  are rejected. No downloaded build recipes are executed by these checks.
- Both real MSYS2 VCS payloads match the declared SHA-256 values for their
  pinned commit trees. All eleven additional vcpkg inputs match their recipe
  SHA-512 values. Source inventories omit transient signed-download parameters.

No final v0.3.0 binary/source ZIP, version bump, release tag or GitHub Release
was created. The tested RC and working Downloads installation are unchanged.
