"""Copy documentation and installed upstream license texts into a Windows build."""

from __future__ import annotations

import hashlib
import importlib.metadata
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / "dist" / "Bridge81"
    if not (target / "Bridge81.exe").is_file():
        raise SystemExit("Build the Windows desktop app before preparing its distribution.")
    licenses = target / "third-party-licenses"
    licenses.mkdir(exist_ok=True)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise SystemExit("Cannot locate Python's license; stopping distribution preparation.")
    shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    for license_path in (Path(sys.base_prefix) / "tcl").rglob("license.terms"):
        shutil.copy2(license_path, licenses / (license_path.parent.name + "-license.terms"))
    distribution = importlib.metadata.distribution("pyinstaller")
    copied = 0
    for item in distribution.files or ():
        if item.name.upper().startswith(("COPYING", "LICENSE")):
            source = Path(distribution.locate_file(item))
            if source.is_file():
                shutil.copy2(source, licenses / ("PyInstaller-" + item.name))
                copied += 1
    if not copied:
        raise SystemExit("Cannot locate PyInstaller's license; stopping distribution preparation.")
    for name in ("README.md", "LICENSE", "THIRD_PARTY.md", "Start-Bridge81.cmd", "Setup-Python.cmd", "Repair-RenPy.cmd"):
        shutil.copy2(ROOT / name, target / name)
    # Start in a desktop build must use the actual app, not look for source modules.
    (target / "Start-Bridge81.cmd").write_bytes(b'@echo off\r\nstart "" "%~dp0Bridge81.exe"\r\n')
    (target / "scripts").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "scripts/Setup-Python.ps1", target / "scripts/Setup-Python.ps1")
    for name in ("Repair-RenPy.ps1", "RuntimeRepair.ps1", "ucrt-manifest.json"):
        shutil.copy2(ROOT / "scripts" / name, target / "scripts" / name)
    shutil.copytree(ROOT / "docs", target / "docs", dirs_exist_ok=True)
    shutil.copytree(ROOT / "examples", target / "examples", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manifest = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            manifest.append("%s  %s" % (hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(target).as_posix()))
    (target / "SHA256SUMS").write_text("\n".join(manifest) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
