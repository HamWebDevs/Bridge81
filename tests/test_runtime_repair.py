import contextlib
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bridge81 import runtime_repair
from bridge81.model import BridgeError


class RuntimeRepairEntryTests(unittest.TestCase):
    def test_source_repair_is_available_without_importing_game_code(self):
        self.assertTrue(runtime_repair.repair_script().is_file())

    def test_frozen_build_uses_the_external_scripts_next_to_the_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "scripts/Repair-RenPy.ps1"
            script.parent.mkdir()
            script.write_text("# fixture", encoding="ascii")
            with patch.object(runtime_repair.sys, "frozen", True, create=True), patch.object(runtime_repair.sys, "executable", str(root / "Bridge81.exe")):
                self.assertEqual(runtime_repair.repair_script(), script)
            script.unlink()
            with patch.object(runtime_repair.sys, "frozen", True, create=True), patch.object(runtime_repair.sys, "executable", str(root / "Bridge81.exe")):
                with self.assertRaisesRegex(BridgeError, "complete Bridge81"):
                    runtime_repair.repair_script()

    def test_windows_entry_uses_separate_arguments_and_an_isolated_dll_search(self):
        fake_os = SimpleNamespace(name="nt", environ={"SystemRoot": "C:/Windows"})
        with patch.object(runtime_repair, "os", fake_os), patch.object(runtime_repair.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, create=True), \
             patch.object(runtime_repair.subprocess, "Popen", return_value=SimpleNamespace(pid=1234)) as popen, \
             patch.object(runtime_repair, "external_dll_search", return_value=contextlib.nullcontext()) as dll_search:
            self.assertEqual(runtime_repair.open_runtime_repair(), 1234)
            args, options = popen.call_args
            self.assertEqual(args[0][-2:], ["-File", str(runtime_repair.repair_script())])
            self.assertIn("-NoProfile", args[0])
            self.assertIn("-STA", args[0])
            self.assertIs(options["shell"], False)
            self.assertNotIn("PYTHONHOME", options["env"])
            dll_search.assert_called_once()

    @unittest.skipIf(os.name == "nt", "non-Windows path only")
    def test_other_hosts_get_a_clear_instruction(self):
        with self.assertRaisesRegex(BridgeError, "runs on Windows"):
            runtime_repair.open_runtime_repair()
