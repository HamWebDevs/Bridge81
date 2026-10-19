"""Read-only host checks and official setup links."""

from __future__ import annotations

import os
import platform
import shutil
import struct
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .model import Finding

PYTHON_URL = "https://www.python.org/downloads/release/python-31210/"
CYGWIN_URL = "https://cygwin.com/install.html"
RENPY_URL = "https://www.renpy.org/doc/html/problems.html"


def default_python() -> str:
    """A frozen GUI executable is not a general-purpose Python interpreter."""
    if not getattr(sys, "frozen", False):
        return sys.executable
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    candidates = [local / "Bridge81" / "Python312" / "python.exe"]
    candidates += [local / "Programs" / "Python" / version / "python.exe" for version in ("Python312", "Python311", "Python310")]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("python.exe") or ""


def default_bash() -> str:
    if os.name != "nt":
        return shutil.which("bash") or ""
    for candidate in (Path("C:/cygwin64/bin/bash.exe"), Path("C:/tools/cygwin/bin/bash.exe")):
        if candidate.is_file():
            return str(candidate)
    return ""


def system_report() -> dict:
    findings = []
    windows = platform.system() == "Windows"
    if windows:
        version = sys.getwindowsversion()
        release = (version.major, version.minor)
        if release == (6, 3):
            findings.append(Finding("windows81", "info", "Windows 8.1 detected. Use the traditional Python 3.12 installer, not the Store or install manager."))
        elif release < (6, 3):
            findings.append(Finding("older-windows", "warning", "This Windows version is older than Bridge81's target; it is not supported."))
        else:
            findings.append(Finding("newer-windows", "info", "Modern Windows detected. Game reports still target Windows 8.1 unless changed to x86."))
    else:
        findings.append(Finding("other-os", "info", "Development host: %s. Windows game launch is disabled here." % platform.system()))
    if sys.version_info[:2] > (3, 12) and windows:
        findings.append(Finding("python-newer", "warning", "This interpreter is newer than the documented Bridge81 Windows 8.1 setup. Python 3.12 is the baseline."))
    if struct.calcsize("P") == 4 and not os.environ.get("PROCESSOR_ARCHITEW6432"):
        findings.append(Finding("32bit", "warning", "32-bit process detected. Current Cygwin needs a 64-bit Windows installation; a process's bitness alone cannot confirm OS bitness."))
    bash = default_bash()
    findings.append(Finding("bash", "info" if bash else "warning", "Bash found; execution requires an explicit Run action." if bash else "Cygwin Bash was not found in the default folders.", "Browse to an installed bash.exe or use the official Cygwin setup guide."))
    findings.append(Finding("linux-boundary", "info", "Cygwin runs Unix tools ported for Windows. It does not run Linux ELF binaries, kernel modules or WSL."))
    return {
        "schema_version": 1, "bridge81": __version__, "system": platform.system(),
        "release": platform.release(), "python": platform.python_version(),
        "process_bits": struct.calcsize("P") * 8,
        "bash_detected": bool(bash), "findings": [asdict(item) for item in findings],
        "official_links": {"python": PYTHON_URL, "cygwin": CYGWIN_URL, "renpy": RENPY_URL},
    }
