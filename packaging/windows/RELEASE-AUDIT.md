# Windows release audit — 0.3.0rc1

Status: **0.3.0rc1 built and tested locally; not cleared for public distribution**.
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

- [ ] Finish component-level license selection, notices and any required
  corresponding-source coverage, including NumPy/OpenBLAS/GCC 10.3, RDKit's
  embedded dependencies, Qt/Pillow third-party code and MSVC runtime
  provenance/redistribution notices. Permissive dependencies do not all require
  source redistribution; review their actual notice and other conditions.
- [ ] Verify nested source inputs/VCS revisions/build recipes; HTTPS downloads
  and local hashes alone do not establish complete corresponding source.
- [x] Rebuild from the recorded release commit, include recovered Qt notices,
  and verify DLL import closure after removing optional Qt components.
- [x] Pass native Windows and WSL regression tests plus relocated candidate
  smoke checks; record final antivirus scan results without suppressing alerts.
- [ ] Record clean-machine interactive testing for the final candidate (capture,
  mixed-DPI screens, editing/undo, recognition, 3D/XYZ, closing/cancellation).
- [ ] Package source materials, final hashes and release notes together; verify
  the actual downloaded assets before publishing/marking the release stable.

The current candidate passed **265 tests on each of native Windows and WSL**
(five optional MolScribe tests deselected), plus relocated portable smoke
checks. See the [candidate validation record](audits/0.3.0rc1/VALIDATION.md)
for the exact build revision, ZIP hash, checks and their limitations.
The owner's earlier interactive Windows test covered the preceding build,
not this reduced Qt payload. It does not close the clean-machine gate above.

## Remaining wheel provenance gaps

The RDKit 2026.3.4 version-bump revision
`cf74fc396a01ebb5915610033d57a7778a31f042` uses the runner's `vcpkg` with no
`builtin-baseline` or dependency version pins in its manifest. Its recipe is
useful evidence, but it does not alone establish the wheel's Cairo/FreeType/
Pixman/Fontconfig input revisions. The candidate's DLL version resources show
FreeType 2.14.3, Expat 2.8.2, zlib 1.3.2 and MSVCP 14.40.33810.0; not all DLLs
provide version resources. Resolve the matching wheel build records and
original notices before claiming complete coverage.

NumPy 1.26.4's helper pins OpenBLAS `v0.3.23-293-gc2f4bdbb`; the upstream
commit resolves to `c2f4bdbbb43a1d20a7342f40122e18e573ce436a`. The runtime notice
identifies statically linked GCC runtime components, including libquadmath.
The exact GCC 10.3 toolchain patches and corresponding build/relink materials
are not yet established. A later OpenBLAS build recipe or the OSRA GCC 16.2
source package must not be substituted as proof of those inputs.

## Source inventory

`fetch_release_sources.py` records URLs and SHA-256 hashes in SOURCES.json.
`inspect_release_sources.py` verifies MSYS2 source-package identity, reads every
container, and extracts original Qt notices without running downloaded code.
Both deliberately keep `license_review_complete: false`. Store raw archives
outside Git; publish required source materials as a separate Release asset.
The current [collection manifest](audits/0.3.0rc1/SOURCES.json) and
[container inspection report](audits/0.3.0rc1/SOURCE-INSPECTION.json) are saved
in Git. The roughly 527 MiB of local source materials under
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
- [RDKit wheel build workflow at the 2026.3.4 version bump](https://github.com/kuelumbus/rdkit-pypi/blob/cf74fc396a01ebb5915610033d57a7778a31f042/.github/workflows/wheels.yml)
- [Matching RDKit vcpkg manifest](https://github.com/kuelumbus/rdkit-pypi/blob/cf74fc396a01ebb5915610033d57a7778a31f042/vcpkg.json)
- [NumPy 1.26.4 OpenBLAS build helper](https://github.com/numpy/numpy/blob/v1.26.4/tools/openblas_support.py)
