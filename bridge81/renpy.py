"""Conservative game inspection: read engine metadata, never import a game."""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .model import BridgeError, Finding, Plan
from .pe import PEInfo, inspect_pe
from .plans import checked_args

MAX_METADATA = 256 * 1024
MAX_DIRECTORY_ENTRIES = 1024
TUPLE_VERSION = re.compile(r"(?m)^version_tuple\s*=\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*[,)]")
TEXT_VERSION = re.compile(r"(?m)^\s*Ren'Py\s+(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?:[.\s]|$)")
PROFILES = {
    "default": {},
    "low-memory": {"RENPY_LESS_MEMORY": "1", "RENPY_LESS_UPDATES": "1", "RENPY_DISABLE_FULLSCREEN": "1"},
    "windowed": {"RENPY_DISABLE_FULLSCREEN": "1"},
    "no-audio": {"RENPY_DISABLE_SOUND": "1"},
    "no-joystick": {"RENPY_DISABLE_JOYSTICK": "1"},
}


@dataclass(frozen=True)
class GameReport:
    game: str
    target: str
    status: str
    engine_version: tuple[int, int, int] | None
    evidence: tuple[str, ...]
    executables: tuple[str, ...]
    executable: str | None
    pe: PEInfo | None
    findings: tuple[Finding, ...]

    def as_dict(self) -> dict:
        return {"schema_version": 1, **asdict(self)}


def _root(value: str | Path) -> Path:
    if not str(value).strip():
        raise BridgeError("Choose the extracted game's folder first.")
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise BridgeError("Choose the extracted game's folder, not a ZIP archive or executable.")
    return root


def _inside(root: Path, relative: str) -> Path:
    result = (root / relative).resolve()
    try:
        result.relative_to(root)
    except ValueError as exc:
        raise BridgeError("Game metadata or executable points outside the game folder.") from exc
    return result


def inspect_game(folder: str | Path, *, exe: str | None = None, target: str = "x64") -> GameReport:
    if target not in ("x86", "x64"):
        raise BridgeError("Target must be x86 or x64 Windows 8.1.")
    root = _root(folder)
    findings: list[Finding] = []
    versions: list[tuple[tuple[int, int, int], str]] = []
    for relative in ("renpy/__init__.py", "renpy/vc_version.py", "log.txt", "traceback.txt"):
        try:
            path = _inside(root, relative)
            if not path.is_file():
                continue
            with path.open("rb") as stream:
                data = stream.read(MAX_METADATA + 1)
            if len(data) > MAX_METADATA:
                findings.append(Finding("metadata-limit", "warning", "%s: inspected only the first 256 KiB." % relative))
            text = data[:MAX_METADATA].decode("utf-8-sig", errors="replace")
            pattern = TUPLE_VERSION if relative.endswith(".py") else TEXT_VERSION
            for match in list(pattern.finditer(text))[:8]:
                versions.append((tuple(int(part) for part in match.groups()), relative))
        except (OSError, BridgeError) as exc:
            findings.append(Finding("metadata-unreadable", "warning", "%s: metadata could not be read safely." % relative, str(exc) if isinstance(exc, BridgeError) else "Check file permissions."))
    distinct = {version for version, _ in versions}
    version = next(iter(distinct)) if len(distinct) == 1 else None
    evidence = tuple(sorted({"%s: %s" % (name, ".".join(map(str, ver))) for ver, name in versions}))
    if len(distinct) > 1:
        findings.append(Finding("conflicting-version", "warning", "Engine metadata and logs disagree; the engine version is unknown.", "Delete nothing. Check whether a log belongs to an older game build."))
        if any(candidate >= (8, 4, 0) for candidate in distinct):
            findings.append(Finding("modern-version-evidence", "blocked", "Conflicting metadata includes Ren'Py 8.4 or newer, which requires Windows 10.", "Ask the developer to confirm the bundled engine before attempting a Windows 8.1 launch."))
    elif version is None:
        findings.append(Finding("unknown-engine", "warning", "No unambiguous Ren'Py engine version was found.", "Start the game normally if possible, then inspect its newly generated log.txt."))
    elif version >= (8, 4, 0):
        findings.append(Finding("renpy-requires-win10", "blocked", "Ren'Py %s requires Windows 10 or later." % ".".join(map(str, version)), "Ask the developer for an older compatible build, or use a supported OS. Graphics profiles cannot fix this."))
    elif version < (6, 0, 0):
        findings.append(Finding("unrecognized-version", "warning", "This engine is outside Bridge81's documented Ren'Py range."))
    else:
        findings.append(Finding("older-engine", "info", "This engine predates Ren'Py 8.4's Windows 10 requirement.", "Compatibility is still unverified: the game's dependencies, GPU and drivers also matter."))

    names = []
    try:
        with os.scandir(root) as entries:
            for index, entry in enumerate(entries):
                if index >= MAX_DIRECTORY_ENTRIES:
                    findings.append(Finding("directory-limit", "warning", "Game folder has too many entries; choose the executable explicitly."))
                    break
                if entry.name.lower().endswith(".exe") and entry.is_file(follow_symlinks=False):
                    names.append(entry.name)
    except OSError as exc:
        raise BridgeError("Cannot list game folder: %s" % exc.strerror) from exc
    names.sort(key=str.casefold)
    selected = exe if exe else names[0] if len(names) == 1 else None
    binary = None
    if selected:
        path = _inside(root, selected)
        if path.suffix.lower() != ".exe":
            raise BridgeError("Choose a Windows .exe file inside the game folder.")
        selected = path.relative_to(root).as_posix()
        try:
            binary = inspect_pe(path)
        except BridgeError as exc:
            findings.append(Finding("invalid-executable", "blocked", str(exc)))
        if binary:
            if binary.architecture not in (("x86", "x64") if target == "x64" else ("x86",)):
                findings.append(Finding("architecture", "blocked", "%s cannot run on Windows 8.1 %s." % (binary.architecture, target), "Get a build for your OS architecture."))
            if binary.subsystem_version > (6, 3):
                findings.append(Finding("subsystem-version", "blocked", "The PE subsystem header declares Windows %d.%d, newer than Windows 8.1 (6.3)." % binary.subsystem_version))
    else:
        findings.append(Finding("select-executable", "warning", "Choose a game executable explicitly." if names else "No Windows executable was found in the game folder."))

    status = "blocked" if any(f.level == "blocked" for f in findings) else "unverified"
    return GameReport(root.name, "windows8.1-" + target, status, version, evidence, tuple(names), selected, binary, tuple(findings))


