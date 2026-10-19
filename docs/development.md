# Development

Bridge81 runs from a source checkout and needs no third-party runtime packages. Python 3.10 is the source minimum; Python 3.12 is the documented Windows 8.1 baseline. Tkinter is needed only for the GUI.

## Structure

- `plans.py` validates input and returns argv/cwd/environment plans without execution.
- `runner.py` executes non-interactive scripts, bounds captured output, applies timeouts and attempts process-tree cancellation.
- `renpy.py` produces conservative reports and temporary game plans.
- `pe.py` reads bounded PE headers without loading executables or DLLs.
- `doctor.py` checks host information and default paths without running detected programs.
- `cli.py` and `gui.py` share those implementations.

Add a backend by implementing a plan builder and testing its argument handling against a real process. Do not concatenate untrusted values into shell commands. The Cygwin adapter uses a constant shell program with positional arguments because Bash itself is the requested runtime. Interpreter paths remain absolute without resolving the final symlink, which preserves virtual environments on Unix development hosts.

CLI and GUI runs are ordinary user processes, not a sandbox. Output is decoded as UTF-8 with replacement for invalid bytes. Python runs explicitly select UTF-8; other commands can still use their own output encoding. Output is displayed after completion, rather than streaming into the Tk event loop. Cancellation uses Windows taskkill or Unix process groups and cannot promise cleanup of detached or protected descendants. Captured output is bounded even if a descendant retains the pipe.

The GUI's worker communicates over a queue; only the UI thread accesses Tk widgets. A frozen GUI is not exposed as a Python interpreter. Child launches clear inherited Python path variables; optional PyInstaller builds reset the app-specific DLL search directory when starting external tools.

## Checks

```console
python -m unittest discover -s tests -v
python tests/gui_smoke.py
python -m bridge81 plan python examples/hello.py
python -m bridge81 run python examples/hello.py
```

`tests/gui_smoke.py` needs a desktop display. Windows CI uses an ordinary modern Windows runner; Linux CI uses Xvfb. Neither is a Windows 8.1 certification.

## Distribution

The standard source ZIP includes `Start-Bridge81.cmd`, the optional Python setup, examples and documentation. It runs without pip-installing the project. Wheels and sdists are also supported with `python -m build`.

The optional **Windows desktop build** GitHub workflow uses Python 3.12.10 x64 and pinned PyInstaller 6.16.0 to produce a folder-based app. Folder mode avoids extracting the runtime on every startup. It is a preview build, not a signed installer or a verified Windows 8.1 binary. Test the generated app on an actual Windows 8.1 machine, including Universal CRT and Tcl/Tk loading, before describing it as compatible. An external full Python installation remains necessary for running user Python scripts and creating venvs; the app's frozen runtime only runs the workbench.

Upstream packaging references: [PyInstaller Windows requirements](https://pyinstaller.org/en/stable/requirements.html) and [external-process environment guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application).
