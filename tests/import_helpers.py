from pathlib import Path
import struct


def import_pe(path: Path, imports=('KERNEL32.dll',), delay=(), *, bits=64):
    data = bytearray(4096)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<HH', data, 132, 0x8664 if bits == 64 else 0x14c, 1)
    optional_size = 240 if bits == 64 else 224
    struct.pack_into('<H', data, 148, optional_size)
    struct.pack_into('<H', data, 152, 0x20b if bits == 64 else 0x10b)
    struct.pack_into('<HH', data, 192, 6, 0)
    struct.pack_into('<HH', data, 200, 6, 0)
    struct.pack_into('<I', data, 152 + 60, 512)
    if bits == 64:
        struct.pack_into('<Q', data, 152 + 24, 0x140000000)
        count, directories = 108, 112
    else:
        struct.pack_into('<I', data, 152 + 28, 0x400000)
        count, directories = 92, 96
    struct.pack_into('<I', data, 152 + count, 16)
    section = 152 + optional_size
    data[section:section + 8] = b'.rdata\0\0'
    struct.pack_into('<IIII', data, section + 8, 3584, 0x1000, 3584, 512)
    for names, rva, names_rva, stride, directory in ((imports, 0x1000, 0x1100, 20, 1), (delay, 0x1200, 0x1300, 32, 13)):
        if not names:
            continue
        struct.pack_into('<II', data, 152 + directories + directory * 8, rva, (len(names) + 1) * stride)
        at = names_rva
        for index, name in enumerate(names):
            encoded = name.encode('ascii') + b'\0'
            target = 512 + at - 0x1000
            data[target:target + len(encoded)] = encoded
            record = 512 + rva - 0x1000 + index * stride
            struct.pack_into('<I', data, record + (12 if directory == 1 else 4), at)
            if directory == 13:
                struct.pack_into('<I', data, record, 1)
            at += len(encoded)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path
