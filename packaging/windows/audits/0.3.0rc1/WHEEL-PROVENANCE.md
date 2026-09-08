# Additional wheel source provenance — 2026-09-07

These records extend the tested candidate's source inventory. They do not
change its binaries or certify complete license compliance.

## RDKit 2026.3.4 cp311 Windows x64

The [wheel build job](https://github.com/kuelumbus/rdkit-pypi/actions/runs/29480276547/job/87562203517)
records checkout `692356f26710ad53595ad889b5b7946052da15cd` and the resulting
wheel SHA-256:

```text
68f27f12063091115df76d0adbd3d1ec7d7ae8a0ddf103cfb88a1fee4670f2cd
```

This matches the PyPI wheel used in the candidate. The later version-bump
commit is not substituted for the actual build checkout.

The job used Windows runner image `20260706.237.1`. Its
[image inventory](https://github.com/actions/runner-images/blob/win22/20260706.237/images/windows/Windows2022-Readme.md)
identifies vcpkg `42e4e33e15`, resolved to
`42e4e33e1505c9f47b58c21e0f557c1571b751ee`. The source URLs, SHA-512 checksums
and patches in those port recipes match the build log. All eleven collected
vcpkg source archives pass those declared SHA-512 checks.

| Native dependency | Matching vcpkg recipe version |
| --- | --- |
| Cairo | 1.18.4#1 |
| Pixman | 0.46.4#1 |
| Fontconfig | 2.17.1#2 |
| FreeType | 2.14.3 |
| Pthreads | 3.0.0#14 |
| Dirent | 1.26 |
| libpng | 1.6.58 |
| Expat | 2.8.2 |
| Brotli | 1.2.0 |
| bzip2 | 1.0.8#6 |
| zlib | 1.3.2#1 |

The RDKit source checkout is `8afba32ec539dcb2369bc84549d802aca3f7eb39`.
The additional manifest includes its Avalon, FreeSASA, CoordGen, MaeParser,
YAeHMOP, InChI, RingDecomposerLib, PubChem alignment, ChemDraw, better-enums
and Boost inputs. The complete wheel and vcpkg recipe archives retain local
patches. This closes the previously unidentified vcpkg input gap; it does
not claim that this wheel has been rebuilt bit-for-bit.

## NumPy 1.26.4 Windows OpenBLAS

The DLL name identifies `v0.3.23-293-gc2f4bdbb`, and embedded compiler strings
identify GCC 10.3.0, built by Jeroen for the R project. The corresponding
[OpenBLAS build recipe](https://github.com/MacPython/openblas-libs/tree/1949e84a97655ed586a2cb4b469e98efec8651c0)
pins OpenBLAS `c2f4bdbbb43a1d20a7342f40122e18e573ce436a`, Rtools package
`4.0.0.20220206`, and the UCRT64 environment. Its workflow and shell script
retain the static runtime linking flags and ILP64 `64_` symbol-suffix options.

The [Rtools UCRT source recipe](https://github.com/r-windows/rtools-ucrt/tree/c5344cc8c7e310ee4eee513b2381af2e75d65cb9)
contains GCC `10.3.0-9804`, the matching compiler identification string and
the toolchain patches preceding that Rtools installer. GCC 10.3.0's full
source archive matches the recipe's SHA-256:

```text
64f404c1a650f27fc33da242e1f2df54952e3963a49e06e73f6940f3223ac344
```

Full OpenBLAS and GCC sources, including libquadmath, plus the Rtools and
OpenBLAS build recipes are collected. This is source/recipe provenance
evidence, not a locally reproduced compiler, static archive or relink test.
The obsolete Anaconda binary URL is not needed as a substitute for source
and has not been accepted as an archive. OSRA's GCC 16.2 sources are separate.

## Original notices

`collect_source_notices.py` preserves named license/copyright files and,
for selected components, complete copyright-bearing leading C/C++ comments.
This matters for InChI 1.07.3: its MIT grant is in source headers, not a
top-level LICENSE file. Original Qt notices are collected separately.
Some notices belong only to optional or test sources; their presence does
not mean all those components were compiled into the binary.

## Inventories

- `WHEEL-SOURCES.json`: NumPy, RDKit and upstream Cairo release sources.
- `WHEEL-SOURCE-REQUESTS.json` and `ADDITIONAL-SOURCES.json`: seventeen further
  sources and build recipes, with collected hashes and check results.
- `VCPKG-SOURCE-REQUESTS.json` and `VCPKG-SOURCES.json`: eleven exact vcpkg inputs.
- `VCS-SOURCES.json`: both previously outstanding MSYS2 Git payloads match
  the SHA-256 of `git archive` for their pinned commits. Only object files
  entered fresh temporary repositories; archived hooks/config were not run.
