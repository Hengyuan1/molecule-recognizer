# MolRecognizer Windows source materials

This is a source-package guide, not a public release announcement or a
declaration that the binary distribution's licensing review is complete.
The upstream alternative-license permission for legacy CImg is preserved in
`packaging/windows/CIMG-PERMISSION.md` and `CIMG-PERMISSION.json` inside the
application source, alongside the full license texts. Original dependency
archives and notices are unchanged. Do not present a generated archive as
blanket legal clearance; publication is a separate owner decision.

The companion asset for the prepared Windows app is
`MolRecognizer-0.3.0-sources.zip`. At publication, provide it on the same
release page as `MolRecognizer-0.3.0-windows-x64.zip`:
https://github.com/Hengyuan1/molecule-recognizer/releases
These are currently local preparation artifacts, not existing public downloads.
The binary's `BUILD-INFO.json` source revision must equal `app_revision` in
the source ZIP's `SOURCES.json`. Do not substitute GitHub's automatic source ZIP;
it does not contain the archived third-party inputs.

In the binary ZIP, this guide is named `SOURCE-ACCESS.md`; the contents below
describe the separate source ZIP, not folders beside the EXE.

## Contents and verification

`SOURCES.json` records the application commit, archive paths, origins and
SHA-256 checksums. `molrecognizer-source.tar.gz` contains that exact committed
application tree, not local working files. `archives/` contains the original
dependency archives and build recipes. Nested archives retain their upstream
layout, licenses and copyright notices. Each component keeps its own license;
MolRecognizer's MIT license does not replace third-party terms.

Verify the outer ZIP against its adjacent `.sha256` file before unpacking.
For example, in PowerShell:

```powershell
Get-FileHash .\MolRecognizer-0.3.0-sources.zip -Algorithm SHA256
```

Verify inner archives against `SOURCES.json` as well. Inspect downloaded build
recipes before running them. Upstream archives may contain symbolic links;
extract using an up-to-date archive tool into a new, isolated build directory.
The source-verification scripts read archives without executing their code.

## Build and replacement map

| Component | Source and build information |
| --- | --- |
| MolRecognizer and capture helper | Application source: `packaging/windows/README.md`, `requirements-build.txt`, `build.py` and `src/molrecognizer/gui/capture_overlay.cs`; application dependencies are in `pyproject.toml`. |
| OSRA and locally compiled libraries | `archives/osra-local/` includes six pinned source inputs and local patches/recipes. Follow the application's `packaging/windows/OSRA-BUILD.md`. |
| OSRA's MSYS2 libraries | Exact-version `.src.tar.zst` packages contain `.SRCINFO`, `PKGBUILD`, patches and source inputs. Binary-to-package provenance is in OSRA's `BUILD-INFO.json`. |
| Qt/PySide | Matching Qt Base, SVG, Image Formats and PySide setup archives contain source and build documentation. Keep compatible DLLs and plugins together under `_internal/PySide6/`. |
| RDKit native wheel | RDKit source plus `rdkit-pypi-692356f2.tar.gz`, `vcpkg-42e4e33e.tar.gz` and the inventoried external inputs. The wheel recipe includes its custom patches and Windows workflow. |
| NumPy/OpenBLAS/GCC runtimes | NumPy 1.26.4 source, `openblas-c2f4bdbb.tar.gz`, `openblas-libs-1949e84a.tar.gz`, `rtools-ucrt-c5344cc8.tar.gz`, and GCC 10.3.0 source. Use the archived OpenBLAS workflow and `tools/build_openblas.sh`, not OSRA's newer GCC recipe. |

The RDKit and NumPy pins, provenance evidence and remaining limitations are
recorded in `packaging/windows/audits/0.3.0rc1/WHEEL-PROVENANCE.md`. The directory
name identifies the tested candidate used for this audit, not a public RC.

For modified LGPL libraries, preserve the relevant ABI, architecture, exported
symbols and dependent DLLs. NumPy's OpenBLAS uses the 64-bit integer interface
and `64_` symbol suffix. Rebuilding from the supplied NumPy/OpenBLAS and Rtools
recipes allows modified runtime code to be linked into a replacement DLL;
update the wheel's DLL location/loading metadata or rebuild the application
with that wheel as needed. The portable app does not enforce vendor hashes
on replacement libraries. Do not discard the original license notices.

Source collection and checksum verification are not bit-for-bit build or
relink testing. The historic wheel builds have not been reproduced locally.
Native Windows build prerequisites, such as the Windows SDK/MSVC toolchain,
must be obtained separately under their own terms; they are not included in
these source archives. Existing scripts that install current packages need
the recorded versions if reproducing this particular bundle.
