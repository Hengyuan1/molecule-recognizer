# Windows 0.3.0 — verified release preparation, 2026-09-10

**Verified locally; owner reports successful initial testing; unsigned; binary
release not published.** Public-release approval remains separate from these
checks. This is not a legal certification or a guarantee of recognition
accuracy/security.

## Exact archive pair

Both archives use source revision `ae2877a6bd93a724cc3cc87ac63ee1d61368ec6a`.
The native Windows build used a clean `git archive` snapshot, installed into
the existing isolated build environment without changing dependency versions.
It includes the larger icons from `9db41d0` and the recorded CImg permission.
The owner's unrelated `TODO.md` changes were excluded.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `MolRecognizer-0.3.0-windows-x64.zip` | 166683576 | `6d82c73696eea6a1a56294668c19df79b44d62377446fa703631e1aac9b2b199` |
| `MolRecognizer-0.3.0-sources.zip` | 986680310 | `90e6b1804afce3679ad009b7ff4e65fd20e9b59785f56a8bcae4ef2e8089be33` |

Assets, receipts and full reports are under `dist/windows-0.3.0-final/`,
outside Git. Ordinary users need only the Windows ZIP. The matching source
ZIP contains the exact application tree and 89 dependency source/build inputs;
GitHub's automatic source download does not replace it. If publishing these
exact assets, their release tag must identify the built revision above, not
a later documentation-only commit.

## Upstream permission and original notices

David Tschumperlé's [explicit permission](https://github.com/GreycLab/CImg/issues/492#issuecomment-5618853659)
and the quoted request were verified through GitHub's API. See
[CIMG-PERMISSION.md](../../CIMG-PERMISSION.md) and its JSON evidence record for
the precise scope, ordinary CeCILL 2.1 selection and GPL-combination route.
This does not grant rights held by other contributors or waive unrelated terms.

The package includes 7,751 hash-inventoried material files plus `MATERIALS.json`.
The permission JSON SHA-256 is
`37317ba26cfc06293b91a377d50939dc421abc1224464ab52dd4b0a67bb20d85`;
the material-index SHA-256 is
`6dcbef7b7e71347b1926012b3972b3e9138e12b42de852426b6eda6445f54ff1`.
The binary's permission record and material index match `BUILD-INFO.json`.
The corresponding application source includes the same permission, license
text and icon code. Original CImg and GREYCstoration header notices remain
byte-for-byte identical to the September 8 package.

## Completed checks

- **358 passed** under WSL; five optional MolScribe tests deselected.
- **355 passed, three skipped** under native Windows; five optional MolScribe
  tests deselected. The Git-dependent skips passed under WSL.
- All **8,950 extracted ZIP files** checked byte-for-byte against the archive.
- Matching source version/revision and all **90 inner source payload hashes**
  verified; 92 source ZIP files total, with no missing/unlisted entries.
- **330 native binaries** passed PE import-presence checks.
- All **326 DLL/PYD dependency files** and `tools/osra/bin/osra.exe` match the
  earlier package byte-for-byte. No OSRA preprocessing or recognition code
  was disabled or changed for the license update.
- Both the builder's relocated EXE and the separately extracted ZIP's EXE
  passed system-only-PATH smoke checks: application icons, large ring/charge
  symbols, Qt/SMILES editor, license access, separate 3D worker, XYZ/comparison,
  capture-helper synthetic pixels, and OSRA PNG-to-SDF benzene recognition.
- Defender custom scans of the **extracted app and final Windows ZIP** both
  returned exit code 0 and reported no threats. Engine `1.1.26080.3`, signatures
  `1.459.153.0`; antivirus and real-time protection were enabled. No exclusions
  or security-policy changes were made. The source ZIP was not malware-scanned.
- No private desktop images or research structures were captured by testing.

Full reports are in the assets' `validation/` directory, including dependency
comparison and the exact extracted-EXE report. Scans are observations, not
code signing or a safety guarantee. The existing known OSRA stereo-recognition
limitation remains documented in the release notes; this run does not claim
that all recognition-accuracy cases pass.

## Validation-path issue and successful retry

The first extraction attempt exceeded legacy Windows path limits because of
the long temporary validation prefix. It stopped before executable checks;
its report is retained as `validation/INITIAL-LONG-PATH-FAILURE.json`.
The exact same ZIP was then validated successfully under a shorter temporary
prefix. No archive contents or Windows long-path settings were changed.

The longest ZIP member name is 160 characters. For the owner's normal Downloads
extraction layout, including the extra folder suggested by Extract All, the
longest complete path is 246 characters. Prefer a short local extraction path
and avoid deeply nested folders on systems with legacy path limits.

## Owner handoff and remaining steps

A checksum-verified Windows ZIP, receipt, release notes and checklist were
copied to `C:\Users\hengyuan\Downloads\MolRecognizer-0.3.0-final`.
The working `MolRecognizer-0.3.0-larger-icons` installation was not replaced.
The owner previously approved that UI build. After testing the final ZIP,
they reported: "I tested, looks good so far." This is successful initial owner
testing on their Windows setup, not confirmation of every checklist item or
of a clean-machine test. No binary/source ZIP was modified after that report.

The owner requested committing and pushing the current branch. Release-tag
creation and binary/source asset publication remain separate actions requiring
approval. At that stage, finalize publication wording, publish the matching
binary/source/checksum pair and verify the downloaded assets. A source-branch
push alone does not publish a downloadable Windows release.
