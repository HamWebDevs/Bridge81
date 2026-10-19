import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

from bridge81.cli import main
from bridge81.dependencies import category, inspect_dependencies, report_markdown
from bridge81.model import BridgeError
from bridge81.pe_imports import inspect_imports
from helpers import game
from import_helpers import import_pe


class ImportTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.exe=self.root/'Story.exe'

    def test_direct_and_delayed_imports_for_32_and_64_bit_images(self):
        for bits in (32,64):
            import_pe(self.exe, ('KERNEL32.dll','ucrtbase.dll'), ('VCRUNTIME140.dll',), bits=bits)
            result=inspect_imports(self.exe)
            self.assertEqual(result['imports'],['KERNEL32.dll','ucrtbase.dll'])
            self.assertEqual(result['delay_imports'],['VCRUNTIME140.dll'])
            self.assertLess(result['bytes_read'],4096)

    def test_no_imports_is_metadata_not_proof_of_no_dependencies(self):
        import_pe(self.exe,(),())
        self.assertEqual(inspect_imports(self.exe)['imports'],[])

    def test_duplicate_names_are_deduplicated_case_insensitively(self):
        import_pe(self.exe,('KERNEL32.dll','kernel32.DLL'))
        self.assertEqual(inspect_imports(self.exe)['imports'],['KERNEL32.dll'])

    def test_legacy_delay_import_virtual_addresses(self):
        import_pe(self.exe,(),('USER32.dll',),bits=32)
        data=bytearray(self.exe.read_bytes());struct.pack_into('<II',data,1024,0,0x401300);self.exe.write_bytes(data)
        self.assertEqual(inspect_imports(self.exe)['delay_imports'],['USER32.dll'])

    def test_bad_rvas_and_unterminated_tables_are_rejected(self):
        import_pe(self.exe)
        original=self.exe.read_bytes()
        for change in ('name','directory','size'):
            data=bytearray(original)
            if change=='name':struct.pack_into('<I',data,512+12,0xffffffff)
            elif change=='directory':struct.pack_into('<I',data,152+112+8,0xfffffffe)
            else:struct.pack_into('<I',data,152+112+8+4,20)
            self.exe.write_bytes(data)
            with self.subTest(change=change),self.assertRaises(BridgeError):inspect_imports(self.exe)

    def test_import_paths_are_not_used_as_filesystem_paths(self):
        import_pe(self.exe,('../outside.dll',))
        with self.assertRaisesRegex(BridgeError,'unsafe path'):inspect_imports(self.exe)

    def test_reads_stay_bounded_for_large_sparse_files(self):
        import_pe(self.exe)
        with self.exe.open('r+b') as stream:stream.truncate(512*1024*1024)
        self.assertLess(inspect_imports(self.exe)['bytes_read'],4096)
        with mock.patch('bridge81.pe_imports.MAX_READ',100),self.assertRaisesRegex(BridgeError,'read budget'):inspect_imports(self.exe)

    def test_descriptor_limit_and_ambiguous_sections(self):
        import_pe(self.exe,('a.dll','b.dll'))
        with mock.patch('bridge81.pe_imports.MAX_IMPORTS',1),self.assertRaisesRegex(BridgeError,'descriptors'):inspect_imports(self.exe)
        data=bytearray(self.exe.read_bytes());struct.pack_into('<H',data,134,2)
        data[432:472]=data[392:432];self.exe.write_bytes(data)
        with self.assertRaisesRegex(BridgeError,'unique'):inspect_imports(self.exe)


class DependencyTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=game(Path(temporary.name)/'Story')
        import_pe(self.root/'Story.exe',('KERNEL32.dll','ucrtbase.dll'))

    def test_missing_bundle_runtime_is_unknown_not_a_missing_system_dll_claim(self):
        report=inspect_dependencies(self.root)
        imports=report['modules'][0]['imports']
        self.assertEqual(imports[1]['category'],'universal-crt')
        self.assertEqual(imports[1]['availability'],'not-in-inspected-bundle-folders')
        self.assertFalse(report['findings'])
        self.assertIn('provided by Windows',report['interpretation'])
        self.assertNotIn(str(self.root),json.dumps(report))

    def test_existing_game_markdown_and_new_dependency_markdown_both_work(self):
        for command, expected in (('game', 'Bridge81 game report'), ('dependencies', 'Bridge81 DLL evidence')):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                code=main([command,str(self.root),'--format','markdown'])
            self.assertEqual(code,0)
            self.assertIn(expected,out.getvalue())

    def test_bundled_wrong_architecture_is_evidence_and_bytes_stay_unchanged(self):
        dll=import_pe(self.root/'ucrtbase.dll',(),bits=32);before=dll.read_bytes()
        report=inspect_dependencies(self.root)
        self.assertEqual(report['findings'][0]['code'],'bundled-dll-different-architecture')
        self.assertEqual(dll.read_bytes(),before)
        self.assertIn('different-architecture',report_markdown(report))

    def test_python_prefixed_engine_and_its_runtime_are_inspected_not_updater(self):
        engine=self.root/'lib/py3-windows-x86_64'
        import_pe(engine/'Story.exe',('USER32.dll',))
        import_pe(engine/'python312.dll',('VCRUNTIME140.dll',))
        (engine/'zsync.exe').write_bytes(b'NOT A PE; must not inspect helpers')
        result=inspect_dependencies(self.root)
        self.assertEqual(result['summary']['modules'],3)
        self.assertEqual(result['summary']['unreadable_modules'],0)
        self.assertEqual(result['summary']['imports'],4)

    def test_broken_import_metadata_is_visible_and_cli_reports_incomplete(self):
        data=bytearray((self.root/'Story.exe').read_bytes());struct.pack_into('<I',data,524,0xffffffff);(self.root/'Story.exe').write_bytes(data)
        out=io.StringIO()
        with contextlib.redirect_stdout(out):code=main(['dependencies',str(self.root),'--format','json'])
        self.assertEqual(code,1)
        self.assertEqual(json.loads(out.getvalue())['summary']['unreadable_modules'],1)

    def test_contract_names_are_classified_without_probing_the_os(self):
        self.assertEqual(category('api-ms-win-core-synch-l1-2-0.dll'),'windows-api-contract')
        self.assertEqual(category('VCRUNTIME140_1.dll'),'visual-c-runtime')
        self.assertEqual(category('custom.dll'),'application')

    def test_symlinked_executable_does_not_trigger_import_reads(self):
        try:(self.root/'alias.exe').symlink_to(self.root/'Story.exe')
        except OSError:self.skipTest('symlinks unavailable')
        with self.assertRaises(BridgeError):inspect_imports(self.root/'alias.exe')
