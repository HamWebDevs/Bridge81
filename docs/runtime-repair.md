# Repair a missing Ren'Py runtime

For errors such as **api-ms-win-crt-heap-l1-1-0.dll is missing**, **api-ms-win-crt-runtime-l1-1-0.dll is missing**, or a missing **ucrtbase.dll** on Windows 8.1.

1. Download the small **runtime-repair ZIP** from [Bridge81 releases](https://github.com/HamWebDevs/Bridge81/releases/tag/v0.3.0) and extract the **whole** ZIP.
2. Close the game and double-click **Repair-RenPy.cmd**.
3. Click **Choose game**, select the main game EXE beside its `game` and `renpy` folders, then click **Repair runtime**.
4. Start the game normally. To reverse the repair, choose the same EXE and click **Undo repair**.

The same launcher is included in the complete source and desktop ZIPs. A running workbench also has **Games → Repair missing runtime**. The repair utility uses Windows PowerShell 4.0 and Windows Forms, independent of Python and the frozen workbench. Run it with your ordinary account. If the game is in a protected folder, extract a fresh copy into a user-writable folder first.

## What it changes

The utility downloads the Windows 10 SDK **10.0.14393.795** UCRT redistributable directly from Microsoft. It verifies each cabinet's pinned SHA-256 and size, extracts it using Windows' `expand.exe`, then checks each DLL's SHA-256, size and PE architecture. It installs the **complete 41-file set** for the selected executable's architecture and separately matches recognized Ren'Py `lib/windows-*`, `lib/win-*` or `lib/win32` engine folders, including `py2-` / `py3-` prefixes, by reading PE headers. A 32-bit launcher and a 64-bit engine receive different matching sets in their respective folders.

Architecture selection prioritizes the game's named engine EXE, `python.exe`, `pythonw.exe`, `renpy.exe` and Python runtime DLLs. A 32-bit helper using the OS `msvcrt.dll` can coexist with a 64-bit engine; its presence no longer causes a false engine conflict. Helper bytes are preserved. If identified game/Python runtime files disagree, repair stops before changing files. A bounded, conservative string scan also refuses opposite-architecture helpers referencing UCRT, cataloged API forwarders or Visual C++ 14 DLL names. This scan is not a complete analysis of transitive or dynamic dependencies. It avoids deliberately placing one incompatible runtime set next to two consumers that both require it.

Only `ucrtbase.dll` and the cataloged `api-ms-win-core-*.dll` / `api-ms-win-crt-*.dll` forwarders are eligible. Existing eligible files are backed up under the game's `.bridge81-runtime` folder; a receipt records relative paths and checksums. Files already matching the official set are left alone. Save data, Python/SDL/graphics libraries, game archives and executable bytes are outside the repair's write set. It does not run the game as a test. Inspection stays read-only; runtime repair is a separate explicit action.

Copies use temporary files and atomic renames/replacements. A write failure attempts rollback. Undo validates the whole receipt and every backup before changing files, and stops if a runtime file was edited after repair. Keep the backup folder if a rollback cannot complete; do not delete it to make an error disappear. Close all instances of the game before repair or Undo. Existing-file replacement requires a filesystem that supports Windows `File.Replace`, normally NTFS; unsupported filesystems stop the repair.

The verified cache is under `%LOCALAPPDATA%\Bridge81\RuntimeCache`. Cached cabinets and extracted runtime files are verified again, and extracted files are rebuilt from the verified cabinet on each repair. Certificate verification stays enabled. The launcher sets execution policy for its own PowerShell process only and does not change the machine's policy.

## If Windows cannot download the files

Old Windows certificate or TLS settings can prevent PowerShell's download even when Firefox works. Use these **official Microsoft** links in your browser; leave both CAB files in your normal **Downloads** folder, then click **Repair runtime** again:

| Runtime | Official download | SHA-256 |
| --- | --- | --- |
| x64 | [948a611cd2aca64b1e5113ffb7b95d5f.cab](https://download.microsoft.com/download/C/D/8/CD8533F8-5324-4D30-824C-B834C5AD51F9/standalonesdk/Installers/948a611cd2aca64b1e5113ffb7b95d5f.cab) | `13719323a05589c3ee7f600794c5d385d692ba1a30d87ce86987b23d511de976` |
| x86 | [fef2cfedd6135e0ed85290b83f3682c3.cab](https://download.microsoft.com/download/C/D/8/CD8533F8-5324-4D30-824C-B834C5AD51F9/standalonesdk/Installers/fef2cfedd6135e0ed85290b83f3682c3.cab) | `408b2c176fdc7eee8ae5ab4bbd1b65f284d4900448b6c014c8dc90294a98c31d` |

Alternatively put the CABs in a `runtime-downloads` folder beside `Repair-RenPy.cmd`, including when transferring them from another computer. Their names and checksums must match. The tool selects the required architecture automatically, verifies the browser-downloaded files, and never executes the cabinets or the SDK installer.

## Scope and limitations

Microsoft supports application-local deployment of the UCRT. Its preferred system-wide deployment is Windows Update; local deployment needs separate servicing. This repair avoids depending on a working Windows Update prerequisite chain, and does not repair the OS itself. On Windows 10 and 11, Windows uses its own system UCRT ahead of a local copy.

This is a fix for missing UCRT dependencies, not a guarantee that every Ren'Py game runs on Windows 8.1. **Ren'Py 8.4+ requires Windows 10**, and recognized newer versions are refused. Missing `vcruntime140*.dll` or `msvcp140*.dll`, unsupported GPU features, CPU instructions, game-specific code and other OS APIs are separate issues. This utility does not replace those components or downgrade the game's engine. Windows 8.1 hardware/game launch verification remains pending; modern Windows CI verifies the repair mechanics only.

## Source provenance

- [Microsoft UCRT deployment documentation](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment): application-local support, the complete forwarder set and the downlevel 14393 runtime family.
- [Official Windows SDK archive](https://learn.microsoft.com/en-us/windows/apps/windows-sdk/downloads-archive): **10.0.14393.795**, [official installer link](https://go.microsoft.com/fwlink/p/?LinkId=838916).
- The archive link resolves to the `CD8533F8-5324-4D30-824C-B834C5AD51F9/standalonesdk` download directory. Its `Installers/Universal CRT Redistributable-x86_en-us.msi` is SHA-256 `6d76c3f206059d0a85a550317c0192f079147c1970335eb79deaba9b2aac9556`.
- The MSI's `Media`, `File`, `Component` and `Directory` tables identify both cabinets, their member-to-filename mappings, architecture and version. `scripts/ucrt-manifest.json` pins hashes from the downloaded official cabinets and all 82 extracted x86/x64 DLLs. The third ARM cabinet is not used.

The repair download contains Bridge81 scripts and the catalog, without Microsoft binaries. Runtime files downloaded from Microsoft retain Microsoft's terms and do not become MIT-licensed. Never substitute a DLL download site for these sources.
