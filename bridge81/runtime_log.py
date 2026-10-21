"""Private, read-only hints from a saved Windows/Ren'Py runtime log."""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat

from .model import BridgeError

MAX_BYTES = 2 * 1024 * 1024
MAX_LINES = 30000
RULES = (
    ("loader-module-missing", r"\b(?:WinError\s*126|error\s*126)\b|DLL load failed[^\n]*specified module could not be found",
     "The log contains a missing-module loader error.",
     "Inspect DLL imports and check the complete game extraction. Error 126 can name a dependent DLL rather than the file being imported; it does not identify which runtime is missing."),
    ("loader-procedure-missing", r"\b(?:WinError\s*127|error\s*127)\b|specified procedure could not be found|procedure entry point[^\n]*could not be located",
     "The log contains a missing-procedure or entry-point error.",
     "Inspect the engine version and DLL imports. A dependency may need an unavailable API or have the wrong version; copying arbitrary DLLs is not a diagnosis."),
    ("loader-architecture", r"\bWinError\s*193\b|not a valid Win32 application|\b0xc000007b\b",
     "The log contains an invalid-image or architecture-related loader error.",
     "Use Bridge81 game/dependencies to compare PE architectures and restore a clean matching build. This error can also indicate a damaged binary."),
    ("ucrt-mentioned", r"\b(?:api-ms-win-crt-[a-z0-9-]+|ucrtbase)\.dll\b",
     "The log mentions a Universal C Runtime library.",
     "A filename mention is not proof the library is missing. Inspect imports and the full local error before choosing the existing reversible runtime repair."),
    ("visual-c-runtime-mentioned", r"\b(?:vcruntime\d+(?:_\d+)?|msvcp\d+(?:_\d+)?)\.dll\b",
     "The log mentions a Visual C++ runtime library.",
     "Check the bundled library architecture and the game's documented prerequisites. Do not replace the game's Python or engine DLLs."),
    ("python-module-missing", r"\bModuleNotFoundError\b|\bImportError:\s*No module named\b",
     "The log contains a Python module import failure.",
     "Check that the whole game archive was extracted and that the error belongs to this build. A game's embedded Python is separate from the system interpreter; installing system packages may not help."),
    ("graphics-context", r"(?:could not|cannot|failed to) (?:create|initiali[sz]e)[^\n]{0,100}(?:OpenGL|GL context|renderer)|(?:OpenGL|GL context|renderer)[^\n]{0,100}(?:initiali[sz]ation failed|not supported)",
     "The log contains a graphics-context or renderer initialization error.",
     "Inspect the GPU/driver and the game's own renderer options. A UCRT repair does not establish graphics compatibility."),
)
INTERPRETATION = "Pattern matches are hints from a saved log, not a root-cause diagnosis or Windows 8.1 compatibility test. Logs may belong to an older build. No game, DLL, script or repair was executed."


def analyse(text):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BYTES:
        raise BridgeError("Runtime log exceeds the 2 MiB text limit.")
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        raise BridgeError("Runtime log exceeds 30,000 lines.")
    findings = []
    for code, pattern, message, action in RULES:
        compiled = re.compile(pattern, re.I)
        locations = [line for line, value in enumerate(lines, 1) if compiled.search(value)]
        if locations:
            findings.append({"code": code, "level": "warning", "message": message, "action": action,
                             "occurrences": len(locations), "first_line": locations[0], "last_line": locations[-1]})
    return {"schema_version": 1, "tool": "bridge81-runtime-log", "status": "hints-found" if findings else "no-recognised-pattern",
            "lines": len(lines), "findings": findings, "privacy": {"raw_lines": "withheld", "paths": "withheld"}, "interpretation": INTERPRETATION}


def load(value):
    path = Path(value).expanduser().absolute()
    if path.is_symlink() or path.resolve() != path or any(parent.is_symlink() for parent in path.parents):
        raise BridgeError("Runtime log cannot use symlinks or redirected directories.")
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            raise BridgeError("Choose a regular runtime log of at most 2 MiB.")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise BridgeError("Runtime log must be a regular file.")
            data = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        current = path.stat()
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        version = lambda s: (*identity(s), s.st_ctime_ns)
        # Windows stat(path) and fstat(fd) can disagree on ctime's meaning.
        # Preserve ctime mutation checks within each API instead.
        if path.is_symlink() or version(before) != version(current) or version(opened) != version(after) or identity(before) != identity(opened) or len(data) != before.st_size:
            raise BridgeError("Runtime log changed during inspection; use a stable saved log.")
        if len(data) > MAX_BYTES:
            raise BridgeError("Runtime log exceeds 2 MiB.")
        text = data.decode("utf-8-sig")
    except UnicodeError:
        raise BridgeError("Runtime log must be UTF-8 text; input content withheld.") from None
    except OSError:
        raise BridgeError("Cannot read the selected runtime log; path and content withheld.") from None
    return analyse(text)


def report_markdown(report):
    lines = ["# Bridge81 saved runtime-log hints", "", report["status"], "", report["interpretation"], ""]
    for item in report["findings"]:
        lines += [f"## {item['code']}", "", item["message"],
                  f"{item['occurrences']} matching line(s); first {item['first_line']}, last {item['last_line']}.", "", item["action"], ""]
    lines.append("Raw log lines and paths are withheld.")
    return "\n".join(lines)
