"""Windowed entry point for PyInstaller (not a general Python interpreter)."""

import os
from pathlib import Path
import sys

# Windowed Python sets these to None. Initialize before third-party imports;
# app.main replaces stderr with the normal application log after Qt starts.
for stream_name in ("stdout", "stderr"):
    if getattr(sys, stream_name) is None:
        setattr(sys, stream_name, open(os.devnull, "w"))

if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--smoke-test":
        from molrecognizer.diagnostics import smoke_test
        if len(sys.argv) == 4 and sys.argv[3] != "--require-osra":
            raise SystemExit(2)
        raise SystemExit(smoke_test(Path(sys.argv[2]), require_osra=len(sys.argv) == 4))
    from molrecognizer.gui.app import main
    main()
