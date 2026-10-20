# Saved runtime-log hints

[Back to Bridge81](../README.md) · [DLL inspection](dependencies.md) · [Runtime repair](runtime-repair.md)

```console
python -m bridge81 runtime-log C:\Games\Story\traceback.txt --format markdown
python -m bridge81 runtime-log C:\Games\Story\log.txt --format json
```

This reads a saved UTF-8 log and recognises common loader/import/graphics-error patterns. It never starts a game, executes log text, loads a DLL, downloads files or repairs anything. JSON/Markdown reports include fixed messages, suggested checks, matching-line counts and first/last line numbers. Raw lines, traceback contents and absolute input paths are withheld, including from parse errors.

| Pattern | Suggested investigation |
| --- | --- |
| WinError 126 / missing module | Complete extraction and DLL imports; the missing item may be a dependency of the named module. |
| WinError 127 / missing procedure | Engine/API requirements and library versions. |
| WinError 193 / invalid Win32 / `0xc000007b` | PE architecture and potentially damaged binaries. |
| UCRT / Visual C++ DLL mentions | Check the complete local error; a filename mention does not prove a runtime is missing. |
| Python module failure | Bundled game files and embedded Python, rather than assuming system Python packages will help. |
| Graphics-context initialization error | GPU/driver and the game's renderer options. |

Patterns are hints from a possibly stale saved log. Unrecognised text returns `no-recognised-pattern`, which is not evidence of compatibility or a clean run. No root cause is certified. Confirm the file belongs to the build being inspected before acting on it.

CLI status 0 means no recognised pattern, 1 means hints were found, and 2 means invalid/unsafe/unreadable input. Select a stable regular UTF-8 file of at most 2 MiB and 30,000 lines; symlinks, redirected directories and special files are refused. No partial-log success is returned when limits are exceeded.

## DevPocket plugin

Install Bridge81 and DevPocket in the same environment. Enable the second read-only plugin explicitly (Bash quoting shown):

```bash
devpocket plugins enable bridge81-runtime-log
devpocket run bridge81-runtime-log --input '{"log":"games/Story/traceback.txt"}' --format sarif
devpocket serve --root /absolute/project --plugin bridge81-runtime-log
```

The SDK exposes only root-contained files. Findings locate the saved log's matching line; the returned report withholds its raw content. Hints are warnings under the normal DevPocket severity/baseline policy. Invalid files are execution errors. The adapter remains uncached and provides no command-running, repair or download interface. Standalone Bridge81 still has zero runtime dependencies.
