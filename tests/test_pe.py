import random
import struct
import tempfile
import unittest
from pathlib import Path

from bridge81.model import BridgeError
from bridge81.pe import inspect_pe
from helpers import pe


class PETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "program.exe"

    def test_x64_headers(self):
        info = inspect_pe(pe(self.path, subsystem=(6, 3)))
        self.assertEqual((info.architecture, info.bits, info.subsystem_version), ("x64", 64, (6, 3)))

    def test_x86_headers(self):
        self.assertEqual(inspect_pe(pe(self.path, machine=0x14C, bits=32)).architecture, "x86")

    def test_arm_is_identified_without_loading_it(self):
        self.assertEqual(inspect_pe(pe(self.path, machine=0xAA64)).architecture, "arm64")

    def test_bitfield_mismatch(self):
        pe(self.path, machine=0x14C)
        with self.assertRaisesRegex(BridgeError, "disagree"):
            inspect_pe(self.path)

    def test_truncated_and_bad_signatures(self):
        pe(self.path)
        original = self.path.read_bytes()
        for data in (b"", b"MZ", original[:60], original[:145], original[:200], b"ELF" + original[3:]):
            with self.subTest(size=len(data)):
                self.path.write_bytes(data)
                with self.assertRaises(BridgeError):
                    inspect_pe(self.path)

    def test_invalid_header_offsets_are_bounded(self):
        pe(self.path)
        original = self.path.read_bytes()
        for offset in (0, 63, 0xFFFFFFFF):
            data = bytearray(original)
            struct.pack_into("<I", data, 60, offset)
            self.path.write_bytes(data)
            with self.assertRaises(BridgeError):
                inspect_pe(self.path)

    def test_random_files_fail_cleanly(self):
        rng = random.Random(81)
        for _ in range(80):
            self.path.write_bytes(rng.randbytes(rng.randrange(1024)))
            with self.assertRaises(BridgeError):
                inspect_pe(self.path)

    def test_large_sparse_input_does_not_require_full_read(self):
        pe(self.path)
        with self.path.open("r+b") as stream:
            stream.truncate(1024 * 1024 * 1024)
        self.assertEqual(inspect_pe(self.path).bits, 64)
