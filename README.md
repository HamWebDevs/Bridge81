# Bridge81

**Python. Unix tools. Older games. A useful workbench for Windows 8.1.**

Bridge81 is a small, local desktop app for giving an older Windows laptop a few more useful jobs. Run Python scripts in project environments, use Bash through Cygwin, and investigate why an older Ren'Py game will not start.

**0.2.1 preview.** Windows 8.1 is the target, not a verified compatibility claim. Core tests and native GUI smoke checks run on modern Windows and Linux. Actual Windows 8.1 hardware and GPU validation are still needed. See [testing status](docs/testing.md).

## Game says a runtime DLL is missing?

Download [**Bridge81-0.2.1-runtime-repair.zip**](https://github.com/HamWebDevs/Bridge81/releases/download/v0.2.1/Bridge81-0.2.1-runtime-repair.zip), extract the whole ZIP, and open **Repair-RenPy.cmd**. Choose the game's main EXE and click **Repair runtime**. It uses Windows' built-in tools and opens even when a missing UCRT stops Python or the main workbench from starting.

The repair downloads Microsoft's complete matching UCRT set, verifies its checksums, places it beside the launcher and recognized engine executables, and provides **Undo** with original-file backups. It targets errors such as `api-ms-win-crt-heap-l1-1-0.dll is missing`; other game requirements still apply. [Repair details and offline downloads](docs/runtime-repair.md).

## Start on Windows 8.1

1. Extract the whole project ZIP to a short folder such as `C:\Tools\Bridge81`.
2. Double-click **Start-Bridge81.cmd**.
3. If it reports that Python is missing, run **Setup-Python.cmd**, then open Start again. Setup checks the official installer's SHA-256 and Python Software Foundation signature, and installs Python for your user without changing PATH.
4. Open **Scripts**, choose `examples\hello.py`, then click **Preview command** or **Run script**.

Already have Python 3.10+ with Tcl/Tk? You can also run:

```console
python run_bridge81.py
```

Use the traditional **Python 3.12** installer for the documented Windows 8.1 baseline. The supplied x64 setup pins **3.12.10**, the last full 3.12 maintenance installer. Later 3.12 security releases are source-only; this is a legacy compatibility choice, not the latest security release. The Microsoft Store package and current Python install manager are not the Windows 8.1 installation route.

[Windows setup and troubleshooting](docs/windows81.md) · [Game compatibility](docs/games.md) · [Contributing](CONTRIBUTING.md)

[Download the 0.2.1 preview](https://github.com/HamWebDevs/Bridge81/releases/tag/v0.2.1) for the small runtime repair, complete source ZIP or optional standalone x64 workbench. Read the release's compatibility status before choosing a build.

## What you can do

| Workflow | What Bridge81 provides |
| --- | --- |
| Python projects | Choose an interpreter, working folder and exact arguments; create a new venv; capture output; cancel or set a timeout. |
| Unix scripts | Run `.sh` scripts with an installed Cygwin Bash, including paths with spaces and positional arguments. |
| Older Ren'Py games | Read engine metadata and PE headers; flag known OS/architecture blockers; export a report without absolute paths or dialogue. |
| Missing UCRT DLLs | Separate Python-free runtime repair; verified Microsoft files, architecture matching, original-file backups and Undo. |
| Troubleshooting | Apply temporary low-memory, windowed, no-audio or no-joystick settings to a selected game launch. |
| Automation | Use the same plans, inspection and execution through a dependency-free CLI and Python API. |

The native Tk interface uses no browser, web server, account, telemetry or third-party runtime packages. Nothing is downloaded when the app starts. Downloads occur only during explicit Python setup or runtime repair.

## Unix tools on Windows 8.1

Install [Cygwin x64](https://cygwin.com/install.html) from its official site. For a per-user installation, launch the official setup with `--no-admin`. Start with `bash`, `coreutils`, `grep`, `sed`, `gawk` and `findutils`; add development tools when needed.

In **Scripts**, select **Bash (Cygwin)** and browse to its `bin\bash.exe`. Try `examples\unix-tools.sh`. Bridge81 uses Cygwin's `cygpath` to translate paths and keeps script arguments separate from the fixed shell wrapper. Scripts are non-interactive and should use LF line endings.

Cygwin provides Unix tools compiled for Windows. It does **not** run arbitrary Linux ELF binaries, provide a Linux kernel, or bring WSL to Windows 8.1. Use Cygwin Terminal for programs that need interactive input. Current Cygwin requires 64-bit Windows.

## Ren'Py compatibility, honestly

Choose a complete, extracted Windows game build in **Games**, then select its `.exe` and click **Inspect game**. Inspection never imports the game's Python files. Reports stay **unverified** unless a known blocker is found; a PE header cannot reveal every DLL, CPU instruction or graphics requirement.

Ren'Py **8.4 and newer require Windows 10**. Bridge81 blocks those builds for its Windows 8.1 target, including when conflicting metadata mentions a newer engine. Older engines can still fail because of drivers, game-specific code or dependencies. The explicit UCRT repair is limited to Microsoft's cataloged runtime files; swapping a game's engine, Python or graphics libraries is outside its scope.

For a black screen, the app also explains Ren'Py's built-in **Shift / Shift+G** graphics menu. Try the game's GL or ANGLE option there. A universal software renderer is not available in current engines.

## CLI examples

The source checkout works without installation:

```console
python -m bridge81 doctor
python -m bridge81 plan python examples/hello.py --args-json "[\"hello world\"]"
python -m bridge81 run python examples/hello.py
python -m bridge81 run venv C:\Projects\demo\.venv
python -m bridge81 game C:\Games\Story --exe Story.exe --format markdown
python -m bridge81 plan renpy C:\Games\Story --exe Story.exe --profile low-memory
python -m bridge81 run renpy C:\Games\Story --exe Story.exe --profile windowed
```

On Linux/macOS, use single quotes around JSON: `--args-json '["hello world"]'`. `plan` never executes. `run renpy` is Windows-only and detaches the game; script runs capture at most 1 MiB and default to a 120-second timeout. Scripts have your ordinary user permissions. They are not sandboxed. Cancellation attempts to stop the process tree; detached descendants and restricted processes can escape cleanup.

To install the CLI into an existing environment:

```console
python -m pip install .
bridge81 --help
```

## For contributors

```console
python -m unittest discover -s tests -v
python tests/gui_smoke.py
python -m pip install build
python -m build
```

The GUI smoke check needs a desktop display. [Development notes](docs/development.md) explain the plan/runner separation, evidence limits and optional standalone Windows build. GitHub Actions configurations cover modern Windows and Linux, plus GUI startup and PowerShell parsing. Their results do not establish Windows 8.1 compatibility.

## Compatibility sources

Reviewed on 2026-10-19. These upstream constraints inform Bridge81's checks:

- [Python 3.12 on Windows](https://docs.python.org/3.12/using/windows.html): Windows 8.1 support, traditional installer, Tcl/Tk and per-user options.
- [Python 3.12.10 release](https://www.python.org/downloads/release/python-31210/): last full maintenance release and official installer/signature files.
- [Cygwin FAQ](https://cygwin.com/faq.html#faq.what.supported): current x64 Windows platform support.
- [Cygwin installation](https://cygwin.com/install.html): package selection and `--no-admin`.
- [Ren'Py 8.4 announcement](https://www.renpy.org/release/8.4.0): Windows 10 minimum.
- [Ren'Py environment variables](https://www.renpy.org/doc/html/environment_variables.html): temporary launch options.
- [Ren'Py display troubleshooting](https://www.renpy.org/doc/html/problems.html): renderer menu and graphics limits.
- [Microsoft PE format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format): executable architecture and subsystem header fields.

MIT licensed. Maintained as **HamWebDevs**. Bridge81 is independent of Python, Cygwin, Microsoft and Ren'Py; third-party projects keep their own licenses.
