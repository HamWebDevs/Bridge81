"""Build the small Python-free repair ZIP without redistributing Microsoft DLLs."""

from __future__ import annotations

import zipfile
from pathlib import Path


def package_runtime_repair(root: Path, version: str) -> Path:
    output = root / "dist"
    output.mkdir(exist_ok=True)
    target = output / ("Bridge81-%s-runtime-repair.zip" % version)
    files = {
        "Repair-RenPy.cmd": "Repair-RenPy.cmd",
        "scripts/Repair-RenPy.ps1": "scripts/Repair-RenPy.ps1",
        "scripts/RuntimeRepair.ps1": "scripts/RuntimeRepair.ps1",
        "scripts/ucrt-manifest.json": "scripts/ucrt-manifest.json",
        "docs/runtime-repair.md": "docs/runtime-repair.md",
        "docs/runtime-repair-quickstart.txt": "READ-ME.txt",
        "LICENSE": "LICENSE",
        "THIRD_PARTY.md": "THIRD_PARTY.md",
    }
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in sorted(files.items()):
            data = (root / source).read_bytes()
            if name.endswith((".cmd", ".ps1", ".txt")):
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            info = zipfile.ZipInfo("Bridge81-Runtime-Repair/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return target
