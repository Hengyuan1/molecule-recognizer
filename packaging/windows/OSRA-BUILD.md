# Native Windows OSRA build

This recipe builds **OSRA 2.2.4 for Windows x64**, using an isolated MSYS2
UCRT64 compiler. MSYS2 is a **build tool only**: the resulting runtime uses
native Windows DLLs, not WSL, Cygwin or `msys-2.0.dll`. It is a local testing
build, not OSRA's paid Windows distribution or a published MolRecognizer release.

## Inputs

Use native Windows Python 3.11 with the MolRecognizer build dependencies
installed (see [README](README.md)). Extract an official MSYS2 base archive
into a short, ASCII-only local NTFS path, for example `C:\osra-build\msys64`.
Do not use a network share for the compiler/build tree. Follow the
[official archive/signature verification instructions](https://www.msys2.org/docs/installer/).
Do not change PowerShell execution policy or system PATH.

Download these exact upstream archives into `C:\osra-build\downloads`.
`build_osra.py` checks their SHA-256 hashes before using them:

| Archive | Official source |
| --- | --- |
| `osra-2.2.4.tar.gz` | [OSRA 2.2.4](https://downloads.sourceforge.net/project/osra/osra/2.2.4/osra-2.2.4.tar.gz?use_mirror=pilotfiber) |
| `gocr-0.50pre-patched-2.tgz` | [OSRA-patched GOCR](https://downloads.sourceforge.net/project/osra/gocr-patched/gocr-0.50pre-patched-2.tgz?use_mirror=pilotfiber) |
| `openbabel-3-0-0-patched-3.tgz` | [OSRA-patched Open Babel](https://downloads.sourceforge.net/project/osra/openbabel-patched/openbabel-3-0-0-patched-3.tgz?use_mirror=pilotfiber) |
| `ocrad-0.23.tar.lz` | [GNU OCRAD 0.23](https://ftp.gnu.org/gnu/ocrad/ocrad-0.23.tar.lz) |
| `tclap-1.2.5.tar.gz` | [TCLAP 1.2.5](https://downloads.sourceforge.net/project/tclap/tclap-1.2.5.tar.gz?use_mirror=pilotfiber) |
| `eigen-3.4.0.tar.gz` | [Eigen 3.4.0](https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz) |

The patched GOCR/Open Babel archives matter; do not replace them with arbitrary
newer packages. This recipe uses GOCR and OCRAD, not optional Tesseract/Cuneiform.

## Compile and stage

From the project directory in PowerShell, run the venv's Python directly:

```powershell
$osraBuildRoot = "C:\osra-build\msys64"
$osraDownloads = "C:\osra-build\downloads"
$osraPython = ".\.venv-windows\Scripts\python.exe"
& $osraPython packaging/windows/build_osra.py --msys2-root $osraBuildRoot --step update
# Core MSYS2 updates can require a second run in a fresh shell:
& $osraPython packaging/windows/build_osra.py --msys2-root $osraBuildRoot --step update
& $osraPython packaging/windows/build_osra.py --msys2-root $osraBuildRoot --step deps
& $osraPython packaging/windows/build_osra.py --msys2-root $osraBuildRoot --downloads $osraDownloads --step build --jobs 4
& $osraPython packaging/windows/stage_osra.py --msys2-root $osraBuildRoot --output "C:\osra-build\osra-runtime"
& $osraPython packaging/windows/build.py --osra-dir "C:\osra-build\osra-runtime" --work-dir "C:\osra-build\app-work" --output "C:\osra-build\dist"
```

The first login initializes the extracted MSYS2 environment; core updates may
close their shell. Run `--step update` again until it completes, before `deps`.
Logs are saved beside `msys64`; sources/intermediates are under
`msys64\opt\osra-build`. Build steps are incremental. Staging and ZIP output
refuse to overwrite an existing destination; use a new path when rebuilding.
MSYS2 package versions move over time; this is a reproducible recipe, not a
claim of bit-for-bit reproducibility with future compiler/package updates.

## Local changes to upstream

- Open Babel's obsolete CMake `CMP0042 OLD` setting becomes `NEW`; Eigen 3.4
  headers are explicitly selected for the upstream version detector.
- Patched Open Babel/InChI and the OCR libraries are linked into OSRA;
  additional libraries use native UCRT64 DLLs collected recursively.
- Enable the Windows math constants and use pointer-width casts in the older
  bundled CImg header, which otherwise fails to compile on Windows x64.
- `osra_portable.h` sets Open Babel, GraphicsMagick and font configuration
  paths relative to the executable, before initializing image decoding.
  Original recognition algorithms and recognition defaults are unchanged.
- GraphicsMagick's `.la` codec descriptors are retained, with build-time
  dependency/library paths removed; both its share/ and lib/ configurations
  are collected. The DLL dependencies are resolved separately.

The runtime includes the three OSRA dictionaries, Open Babel data, image
codecs (PNG, JPEG, BMP, GIF, TIFF, PNM and internal pixel formats), recursively
resolved DLLs, available original notices, and the exact
source archives/local patches for the components compiled here. It includes
`BUILD-INFO.json` with binary hashes and MSYS2 package provenance.
Never copy just `osra.exe`: keep the entire staged runtime folder.
Optional HEIF/JXL/video codecs and external Ghostscript delegates are not
included. MolRecognizer converts its supported input images to PNG for OSRA.

The MolRecognizer builder tests a relocated bundle from a path with spaces,
with only Windows system folders on PATH. It must recognize a generated PNG
through OSRA's SDF route before producing the ZIP. This does not replace
manual recognition, screenshot and mixed-DPI tests on a clean Windows laptop.

Additional recognition checks can be run with:

```powershell
& $osraPython packaging/windows/check_osra.py "C:\osra-build\osra-runtime" --report "C:\osra-build\recognition-tests.json"
```

Local validation on 2026-09-07: OSRA 2.2.4 was compiled with UCRT64 GCC 16.2.0.
The staged executable ran with the entire MSYS2 build tree temporarily renamed
out of the way and only Windows system directories on PATH. Six generated
image tests matched their expected molecular graphs: benzene, aspirin in
PNG/JPEG/BMP, caffeine and an amino-nitrile. A seventh test, an RDKit drawing
of chiral lactic acid, was misrecognized (`C[C@H](O)C(=O)O` became
`CC(CO)C(O)O`). That result is recorded as a failure, not hidden or treated as
an accuracy pass. Review connectivity and stereochemistry before using output
for training data; this build does not claim to fix OSRA recognition errors.

## Distribution status

OSRA is GPL-2.0-or-later; its dependencies have their own license/source
requirements. The automatically collected notices and source links are not
a complete redistribution review. Before publishing a binary release, verify
the exact corresponding sources/build recipes for **all shipped DLLs**, as
well as the compiled libraries, and satisfy their applicable obligations.
The current runtime is for local testing. It is unsigned; follow workplace
software approval policies. No public release is created by these scripts.
