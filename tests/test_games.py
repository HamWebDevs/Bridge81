import json
import tempfile
import unittest
from pathlib import Path

from bridge81.model import BridgeError
from bridge81.renpy import MAX_METADATA, game_plan, inspect_game, report_markdown
from helpers import game, pe


class GameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bridge81 games ")
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name).resolve()
        self.root = game(self.parent / "A Story")

    def test_older_game_is_unverified_not_a_false_pass(self):
        report = inspect_game(self.root)
        self.assertEqual(report.engine_version, (8, 3, 7))
        self.assertEqual(report.status, "unverified")
        self.assertEqual(report.executable, "Story.exe")

    def test_modern_engine_is_blocked_even_with_unknown_override(self):
        (self.root / "renpy/__init__.py").write_text("version_tuple = (8, 4, 0, 12345)\n")
        self.assertEqual(inspect_game(self.root).status, "blocked")
        with self.assertRaisesRegex(BridgeError, "Windows 10"):
            game_plan(self.root, allow_unknown=True)

    def test_future_engine_is_conservatively_blocked(self):
        (self.root / "renpy/__init__.py").write_text("version_tuple = (9, 0, 0)\n")
        self.assertEqual(inspect_game(self.root).status, "blocked")

    def test_logs_detect_engine_when_source_is_missing(self):
        (self.root / "renpy/__init__.py").unlink()
        (self.root / "log.txt").write_text("Windows 8.1\nRen'Py 7.8.7.25031702\n\nprivate dialogue\n")
        self.assertEqual(inspect_game(self.root).engine_version, (7, 8, 7))

    def test_disagreement_is_unknown_and_modern_evidence_stays_blocked(self):
        (self.root / "log.txt").write_text("Ren'Py 8.4.0.12345\n")
        report = inspect_game(self.root)
        self.assertIsNone(report.engine_version)
        self.assertEqual(report.status, "blocked")
        with self.assertRaises(BridgeError):
            game_plan(self.root, allow_unknown=True)

    def test_old_log_disagreement_requires_explicit_override(self):
        (self.root / "log.txt").write_text("Ren'Py 7.7.0.1234\n")
        with self.assertRaisesRegex(BridgeError, "unknown"):
            game_plan(self.root)
        self.assertEqual(game_plan(self.root, allow_unknown=True).kind, "renpy")

    def test_game_python_is_never_executed(self):
        marker = self.parent / "executed"
        (self.root / "renpy/__init__.py").write_text("version_tuple = (8,3,7)\nfrom pathlib import Path\nPath(%r).touch()\n" % str(marker))
        inspect_game(self.root)
        self.assertFalse(marker.exists())

    def test_x86_target_rejects_x64_and_x64_accepts_x86(self):
        self.assertEqual(inspect_game(self.root, target="x86").status, "blocked")
        pe(self.root / "Story.exe", machine=0x14C, bits=32)
        self.assertEqual(inspect_game(self.root, target="x64").status, "unverified")

    def test_arm_and_newer_subsystem_are_blocked(self):
        pe(self.root / "Story.exe", machine=0xAA64)
        self.assertEqual(inspect_game(self.root).status, "blocked")
        pe(self.root / "Story.exe", subsystem=(10, 0))
        self.assertEqual(inspect_game(self.root).status, "blocked")

    def test_invalid_executable_cannot_be_launched(self):
        (self.root / "Story.exe").write_bytes(b"MZ")
        with self.assertRaisesRegex(BridgeError, "Launch blocked"):
            game_plan(self.root)

    def test_multiple_executables_require_a_selection(self):
        pe(self.root / "Other.exe")
        self.assertIsNone(inspect_game(self.root).executable)
        with self.assertRaises(BridgeError):
            game_plan(self.root)
        self.assertEqual(game_plan(self.root, exe="Other.exe").argv[0], str(self.root / "Other.exe"))

    def test_external_executable_and_metadata_symlink(self):
        pe(self.parent / "Outside.exe")
        with self.assertRaises(BridgeError):
            inspect_game(self.root, exe="../Outside.exe")
        metadata = self.root / "renpy/__init__.py"
        metadata.unlink()
        outside = self.parent / "metadata.py"
        outside.write_text("version_tuple = (8,3,7)\n")
        try:
            metadata.symlink_to(outside)
        except OSError:
            self.skipTest("Symlinks unavailable on this host")
        report = inspect_game(self.root)
        self.assertIsNone(report.engine_version)
        self.assertTrue(any(f.code == "metadata-unreadable" for f in report.findings))

    def test_low_memory_profile_changes_only_child_environment(self):
        import os
        before = os.environ.copy()
        plan = game_plan(self.root, profile="low-memory")
        self.assertEqual(plan.env["RENPY_LESS_MEMORY"], "1")
        self.assertEqual(os.environ.copy(), before)
        self.assertFalse((self.root / "environment.txt").exists())

    def test_reports_exclude_absolute_paths_and_log_text(self):
        (self.root / "log.txt").write_text("Ren'Py 8.3.7.1234\nSECRET DIALOGUE\n")
        report = inspect_game(self.root)
        for rendered in (json.dumps(report.as_dict()), report_markdown(report)):
            self.assertNotIn(str(self.parent), rendered)
            self.assertNotIn("SECRET DIALOGUE", rendered)

    def test_oversized_metadata_is_bounded_and_reported(self):
        (self.root / "log.txt").write_bytes(b"x" * (MAX_METADATA + 100))
        self.assertTrue(any(f.code == "metadata-limit" for f in inspect_game(self.root).findings))

    def test_target_and_profile_validation(self):
        with self.assertRaises(BridgeError):
            inspect_game(self.root, target="arm64")
        with self.assertRaises(BridgeError):
            game_plan(self.root, profile="magic-fix")
        with self.assertRaises(BridgeError):
            inspect_game("")

    def test_non_exe_selection_is_rejected(self):
        with self.assertRaises(BridgeError):
            inspect_game(self.root, exe="renpy/__init__.py")
