# Game checks and temporary launch profiles

Select the complete, extracted Windows build. A Linux-only build cannot be launched natively on Windows through Bridge81. Select the intended executable explicitly if the folder contains multiple `.exe` files.

## Evidence

The checker reads up to 256 KiB from each of `renpy/__init__.py`, `renpy/vc_version.py`, `log.txt` and `traceback.txt`. It recognizes literal engine version tuples or version lines; it never imports those files. It examines at most 1,024 entries in the game root and never recursively unpacks archives. Explicit executable selection remains possible when a folder has many entries.

Metadata pointing outside the selected folder is skipped with a warning. An executable outside that folder is rejected. Files are ordinary local inputs: inspection is not a malware scan or a security boundary against a hostile filesystem being changed concurrently.

The PE checker reads a small header and reports machine architecture, optional-header format and declared subsystem version. A Windows 8.1 x64 target accepts x86 or x64; an x86 target accepts x86 only. ARM builds and a declared subsystem newer than Windows 6.3 are blocked. The launcher's header can differ from the engine it starts, so a passing header never establishes complete architecture or dependency compatibility.

**Unverified** means no recognized blocker was found. Dynamic DLL imports, CPU instructions, GPU drivers, model-based graphics requirements and game-specific scripts are not assessed. Conflicting versions are unknown; if any evidence says Ren'Py 8.4 or newer, launch stays blocked until the developer resolves that evidence.

## Profiles

| Profile | Child-process settings | Intended use |
| --- | --- | --- |
| default | No overrides | Normal launch; inherited game settings still apply. |
| low-memory | `RENPY_LESS_MEMORY=1`, `RENPY_LESS_UPDATES=1`, `RENPY_DISABLE_FULLSCREEN=1` | Trade speed and updates for lower memory use; refuse fullscreen. |
| windowed | `RENPY_DISABLE_FULLSCREEN=1` | Investigate fullscreen-specific issues. |
| no-audio | `RENPY_DISABLE_SOUND=1` | Isolate an audio issue. |
| no-joystick | `RENPY_DISABLE_JOYSTICK=1` | Isolate faulty controller input. |

These are documented Ren'Py variables, whose availability can vary by engine. Settings affect the launched child only. Bridge81 writes no `environment.txt`, patches no game files and changes no machine environment. The game itself can write its normal logs, configuration and save data. Games are detached and keep running when the workbench closes.

## Missing runtime DLLs

For `api-ms-win-crt-*.dll` or `ucrtbase.dll` errors, use **Games → Repair missing runtime** or the independent **Repair-RenPy.cmd** launcher. That explicit action adds Microsoft's checksum-verified application-local UCRT set and keeps original-file backups with Undo. It also works when Python cannot start. It is separate from read-only inspection and temporary launch profiles. See [runtime repair](runtime-repair.md) for scope, offline downloads and source provenance.

Unknown engines require an explicit trust override. That override does not bypass a recognized OS, header or architecture blocker. Use only trusted game builds: running one grants it your normal user permissions.

## Mixed 32-bit and 64-bit executables

If Bridge81 refuses a game because an engine folder mixes x86 and x64 executables, it has found inconsistent architecture evidence. This is a **protective stop**, not proof that every file in the folder is broken. Some complete game distributions bundle separate platform helpers, while manually mixed or partly overwritten installs can also create this situation. The inspector cannot safely guess which of these applies.

1. Confirm the game's selected main `.exe` and use **Inspect game** or `bridge81 dependencies <folder> --exe <game.exe>` to collect read-only architecture evidence.
2. Compare the installation with a clean, unmodified download from the game's publisher. Check that the correct **Windows** edition was extracted completely; avoid merging builds or replacing a single `renpy`, `lib` or `python` folder with one from another version.
3. If the publisher supplies a clear x86/x64 launch choice, select its matching launcher. Do not rename a 32-bit executable to bypass an architecture gate, mix DLLs from random web sites or turn off checksum verification.
4. If the clean build still triggers a mixed-engine stop, preserve the read-only report and ask the game developer to confirm its supported layout. A future scoped compatibility rule needs reproducible evidence rather than a blanket override.

The repair does not install DirectX, OpenGL drivers, GPU capabilities or new Ren'Py engine binaries. An x64 computer can run many x86 programs, but **a single process cannot load a DLL of the wrong architecture**.

## Graphics issues

Hold Shift while starting Ren'Py, or press Shift+G after it starts, to open the built-in Graphics Acceleration menu. Try GL or ANGLE using the choices that the game actually offers. Classic renderers are not suitable for every model-based game and were removed in Ren'Py 8.4. Old software-renderer instructions do not provide a universal fallback.

Ren'Py 8.4+ requires Windows 10. A profile cannot change that requirement. Ask the developer for an older compatible build, or use a supported operating system. Replacing bundled runtime files can break Python bytecode, script compilation, extensions and save compatibility.

Exported reports include only the folder name, relative evidence names, selected executable header and findings. They omit absolute paths and log contents. Folder and executable names can still identify a game; review a report before sharing it.
