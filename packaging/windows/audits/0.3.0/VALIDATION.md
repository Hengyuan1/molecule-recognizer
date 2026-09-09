# Windows 0.3.0 — local release preparation, 2026-09-08

**Not published; not signed; CImg compatibility clarification remains pending.**
This is a record of the exact local artifacts, not legal clearance, a malware
guarantee, or a claim of clean-machine interactive acceptance.

## Exact artifact pair

Both archives identify source revision
`12e93ba1f396ef6c60b3a76220593ba196ccfdc2`. The Windows build used a clean
`git archive` export installed into the existing isolated build environment,
without updating dependencies. The owner's unrelated TODO changes were not
committed or included in the source export.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `MolRecognizer-0.3.0-windows-x64.zip` | 166667358 | `a6b7ec618eb9aa092b6a93070f32901fc03826f455cb30eb71586972310e1cc7` |
| `MolRecognizer-0.3.0-sources.zip` | 986670080 | `fe6b65f2a4c225e024330fd1b180493fa787f93f0300451481c14fae2c39a6d8` |

Local assets are under `dist/windows-0.3.0-prepared/` (ignored by Git).
They include individual checksum receipts, draft release notes, the final
interactive test checklist and platform test reports. No public download is
claimed. The source ZIP is for source access/development, not required to run
the application; do not replace it with GitHub's automatic source archive.

## Completed automated checks

- **349 passed** under WSL; five optional MolScribe tests deselected.
- **346 passed, three skipped** under native Windows; five optional MolScribe
  tests deselected. The three skips require Git on Windows PATH and passed
  under WSL. The clean Windows source export was tested again with the same
  results, with JUnit output saved alongside the release assets.
- The notice build contains **7,748 inventoried material files**, plus their
  integrity index: original Qt/wheel/header notices, component/license-option
  map, Microsoft runtime notice and source/library-replacement instructions.
  The builder verified hashes and exact package-version matching before use.
- **8,947 files** in the binary ZIP were extracted into a fresh Windows path
  containing spaces and checked byte-for-byte against the ZIP.
- The source ZIP's version/revision match the binary. All **90 source payloads**
  (89 dependency source/build-recipe inputs plus the application archive) passed
  inner SHA-256 checks; no unlisted files were accepted (92 files total).
- **330 native binaries** passed the PE import-presence audit. All **326
  dependency DLL/PYD files** are byte-for-byte identical to the earlier RC;
  its vendor/runtime provenance evidence remains applicable to those bytes.
- Both the builder's relocated EXE and the separately extracted ZIP's EXE
  passed smoke tests with a Windows-system-only PATH: icons/editor/SMILES,
  license access/source instructions, separate 3D worker, XYZ/comparison,
  compiled capture-helper synthetic pixels and bundled OSRA PNG-to-SDF.
- No desktop screenshots or user research images were captured by these checks.

The native build used Python 3.11.16, PySide6 6.11.0, RDKit 2026.3.4,
NumPy 1.26.4, Pillow 12.2.0 and PyInstaller 6.22.2. OSRA remains 2.2.4;
neither the recognition algorithm nor its legacy CImg license was changed.

## Recognition accuracy check

The broader seven-drawing OSRA check again matched six reference structures:
benzene, aspirin PNG/JPEG/BMP, caffeine and nitrile. The chiral lactic-acid
drawing remains a known upstream recognition limitation:

- Expected: `C[C@H](O)C(=O)O`
- Recognized: `CC(CO)C(O)O`

The recognition script correctly exits nonzero for this case. Its result is
not hidden or counted as a passing accuracy test. The same failure was recorded
for the previous native Windows and Linux OSRA builds. Source images, bond
orders and stereo still require user review before ML data collection.

## Security scans

Both the extracted folder and final ZIP scans completed with exit code 0 and
reported no threats. Full results are retained in
`dist/windows-0.3.0-prepared/validation/VALIDATION.json`; validation completed
at `2026-09-09T04:31:27Z` (September 8 local time). Defender signatures were
`1.459.120.0`, engine `1.1.26080.3`.
Defender reported antivirus and real-time protection enabled. No exclusions,
security-policy changes or suppression of findings were used. The custom scans
use `-DisableRemediation` to report findings without changing files; that flag
does not disable system protection.

## Remaining owner/publication checks

A separate owner test copy was extracted from the same scanned ZIP into
`C:\Users\hengyuan\Downloads\MolRecognizer-0.3.0-test\MolRecognizer`.
All 8,947 files were checked against the ZIP during extraction. The existing
working installation and Desktop shortcut were not changed.

- Resolve the specific CImg/GPL compatibility question; the maintainer's
  supportive explanation has not been treated as a new license exception.
- Complete `TEST-CHECKLIST.md` on this exact ZIP, preferably on a clean Windows
  machine, including real region capture and mixed-DPI monitor interaction.
- After clearance, finalize publication wording/status, verify any changed
  artifacts again, and publish the matching binary/source/checksum assets.
  No release tag, public GitHub Release or installed-app replacement was made.

For future builds, stage both build intermediates **and notice inputs** on local
Windows storage. The thousands of path/integrity checks are slow over a WSL
share. One older preflight/build tree was stopped and superseded by the build
using identical notices on local NTFS; it produced no release ZIP.
