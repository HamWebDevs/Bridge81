import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from bridge81.cli import main
from bridge81.model import BridgeError, Plan
from bridge81.plans import CYGWIN_SCRIPT, bash_plan, python_plan, venv_plan
from bridge81.runner import child_environment, run
from helpers import pe


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="Bridge81 path with spaces ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def script(self, body, name="example.py"):
        source = self.root / name
        source.write_text(body, encoding="utf-8")
        return source

    def test_python_preserves_arguments_without_shell_interpretation(self):
        source = self.script("import sys,json; print(json.dumps(sys.argv[1:]))\n")
        args = ["two words", "a'\"b", "$HOME", "$(touch INJECTED)", "a&b", "", "é"]
        result = run(python_plan(source, args))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.output), args)
        self.assertFalse((self.root / "INJECTED").exists())

    def test_default_and_explicit_working_directory(self):
        source = self.script("import os; print(os.getcwd())\n")
        self.assertEqual(run(python_plan(source)).output.strip(), str(self.root))
        work = self.root / "other"
        work.mkdir()
        self.assertEqual(run(python_plan(source, cwd=str(work))).output.strip(), str(work))

    def test_nonzero_exit_is_preserved(self):
        result = run(python_plan(self.script("import sys; print('bad'); sys.exit(7)\n")))
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.reason, "completed")

    def test_timeout(self):
        result = run(python_plan(self.script("import time; time.sleep(30)\n")), timeout=0.15)
        self.assertEqual(result.reason, "timeout")
        self.assertLess(result.elapsed_seconds, 8)

    def test_cancel(self):
        stop = threading.Event()
        timer = threading.Timer(0.15, stop.set)
        timer.start()
        self.addCleanup(timer.cancel)
        result = run(python_plan(self.script("import time; time.sleep(30)\n")), cancel=stop)
        self.assertEqual(result.reason, "cancelled")

    def test_pre_cancel_does_not_start_script(self):
        marker = self.root / "started"
        plan = python_plan(self.script("from pathlib import Path; Path('started').touch()\n"))
        stop = threading.Event()
        stop.set()
        self.assertEqual(run(plan, cancel=stop).reason, "cancelled")
        self.assertFalse(marker.exists())

    def test_output_cap_stops_a_chatty_process(self):
        source = self.script("import os\nwhile True: os.write(1, b'x' * 8192)\n")
        result = run(python_plan(source), max_output=10000, timeout=5)
        self.assertEqual(result.reason, "output-limit")
        self.assertTrue(result.output_truncated)
        self.assertEqual(len(result.output), 10000)

    def test_invalid_output_bytes_are_replaced(self):
        result = run(python_plan(self.script("import os; os.write(1, b'\\xff\\x00abc')\n")))
        self.assertEqual(result.output, "\ufffd\0abc")

    def test_inherited_pipe_does_not_hang_monitor(self):
        source = self.script("import subprocess,sys\nsubprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])\n")
        result = run(python_plan(source), timeout=0.4)
        self.assertEqual(result.reason, "timeout")
        self.assertLess(result.elapsed_seconds, 8)

    def test_timeout_and_capture_bounds(self):
        plan = python_plan(self.script("pass\n"))
        for value in (0, -1, math.inf, math.nan, 86401, True):
            with self.subTest(timeout=value), self.assertRaises(BridgeError):
                run(plan, timeout=value)
        with self.assertRaises(BridgeError):
            run(plan, max_output=2**30)

    def test_arguments_are_validated(self):
        source = self.script("pass\n")
        for args in (["\0"], ["x"] * 257, ["x" * 25000]):
            with self.assertRaises(BridgeError):
                python_plan(source, args)

    def test_missing_interpreter_and_existing_venv(self):
        with self.assertRaises(BridgeError):
            python_plan(self.script("pass\n"), python=str(self.root / "not-found"))
        with self.assertRaises(BridgeError):
            venv_plan(self.root)

    def test_child_python_environment_is_not_injected(self):
        with patch.dict(os.environ, {"PYTHONHOME": "wrong", "PYTHONPATH": "wrong", "KEEP_ME": "yes"}):
            env = child_environment({"RENPY_LESS_MEMORY": "1"})
        self.assertNotIn("PYTHONHOME", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertEqual(env["KEEP_ME"], "yes")

    @unittest.skipUnless(shutil.which("bash") and os.name != "nt", "native Bash integration on Unix")
    def test_native_bash_arguments_and_working_directory(self):
        source = self.script("printf '%s\\n' \"$PWD\" \"$1\" \"$2\"\n", "script with spaces.sh")
        result = run(bash_plan(source, ["two words", "$(touch INJECTED)"]))
        self.assertEqual(result.output.splitlines(), [str(self.root), "two words", "$(touch INJECTED)"])
        self.assertFalse((self.root / "INJECTED").exists())

    def test_cygwin_plan_keeps_paths_and_arguments_out_of_wrapper_source(self):
        fake = self.root / "cygwin bin"
        fake.mkdir()
        bash = pe(fake / "bash.exe")
        (fake / "cygwin1.dll").touch()
        (fake / "cygpath.exe").touch()
        source = self.script("echo ok\n", "unsafe $name.sh")
        fake_os = types.SimpleNamespace(name="nt", path=os.path, access=os.access, X_OK=os.X_OK)
        with patch("bridge81.plans.os", fake_os):
            plan = bash_plan(source, ["$(touch INJECTED)"], bash=str(bash))
        self.assertEqual(plan.argv[4], CYGWIN_SCRIPT)
        self.assertNotIn(str(source), CYGWIN_SCRIPT)
        self.assertEqual(plan.argv[-1], "$(touch INJECTED)")

    @unittest.skipUnless(shutil.which("bash") and os.name != "nt", "Bash wrapper integration on Unix")
    def test_cygwin_fixed_wrapper_using_a_path_converter_fixture(self):
        source = self.script("printf '%s\\n' \"$PWD\" \"$1\" \"$2\"\nprintf 'z\\na\\n' | sort\n", "test $with ' quotes.sh")
        converter = self.root / "cygpath"
        converter.write_text("#!/bin/sh\nshift 2\nprintf '%s\\n' \"$1\"\n")
        converter.chmod(0o755)
        env = os.environ.copy()
        # A normal Cygwin installation does not add its bin folder to Windows PATH.
        env["PATH"] = str(self.root)
        args = [shutil.which("bash"), "--noprofile", "--norc", "-c", CYGWIN_SCRIPT, "bridge81", str(self.root), str(source), "a & b", "$(touch INJECTED)"]
        result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [str(self.root), "a & b", "$(touch INJECTED)", "a", "z"])
        self.assertFalse((self.root / "INJECTED").exists())

    def test_venv_is_created_and_runs_a_script(self):
        destination = self.root / "isolated python"
        result = run(venv_plan(destination), timeout=120)
        self.assertEqual(result.returncode, 0, result.output)
        python = destination / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        result = run(python_plan(self.script("import sys; print(sys.prefix)\n"), python=str(python)))
        self.assertEqual(Path(result.output.strip()), destination)

    def test_cli_plan_does_not_execute(self):
        import contextlib
        import io
        source = self.script("from pathlib import Path; Path('INJECTED').touch()\n")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = main(["plan", "python", str(source)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["kind"], "python")
        self.assertFalse((self.root / "INJECTED").exists())

    def test_cli_invalid_json_is_a_clear_error(self):
        import contextlib
        import io
        source = self.script("pass\n")
        for text in ("oops", "{}", "[1]", "null"):
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = main(["plan", "python", str(source), "--args-json", text])
            self.assertEqual(code, 2)
            self.assertIn("JSON array", stderr.getvalue())
