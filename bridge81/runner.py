"""Cancelable non-interactive script execution with bounded captured output."""

from __future__ import annotations

import math
import os
import signal
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from .model import BridgeError, Plan

MAX_OUTPUT = 1024 * 1024
DLL_LOCK = threading.Lock()


@dataclass(frozen=True)
class RunResult:
    returncode: int
    output: str
    elapsed_seconds: float
    reason: str
    output_truncated: bool

    def as_dict(self) -> dict:
        return asdict(self)


def child_environment(changes: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    # Do not inject the app's Python environment into a game or another interpreter.
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONINSPECT"):
        env.pop(name, None)
    if getattr(sys, "frozen", False) and "LD_LIBRARY_PATH" in env:
        original = env.get("LD_LIBRARY_PATH_ORIG")
        if original is None:
            env.pop("LD_LIBRARY_PATH", None)
        else:
            env["LD_LIBRARY_PATH"] = original
    if getattr(sys, "frozen", False):
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    env.update(changes)
    return env


@contextmanager
def external_dll_search():
    """A frozen workbench must not force its DLL folder on an external tool."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        yield
        return
    import ctypes
    with DLL_LOCK:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
        kernel.SetDllDirectoryW(None)
        try:
            yield
        finally:
            kernel.SetDllDirectoryW(str(sys._MEIPASS))


def _stop(process: subprocess.Popen, job=None) -> None:
    if job is not None:
        job.terminate()
        return
    if os.name == "nt":
        # Built into Windows 8.1; argv is numeric and never passed through cmd.exe.
        system = Path(os.environ.get("SystemRoot", "C:/Windows"))
        try:
            subprocess.run([str(system / "System32" / "taskkill.exe"), "/PID", str(process.pid), "/T", "/F"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass


def run(plan: Plan, *, timeout: float = 120, cancel: threading.Event | None = None, max_output: int = MAX_OUTPUT) -> RunResult:
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise BridgeError("Timeout must be a finite number between 0 and 86400 seconds.")
    if not isinstance(max_output, int) or isinstance(max_output, bool) or not 1 <= max_output <= MAX_OUTPUT:
        raise BridgeError("Output limit must be between 1 byte and 1 MiB.")
    cancel = cancel or threading.Event()
    if cancel.is_set():
        return RunResult(-1, "", 0, "cancelled", False)
    if not plan.argv or not Path(plan.argv[0]).is_absolute() or not Path(plan.cwd).is_dir():
        raise BridgeError("Execution requires an absolute interpreter path and an existing working directory.")
    started = time.monotonic()
    job = None
    process = None
    if os.name == "nt":
        from .winjob import CREATE_SUSPENDED, WindowsJob
        job = WindowsJob()
        options = {"creationflags": subprocess.CREATE_NO_WINDOW | CREATE_SUSPENDED}
    else:
        options = {"start_new_session": True}
    try:
        with external_dll_search():
            process = subprocess.Popen(plan.argv, cwd=plan.cwd, env=child_environment(plan.env),
                                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       shell=False, **options)
        if job is not None:
            job.attach_and_resume(process.pid)
    except (OSError, BridgeError) as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=7)
        if job is not None:
            job.close()
        raise BridgeError("Could not start the process: %s" % exc) from exc
    captured = bytearray()
    overflow = threading.Event()
    finished = threading.Event()
    output_lock = threading.Lock()

    def read_output() -> None:
        try:
            assert process.stdout is not None
            while True:
                chunk = process.stdout.read1(8192)
                if not chunk:
                    break
                with output_lock:
                    remaining = max_output - len(captured)
                    captured.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        overflow.set()
        finally:
            finished.set()

    reader = threading.Thread(target=read_output, daemon=True, name="bridge81-output")
    reader.start()
    reason = "completed"
    try:
        while True:
            if cancel.is_set():
                reason = "cancelled"
            elif overflow.is_set():
                reason = "output-limit"
            elif time.monotonic() - started >= timeout:
                reason = "timeout"
            elif process.poll() is not None and finished.is_set():
                break
            else:
                time.sleep(0.02)
                continue
            _stop(process, job)
            break
        process.wait(timeout=7)
    except BaseException:
        _stop(process, job)
        process.wait(timeout=7)
        raise
    finally:
        if job is not None:
            job.close()
        reader.join(timeout=1)
        if finished.is_set() and process.stdout is not None:
            process.stdout.close()
    # A quickly exiting process can exceed the cap before the monitor sees it.
    if reason == "completed" and overflow.is_set():
        reason = "output-limit"
    with output_lock:
        output = bytes(captured).decode("utf-8", errors="replace")
    return RunResult(process.returncode, output, round(time.monotonic() - started, 3), reason, overflow.is_set())


def launch_game(plan: Plan) -> int:
    """Detached games keep running when the workbench closes."""
    if plan.kind != "renpy" or os.name != "nt":
        raise BridgeError("Game launch is available only on Windows.")
    try:
        with external_dll_search():
            process = subprocess.Popen(plan.argv, cwd=plan.cwd, env=child_environment(plan.env), shell=False,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        return process.pid
    except OSError as exc:
        raise BridgeError("Windows could not start the game: %s" % exc) from exc
