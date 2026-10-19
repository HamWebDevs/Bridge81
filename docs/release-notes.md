# Bridge81 0.1.0 preview

A lightweight native workbench for Python projects, Cygwin Bash scripts and older Ren'Py game troubleshooting, targeting Windows 8.1.

## Choose a download

- **Bridge81-0.1.0-source.zip**: the complete project, Windows source launcher, optional verified Python setup, examples and documentation. Extract it and open `Start-Bridge81.cmd`. If Python is missing, run `Setup-Python.cmd` first.
- **Bridge81-0.1.0-windows-x64-preview.zip**: the standalone workbench. Extract the whole folder and open `Bridge81.exe`. No external Python is needed to open the app or inspect games. Running your own Python scripts and creating venvs still need a full external Python; the included optional setup provides the documented x64 baseline. Cygwin is installed separately.
- The **wheel** and **sdist** are for developers installing the Python CLI/package.
- **SHA256SUMS** covers the four downloadable build files.

## Included

- Native Tk interface and matching CLI, with no third-party Python runtime dependencies in the source app.
- Explicit Python and Cygwin plans, project venvs, exact arguments and working directories.
- Bounded script output, timeouts and cancellation. Windows scripts join a kill-on-close Job Object before user code runs, so cleanup still tracks children after their parent exits.
- Read-only Ren'Py version/PE checks and report export without absolute paths or dialogue.
- Temporary low-memory, windowed, no-audio and no-joystick game launch options.
- Optional Python.org setup with pinned SHA-256 and Authenticode verification.

## Compatibility status

This is a **prerelease**, not a Windows 8.1 certification. Publication requires the core tests, native GUI smoke, source launcher and setup parsing checks on modern Windows/Linux CI, a real Cygwin integration run on modern Windows, and a frozen Windows GUI smoke check. Actual Windows 8.1 hardware, its Cygwin/certificate behavior and specific GPU/game combinations still need device testing.

The optional setup uses Python **3.12.10**, the last full 3.12 maintenance installer, not the latest security source release. Cygwin runs Unix tools ported to Windows; it does not run arbitrary Linux ELF binaries or add WSL. Ren'Py **8.4+ requires Windows 10** and is blocked for the Windows 8.1 target. Older games remain unverified until tested on the machine. No game engines, saves or DLLs are patched or redistributed.
