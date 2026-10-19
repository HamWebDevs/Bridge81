"""Open the separate Python-free Windows runtime repair utility on request."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .model import BridgeError
from .runner import child_environment, external_dll_search


def repair_script() -> Path:
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    script = root / "scripts" / "Repair-RenPy.ps1"
    if not script.is_file():
        raise BridgeError("Download the complete Bridge81 source or desktop ZIP to use Repair-RenPy.cmd.")
    return script


def open_runtime_repair() -> int:
    if os.name != "nt":
        raise BridgeError("The runtime repair utility runs on Windows. Use Repair-RenPy.cmd on the laptop.")
    script = repair_script()
    powershell = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    try:
        with external_dll_search():
            process = subprocess.Popen(
                [str(powershell), "-NoLogo", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                cwd=script.parent, env=child_environment({}), shell=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        return process.pid
    except OSError as exc:
        raise BridgeError("Windows could not open the runtime repair utility: %s" % exc) from exc
