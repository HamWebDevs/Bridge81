"""Entry point for the optional frozen GUI; not a general Python interpreter."""

import sys

from bridge81.gui import App, main


if __name__ == "__main__":
    if sys.argv[1:] == ["--smoke-test"]:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        App(root)
        root.update()
        root.destroy()
        raise SystemExit(0)
    raise SystemExit(main())
