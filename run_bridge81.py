"""Source/desktop entry point; keep beside the bridge81 package folder."""

import sys

if sys.version_info < (3, 10):
    raise SystemExit("Bridge81 needs Python 3.10 or later. Python 3.12 is the Windows 8.1 setup baseline.")

from bridge81.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
