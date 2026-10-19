# Windows 8.1 setup

## Start from the source ZIP

Extract the complete archive. Do not run a `.cmd` while it is still inside Explorer's ZIP viewer. Keep paths short; Windows 8.1 does not have modern Windows' general long-path support.

`Start-Bridge81.cmd` looks for the private Bridge81 runtime, then traditional Python launchers for 3.12, 3.11 and 3.10, then `python` on PATH. The app needs Tcl/Tk, which the standard traditional installer normally includes. An embeddable Python ZIP does not include Tk or a normal pip/venv setup and is not the recommended interpreter here.

You can explicitly use a trusted installation:

```console
"C:\Path To Python\python.exe" "C:\Tools\Bridge81\run_bridge81.py"
```

## Optional Python setup

`Setup-Python.cmd` runs the included Windows PowerShell 4-compatible setup script. It explains the action before it starts. The PowerShell execution-policy override affects that process only.

The script downloads `python-3.12.10-amd64.exe` from Python.org into a unique temporary folder, checks a pinned SHA-256 and a valid Python Software Foundation Authenticode signature, and runs the traditional installer in passive mode. It requests a per-user runtime under `%LOCALAPPDATA%\Bridge81\Python312`, with pip and Tcl/Tk. It requests no PATH changes, file associations, Python launcher or shortcuts. The installer registers its normal per-user uninstall entry. It can still require Windows runtime updates already missing from a very old installation.

Pinned installer SHA-256:

```text
67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb
```

The digest was read from the official release's `.sigstore` bundle. Setup verifies the downloaded file and Authenticode; it does not implement a Sigstore verifier. Temporary downloads are removed when setup ends.

Python 3.12.10 is the last full maintenance installer, not the latest security source release. Use a newer trusted compatible runtime if you maintain one. No third-party patched Python distribution is bundled or recommended.

If another traditional Python 3.12 is already installed, use or modify that installation rather than forcing a second private copy. If its launcher is unavailable, use its full `python.exe` path. An existing private runtime that fails validation is reported for repair and is not overwritten by the setup script.

## Cygwin

Current Cygwin is x64. Install the official build for your own user with `setup-x86_64.exe --no-admin`, choose a root you can write to, and select the packages you actually need. Bridge81 checks that the selected `bash.exe` has `cygwin1.dll` and `cygpath.exe` beside it. Git Bash and MSYS2 are separate environments and are not treated as interchangeable adapters.

A `.sh` script must use tools installed in Cygwin. A Linux `.deb`, ELF executable, `apt` command or Linux game is not made compatible by this adapter. Use a VM, a separate Linux installation or a remote Linux system when a real Linux kernel is required; those are outside this preview.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| Start reports missing Python | Run Setup-Python.cmd, or use the traditional Python 3.12 installer with Tcl/Tk. |
| Certificate verification fails | Check the laptop's date, time and Windows certificate updates. Setup refuses to skip verification. The official release page is linked in the app. |
| Missing runtime DLL when Python starts | Use the traditional official installer and apply its required Windows runtime updates. Do not fetch individual DLLs from download sites. |
| Python package refuses to install | That package may have dropped Windows 8.1 or compatible wheels. A compatible interpreter does not guarantee every third-party package will work. |
| Bash reports `\r` or a strange option | Save the script with LF line endings. |
| Command waits for input | The runner closes stdin; run interactive programs in Cygwin Terminal or a normal terminal. |
| Wrong Python packages are loaded | Select the project's venv `Scripts\python.exe` and confirm the working directory. |
| Game does not start | Inspect its extracted Windows build and read [game troubleshooting](games.md). |

## Removal

The source app has no service or installer; remove its extracted folder when finished. Uninstall the optional Python runtime through Windows' normal Programs and Features entry if you no longer use it. Remove project virtual environments separately only when you no longer need them. Cygwin is a separate installation managed by its own setup.
