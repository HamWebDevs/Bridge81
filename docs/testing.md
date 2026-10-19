# Validation record

Version: **0.3.0 preview**. Development date: **2026-10-19**.

## Runtime repair validation

### Windows 8.1 user report

On 2026-10-19, a user of Windows 8.1 x64 reported that one Ren'Py game worked after the 0.2.0 UCRT repair. Its game/engine version and a launch log were not recorded, and this was a user report rather than an independently observed device test. A second game hit the overly broad mixed-architecture check; 0.2.1 adds specific regression fixtures for a 32-bit helper beside a 64-bit engine, conflicting Python DLLs and Python-prefixed platform folders. The first report does not establish compatibility with other games or hardware.

The release gate runs `tests/runtime_repair_test.ps1` using **Windows PowerShell** on modern Windows. It downloads the actual Microsoft SDK redistributable cabinets, checks their pinned hashes, uses Windows `expand.exe`, verifies all 82 x86/x64 DLLs, matches a mixed-architecture Ren'Py fixture, installs three complete runtime sets, checks executable/data preservation, restores an original DLL, refuses later user changes and receipt traversal, repairs a corrupted cache and injects a write failure to check rollback. It also checks junction rejection. Native repair-window smoke checks run before and after desktop packaging.

The mixed-helper regression uses Ren'Py's actual official 32-bit `zsync.exe`, downloaded from an immutable source commit and verified with a pinned SHA-256. It is read as data and never executed. The tests verify a 64-bit runtime is selected, helper bytes survive repair/Undo, conflicting Python files still stop before changes, and Python-prefixed platform folders receive the matching runtime.

Local PowerShell 7 checks on Linux use an extraction fixture backed by `cabextract`; those checks exercise the same official payloads and repair transactions but do not establish Windows PowerShell or Windows 8.1 behaviour. The Windows release gate supplies the native Windows checks. Consult the completed workflow before reporting a CI result.

## Automated coverage

The unit/integration suite exercises real Python execution, exact arguments with quotes and shell metacharacters, working directories, virtual environment creation and interpreter selection, timeouts, cancellation, bounded output, inherited output pipes, Bash execution and the fixed Cygwin wrapper with a path-converter fixture. Read-only game cases cover version evidence, conflicts, architecture and subsystem blockers, unknown engines, malformed PE input, path containment, metadata limits and report privacy.

Completed locally on a Linux development host with Python 3.12.14:

- **63 unit/integration tests passed** for 0.3.0, including malformed PE images, direct/delay imports, bounded sparse-file reads, bundle evidence and both Markdown report commands.
- **Native Tk GUI smoke passed:** widget creation, exact-argument preview, a background script run, game/DLL inspection and launch preview.
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
- [ ] Open Repair-RenPy.cmd without Python installed and verify its large-text picker.
- [ ] Repair the missing-UCRT error on a real older Ren'Py game, launch it and test Undo.
- [ ] Test browser-downloaded cabinets when Windows' TLS or certificate store prevents downloads.
- [ ] Record Windows build, OS architecture, Python, Cygwin, GPU/driver and game engine versions.

Do not claim all games work, all Linux programs work, or Windows 8.1 has been tested until actual device evidence supports the narrower claim. Screenshots of a GUI on Linux or Windows 11 do not prove Windows 8.1 support.
