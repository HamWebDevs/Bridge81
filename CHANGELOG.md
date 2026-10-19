# Changelog

## 0.2.0 — 2026-10-19

- Python-free `Repair-RenPy.cmd` and native repair window for missing Microsoft UCRT DLLs.
- Official SDK 14393.795 runtime downloads pinned by cabinet and individual-file SHA-256; all 41 files per architecture are included in each repair.
- Separate architecture matching for the launcher and recognized Ren'Py Windows engine folders.
- Original-file backups, verified Undo, atomic file copies and automatic rollback after write failures.
- Offline/browser-downloaded cabinet support when old Windows certificate or TLS settings prevent the download.
- Small standalone repair ZIP, a Games-tab entry point, and Windows PowerShell integration checks with real Microsoft cabinets.

The new utility targets the missing runtime error. Actual Windows 8.1 game verification remains pending.

## 0.1.0 — 2026-10-19

Initial preview:

- Native Tk desktop workbench and shared command-line interface.
- Explicit Python and Cygwin Bash script plans with separate arguments.
- New virtual environments, bounded captured output, timeouts and cancellation.
- Windows scripts start suspended and join a cleanup Job Object before execution; descendants remain owned when a parent exits.
- Bounded Ren'Py metadata and PE header inspection with conservative blockers.
- Temporary low-memory, windowed, no-audio and no-joystick profiles.
- Privacy-conscious game report exports.
- Optional checksum/signature-verified traditional Python setup for x64 Windows.
- Automated core checks, GUI smoke test and GitHub workflow configurations.

Actual Windows 8.1 hardware validation is pending; this is not a v1 compatibility certification.
