# CImg 1.2.7 — upstream alternative-license permission

## Permission and its scope

On September 10, 2026, David Tschumperlé (`dtschump`) granted the requested
ordinary CeCILL alternative for the CImg 1.2.7 code bundled with OSRA, insofar
as he holds the relevant copyrights. The public GitHub REST API was checked;
`CIMG-PERMISSION.json` preserves the exact request and permission bodies,
authors, timestamps and comment permalinks. The JSON is a selected-field
transcription, not a signed legal instrument or a complete API response.

[Request by Hengyuan1](https://github.com/GreycLab/CImg/issues/492#issuecomment-5612079056):

> Would you be willing to explicitly offer the ordinary CeCILL license as an alternative for the CImg 1.2.7 code bundled with OSRA, insofar as you hold the relevant copyrights?

[Reply by David Tschumperlé](https://github.com/GreycLab/CImg/issues/492#issuecomment-5618853659),
September 10, 2026 at 12:42:40 UTC, quoting that question:

> If it helps, you have my permission—yes.

This is the permission relied upon, not the earlier discussion comparing
CeCILL-C to the LGPL. It does not grant rights held by other contributors,
endorse MolRecognizer, or change the terms of unrelated dependencies.

## License option used by this distribution

For the covered CImg code, this distribution elects **ordinary CeCILL 2.1**
(`CECILL-2.1`), supplied in `license-texts/CECILL-2.1.txt`. The reply grants
ordinary CeCILL without naming a version; 2.1 is the distributor's explicit
choice of the current ordinary agreement, not a version number quoted from
David's reply. Article 5.3.4 permits combining covered code with GNU GPL code
and distributing the combined code under that GPL version. The OSRA executable
is distributed on the GPLv3 route, consistent with its GPL-2.0-or-later code
and linked GPLv3 OCRAD. This does not relicense MolRecognizer's own MIT code.

Original CImg copyright/CeCILL-C notices are retained verbatim. They are
supplemented by this permission record, not erased or silently rewritten.
GREYCstoration's original ordinary CeCILL notice is retained separately.
No recognition/preprocessing code or native OSRA binary is changed by this
licensing-documentation update.

## Exact source and local modifications

The source is `osra-2.2.4.tar.gz`, SHA-256
`419d87fbf540338d881aaf6df6227785c7af8cbab73e487877a2fb182216bf46`.
Its `src/CImg.h` defines `cimg_version 127` and names David Tschumperlé in its
copyright notice. The matching source archive contains this original input,
the local `osra-cimg.patch` pointer-size fixes and other Windows build patches.
This record and the full license texts are in the committed application
source under `packaging/windows/` and in the binary's
`licenses/release-materials/` directory.

References:

- [Ordinary CeCILL 2.1 agreement](https://www.cecill.info/licences/Licence_CeCILL_V2.1-en.html)
- [GNU explanation of CeCILL/GPL combinations](https://www.gnu.org/licenses/license-compatibility.en.html)
- [Current CImg license options](https://cimg.eu/)

This record addresses the specific legacy-CImg permission gap. It is not a
legal opinion or blanket certification of the complete binary distribution.
