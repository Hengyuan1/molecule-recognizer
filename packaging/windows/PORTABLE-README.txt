Molecule Recognizer — Windows x64 portable build

Extract the WHOLE ZIP to a folder you can write to, then double-click
MolRecognizer.exe. Do not run from inside the ZIP or move the EXE alone.
No Python, Conda, uv, WSL, or administrator installation is needed to run it.
The capture helper uses Windows' .NET Framework 4.x, not PowerShell.

IMPORTANT: If NO-OSRA.txt is present or the download name contains "no-osra",
this is an editor-only preview. Image recognition needs a separate native
Windows OSRA runtime. Load SMILES, editing, 3D generation and XYZ export work
without OSRA. BUILD-INFO.json records whether OSRA was included.

For a complete build, keep tools/osra/bin/osra.exe and its DLLs together, with
chain.txt, spelling.txt and superatom.txt under tools/osra/share/. The app
finds this runtime automatically. OSRA_EXECUTABLE can explicitly override it.
Images are processed locally; they are not uploaded to a recognition service.
The locally compiled OSRA 2.2.4 runtime includes its sources/patches and notices.
This is an unsigned local release-preparation build. The version number is
not a statement of publication or blanket licensing clearance. The scoped
ordinary-CeCILL permission for legacy CImg is preserved with its original
notices in licenses/release-materials/CIMG-PERMISSION.md and the JSON record.
Public upload remains a separate owner decision after final package checks.
Review recognized connectivity and stereochemistry carefully;
the generated stereo test in the build recipe was not recognized correctly.

Open Image: select an image, review the drawing and SMILES, fix recognition
errors manually. Render: generate 3D coordinates. Double-click the preview to
compare 2D and 3D side by side. Save xyz / Copy xyz export coordinates.
Screenshot: put the cursor on the desired monitor, press Alt+Y while this app
has keyboard focus, adjust the box, then Enter / Recognize. Esc cancels.
Native Windows does not yet have the WSL configuration's system-wide hotkey.

Keep _internal/, tools/, MolRecognizerWorker.exe and licenses/ with the app.
Settings/logs are stored in your Windows user profile, not beside the EXE.
Errors: %USERPROFILE%\.molrecognizer\molrecognizer.log
This build is unsigned. Your employer may require approval before running it;
do not disable company security policies to run it.

A file-origin warning when opening/extracting a downloaded ZIP is different
from a virus detection. Verify the download source and SHA-256 checksum first.
For a trusted ZIP on your personal PC, Properties > General > Unblock (if
offered) applies to that file only; then Extract All into a fresh local folder.
Do not turn off Defender, add broad exclusions, or bypass workplace policies.
If Windows names a threat or quarantines a file, stop and report the exact
threat name and affected file in a GitHub issue (without private images/logs).

SMOKE-TEST.json records automated checks, not a certification of recognition
accuracy or a guarantee of correct behavior on every monitor configuration.

Project and source: https://github.com/Hengyuan1/molecule-recognizer
See THIRD-PARTY-NOTICES.md and licenses/ for dependency notices.
Help > Third-party licenses opens the local notice folder. SOURCE-ACCESS.md
describes the matching source/patch/build-recipe ZIP and library replacement.
