# Validation record

Version: **0.1.0 preview**. Development date: **2026-10-19**.

## Automated coverage

The unit/integration suite exercises real Python execution, exact arguments with quotes and shell metacharacters, working directories, virtual environment creation and interpreter selection, timeouts, cancellation, bounded output, inherited output pipes, Bash execution and the fixed Cygwin wrapper with a path-converter fixture. Read-only game cases cover version evidence, conflicts, architecture and subsystem blockers, unknown engines, malformed PE input, path containment, metadata limits and report privacy.

Completed locally on a Linux development host with Python 3.12.14:

- **44 unit/integration tests passed.**
- **Native Tk GUI smoke passed:** widget creation, exact-argument preview, a background script run, game inspection and launch preview.
- **Desktop layout reviewed at 1000×660**, within a 1366×768 virtual display. The host's bitmap-font fallback is not representative of Windows' Segoe UI rendering.
- **Wheel and source distribution built**, with the installed wheel's CLI checked outside the source tree.
- **Official Python installer SHA-256 checked** against the actual downloaded installer, not just copied metadata.

GitHub validation on commit `994e057aad9d1d0afce447b74b58ae8b04252813` passed all **9 jobs**: core tests on Windows/Linux with Python 3.10, 3.12.10 and 3.13; native GUI smoke on both hosts; and distribution builds. Windows also passed the source launcher and PowerShell setup parser checks. The Windows core run includes Job Object cleanup after a parent process exits and canonical handling of short/long path aliases.

A dedicated real-Cygwin smoke job and a standalone Windows build are part of the preview release gate. Do not treat their configuration as a result; consult the completed release workflow. The Python installer has been checksum-checked but has not been executed by CI or on Windows 8.1.

## Windows 8.1 device checklist — pending

- [ ] Start source GUI using traditional Python 3.12 with Tcl/Tk.
- [ ] Verify optional setup download, checksum, Authenticode and per-user install.
- [ ] Run the Python example from a path with spaces and Unicode.
- [ ] Create a venv, select its interpreter and verify project isolation.
- [ ] Run the Cygwin example and compare all passed arguments.
- [ ] Cancel a script and test output/time limits.
- [ ] Inspect and launch a trusted older Ren'Py game using each relevant profile.
- [ ] Confirm Ren'Py 8.4+ is blocked without modifying game files.
- [ ] Test the actual generated standalone app, Universal CRT and Tcl/Tk loading.
- [ ] Record Windows build, OS architecture, Python, Cygwin, GPU/driver and game engine versions.

Do not claim all games work, all Linux programs work, or Windows 8.1 has been tested until actual device evidence supports the narrower claim. Screenshots of a GUI on Linux or Windows 11 do not prove Windows 8.1 support.
