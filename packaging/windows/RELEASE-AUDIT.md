# Windows release audit — 0.3.0 preparation and RC history

Status: **CImg permission recorded; final 0.3.0 repackaging/verification in progress;
public distribution still pending**.
This is an engineering inventory and release checklist, not legal advice or
a certification that every bundled license obligation has been satisfied.

## Explicit CImg permission — 2026-09-10

David Tschumperlé (`dtschump`) quoted the request for ordinary CeCILL as an
alternative for CImg 1.2.7 bundled with OSRA, insofar as he holds its copyrights,
and replied: "If it helps, you have my permission—yes."
The [public comment](https://github.com/GreycLab/CImg/issues/492#issuecomment-5618853659)
and [request](https://github.com/GreycLab/CImg/issues/492#issuecomment-5612079056)
were verified using the GitHub API. Exact bodies and metadata are preserved in
[CIMG-PERMISSION.json](CIMG-PERMISSION.json); the scoped license choice is
explained in [CIMG-PERMISSION.md](CIMG-PERMISSION.md).

This addresses the specific legacy-CImg permission gap. The distribution
elects ordinary CeCILL 2.1 and its article 5.3.4 GPL-combination route for the
covered code. The reply does not specify a version; 2.1 is the distributor's
recorded selection, not a quotation from the reply. Original CImg/CeCILL-C
and GREYCstoration notices remain unchanged. No preprocessing or recognition
code is removed, no native OSRA binary changes, and no rights held by others
or unrelated license obligations are waived by this record.

The owner tested and approved the larger toolbar symbols in `9db41d0`.
That build passed 353 WSL tests and 350 Windows tests (three Git-dependent
skips; five optional MolScribe tests deselected), plus packaged OSRA/editor/3D
smoke checks. This is owner acceptance on their Windows setup, not evidence
of a clean-machine test. Its Downloads copy remains the working installation.

The final matching archive pair will include both this permission and those
icon changes, built from a clean committed snapshot. Previous archive hashes
and scan reports below are historical evidence, not results for new bytes.
Public upload is not authorized by successful automated checks alone.

## Historical 0.3.0 preparation — 2026-09-08

The owner reports receiving a supportive reply from CImg's maintainer and
having replied to his compatibility question. This is not recorded as a new
license grant. At the owner's request, work continues on final-version notice
integration, source packaging and Windows validation **while public upload
remains pending**. No recognition algorithm or CImg license is changed.

The source version is now 0.3.0 for local preparation. `release_materials.py`
checks original notice hashes against exact source inputs, recovers Qt notices,
and includes `DEPENDENCY-LICENSES.md`, source/replacement instructions and the
original CImg/GREYCstoration notices. Cairo's per-file copyright headers are
also preserved. `build.py` requires these materials and a source revision for
stable OSRA builds, and verifies their package versions before building.
The GUI exposes the bundled notices through Help → Third-party licenses.

`validate_release.py` checks the exact extracted ZIP, matches it to the source
ZIP revision, verifies every inner source hash, runs PE/import and relocated
EXE checks, and optionally records Defender scans. The final interactive
acceptance form is `TEST-CHECKLIST.md`. These tools do not publish a Release,
tag, install over the owner's working copy, or claim licensing clearance.
The [0.3.0 validation record](audits/0.3.0/VALIDATION.md) identifies the exact
matching ZIPs, source commit, 349 passing WSL tests / 346 passing native Windows
tests (three Git-dependent skips), 8,947 verified extracted files, PE closure,
extracted-EXE smoke checks and both clean Defender scans. The broader OSRA
accuracy check retains its known failed stereo case (six of seven match).
All 326 dependency DLL/PYD files are unchanged from the RC. Assets and full
machine-readable reports are in `dist/windows-0.3.0-prepared/`. These results
are separate from the historical RC results below.

## Findings from the tested 0.2.0 portable bundle

- All 39 MSYS2 package bases/versions owning the 51 OSRA dependency DLLs and
  11 image plugins are recorded by the runtime's BUILD-INFO.json. Matching
  `.src.tar.zst` packages have been collected from the official MSYS2 archive.
- The six locally compiled source archives match the original build's pinned
  hashes. Local compatibility/relocation patches and build recipes are retained.
- The installed PySide wheels declare LGPL/GPL alternatives in metadata but
  their collected license files contain only the commercial-license text.
  Recovered LGPL/GPL texts and third-party notices from the matching 6.11.0
  Qt/PySide source archives must accompany the candidate.
- PyInstaller pulled in the unused GPL-only Qt Virtual Keyboard plugin, QML/
  Quick dependencies, PDF plugin and optional software OpenGL renderer. These
  are excluded from 0.3.0rc1; the existing user installation is untouched.
- MSYS2 labels JBIG-KIT 2.1 `GPL-2.0` without a later-version suffix. The actual
  `libjbig/jbig.c` header in the 2.1 source says version 2 **or any later version**.
  Record the upstream grant rather than treating the shorthand as GPLv2-only.
- OSRA's own source is GPL-2.0-or-later; OCRAD 0.23 uses GPLv3. The linked OSRA
  binary and its combined dependencies need GPLv3-compatible distribution
  terms. Do not imply that the executable as a whole is GPLv2-only, or that
  the application's MIT license covers third-party binaries.
- NumPy's OpenBLAS DLL identifies GCC **10.3.0**, which is different from the
  OSRA runtime's GCC **16.2.0**. Collecting the latter's source does not establish
  matching source coverage for NumPy's statically linked runtime components.
- RDKit's wheel-package MIT notice and RDKit BSD notice do not by themselves
  inventory the native wheel's embedded third-party code (e.g. Avalon, Boost).

## Blocking gates

- [x] Record the scoped upstream ordinary-CeCILL alternative for legacy CImg
  inside OSRA. Include the exact request/permission and original notices.
  The September 10 grant, not a source ZIP or the earlier supportive replies,
  addresses this particular permission gap.
- [x] Integrate the identified component notices, explicit license-option map,
  source inventory and build/replacement instructions into the 0.3.0 package,
  including NumPy/OpenBLAS/GCC 10.3, RDKit's embedded dependencies, Qt/Pillow
  notices and Microsoft runtime information. Exact source inputs and archive
  pairing are verified. This engineering completion is not a legal certification
  and does not resolve the separate CImg compatibility item.
- [x] Verify MSYS2 nested source hashes and both pinned Git payloads; collect
  the identified wheel source/build recipes. This is integrity/provenance
  verification, not a complete corresponding-source or license certification.
- [x] Rebuild from the recorded release commit, include recovered Qt notices,
  and verify DLL import closure after removing optional Qt components.
- [x] Pass native Windows and WSL regression tests plus relocated candidate
  smoke checks; record final antivirus scan results without suppressing alerts.
- [ ] Record clean-machine interactive testing for the final candidate (capture,
  mixed-DPI screens, editing/undo, recognition, 3D/XYZ, closing/cancellation).
- [x] Package matching binary/source ZIPs, checksums, release notes and test
  instructions; validate the exact local ZIP contents and source revision.
- [ ] Once publication is cleared, finalize release wording/status and verify
  uploaded/downloaded GitHub assets before marking the release public/stable.

The current candidate passed **265 tests on each of native Windows and WSL**
(five optional MolScribe tests deselected), plus relocated portable smoke
checks. See the [candidate validation record](audits/0.3.0rc1/VALIDATION.md)
for the exact build revision, ZIP hash, checks and their limitations.
The owner subsequently reported that the new candidate works well on their
Windows setup. Record that as a successful user test, not a claim that all
checklist items were individually exercised or that the machine was clean.

## Review progress after owner testing

- `verify_source_inputs.py` checked all 39 MSYS2 source containers and verified
  150 nested source/patch hashes against their `.SRCINFO` declarations. Eighteen
  detached signature files are explicitly marked `SKIP` upstream. Both Git
  payloads subsequently passed pinned-commit object/tree checks, including
  their declared `git archive` SHA-256 values; see
  [VCS-SOURCES.json](audits/0.3.0rc1/VCS-SOURCES.json). The nested-input report is retained at
  `.tools/release-audit/SOURCE-INPUTS.json`.
- Pillow 12.2.0's bundled LICENSE already contains named dependency notices,
  including FreeType, HarfBuzz, image codecs and compression libraries. It is
  not limited to Pillow's own license. Keep that original combined file.
- Read-only version APIs in the tested RDKit DLLs identify Cairo 1.18.4,
  Pixman 0.46.4, Fontconfig 2.17.1, Brotli 1.2.0 and bzip2 1.0.8. These identify
  upstream versions, not exact distributor patches.
- Collected matching upstream NumPy 1.26.4, RDKit 2026.3.4 and Cairo 1.18.4
  source archives. The [supplemental inventory](audits/0.3.0rc1/WHEEL-SOURCES.json)
  records their hashes and explicitly does not claim complete source coverage.
- The NumPy OpenBLAS DLL embeds the compiler identifier `Built by Jeroen for
  the R-project` with GCC 10.3.0. This narrows the toolchain to legacy Rtools40's
  UCRT toolchain, not the newer GCC collected for OSRA. The old Anaconda binary
  link now returns HTML and its API endpoint returns 404; it was not accepted
  as a source archive. The matching OpenBLAS/GCC sources and historic Rtools
  build recipes have now been collected; see the updated provenance below.

## Microsoft runtime review — Visual Studio installation confirmed

The owner subsequently installed **Visual Studio Community 2026** themselves
and reported linking their GitHub account. A read-only `vswhere` check confirmed
version **18.9.2** (`18.9.12120.119`) at
`C:\Program Files\Microsoft Visual Studio\18\Community`: complete, launchable,
on the stable Release channel, not prerelease, and with no reboot required.
The previous "VS Code only" installation blocker is no longer current. No
additional workloads were installed, and no license was accepted on the
owner's behalf.

Redistribution remains subject to the owner's eligibility and the applicable
[Community 2026 terms](https://visualstudio.microsoft.com/license-terms/vs2026-ga-community/)
and [2026 distributable-code list](https://learn.microsoft.com/en-us/visualstudio/releases/2026/redistribution).
The installed `Licenses/1033/Redist.txt` points to that list. GitHub sign-in is
not evidence of runtime redistribution rights, code signing, or publication.
Do not copy arbitrary IDE DLLs as substitutes for documented redistributables.

Read-only Authenticode checks returned `Valid` for all 12 runtime DLLs matched
in the extracted candidate. Ten are Microsoft-signed; PySide6's
`MSVCP140_1.dll` and `MSVCP140_2.dll` are signed by The QT Company Oy. Preserve
that distinction when reviewing provenance and the unmodified-file conditions;
a valid signature alone does not establish redistribution permission. See
the [runtime check record](audits/0.3.0rc1/VALIDATION.md#runtime-signature-check-after-visual-studio-installation).

The tested app and ZIP were not changed. The installation does not finish the
remaining dependency notices/source review or sign MolRecognizer itself.
End users do not need Visual Studio to run the portable app.

## Wheel provenance recovered

The matching RDKit build log records a wheel checksum identical to the
candidate's wheel. Its actual checkout, runner/vcpkg revision, eleven native
dependency inputs and patches are now identified. Seventeen additional
archives include embedded RDKit libraries, full Boost source, the historic
OpenBLAS source/recipe and the matching Rtools GCC 10.3.0 sources/patches.
All eleven vcpkg downloads match the SHA-512 values in their pinned recipes.
See [WHEEL-PROVENANCE.md](audits/0.3.0rc1/WHEEL-PROVENANCE.md) for exact pins,
evidence and limitations. Header-based notices, including InChI's MIT grant,
are collected in addition to top-level license files.

These findings resolve the earlier unidentified-input gaps. The historic
wheel/compiler builds and LGPL library replacement/relink procedure have
not been reproduced locally. The collected notices have now been integrated
into the separate 0.3.0 local preparation. The earlier RC and installed Downloads
copy remain unchanged.

## Historical publication hold: CImg inside OSRA

The following records the reason for the earlier hold. It is superseded for
the covered code by the explicit September 10 permission documented above;
it is retained to explain the investigation, not to claim permission is still
awaited.

The exact OSRA 2.2.4 source archive (SHA-256
`419d87fbf540338d881aaf6df6227785c7af8cbab73e487877a2fb182216bf46`)
contains `src/CImg.h`, version macro `127` (1.2.7), with a CeCILL-C grant.
`src/osra_anisotropic.cpp` includes that header and the GREYCstoration plugin;
`src/Makefile` includes `osra_anisotropic.o` in the linked object list. This
is not an unused file merely sitting beside the executable. Our Windows
compatibility patch changes this header without changing its license.

The [FSF license list](https://www.gnu.org/licenses/license-list.en.html#CeCILL-C)
classifies CeCILL-C as GPL-incompatible. OSRA's own source is GPL-2.0-or-later
and this build also links GPLv3 OCRAD. No explicit exception for this
combination was found in the inspected OSRA source notices, README, COPYING
or bundled Debian copyright files. The basic CeCILL license's GPL clause
must not be assumed to apply to the distinct CeCILL-C license.

This is a concrete compatibility question requiring clarification, not a
legal ruling that every OSRA distribution is unlawful. Seek an applicable
upstream permission/exception or informed licensing review before uploading
this binary. An alternative build without the disputed code would require
an explicit implementation decision and recognition regression testing;
it must not silently replace the owner's tested build. Contacting upstream
on the owner's behalf also requires approval. Merely installing Visual
Studio, adding attribution files or supplying source does not answer this
particular question. No public Release, tag or final-version build was made
as part of this preparation.

### Upstream inquiry status — 2026-09-07

The owner authorized contacting OSRA's maintainer. Igor Filippov's address
`igor.v.filippov@gmail.com` appears in the exact 2.2.4 README and the
[official release directory's README](https://sourceforge.net/projects/osra/files/osra/2.2.4/).
A [message template](OSRA-LICENSING-EMAIL.txt) was prepared locally. The owner
subsequently confirmed that they sent the email to the maintainer.
The owner subsequently provided the maintainer's reply: it explains his
understanding of the CeCILL family and recommends asking the CImg/GREYCstoration
developers for further clarification. This is not recorded as a new license
exception. The assistant did not send the email, and its private text has not
been published in an upstream issue.

The inquiry also acknowledges the [official OSRA license page](https://sourceforge.net/p/osra/wiki/License/),
which describes NCI-authored portions as public domain while preserving
third-party license conditions. That clarification alone does not answer
the CImg/GPL dependency-combination question. The message asks for applicable
existing permissions rather than asserting that OSRA is unlawfully licensed.

### CImg follow-up

At the owner's request, a focused public question was posted from `Hengyuan1`
to CImg's official GitHub issue tracker:
[GreycLab/CImg #492 — License option for legacy CImg 1.2.7 bundled in OSRA](https://github.com/GreycLab/CImg/issues/492).
The [posted message](CIMG-LICENSING-QUESTION.md) contains public technical
details, not the private email exchange. Initial status: awaiting clarification;
the subsequent explicit permission is recorded above.

The [current CImg website](https://cimg.eu/) explicitly describes the core as
dual-licensed under CeCILL-C or GPL-compatible CeCILL, and identifies David
Tschumperlé as project manager. This is useful additional evidence beyond the
CeCILL-C notice in OSRA's older header. The question asks whether the alternative
CeCILL grant also covers that legacy 1.2.7 code, which license version/notices
apply, or whether another documented permission is needed. It does not assume
that the modern grant automatically applies retroactively. No dependency
license or recognition implementation has been changed. The owner has since
replied to the maintainer and authorized local 0.3.0 release preparation while
the focused compatibility question was still pending. That historical status
does not override the September 10 permission.

## Source inventory

`fetch_release_sources.py` records URLs and SHA-256 hashes in SOURCES.json.
`inspect_release_sources.py` verifies MSYS2 source-package identity, reads every
container, and extracts original Qt notices without running downloaded code.
Both deliberately keep `license_review_complete: false`. Store raw archives
outside Git; publish required source materials as a separate Release asset.
The current [collection manifest](audits/0.3.0rc1/SOURCES.json) and
[container inspection report](audits/0.3.0rc1/SOURCE-INSPECTION.json) are saved
in Git. The roughly 940 MiB of collected source archives under
`.tools/release-sources/` are an incomplete audit collection, **not** an already
cleared corresponding-source release asset. Keep them for completion of the
review; downloading them again is unnecessary.

Do not upload the old Downloads ZIP as v0.3.0-rc1. The old archive still contains
the pre-audit Qt payload and identifies itself as a private testing version.
The existing GitHub workflow builds a **no-OSRA** preview, not this full bundle.

## Primary references

- [Qt module licensing](https://doc.qt.io/qt-6/licensing.html)
- [Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations)
- [GNU GPL compatibility and corresponding source FAQ](https://www.gnu.org/licenses/gpl-faq.html.en)
- [JBIG-KIT author/source](https://www.cl.cam.ac.uk/~mgk25/jbigkit/)
- [MSYS2 source archive](https://repo.msys2.org/mingw/sources/)
- [PySide 6.11.0 source](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.0-src/)
- [Actual RDKit wheel build checkout](https://github.com/kuelumbus/rdkit-pypi/tree/692356f26710ad53595ad889b5b7946052da15cd)
- [Matching vcpkg recipes](https://github.com/microsoft/vcpkg/tree/42e4e33e1505c9f47b58c21e0f557c1571b751ee)
- [NumPy 1.26.4 OpenBLAS build helper](https://github.com/numpy/numpy/blob/v1.26.4/tools/openblas_support.py)
- [Legacy Rtools40 toolchains](https://github.com/r-windows/docs)
- [Visual Studio Community eligibility](https://visualstudio.microsoft.com/vs/community/)
