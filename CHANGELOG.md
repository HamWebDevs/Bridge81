# Changelog

## 0.4.0 — 2026-10-21

- Add `bridge81 runtime-log` for saved Windows/Ren'Py log hints: missing modules/procedures, invalid images, UCRT/Visual C++ mentions, Python import failures and graphics-context errors.
- Return fixed explanations, cautious next steps and line counts/locations while withholding raw lines and private paths. Pattern matches are hints, not root-cause or compatibility claims.
- Add the optional read-only `bridge81-runtime-log` DevPocket API v1 plugin for project checks, SARIF and explicit MCP exposure. No launch, repair, downloader or automatic upload is exposed.
- Bound regular UTF-8 inputs to 2 MiB/30,000 lines; reject symlinks, special files and observed mutations. Include privacy/CLI and installed-plugin regression checks.
- Retain the existing DLL inspector, reversible runtime repair and Windows 8.1 preview status.

## 0.3.0 — 2026-10-19

- Add bounded PE direct/delay-import inspection, a Games-tab **Inspect DLLs** action and JSON/Markdown CLI reports.
- Classify UCRT, Visual C++, API contracts and application libraries; show nearby bundle candidates and architecture mismatches while keeping system availability unknown.
- Inspect recognized game/Python engine files and Python DLLs, including Python-prefixed folders. Ignore unrelated helpers and preserve all game files.
- Add the optional read-only `bridge81-game` DevPocket API v1 plugin for CLI, SARIF and explicit MCP exposure. It never launches or repairs and remains uncached.
- Add malformed-image, delayed-import, sparse-file, path and architecture regression tests, installed plugin checks and native GUI smoke coverage.
- Retain the Python-free UCRT repair, backups, Undo and 0.2.1 mixed-helper fix. Actual Windows 8.1 validation remains limited to the documented user report.

## 0.2.1 — 2026-10-19

- Fix a false architecture conflict when a 32-bit updater/helper sits beside a 64-bit Ren'Py engine.
- Select the runtime architecture from recognized game/Python entry points and Python DLL headers. Utilities no longer determine the engine architecture.
- Recognize Python-prefixed platform folders such as `lib/py3-windows-x86_64` and `lib/py2-windows-i686`.
- Preserve helpers through repair and Undo. Keep blocking actual engine/Python mismatches, and mixed helpers that reference UCRT or Visual C++ 14 DLLs requiring a conflicting runtime set.
- Add regression checks for both mixed-helper and Python-prefixed layouts.

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
