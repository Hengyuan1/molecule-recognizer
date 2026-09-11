# Windows dependency licenses and source access

This inventory accompanies the **0.3.0 Windows release preparation**.
The scoped upstream permission for legacy CImg is preserved in
`CIMG-PERMISSION.md` and `CIMG-PERMISSION.json`; it is not a blanket license
certification for the entire package.
Each original notice governs its component; MolRecognizer's MIT license does
not replace third-party terms. Version pins are in `BUILD-INFO.json` and the
source archive's `SOURCES.json`. No upstream project endorses this package.

Paths below are relative to `licenses/release-materials/` unless stated otherwise.
`MATERIALS.json` checks the integrity of these documents, not legal compliance.

## GUI and native wheel dependencies

| Component | Terms / license option used for this preparation | Original notices |
| --- | --- | --- |
| MolRecognizer 0.3.0 | MIT | `../MolRecognizer-LICENSE.txt` |
| Python 3.11.16 | PSF and bundled third-party terms | `../Python-LICENSE.txt` |
| Qt / PySide / Shiboken 6.11.0 | LGPL-3.0 for the included library modules; preserve embedded third-party terms | `qt-source-notices/` and `../PySide6*/`, `../shiboken6/` |
| PyInstaller 6.22.2 bootloader | GPL with the upstream bootloader exception | `../PyInstaller/` |
| RDKit 2026.3.4 | BSD-3-Clause for RDKit; separate embedded component terms | `wheel-source-notices/rdkit/`, `../rdkit/` |
| NumPy 1.26.4 | BSD-3-Clause plus the wheel's bundled-library terms | `wheel-source-notices/numpy/`, `../numpy/` |
| Pillow 12.2.0 | Pillow/HPND and its combined third-party notice | `../Pillow/` (keep the entire wheel LICENSE) |
| OpenBLAS c2f4bdbb | BSD-3-Clause and retained subcomponent notices | `wheel-source-notices/openblas/` |
| GCC 10.3.0 runtime code in NumPy's OpenBLAS | Applicable GPL runtime exceptions for libgcc/libgfortran; LGPL terms for libquadmath | `wheel-source-notices/gcc-rtools-runtime-source/` |
| Cairo 1.18.4 in RDKit | **LGPL-2.1** option; not the alternative MPL option for this preparation | `wheel-source-notices/rdkit-cairo/` |
| FreeType 2.14.3 in RDKit | **FreeType License (FTL)** option; not its alternative GPL option | `wheel-source-notices/rdkit-freetype/` |
| Pixman / Fontconfig / Expat / Brotli / Dirent | Original MIT-style notices | `wheel-source-notices/rdkit-{pixman,fontconfig,expat,brotli,dirent}/` |
| Pthreads 3.0.0 | Apache-2.0, including NOTICE | `wheel-source-notices/rdkit-pthreads/` |
| libpng / zlib / bzip2 | Original libpng, zlib and bzip2 notices | `wheel-source-notices/rdkit-{libpng,zlib,bzip2}/` |
| Boost 1.85.0 / better-enums | Boost Software License 1.0 | `wheel-source-notices/boost-rdkit/`, `wheel-source-notices/better-enums/` |
| Avalon / CoordGen / RingDecomposerLib | Original BSD notices | `wheel-source-notices/{avalon,coordgen,ringdecomposerlib}/` |
| MaeParser / InChI | Original MIT notices (InChI notices are in source headers) | `wheel-source-notices/{maeparser,inchi}/` |
| FreeSASA / YAeHMOP / PubChem alignment / ChemDraw support | Original component notices, including source-header notices | `wheel-source-notices/{freesasa,yaehmop,pubchem-align3d,chemdraw}/` |
| Microsoft Visual C++ runtime | Microsoft runtime redistribution terms, **not MIT/GPL** | `MICROSOFT-RUNTIME-NOTICE.txt`; signed files stay unmodified |

Portions of this software are copyright © The FreeType Project
(www.freetype.org). All rights reserved. See the original FTL for attribution
and disclaimers. Qt's separate FreeType/codecs and Pillow's embedded libraries
retain their own original notices; the RDKit license choice does not replace them.

Notice extraction also preserves notices in optional/test/build-tool sources.
Their presence is not a claim that every optional component is in the EXE.
The unused Qt Virtual Keyboard, QML/Quick, PDF and software OpenGL payloads are
excluded. MolScribe, PyTorch and model weights are not bundled.

## OSRA subprocess and its dependencies

OSRA is a separate executable under `tools/osra/`. Its original notices,
component versions, binary hashes and local sources are retained there.
The six local source inputs and all 39 exact MSYS2 source packages/build recipes
also appear in the accompanying source archive. Do not substitute latest
upstream versions for the recorded versions.

- OSRA's source grant is GPL-2.0-or-later; this build also links GPLv3 OCRAD.
  GPLv3-compatible distribution terms are therefore needed for that combined
  binary. Open Babel, GOCR and other dependencies keep their original notices.
- The legacy CImg 1.2.7 header originally specifies **CeCILL-C**, copyright
  David Tschumperlé. His September 10, 2026 permission offers ordinary CeCILL
  as an alternative for the code whose copyrights he holds. This distribution
  elects **CeCILL 2.1** and its article 5.3.4 GPL-combination route; see
  `CIMG-PERMISSION.md` for the exact scope and version-selection explanation.
  CImg is used for image processing inside OSRA. The GREYCstoration 2.51 header
  carries an **ordinary CeCILL** notice, not CeCILL-C. The original notices are
  in `osra-header-notices/`. Both full agreements are in `license-texts/`.
  Original notices are retained unchanged and supplemented by the permission.
- `osra-cimg.patch` documents our three pointer-size compatibility fixes;
  `osra-portable.patch`, `osra_portable.h` and `openbabel-compat.patch` record
  the other local build/relocation changes. All accompany the sources.
- JBIG-KIT 2.1's actual source permits GPLv2 **or later**, despite the shorter
  package metadata label. Preserve the source grant.
- GCC 16.2/MSYS2 OSRA runtimes are distinct from NumPy's GCC 10.3 runtime code.
  Both sets of exact sources/recipes are supplied; one does not replace the other.

The specific legacy-CImg permission gap is addressed by the linked upstream
grant, not merely by collecting notices or sources. Publication remains a
separate owner decision after final package checks; no upstream endorsement
or rights beyond the permission's stated scope are claimed.

## Source access, modification and library replacement

The planned companion asset is `MolRecognizer-0.3.0-sources.zip`, on the same
GitHub Release as the application ZIP **when that release is published**:
https://github.com/Hengyuan1/molecule-recognizer/releases

It contains the exact committed application source, original dependency
archives, distributor build recipes and local patches, with checksums.
While publication is pending, both packages are local preparation artifacts;
the URL above is not a claim that these assets are already downloadable.
See `SOURCE-ACCESS.md` beside the EXE for the build/replacement map.

Users may modify and replace the LGPL libraries and debug those modifications,
including reverse engineering to the extent needed for that purpose. The app
adds no license restriction or signature/hash enforcement preventing library
replacement. The material/build checks are distributor tools, not runtime locks.
Keep compatible DLLs together; static components require rebuilding the containing
DLL from the supplied source and recipes. Do not remove original notices.

Historic wheel/compiler builds have not been reproduced bit-for-bit locally;
source provenance and automated runtime checks must not be described as a
successful modified-library relink test.
