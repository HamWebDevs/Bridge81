"""Native Tk desktop UI. No browser, web server, account or background service."""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import webbrowser
from pathlib import Path

from . import __version__
from .cli import arguments
from .doctor import CYGWIN_URL, PYTHON_URL, RENPY_URL, default_bash, default_python, system_report
from .model import BridgeError, Plan
from .plans import bash_plan, python_plan, venv_plan
from .renpy import PROFILES, game_plan, inspect_game, report_markdown
from .runner import launch_game, run

GUIDE = """GET STARTED ON WINDOWS 8.1

1. Extract the whole Bridge81 ZIP to a short path, such as C:\\Tools\\Bridge81.
2. Double-click Start-Bridge81.cmd. If Python is missing, run Setup-Python.cmd.
   Setup uses Python.org's traditional Python 3.12.10 x64 installer, checks
   a pinned SHA-256 and its Authenticode signature, then installs for your user.
   Python 3.12.10 is the last full 3.12 maintenance installer, not the latest
   security source release. You can choose another trusted compatible Python.
3. In Scripts, pick a .py file. Arguments are a JSON array, e.g. ["hello world"].
   Preview shows exactly what will run. Run uses your normal user permissions.
   Output appears when the command finishes; Cancel stops a running script.
4. Use Create venv to make a new project environment, then choose that folder's
   Scripts\\python.exe as the interpreter for the project. Existing folders
   are never overwritten by the venv action.

UNIX TOOLS WITHOUT WSL

Install Cygwin x64 from its official site. For a per-user install, start the
official setup-x86_64.exe with --no-admin. Start with bash, coreutils, grep,
sed, gawk and findutils; add make, gcc-core or openssh when you need them.
Select your installed Cygwin bin\\bash.exe in Scripts and choose Bash mode.
Bridge81 translates paths using Cygwin's cygpath and keeps arguments separate
from its fixed shell wrapper. Save .sh scripts with LF line endings.

Cygwin runs Unix programs built for Cygwin. Linux ELF binaries, apt, systemd,
kernel modules and Linux GUI games do not become native Windows applications.
Scripts run non-interactively. Use Cygwin Terminal when a program needs input.
Current Cygwin requires a 64-bit OS. This app also accepts Python's 32-bit
traditional installer manually on 32-bit Windows; the supplied setup is x64.

OLDER REN'PY GAMES

Extract a trusted game's complete Windows build. In Games, choose its folder
and .exe, then Inspect. Bridge81 reads small metadata files and PE headers;
it does not execute game Python, unpack archives, replace DLLs or touch saves.
Reports intentionally say UNVERIFIED when no known blocker is found.

Ren'Py 8.4+ needs Windows 10 and is blocked for this Windows 8.1 target.
An older engine may work, but graphics drivers and game dependencies matter.
Low-memory trades speed/updates for lower memory use; windowed, no-audio and
no-joystick profiles can help isolate a specific problem. They apply only
to the child game. A game can still write its normal logs and save files.

For black screens: hold Shift while launching, or press Shift+G in game,
then use its Graphics Acceleration menu to try GL or ANGLE. Classic renderers
may not work with model-based games. There is no universal software-renderer
fallback. Replacing a bundled engine can break compiled scripts and saves.

TESTING STATUS

This is a 0.1 preview targeting Windows 8.1. The core has automated tests;
modern Windows CI is not a test on Windows 8.1 or on your GPU. See docs/testing.md
for the real-device checklist. No telemetry or automatic game downloads.
"""


