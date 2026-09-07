# Windows release audit — 0.3.0rc1

Status: **preparation in progress; not cleared for public distribution**.
This is an engineering inventory and release checklist, not legal advice or
a certification that every bundled license obligation has been satisfied.

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
  are excluded from the next build; the existing user installation is untouched.
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

- [ ] Finish component-level license selection, notices and corresponding-source
  coverage, including NumPy/OpenBLAS/GCC 10.3, RDKit's embedded dependencies,
  Qt third-party code and MSVC runtime provenance/redistribution notices.
- [ ] Verify nested source inputs/VCS revisions/build recipes; HTTPS downloads
  and local hashes alone do not establish complete corresponding source.
- [ ] Rebuild from the recorded release commit, include the missing notices,
  and verify DLL import closure after removing optional Qt components.
- [ ] Pass native Windows and WSL regression tests plus relocated candidate
  smoke checks; record final antivirus scan results without suppressing alerts.
- [ ] Record clean-machine interactive testing for the final candidate (capture,
  mixed-DPI screens, editing/undo, recognition, 3D/XYZ, closing/cancellation).
- [ ] Package source materials, final hashes and release notes together; verify
  the actual downloaded assets before publishing/marking the release stable.

Core program functionality already passed 247 automated tests on both native
Windows and WSL before this preparation, plus portable smoke checks and the
owner's interactive Windows test. That is not an antivirus or legal clearance.

## Source inventory

`fetch_release_sources.py` records URLs and SHA-256 hashes in SOURCES.json.
`inspect_release_sources.py` verifies MSYS2 source-package identity, reads every
container, and extracts original Qt notices without running downloaded code.
Both deliberately keep `license_review_complete: false`. Store raw archives
outside Git; publish required source materials as a separate Release asset.

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
