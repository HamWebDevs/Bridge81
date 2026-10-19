# DLL evidence without starting the game

[Back to Bridge81](../README.md) · [Runtime repair](runtime-repair.md) · [Testing status](testing.md)

In **Games**, choose a complete extracted game folder and its main executable, then click **Inspect DLLs**. Or use the dependency-free CLI:

```console
python -m bridge81 dependencies C:\Games\Story --exe Story.exe --format markdown
python -m bridge81 dependencies C:\Games\Story --exe Story.exe --format json
```

The report reads PE import and delay-import tables as file metadata. It never starts the game, imports game Python, loads a DLL, downloads files or changes the build. It inspects the selected launcher and recognized game/Python executables and Python DLLs in Windows platform folders. Helpers such as `zsync.exe` do not determine engine architecture.

| Evidence | Interpretation |
| --- | --- |
| `universal-crt` | A UCRT import such as `ucrtbase.dll` or `api-ms-win-crt-*`. The independent repair targets the cataloged UCRT set. |
| `visual-c-runtime` | A Visual C/C++ runtime name. The UCRT repair does not supply every Visual C++ DLL. |
| `windows-api-contract` | An API-set contract, not an ordinary file that must sit beside the game. |
| `windows-system` | A recognized Windows name; this scan does not verify the installed OS copy or required exports. |
| `application` | Another imported library; investigate the game's complete original distribution. |
| `bundle_candidates` | Files beside the importer or at the game root, with architecture evidence. Presence does not prove Windows will select or successfully load them. |

A DLL absent from the inspected bundle can be supplied by Windows or an installed runtime. System availability stays **unknown**. An incompatible or unreadable file beside an importer produces a warning. A root-level candidate is listed as evidence because process directory/search rules can differ from an engine module's folder.

This does not simulate the Windows loader or recursively resolve dependencies, dynamic imports, exported functions, manifests, API-set mappings, CPU instructions or graphics drivers. It cannot make Ren'Py 8.4+ support Windows 8.1. Use the original game distribution and official runtime sources when investigating dependencies.

## Bounds and privacy

The scanner reads at most 256 KiB of import metadata per module, up to 32 modules and 512 direct/delay library references across a build. It bounds PE sections, descriptors, names, directory entries and file offsets; malformed, ambiguous or unsupported structures are reported as unreadable. Dependency inputs reject symbolic links and junctions. Reports contain relative filenames without dialogue, full logs or absolute checkout paths.

CLI status **0** means inspection completed, including warnings and unknown system availability; **1** means at least one module's import metadata could not be inspected; **2** means invalid input or a resource limit stopped the operation. Status 0 is not a compatibility certification.

## Connect to DevPocket

Install Bridge81 and DevPocket 1.x in the same Python environment. Standalone Bridge81 does not require DevPocket:

```console
python -m pip install .
devpocket plugins list
devpocket plugins enable bridge81-game
```

From a project containing `games/Story`, use these Bash quoting examples:

```bash
devpocket run bridge81-game --input '{"folder":"games/Story","exe":"Story.exe"}' --format sarif
devpocket serve --root /absolute/project --plugin bridge81-game
```

On Windows Command Prompt, use `--input "{\"folder\":\"games/Story\",\"exe\":\"Story.exe\"}"`.

The API v1 tool exposes metadata, conservative compatibility findings and DLL evidence. Optional inputs are `target` (`x64` or `x86`) and `dependencies` (default true). Paths stay inside the project. Known OS/architecture blockers and unreadable dependency metadata return an operational failure that findings baselines and `--fail-on none` cannot suppress. Other warnings follow normal DevPocket severity policy.

The adapter stays uncached because complete game/engine/runtime inputs are not a single declared file. Plugin enablement is a trust decision; a read-only declaration is not a sandbox. MCP exposure requires both project enablement and the explicit server flag. No launch, repair or downloader is exposed.

PE tables follow Microsoft's [PE format specification](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).
