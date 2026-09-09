Hello David and the CImg team,

I am preparing a free, open-source Windows distribution of
[MolRecognizer](https://github.com/Hengyuan1/molecule-recognizer), a molecular
structure editor that invokes a separately compiled OSRA command-line program.
I would appreciate clarification of the license options for the older CImg
copy included in OSRA.

The [current CImg website](https://cimg.eu/) explicitly describes the library
core as dual-licensed under CeCILL-C or GPL-compatible CeCILL. Does that
CeCILL option also cover the **CImg 1.2.7** code bundled in
[OSRA 2.2.4's published source archive](https://sourceforge.net/projects/osra/files/osra/2.2.4/)?

Specifically, that archive contains:

- `src/CImg.h`: `cimg_version 127`, with a CeCILL-C notice but no explicit
  alternative-license notice in its header.
- `src/greycstoration.h`: plugin version 2.51, with a CeCILL notice.
- `src/osra_anisotropic.cpp`: includes both files and is linked into OSRA.

OSRA's source headers use GPL-2.0-or-later, and our source-built Windows
executable also links GPLv3 OCRAD 0.23. I am asking because the
[FSF license list](https://www.gnu.org/licenses/license-list.en.html#CeCILL-C)
distinguishes GPL-compatible CeCILL from CeCILL-C; I do not want to assume
that an alternative license for current CImg automatically applies to the
historical copy.

Can we elect the GPL-compatible CeCILL option for this legacy CImg code when
distributing the OSRA executable? If so, which CeCILL version and notice or
permission should accompany it? If not, is there an existing exception or
other documented permission applicable to this combination?

We intend to provide the corresponding sources, clearly identified local
Windows compatibility/relocation patches, build instructions, and original
copyright/license notices. Our small CImg patch fixes Windows compilation;
it does not intentionally change the recognition algorithms. We would retain
the applicable licenses on the original code and our modifications.

If another rightsholder/contact needs to address the historical version,
please let me know. Thank you for your work on CImg and GREYCstoration!
