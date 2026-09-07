"""Private console helper: SMILES on stdin, RDKit binary on stdout.

This is a separate executable in portable builds. A windowed PyInstaller EXE
has no standard streams and cannot act as ``python -c`` for its own children.
QProcess launches this console helper without opening a console window.
"""

import sys
import traceback


def main() -> int:
    from .core.xyz import generate_3d

    try:
        mol = generate_3d(sys.stdin.read())
        sys.stdout.buffer.write(mol.ToBinary())
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
