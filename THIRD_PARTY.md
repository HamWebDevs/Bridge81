# Third-party components

The source project contains no bundled third-party runtime or game. Its code is MIT licensed. The optional Python setup downloads an official installer governed by Python's own license. The explicit Ren'Py runtime repair downloads Microsoft's UCRT redistributable cabinets directly from Microsoft, verifies their checksums and extracts the application-local runtime. Microsoft runtime files retain Microsoft's terms; they are not part of Bridge81's MIT license and are not bundled in the repair ZIP. See [runtime source provenance](docs/runtime-repair.md#source-provenance).

The optional standalone desktop build bundles CPython, Tcl/Tk and a PyInstaller bootloader. Distribution preparation copies the installed Python and PyInstaller license files, plus available Tcl/Tk license texts, into `third-party-licenses`. Keep those files with any redistributed build.

- [CPython license and incorporated software](https://docs.python.org/3.12/license.html)
- [Tcl/Tk licensing](https://www.tcl-lang.org/software/tcltk/license.html)
- [PyInstaller licensing and bootloader exception](https://pyinstaller.org/en/stable/license.html)

The frozen runtime runs the workbench only. A full external Python installation is needed to run user Python scripts or create venvs. Cygwin is installed separately and retains its own package licenses. Ren'Py's engine, game archives and save data are not bundled or redistributed. Explicit runtime repair writes only its cataloged Microsoft runtime files and reversible backups in the chosen game folder.
