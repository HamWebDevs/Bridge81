"""Bounded PE import/delay-import names. Never maps or loads the input image."""
from __future__ import annotations

import os
from pathlib import Path
import re
import struct

from .model import BridgeError
from .pe import MAX_PE_OFFSET

MAX_READ = 256 * 1024
MAX_IMPORTS = 256
MAX_NAME = 260


class _Reader:
    def __init__(self, stream):
        self.stream = stream
        self.length = os.fstat(stream.fileno()).st_size
        self.used = 0

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.length:
            raise BridgeError('PE import data points outside the file.')
        self.used += size
        if self.used > MAX_READ:
            raise BridgeError('PE import inspection exceeds its 256 KiB read budget.')
        self.stream.seek(offset)
        data = self.stream.read(size)
        if len(data) != size:
            raise BridgeError('PE import data is truncated or changed during inspection.')
        return data


def inspect_imports(path: Path) -> dict:
    """Read at most 256 KiB of import metadata, independent of executable size."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise BridgeError('Import inspection needs an ordinary PE file, not a link.')
    try:
        with path.open('rb') as stream:
            reader = _Reader(stream)
            dos = reader.read(0, 64)
            if dos[:2] != b'MZ':
                raise BridgeError('Not a Windows PE file.')
            offset = struct.unpack_from('<I', dos, 60)[0]
            if not 64 <= offset <= MAX_PE_OFFSET:
                raise BridgeError('PE header offset exceeds the inspection limit.')
            header = reader.read(offset, 24)
            if header[:4] != b'PE\0\0':
                raise BridgeError('Invalid PE signature.')
            sections = struct.unpack_from('<H', header, 6)[0]
            optional_size = struct.unpack_from('<H', header, 20)[0]
            if not 1 <= sections <= 96 or not 96 <= optional_size <= 512:
                raise BridgeError('Invalid PE section count or optional header.')
            optional = reader.read(offset + 24, optional_size)
            magic = struct.unpack_from('<H', optional)[0]
            if magic == 0x10b:
                directories, count_offset = 96, 92
                image_base = struct.unpack_from('<I', optional, 28)[0]
            elif magic == 0x20b and optional_size >= 112:
                directories, count_offset = 112, 108
                image_base = struct.unpack_from('<Q', optional, 24)[0]
            else:
                raise BridgeError('Unsupported PE optional header.')
            count = struct.unpack_from('<I', optional, count_offset)[0]
            if count > 32 or directories + count * 8 > optional_size:
                raise BridgeError('Invalid PE data-directory count.')
            size_headers = struct.unpack_from('<I', optional, 60)[0]
            section_data = reader.read(offset + 24 + optional_size, sections * 40)
            ranges = []
            for index in range(sections):
                virtual_size, address, raw_size, raw_offset = struct.unpack_from('<IIII', section_data, index * 40 + 8)
                if address + max(virtual_size, raw_size) > 2**32 or raw_offset + raw_size > reader.length:
                    raise BridgeError('Invalid PE section extent.')
                if raw_size:
                    ranges.append((address, raw_size, raw_offset))

            def location(rva, size=1):
                if rva <= 0 or rva + size > 2**32:
                    raise BridgeError('Invalid PE import RVA.')
                matches = []
                if rva + size <= size_headers and rva + size <= reader.length:
                    matches.append((rva, min(size_headers, reader.length) - rva))
                for address, raw_size, raw_offset in ranges:
                    if address <= rva and rva + size <= address + raw_size:
                        matches.append((raw_offset + rva - address, address + raw_size - rva))
                if len(matches) != 1:
                    raise BridgeError('Import RVA has no unique file-backed section.')
                return matches[0]

            def name(rva):
                at, available = location(rva)
                data = reader.read(at, min(available, MAX_NAME + 1))
                end = data.find(b'\0')
                if end < 1 or end > MAX_NAME:
                    raise BridgeError('PE import name is empty, unterminated or too long.')
                try:
                    value = data[:end].decode('ascii')
                except UnicodeError as exc:
                    raise BridgeError('PE import name is not supported ASCII metadata.') from exc
                if not re.fullmatch(r'[A-Za-z0-9_.+\-]{1,260}', value):
                    raise BridgeError('PE import name contains unsafe path characters.')
                return value

            result = {'imports': [], 'delay_imports': []}
            for directory, stride, field in ((1, 20, 'imports'), (13, 32, 'delay_imports')):
                if directory >= count:
                    continue
                rva, size = struct.unpack_from('<II', optional, directories + directory * 8)
                if not rva and not size:
                    continue
                if not rva or size < stride:
                    raise BridgeError('PE import directory is incomplete.')
                complete = False
                for index in range(min(size // stride, MAX_IMPORTS + 1)):
                    at, _ = location(rva + index * stride, stride)
                    record = reader.read(at, stride)
                    if not any(record):
                        complete = True
                        break
                    if index >= MAX_IMPORTS:
                        raise BridgeError('PE import table exceeds 256 descriptors.')
                    name_rva = struct.unpack_from('<I', record, 12 if directory == 1 else 4)[0]
                    if directory == 13:
                        attributes = struct.unpack_from('<I', record)[0]
                        if attributes & ~1:
                            raise BridgeError('Unsupported delay-import attributes.')
                        if not attributes & 1:
                            name_rva -= image_base
                    value = name(name_rva)
                    if value.casefold() not in {v.casefold() for v in result[field]}:
                        result[field].append(value)
                if not complete:
                    raise BridgeError('PE import table lacks a bounded terminator.')
            result['bytes_read'] = reader.used
            return result
    except OSError as exc:
        raise BridgeError('Cannot inspect PE imports: ' + (exc.strerror or 'read failed')) from exc
