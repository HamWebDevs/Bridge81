# Bridge81 development rules

- Preserve the Windows 8.1 target and the explicit preview testing status.
- Use Python 3.10-compatible source; test the traditional Python 3.12 baseline.
- Runtime dependencies remain at zero. Tkinter is optional for CLI use.
- Inspection must never execute game code, load a DLL, patch an executable or unpack game archives.
- Build argv arrays and use shell=False. Only the fixed Cygwin wrapper is shell code; pass user values positionally.
- Preserve venv executable symlinks and child-only environment settings.
- Do not invent compatibility: absence of a recognized blocker is unverified.
- Real Windows 8.1, Cygwin and GPU tests must be identified separately from modern CI.
- Use HamWebDevs only for owner credits. Do not introduce personal identity details.
- Run the unit/integration suite and use the GUI smoke test for UI changes.
