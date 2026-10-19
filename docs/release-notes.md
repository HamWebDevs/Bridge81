# Bridge81 0.2.0 preview - Ren'Py runtime repair

A Python-free repair utility for missing `api-ms-win-crt-heap-l1-1-0.dll` and related Microsoft Universal C Runtime errors on older Windows installations.

## Download for the missing DLL error

Choose **Bridge81-0.2.0-runtime-repair.zip**, extract the entire ZIP, then double-click **Repair-RenPy.cmd**. Choose your main game EXE and click **Repair runtime**. Launch the game normally afterwards. No Python or administrator access is needed for the repair window.

The utility downloads Microsoft's SDK 14393.795 runtime directly, checks cabinet and individual-DLL SHA-256 hashes, and adds the complete 41-file set beside each recognized executable. It matches 32-bit and 64-bit launcher/engine folders separately. Existing runtime files are backed up for **Undo repair**; later edits are preserved by refusing an unsafe Undo. Write failures attempt rollback. Offline/browser-downloaded Microsoft cabinets are supported when Windows' TLS or certificates prevent downloading.

## Other downloads

- **Bridge81-0.2.0-source.zip**: the full project, Python-free repair, optional verified Python setup, examples and documentation. Open `Start-Bridge81.cmd` for the workbench or `Repair-RenPy.cmd` for runtime repair.
- **Bridge81-0.2.0-windows-x64-preview.zip**: standalone native workbench plus the independent repair launcher. Extract the whole folder. The workbench still needs a working UCRT to start; the repair launcher does not depend on its Python runtime.
- **Wheel / sdist**: Python CLI/package for developers. Use a complete ZIP for the independent repair launcher and its external resources.
- **SHA256SUMS** covers the five downloadable build files.

## Validation and scope

Publication is gated by Windows/Linux core tests, native Tk smoke checks, real Cygwin integration, Python distribution builds, Windows PowerShell repair-window and transaction checks with actual Microsoft cabinets, and a frozen Windows desktop smoke check. The packaged independent repair window is checked too. These run on modern CI systems; **actual Windows 8.1 game launch verification remains pending**.

This targets the missing UCRT dependency. It does not make every game compatible or repair Windows Update. Ren'Py **8.4+ needs Windows 10** and is refused for this target; graphics drivers, CPU instructions, other runtime DLLs and game-specific code can still need separate attention. The repair writes only the cataloged Microsoft runtime set and reversible backups, preserving game executable bytes and save data. Microsoft DLLs are downloaded from Microsoft and retain Microsoft's terms; none are bundled in the repair ZIP.

The rest of Bridge81 remains available: Python and Cygwin script runners, project venvs, exact-argument plans, bounded output, timeouts/cancellation, read-only game inspection, privacy-conscious reports and temporary low-memory/windowed/audio/controller profiles. Optional Python setup remains pinned to the traditional Python.org 3.12.10 installer, the last full 3.12 maintenance installer rather than the latest security source release.
