from pathlib import Path
import struct


def pe(path: Path, *, machine=0x8664, bits=64, subsystem=(6, 0)) -> Path:
    data = bytearray(512)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 128)
    data[128:132] = b"PE\0\0"
    size = 240 if bits == 64 else 224
    struct.pack_into("<HH", data, 132, machine, 2)
    struct.pack_into("<H", data, 148, size)
    struct.pack_into("<H", data, 152, 0x20B if bits == 64 else 0x10B)
    struct.pack_into("<HH", data, 192, 6, 0)
    struct.pack_into("<HH", data, 200, *subsystem)
    struct.pack_into("<H", data, 220, 2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def game(root: Path, version=(8, 3, 7), *, machine=0x8664, bits=64) -> Path:
    (root / "renpy").mkdir(parents=True)
    (root / "renpy" / "__init__.py").write_text("version_tuple = %r\nraise RuntimeError('MUST NOT EXECUTE')\n" % (version,), encoding="utf-8")
    pe(root / "Story.exe", machine=machine, bits=bits)
    return root
