"""Construct argv arrays. User arguments are never interpolated into shell code."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .doctor import default_bash, default_python
from .model import BridgeError, Plan
from .pe import inspect_pe

# Only the constant program below is shell code. All paths/arguments are positional.
CYGWIN_SCRIPT = '''export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"
work=$(cygpath -u -- "$1") || exit
script=$(cygpath -u -- "$2") || exit
shift 2
cd -- "$work" || exit
exec /bin/bash --noprofile --norc -- "$script" "$@"'''


def existing_file(value: str | Path, suffix: str | None = None) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise BridgeError("File does not exist: %s" % path)
    if suffix and path.suffix.lower() != suffix:
        raise BridgeError("Choose a %s file." % suffix)
    return path


def working_directory(value: str | Path | None, default: Path) -> Path:
    path = Path(value).expanduser().resolve() if value else default
    if not path.is_dir():
        raise BridgeError("Working directory does not exist: %s" % path)
    return path


def executable(value: str | Path, purpose: str) -> Path:
    if not value:
        raise BridgeError("Choose an installed %s executable first." % purpose)
    # Keep a venv's executable path: resolving its symlink starts the base Python.
    path = Path(os.path.abspath(os.path.expanduser(str(value))))
    if not path.is_file():
        raise BridgeError("Interpreter does not exist: %s" % path)
    if purpose == "Python" and getattr(sys, "frozen", False) and path.resolve() == Path(sys.executable).resolve():
        raise BridgeError("The packaged app is not a Python interpreter; choose python.exe.")
    if os.name == "nt":
        if path.suffix.lower() != ".exe":
            raise BridgeError("Choose a native .exe; batch wrappers are not accepted as interpreters.")
        inspect_pe(path)
    elif not os.access(path, os.X_OK):
        raise BridgeError("Interpreter is not executable: %s" % path)
    return path


def checked_args(args: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if len(args) > 256 or any(not isinstance(a, str) or "\0" in a for a in args):
        raise BridgeError("Arguments must be NUL-free strings (at most 256).")
    if sum(len(a) + 3 for a in args) > 24000:
        raise BridgeError("Arguments exceed Bridge81's portable command-line limit.")
    return tuple(args)


def python_plan(script: str | Path, args: list[str] | tuple[str, ...] = (), *, python: str = "", cwd: str = "") -> Plan:
    source = existing_file(script, ".py")
    interpreter = executable(python or default_python(), "Python")
    work = working_directory(cwd, source.parent)
    return Plan("python", (str(interpreter), "-u", "-X", "utf8", str(source), *checked_args(args)), str(work),
                {"PYTHONIOENCODING": "utf-8"}, ("This runs the chosen script with your normal user permissions; it is not a sandbox.",))


def bash_plan(script: str | Path, args: list[str] | tuple[str, ...] = (), *, bash: str = "", cwd: str = "") -> Plan:
    source = existing_file(script, ".sh")
    interpreter = executable(bash or default_bash(), "Cygwin Bash")
    work = working_directory(cwd, source.parent)
    parameters = checked_args(args)
    if os.name == "nt":
        # Enforce the Cygwin adapter rather than silently treating Git Bash as equivalent.
        if not (interpreter.parent / "cygwin1.dll").is_file() or not (interpreter.parent / "cygpath.exe").is_file():
            raise BridgeError("This adapter needs Cygwin Bash with cygwin1.dll and cygpath.exe in the same bin folder.")
        argv = (str(interpreter), "--noprofile", "--norc", "-c", CYGWIN_SCRIPT, "bridge81", str(work), str(source), *parameters)
    else:
        argv = (str(interpreter), "--noprofile", "--norc", "--", str(source), *parameters)
    return Plan("bash", argv, str(work), notes=("Non-interactive Bash; stdin is closed. For prompts or a full terminal, use Cygwin Terminal.", "Use LF line endings and Cygwin packages, not Linux ELF binaries."))


def venv_plan(destination: str | Path, *, python: str = "") -> Plan:
    target = Path(destination).expanduser().resolve()
    if target.exists():
        raise BridgeError("Choose a new virtual environment folder; an existing folder will not be reused.")
    if not target.parent.is_dir():
        raise BridgeError("The virtual environment's parent folder must already exist.")
    interpreter = executable(python or default_python(), "Python")
    if getattr(sys, "frozen", False) and interpreter == Path(sys.executable).resolve():
        raise BridgeError("The packaged app is not a Python interpreter; choose python.exe.")
    return Plan("venv", (str(interpreter), "-m", "venv", str(target)), str(target.parent), notes=("Creates a local virtual environment with bundled pip. No packages are downloaded.",))
