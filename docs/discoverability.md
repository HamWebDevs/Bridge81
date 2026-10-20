# Bridge81 GitHub discovery and release positioning

[Bridge81](../README.md) · [Releases](https://github.com/HamWebDevs/Bridge81/releases) · [Windows 8.1 setup](windows81.md)

Bridge81 is a **local Windows 8.1 workbench and Ren'Py diagnostic utility**, not a universal game compatibility patch. The independent runtime-repair ZIP targets verified missing Microsoft UCRT files with backups and Undo. The separate workbench runs Python/Cygwin tasks and analyzes games without executing their scripts during inspection.

## Suggested GitHub repository About settings

Repository maintainers can apply these under **About → gear icon**. This document does not set them.

**Description:** `Windows 8.1 workbench for Python, Cygwin and older Ren'Py games, with verified UCRT repair and DLL diagnostics.`

**Topics:** `windows-8-1`, `renpy`, `legacy-windows`, `runtime-repair`, `python`, `cygwin`, `game-development`, `troubleshooting`, `desktop-app`, `compatibility`.

Use precise, discoverable keywords. Do not claim modern Ren'Py compatibility, universal DLL fixes, Windows 8.1 hardware certification or an official relationship with Microsoft/Ren'Py.

## Quick paths for visitors

- **Missing `api-ms-win-crt-*.dll`:** Download the small [verified runtime-repair ZIP](https://github.com/HamWebDevs/Bridge81/releases/tag/v0.3.0), extract it and launch `Repair-RenPy.cmd`.
- **Mixed engine architecture:** Follow [the read-only diagnosis and clean-build checklist](games.md#mixed-32-bit-and-64-bit-executables), not an unsafe patch override.
- **Run local scripts:** Follow the [Python and Cygwin setup guide](windows81.md).
- **Integrate game evidence with CI:** Use [the optional DevPocket plugin](dependencies.md).

## Responsible usage signals

Release asset download counts can indicate that someone fetched a package, but do not prove the repair completed, that a game launched, or that a Windows 8.1 device was tested. Bridge81 sends no telemetry. Repository maintainers can examine short-window repository traffic through **Insights → Traffic**. Publish anonymized compatibility results only with the reporter's permission.
