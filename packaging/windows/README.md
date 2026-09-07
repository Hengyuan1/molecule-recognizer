# Windows portable builds (development)

Target: native Windows 10/11 x64. Users extract a ZIP and run
`MolRecognizer.exe`; they do not install Python, Conda, uv or WSL.
This packaging work is not part of the published v0.2.0 tag. No complete,
OSRA-bundled Windows release has been published yet.

Local validation on **2026-09-07**: built a no-OSRA Windows x64 ZIP with Python
3.11.16, PyInstaller 6.22.2, PySide6 6.11.0 and RDKit 2026.3.4. Its relocated
EXE smoke checks passed (workbench, packaged 3D worker/XYZ/comparison and
compiled capture helper with synthetic pixels). All **233 regression tests**
passed on both native Windows and WSL; five optional MolScribe tests were
excluded. Native desktop checks moved an isolated window between a laptop at
250% scaling and two external monitors at 100%, checking full-frame placement
and dropdown rendering. Interactive capture/manual dragging on a clean Windows
machine still need release testing. The preview has not been published.

Native OSRA **2.2.4** has also been compiled locally with its patched GOCR and
Open Babel dependencies. The staged runtime includes dictionaries, raster
codecs and 51 native dependency DLLs, plus source archives/patches and available
notices (about 107 MiB total). With the compiler tree unavailable, six of seven
generated recognition tests matched their expected graphs; a chiral lactic-acid
drawing was misrecognized. See the [OSRA build recipe and limitations](OSRA-BUILD.md).

The complete OSRA-inclusive ZIP was then built and passed its relocated-EXE
checks for the editor, 3D worker/XYZ/comparison, compiled selector and PNG-to-SDF
recognition. The icon update also passed the relocated and installed-executable
checks; copied bundle files and the ZIP checksum were verified. The full suite now has
**247 passing tests on both Windows and WSL**, with five optional MolScribe
tests excluded. The failed stereo drawing produces the same incorrect graph
with the existing Linux OSRA 2.2.4; it is not unique to this Windows build.

## Build on Windows

To compile the OSRA runtime first, follow [OSRA-BUILD.md](OSRA-BUILD.md), then
pass the resulting folder to `--osra-dir` below.