def game_plan(folder: str | Path, *, exe: str | None = None, profile: str = "default", target: str = "x64", allow_unknown: bool = False, args: tuple[str, ...] = ()) -> Plan:
    if profile not in PROFILES:
        raise BridgeError("Unknown game profile: %s" % profile)
    root = _root(folder)
    report = inspect_game(root, exe=exe, target=target)
    if report.status == "blocked":
        raise BridgeError("Launch blocked: " + " ".join(f.message for f in report.findings if f.level == "blocked"))
    if report.engine_version is None and not allow_unknown:
        raise BridgeError("The engine version is unknown. Inspect the evidence first; use --allow-unknown only for a game you trust.")
    if report.executable is None or report.pe is None:
        raise BridgeError("Select a valid Windows game executable before creating a launch plan.")
    return Plan("renpy", (str(_inside(root, report.executable)), *checked_args(args)), str(root), dict(PROFILES[profile]), (
        "Compatibility remains unverified until tested on your machine.",
        "Profile settings apply only to this launch. Bridge81 does not patch the game; the game may write saves or logs.",
        "For a black screen, hold Shift while starting or press Shift+G and try the game's GL or ANGLE renderer.",
    ))


def report_markdown(report: GameReport) -> str:
    def safe(text: str) -> str:
        return text.replace("\\", "\\\\").replace("`", "'").replace("<", "&lt;").replace(">", "&gt;").replace("\r", " ").replace("\n", " ")
    lines = ["# Bridge81 game report", "", "Game: `%s`" % safe(report.game), "Target: `%s`" % report.target,
             "Status: **%s**" % report.status, "Engine: %s" % (".".join(map(str, report.engine_version)) if report.engine_version else "unknown"), ""]
    for finding in report.findings:
        lines.append("- **%s** %s%s" % (finding.level, safe(finding.message), " " + safe(finding.action) if finding.action else ""))
    lines += ["", "Header inspection is not a complete dependency or GPU compatibility test.", "No game code was executed. Absolute paths and log contents are omitted.", ""]
    return "\n".join(lines)
