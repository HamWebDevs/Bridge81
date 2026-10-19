# Bridge81 0.3.0 preview — DLL evidence and developer integration

Investigate native game dependencies without running the game. **Inspect DLLs** and `bridge81 dependencies` read bounded direct/delay-import tables, classify runtime/API-set imports and show bundled architecture evidence. System availability stays unknown; this does not simulate the Windows loader or promise compatibility.

The optional `bridge81-game` DevPocket API v1 plugin connects inspection to structured checks, SARIF and explicitly exposed MCP tools. It cannot launch, repair or download. Known blockers remain operational failures under findings suppression. [Usage and limits](https://github.com/HamWebDevs/Bridge81/blob/main/docs/dependencies.md).

## Missing UCRT error

Choose **Bridge81-0.3.0-runtime-repair.zip**, extract the entire ZIP and open **Repair-RenPy.cmd**. Choose the main game EXE and click **Repair runtime**. The independent repair window needs no Python or administrator access.

The retained repair downloads Microsoft's SDK 14393.795 runtime, checks cabinet and individual-file SHA-256 hashes and adds the complete 41-file matching set beside recognized launchers/engines. Original-file backups, verified Undo and offline/browser-downloaded cabinets remain supported. The 0.2.1 mixed-helper fix and prior receipt compatibility are retained.

## Downloads

- **Bridge81-0.3.0-source.zip**: full project, independent repair, optional verified Python setup, examples and documentation. Open `Start-Bridge81.cmd` or `Repair-RenPy.cmd`.
- **Bridge81-0.3.0-windows-x64-preview.zip**: standalone native workbench plus independent repair utility. Extract the whole folder. The workbench needs a working UCRT; the repair launcher does not depend on its Python runtime.
- **Wheel / sdist**: Python CLI/package for developers. Use a complete ZIP for the independent repair launcher and external resources.
- **SHA256SUMS** covers all five build files.

## Validation and scope

Publication is gated by Windows/Linux core tests, native Tk checks including DLL inspection, installed DevPocket CLI/SARIF/MCP integration, real Cygwin integration, distribution builds, Windows PowerShell repair transactions using actual Microsoft cabinets and frozen desktop/packaged repair-window smoke checks.

These run on modern CI. Actual Windows 8.1 hardware/game validation remains limited: one user reported an older game working after UCRT repair without a recorded engine/launch log. This does not certify other games or devices. Ren'Py **8.4+ needs Windows 10**; graphics, CPU instructions, other runtime DLLs and game-specific code remain separate constraints.

Python/Cygwin runners, venvs, exact-argument plans, bounded output, timeouts/cancellation and temporary game profiles remain available. Optional Python setup pins the traditional Python.org 3.12.10 installer, the last full 3.12 maintenance installer rather than the latest security source release. No third-party runtime dependencies, automatic tuning or telemetry.