Use **native Windows x64 Python 3.11** in PowerShell (not WSL's Python):

```powershell
python -m venv .venv-windows
.\.venv-windows\Scripts\python.exe -m pip install . -r packaging/windows/requirements-build.txt
.\.venv-windows\Scripts\python.exe -m pytest -m "not slow" -q
.\.venv-windows\Scripts\python.exe packaging/windows/build.py --osra-dir "C:\build-inputs\osra"
```

Calling the venv's Python directly does not require running an activation
script or changing PowerShell's execution policy. Build tools are separate
from application dependencies; ordinary `pip install` / `uv sync` is unchanged.

The builder creates `dist/MolRecognizer-<version>-windows-x64.zip` plus a
SHA-256 file. It refuses to overwrite an existing ZIP; move the old one or
specify `--output C:\path\to\new-output`. Intermediate files and the
uncompressed app remain under a unique `build/windows-*/` directory for
diagnosis. These generated folders are ignored by Git.

If the source is on a WSL/network share, put the build environment and cache
on local Windows storage. Pass `--work-dir C:\path\to\build-work` for local
intermediates; Windows tools may not support file locking on the WSL share.

### OSRA input

The input folder must be a **complete native Windows distribution**, not the
Linux OSRA currently installed under WSL:

```text
osra/
├── bin/
│   ├── osra.exe
│   └── all required DLLs and runtime files
├── share/
│   ├── chain.txt
│   ├── spelling.txt
│   └── superatom.txt
├── licenses/
│   └── OSRA and dependency license notices
└── SOURCE-NOTICE.txt
```

Keep any other runtime/configuration/plugin files the distribution needs in
this folder too; the builder copies it in full. `SOURCE-NOTICE.txt` must record
where the binary came from, its version, build instructions/patches and how to
obtain its exact corresponding sources. Review OSRA and its dependencies'
redistribution requirements before making the package public. The builder
checks the files' presence, **not their legal sufficiency**.

The [official OSRA downloads](https://sourceforge.net/p/osra/wiki/Download/)
provide free source and paid prebuilt Windows binaries. The
[Windows compilation instructions](https://sourceforge.net/p/osra/wiki/Compilation_on_Windows/)
describe MinGW, but refer to old dependency versions and are not an automated
recipe for a current build. We have not yet established/tested a reproducible
Windows OSRA source build from a clean machine end to end; the local native
build recipe and tested version details are now in OSRA-BUILD.md.
Nothing in this packaging script downloads or
purchases OSRA, changes the default recognizer, or uploads images to a service.

### Explicit editor-only preview

Packaging can be tested before OSRA is available:

```powershell
.\.venv-windows\Scripts\python.exe packaging/windows/build.py --without-osra
```

This produces a ZIP with `-no-osra` in the name and a `NO-OSRA.txt` notice.
SMILES loading, editing and 3D/XYZ export are available; image recognition
requires an external Windows OSRA runtime. Do not label this preview as a
complete standalone recognizer. The two build modes are mutually exclusive;
omitting both flags is an error.

## What is packaged

- The approved molecule/recognition-frame icon is embedded at ten sizes in
  the GUI, worker and capture EXEs. `MolRecognizer.ico` is also included for
  shortcuts, and Qt uses it for the title bar and child windows. The builder
  checks the actual PE icon resources before creating the ZIP.
- `MolRecognizer.exe`: windowed PyInstaller launcher with the Qt workbench.
- `MolRecognizerWorker.exe`: separate, killable 3D-generation helper. It has
  stdin/stdout pipes, unlike the windowed launcher; it cannot recursively
  reopen the GUI. Both EXEs share the `_internal/` dependency folder.
- `tools/MolRecognizerCapture.exe`: the existing C# selector compiled using
  the Windows .NET Framework 4.x compiler. Running a portable build's capture
  does not use PowerShell, `Add-Type`, Python or a runtime compiler. It still
  needs the .NET Framework 4.x runtime on Windows. Source/WSL installations
  retain their existing PowerShell route.
- `tools/osra/`: the supplied OSRA runtime, when requested. Absolute dictionary
  arguments make it relocatable, and the bundled OSRA wins over `PATH`.
  `OSRA_EXECUTABLE` remains an explicit override.
- Qt plugins, RDKit data, NumPy, Pillow, bond icons and available license
  notices. MolScribe/PyTorch/model weights are deliberately not bundled.
- `BUILD-INFO.json`, `SMOKE-TEST.json`, a user README and third-party notices.

No installer, registry changes or administrator elevation are needed to
extract/run the app. Normal application settings and logs still use the
Windows user profile. This is **not** a single-file executable: keep the entire
folder together. Builds are unsigned and may require your organization's
approval. Do not bypass workplace policies.

## Automated validation

Before writing a ZIP, the build copies the bundle to a new path containing
spaces and runs its own EXE from a different working directory. `PATH` is
reduced to Windows system directories; `OSRA_EXECUTABLE`, `PYTHONPATH` and
external Qt plugin paths are removed. Checks cover:

- Creating the offscreen Qt workbench, loading SMILES and finding bond icons.
- Checking all ten application-icon sizes and the workbench title-bar icon.
- Calling the **packaged** 3D helper, producing XYZ and opening the comparison
  pane without changing the molecule.
- Calling the compiled capture helper's synthetic-image self-test; it does
  not screenshot the desktop or interact with another application.
- For complete builds, recognizing a generated benzene PNG through OSRA's
  SDF route, including image codecs, dictionary paths and external DLL loading.

A failed check prevents ZIP creation. These checks do not replace interactive
testing or guarantee recognition accuracy. Before a public release, test the
extracted folder on a clean Windows machine without Python/Conda/WSL/OSRA:

1. Load SMILES, edit atoms/bonds and undo/redo.
2. Recognize reference images (including rings, labels and stereocenters),
   then compare retry candidates. Inspect both the drawing and SMILES.
3. Capture on the laptop and each extended monitor; adjust/cancel/accept a crop.
4. Generate 3D, compare beside 2D, copy/save XYZ, then close while a job runs.
5. Move/resize between mixed-DPI displays and check menus, focus and shutdown.
6. Check every bundled dependency's notices/source obligations and signing/
   IT approval requirements. Automated notice collection is only an aid.

## GitHub Actions

`.github/workflows/windows-portable.yml` runs tests and builds an explicitly
labelled **no-OSRA preview** on a Windows runner. It supports pull requests and
manual dispatch. Manual dispatch becomes available once the workflow exists
on the repository's default branch; the run can then select the feature branch.
The workflow uploads an Actions artifact only; it does not push commits, tag
versions, or publish GitHub Releases. No workflow has been run by adding it
locally. Complete OSRA packaging currently uses the local `--osra-dir` route.

Technical references:
[PyInstaller packaging](https://pyinstaller.org/en/stable/operating-mode.html),
[windowed streams and external-process DLL search](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html).

## Release-candidate preparation

The source version is now `0.3.0rc1`; the proposed Git tag is `v0.3.0-rc1`.
This does not replace the existing v0.2.0 release. No public binary release
is created by changing the version. See [RELEASE-AUDIT.md](RELEASE-AUDIT.md)
and [draft release notes](RELEASE-NOTES-0.3.0-rc1.md) for the remaining gates.
The local candidate was built from `cd5bf78` and passed 265 regression tests
on each platform. Its [validation record](audits/0.3.0rc1/VALIDATION.md) identifies
the exact ZIP and distinguishes completed checks from outstanding review.

`fetch_release_sources.py` collects matching MSYS2 source packages, the six
locally compiled OSRA source archives/patches, and Qt/PySide source archives.
It downloads data only and never executes PKGBUILDs or changes the installed
runtime. Resumed downloads are checked against local SHA-256 receipts.
These receipts are not upstream signature verification.

`inspect_release_sources.py` checks source-package versions and recovers
original Qt license texts and attribution notices. It requires `zstandard`.
Pass its `qt-notices` output to `build.py --qt-notices-dir ...` when rebuilding.
The default wheel notice collection alone misses Qt's LGPL/GPL texts.

The GUI bundle now excludes unused Qt Virtual Keyboard, PDF, QML/Quick and
the optional software OpenGL renderer. Both editors use QWidget/QPainter.
Required platform and SVG plugins are checked before packaging; run the
relocated EXE checks after every change to this list.

`--source-revision` records the full commit hash supplied by the builder.
Only provide it for a build from that exact revision; it is a provenance
record, not a substitute for verifying a clean source checkout.
