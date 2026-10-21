"""Runtime-log hints never execute or export untrusted source text."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from bridge81.cli import main
from bridge81.model import BridgeError
from bridge81 import runtime_log


class RuntimeLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / 'traceback.txt'

    def test_loader_codes_runtime_mentions_and_locations(self):
        text = '[WinError 126] missing\nDLL load failed: The specified module could not be found.\n[WinError 127]\n0xc000007b\napi-ms-win-crt-runtime-l1-1-0.dll\nVCRUNTIME140_1.dll\n'
        report = runtime_log.analyse(text)
        by_code = {row['code']: row for row in report['findings']}
        self.assertEqual(by_code['loader-module-missing']['occurrences'], 2)
        self.assertEqual(by_code['loader-module-missing']['first_line'], 1)
        self.assertEqual(by_code['loader-module-missing']['last_line'], 2)
        self.assertIn('loader-procedure-missing', by_code)
        self.assertIn('loader-architecture', by_code)
        self.assertIn('ucrt-mentioned', by_code)
        self.assertIn('visual-c-runtime-mentioned', by_code)

    def test_private_paths_tokens_and_traceback_bodies_are_absent(self):
        text = 'C:\\Users\\PRIVATE_NAME\\private-game\\run.py\npassword=PRIVATE_PASSWORD\nModuleNotFoundError: PRIVATE_MODULE\n'
        report = runtime_log.analyse(text)
        self.assertIn('python-module-missing', {row['code'] for row in report['findings']})
        self.assertNotIn('PRIVATE_', json.dumps(report))
        self.assertNotIn('PRIVATE_', runtime_log.report_markdown(report))

    def test_renderer_context_and_ordinary_text_are_distinguished(self):
        self.assertEqual(runtime_log.analyse('OpenGL initialized normally')['findings'], [])
        report = runtime_log.analyse('Could not create OpenGL context')
        self.assertEqual(report['findings'][0]['code'], 'graphics-context')
        self.assertIn('not a root-cause diagnosis', report['interpretation'])

    def test_unknown_does_not_claim_compatibility(self):
        report = runtime_log.analyse('unrecognized crash')
        self.assertEqual(report['status'], 'no-recognised-pattern')
        self.assertNotIn('compatible', json.dumps(report))

    def test_never_executes_log_contents(self):
        self.path.write_text("__import__('pathlib').Path('marker').touch()\nWinError 193", encoding='utf-8')
        with mock.patch('subprocess.Popen', side_effect=AssertionError('must not execute')):
            self.assertEqual(runtime_log.load(self.path)['status'], 'hints-found')
        self.assertFalse((self.root / 'marker').exists())

    def test_size_line_utf8_and_regular_file_limits(self):
        self.path.write_bytes(b'PRIVATE_BYTES\xff')
        with self.assertRaises(BridgeError) as error:
            runtime_log.load(self.path)
        self.assertNotIn('PRIVATE_BYTES', str(error.exception))
        with self.assertRaises(BridgeError):
            runtime_log.load(self.root)
        with mock.patch.object(runtime_log, 'MAX_BYTES', 2):
            with self.assertRaises(BridgeError):
                runtime_log.analyse('long')
        with mock.patch.object(runtime_log, 'MAX_LINES', 1):
            with self.assertRaises(BridgeError):
                runtime_log.analyse('one\ntwo')

    @unittest.skipUnless(os.name == 'posix', 'symlinks')
    def test_symlinks_and_special_files_refused(self):
        self.path.write_text('log')
        link = self.root / 'link'
        link.symlink_to(self.path)
        os.mkfifo(self.root / 'pipe')
        for path in (link, self.root / 'pipe'):
            with self.assertRaises(BridgeError):
                runtime_log.load(path)

    def test_cli_json_markdown_and_missing_file_privacy(self):
        self.path.write_text('WinError 126\nPRIVATE_CONTENT', encoding='utf-8')
        for format in ('json', 'markdown'):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['runtime-log', str(self.path), '--format', format])
            self.assertEqual(code, 1)
            self.assertNotIn('PRIVATE_CONTENT', output.getvalue())
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = main(['runtime-log', str(self.root / 'PRIVATE_NAME')])
        self.assertEqual(code, 2)
        self.assertNotIn('PRIVATE_NAME', errors.getvalue())

    def test_windows_path_and_handle_ctime_difference_is_not_mutation(self):
        self.path.write_text('WinError 126', encoding='utf-8')
        original = os.fstat
        fields = ('st_mode', 'st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')

        def metadata(fd):
            value = original(fd)
            attributes = {key: getattr(value, key) for key in fields}
            attributes['st_ctime_ns'] += 123
            return SimpleNamespace(**attributes)

        with mock.patch('bridge81.runtime_log.os.fstat', side_effect=metadata):
            self.assertEqual(runtime_log.load(self.path)['status'], 'hints-found')


if __name__ == '__main__':
    unittest.main()