class App:
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk, self.root = tk, ttk, root
        self.events: queue.Queue = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.closing = False
        self.last_report = None
        root.title("Bridge81 — Python · Unix tools · Older games")
        root.geometry("1000x660")
        root.minsize(780, 570)
        root.configure(bg="#101b2b")
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#101b2b")
        style.configure("TLabel", background="#101b2b", foreground="#e6edf5", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 25, "bold"), foreground="#70e2ca")
        style.configure("Sub.TLabel", foreground="#a5b8cf")
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
        style.configure("TNotebook", background="#101b2b", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(18, 10))
        style.configure("TCheckbutton", background="#101b2b", foreground="#e6edf5")
        heading = ttk.Frame(root, padding=(24, 18, 24, 12))
        heading.pack(fill="x")
        ttk.Label(heading, text="Bridge81", style="Title.TLabel").pack(side="left")
        ttk.Label(heading, text="A little more life for your Windows laptop.   /   " + __version__, style="Sub.TLabel").pack(side="left", padx=22)
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=20)
        overview = ttk.Frame(self.tabs, padding=18)
        self.script_tab = ttk.Frame(self.tabs, padding=18)
        self.game_tab = ttk.Frame(self.tabs, padding=18)
        help_tab = ttk.Frame(self.tabs, padding=18)
        for widget, name in ((overview, "Overview"), (self.script_tab, "Scripts"), (self.game_tab, "Games"), (help_tab, "Setup & help")):
            self.tabs.add(widget, text=name)
        self.status = tk.StringVar(value="Ready. Checks are read-only; scripts run only when you choose Run.")
        ttk.Label(root, textvariable=self.status, style="Sub.TLabel", padding=(24, 12)).pack(fill="x")
        self.make_overview(overview)
        self.make_scripts(self.script_tab)
        self.make_games(self.game_tab)
        text = self.text_box(help_tab)
        self.set_text(text, GUIDE)
        root.after(80, self.poll)

    def text_box(self, parent, *, height=10):
        frame = self.ttk.Frame(parent)
        frame.pack(fill="both", expand=True, pady=(12, 0))
        text = self.tk.Text(frame, wrap="word", bg="#091321", fg="#d9e8f5", insertbackground="#70e2ca",
                            relief="flat", padx=14, pady=12, font=("Consolas", 10), height=height)
        scroll = self.ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.configure(state="disabled")
        return text

    @staticmethod
    def set_text(widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value.replace("\0", "\\0"))
        widget.configure(state="disabled")

    def make_overview(self, parent):
        self.ttk.Label(parent, text="Your workbench, without the weight.", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        self.ttk.Label(parent, text="Run Python projects · Use Cygwin Bash · Check older Ren'Py games", style="Sub.TLabel").pack(anchor="w", pady=(8, 14))
        row = self.ttk.Frame(parent)
        row.pack(fill="x")
        self.ttk.Button(row, text="Python setup page", command=lambda: webbrowser.open(PYTHON_URL)).pack(side="left", padx=(0, 8))
        self.ttk.Button(row, text="Cygwin setup page", command=lambda: webbrowser.open(CYGWIN_URL)).pack(side="left", padx=(0, 8))
        self.ttk.Button(row, text="Refresh checks", command=self.refresh_doctor).pack(side="left")
        self.doctor_text = self.text_box(parent)
        self.refresh_doctor()

    def refresh_doctor(self):
        report = system_report()
        text = "HOST CHECK\n\n%s %s  |  Python %s  |  %s-bit process\n\n" % (report["system"], report["release"], report["python"], report["process_bits"])
        for item in report["findings"]:
            text += "%s\n%s\n\n" % (item["message"], item["action"])
        text += "Game support is assessed separately. A clean header check does not prove a game will run.\n\nStart with Setup & help if this is your first visit."
        self.set_text(self.doctor_text, text)

    def field(self, parent, label, variable, browse=None):
        row = self.ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        self.ttk.Label(row, text=label, width=16).pack(side="left")
        self.ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
        if browse:
            self.ttk.Button(row, text="Browse", command=browse).pack(side="left", padx=(8, 0))

    def make_scripts(self, parent):
        tk, ttk = self.tk, self.ttk
        self.kind = tk.StringVar(value="Python")
        self.script = tk.StringVar()
        self.interpreter = tk.StringVar(value=default_python())
        self.cwd = tk.StringVar()
        self.script_args = tk.StringVar(value="[]")
        self.timeout = tk.StringVar(value="120")
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="SCRIPT RUNNER", font=("Segoe UI", 14, "bold")).pack(side="left")
        box = ttk.Combobox(row, textvariable=self.kind, values=("Python", "Bash (Cygwin)"), state="readonly", width=18)
        box.pack(side="right")
        box.bind("<<ComboboxSelected>>", lambda event: self.interpreter.set(default_python() if self.kind.get() == "Python" else default_bash()))
        self.field(parent, "Script", self.script, self.choose_script)
        self.field(parent, "Interpreter", self.interpreter, lambda: self.choose_file(self.interpreter, "Choose the interpreter executable"))
        self.field(parent, "Working folder", self.cwd, lambda: self.choose_directory(self.cwd))
        self.field(parent, "Arguments (JSON)", self.script_args)
        self.field(parent, "Timeout (seconds)", self.timeout)
        ttk.Label(parent, text='Arguments example: ["two words", "--verbose"]  ·  Working folder defaults to the script folder.', style="Sub.TLabel").pack(anchor="w", pady=6)
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=6)
        ttk.Button(row, text="Preview command", command=self.preview_script).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Run script", command=self.run_script).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Cancel", command=self.cancel_run).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Create venv", command=self.create_venv).pack(side="left")
        self.script_output = self.text_box(parent)
        self.set_text(self.script_output, "Choose a trusted script, then Preview or Run.\n\nScripts have your user permissions. This runner is not a sandbox.\nInput is closed; output is shown when the script finishes (up to 1 MiB).")

    def choose_script(self):
        from tkinter import filedialog
        suffix = ".py" if self.kind.get() == "Python" else ".sh"
        value = filedialog.askopenfilename(parent=self.root, title="Choose a trusted script", filetypes=((suffix + " scripts", "*" + suffix), ("All files", "*")))
        if value:
            self.script.set(value)

    def choose_file(self, variable, title):
        from tkinter import filedialog
        value = filedialog.askopenfilename(parent=self.root, title=title)
        if value:
            variable.set(value)

    def choose_directory(self, variable):
        from tkinter import filedialog
        value = filedialog.askdirectory(parent=self.root, title="Choose a folder")
        if value:
            variable.set(value)

    def script_plan(self):
        args = arguments(self.script_args.get())
        if self.kind.get() == "Python":
            return python_plan(self.script.get(), args, python=self.interpreter.get(), cwd=self.cwd.get())
        return bash_plan(self.script.get(), args, bash=self.interpreter.get(), cwd=self.cwd.get())

    def fail(self, error):
        from tkinter import messagebox
        self.status.set(str(error))
        messagebox.showerror("Bridge81", str(error), parent=self.root)

    def preview_script(self):
        try:
            self.set_text(self.script_output, json.dumps(self.script_plan().as_dict(), indent=2))
        except (BridgeError, OSError) as exc:
            self.fail(exc)

    def run_script(self):
        try:
            self.start_run(self.script_plan(), float(self.timeout.get()))
        except (ValueError, OSError) as exc:
            self.fail(exc)

    def start_run(self, plan: Plan, timeout: float):
        if self.busy:
            raise BridgeError("A script is already running. Cancel it or wait for it to finish.")
        self.cancel.clear()
        self.busy = True
        self.status.set("Running %s. Output will appear when it finishes; Cancel is available." % plan.kind)
        self.set_text(self.script_output, json.dumps(plan.as_dict(), indent=2) + "\n\nRunning…")

        def worker():
            try:
                self.events.put(("result", run(plan, timeout=timeout, cancel=self.cancel)))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True, name="bridge81-run").start()

    def cancel_run(self):
        if self.busy:
            self.cancel.set()
            self.status.set("Stopping the script and its process tree where supported…")

    def create_venv(self):
        from tkinter import filedialog
        if self.busy:
            self.fail("Wait for the running script to finish first.")
            return
        value = filedialog.asksaveasfilename(parent=self.root, title="Choose a NEW virtual environment folder", initialfile=".venv")
        if value:
            try:
                # Bash mode must not pass bash.exe to python -m venv.
                python = self.interpreter.get() if self.kind.get() == "Python" else default_python()
                self.start_run(venv_plan(value, python=python), 180)
            except (BridgeError, OSError) as exc:
                self.fail(exc)

    def make_games(self, parent):
        tk, ttk = self.tk, self.ttk
        self.folder = tk.StringVar()
        self.game_exe = tk.StringVar()
        self.profile = tk.StringVar(value="default")
        self.target = tk.StringVar(value="x64")
        self.allow_unknown = tk.BooleanVar(value=False)
        ttk.Label(parent, text="REN'PY GAME CHECK", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 10))
        self.field(parent, "Game folder", self.folder, lambda: self.choose_directory(self.folder))
        self.field(parent, "Executable", self.game_exe, self.choose_game_exe)
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="Launch profile").pack(side="left", padx=(0, 8))
        ttk.Combobox(row, textvariable=self.profile, values=tuple(PROFILES), state="readonly", width=15).pack(side="left")
        ttk.Label(row, text="Windows 8.1 target").pack(side="left", padx=(18, 8))
        ttk.Combobox(row, textvariable=self.target, values=("x64", "x86"), state="readonly", width=6).pack(side="left")
        ttk.Checkbutton(parent, text="I trust this game and allow launch if its engine version is unknown", variable=self.allow_unknown).pack(anchor="w", pady=4)
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=8)
        ttk.Button(row, text="Inspect game", command=self.inspect_game).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Preview launch", command=lambda: self.game_action(False)).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Launch game", command=lambda: self.game_action(True)).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Export report", command=self.export_report).pack(side="left")
        self.game_output = self.text_box(parent)
        self.set_text(self.game_output, "Inspect the extracted Windows game before launching.\n\nKnown OS or architecture blockers prevent launch. Other results remain UNVERIFIED until tested on your laptop.\n\nFor graphics problems, hold Shift while starting the game or press Shift+G, then try GL or ANGLE in its graphics menu.")

    def choose_game_exe(self):
        from tkinter import filedialog
        value = filedialog.askopenfilename(parent=self.root, title="Choose the game's Windows executable", initialdir=self.folder.get() or None,
                                           filetypes=(("Windows executable", "*.exe"),))
        if value:
            root = Path(self.folder.get()).resolve() if self.folder.get() else Path(value).resolve().parent
            try:
                relative = Path(value).resolve().relative_to(root)
            except ValueError:
                self.fail("Choose an executable inside the selected game folder.")
                return
            self.folder.set(str(root))
            self.game_exe.set(relative.as_posix())

    def current_report(self):
        return inspect_game(self.folder.get(), exe=self.game_exe.get() or None, target=self.target.get())

    def inspect_game(self):
        try:
            self.last_report = self.current_report()
            self.set_text(self.game_output, report_markdown(self.last_report))
            if self.last_report.executable:
                self.game_exe.set(self.last_report.executable)
            elif self.last_report.executables:
                self.set_text(self.game_output, report_markdown(self.last_report) + "\nExecutables:\n" + "\n".join(self.last_report.executables))
            self.status.set("Game check complete. Status: " + self.last_report.status.upper())
        except (BridgeError, OSError) as exc:
            self.fail(exc)

    def game_action(self, execute):
        try:
            if self.busy:
                raise BridgeError("Wait for the running script to finish before launching a game.")
            plan = game_plan(self.folder.get(), exe=self.game_exe.get() or None, profile=self.profile.get(),
                             target=self.target.get(), allow_unknown=self.allow_unknown.get())
            self.set_text(self.game_output, json.dumps(plan.as_dict(), indent=2))
            if execute:
                pid = launch_game(plan)
                self.status.set("Game started (PID %s). It keeps running if you close Bridge81." % pid)
        except (BridgeError, OSError) as exc:
            self.fail(exc)

    def export_report(self):
        from tkinter import filedialog
        try:
            report = self.current_report()  # Never export a stale report for another folder.
            value = filedialog.asksaveasfilename(parent=self.root, title="Save game report", initialfile="bridge81-game-report.md",
                                                defaultextension=".md", filetypes=(("Markdown", "*.md"), ("JSON", "*.json")))
            if value:
                text = json.dumps(report.as_dict(), indent=2) + "\n" if value.lower().endswith(".json") else report_markdown(report)
                Path(value).write_text(text, encoding="utf-8")
                self.status.set("Saved a report without absolute paths or game log contents.")
        except (BridgeError, OSError) as exc:
            self.fail(exc)

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                self.busy = False
                if kind == "result":
                    summary = "%s · exit %s · %.3fs%s" % (value.reason, value.returncode, value.elapsed_seconds, " · output capped" if value.output_truncated else "")
                    self.set_text(self.script_output, value.output + "\n\n" + summary)
                    self.status.set(summary)
                else:
                    self.set_text(self.script_output, value)
                    self.status.set(value)
        except queue.Empty:
            pass
        if self.closing and not self.busy:
            self.root.destroy()
        else:
            self.root.after(80, self.poll)

    def close(self):
        self.closing = True
        if self.busy:
            self.cancel_run()
        else:
            self.root.destroy()


def main() -> int:
    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception as exc:
        print("Bridge81 needs a desktop display and Python's Tcl/Tk component.\nUse the traditional Python installer with Tcl/Tk selected, or run python -m bridge81 --help.\n%s" % exc, file=sys.stderr)
        return 2
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
