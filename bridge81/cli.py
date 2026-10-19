"""The CLI exposes the same plans, reports and runner as the desktop app."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .doctor import system_report
from .model import BridgeError
from .plans import bash_plan, python_plan, venv_plan
from .renpy import PROFILES, game_plan, inspect_game, report_markdown
from .runner import launch_game, run


def arguments(value: str) -> tuple[str, ...]:
    try:
        decoded = json.loads(value)
    except (ValueError, RecursionError) as exc:
        raise BridgeError("Arguments must be a JSON array of strings, for example [\"hello\", \"two words\"].") from exc
    if not isinstance(decoded, list) or any(not isinstance(item, str) for item in decoded):
        raise BridgeError("Arguments must be a JSON array of strings.")
    return tuple(decoded)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="bridge81", description="Python, Cygwin and older Ren'Py workflows for Windows 8.1.")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command")
    commands.add_parser("gui", help="Open the native desktop app (default).")
    commands.add_parser("doctor", help="Read-only host report; does not run detected interpreters.")
    inspect = commands.add_parser("game", help="Inspect an extracted game without executing code.")
    inspect.add_argument("folder")
    inspect.add_argument("--exe", help="Executable path relative to the game folder.")
    inspect.add_argument("--target", choices=("x86", "x64"), default="x64")
    inspect.add_argument("--format", choices=("json", "markdown"), default="json")
    dependencies = commands.add_parser("dependencies", help="Read direct/delay DLL imports without loading the game or its libraries.")
    dependencies.add_argument("folder")
    dependencies.add_argument("--exe", help="Executable relative to the extracted game folder.")
    dependencies.add_argument("--target", choices=("x86", "x64"), default="x64")
    dependencies.add_argument("--format", choices=("json", "markdown"), default="json")
    for mode in ("plan", "run"):
        command = commands.add_parser(mode, help="Preview a command." if mode == "plan" else "Execute a selected script, create a venv, or launch a game.")
        command.add_argument("kind", choices=("python", "bash", "venv", "renpy"))
        command.add_argument("path", help="Script, new venv folder, or extracted game folder.")
        command.add_argument("--python", default="", help="Explicit python.exe / interpreter path.")
        command.add_argument("--bash", default="", help="Explicit Cygwin bash.exe path.")
        command.add_argument("--cwd", default="", help="Working directory for Python or Bash scripts.")
        command.add_argument("--args-json", default="[]", help="Arguments as a JSON array of strings.")
        command.add_argument("--exe", help="Ren'Py executable relative to the game folder.")
        command.add_argument("--profile", choices=tuple(PROFILES), default="default")
        command.add_argument("--target", choices=("x86", "x64"), default="x64")
        command.add_argument("--allow-unknown", action="store_true", help="Allow a trusted game's unknown engine version; known blockers still apply.")
        if mode == "run":
            command.add_argument("--timeout", type=float, default=120, help="Script/venv timeout in seconds; games are detached.")
    return root


def main(argv: list[str] | None = None) -> int:
    options = parser().parse_args(argv)
    try:
        if options.command in (None, "gui"):
            from .gui import main as gui_main
            return gui_main()
        if options.command == "doctor":
            print(json.dumps(system_report(), indent=2))
            return 0
        if options.command == "game":
            report = inspect_game(options.folder, exe=options.exe, target=options.target)
            print(report_markdown(report) if options.format == "markdown" else json.dumps(report.as_dict(), indent=2))
            return 2 if report.status == "blocked" else 0
        if options.command == "dependencies":
            from .dependencies import inspect_dependencies, report_markdown
            report = inspect_dependencies(options.folder, exe=options.exe, target=options.target)
            print(report_markdown(report) if options.format == "markdown" else json.dumps(report, indent=2))
            return 1 if report['summary']['unreadable_modules'] else 0
        args = arguments(options.args_json)
        if options.kind == "python":
            plan = python_plan(options.path, args, python=options.python, cwd=options.cwd)
        elif options.kind == "bash":
            plan = bash_plan(options.path, args, bash=options.bash, cwd=options.cwd)
        elif options.kind == "venv":
            if args or options.cwd:
                raise BridgeError("A venv plan does not accept script arguments or a working directory.")
            plan = venv_plan(options.path, python=options.python)
        else:
            if options.cwd:
                raise BridgeError("A game's working directory is its extracted root folder.")
            plan = game_plan(options.path, exe=options.exe, profile=options.profile, target=options.target,
                             allow_unknown=options.allow_unknown, args=args)
        if options.command == "plan":
            print(json.dumps(plan.as_dict(), indent=2))
            return 0
        if plan.kind == "renpy":
            print(json.dumps({"pid": launch_game(plan), "notes": plan.notes}, indent=2))
            return 0
        result = run(plan, timeout=options.timeout)
        sys.stdout.write(result.output)
        print("\n[Bridge81: %s, exit %d, %.3fs]" % (result.reason, result.returncode, result.elapsed_seconds), file=sys.stderr)
        return 0 if result.reason == "completed" and result.returncode == 0 else 1
    except (BridgeError, OSError) as exc:
        print("Bridge81: %s" % exc, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Bridge81: interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
