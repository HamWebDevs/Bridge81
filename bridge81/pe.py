"""Bounded PE header inspection. Never loads DLLs or executes the input."""

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass
from pathlib import Path

from .model import BridgeError

MACHINES = {0x14C: "x86", 0x8664: "x64", 0xAA64: "arm64", 0x1C4: "arm"}
MAX_PE_OFFSET = 16 * 1024 * 1024


@dataclass(frozen=True)
class PEInfo:
    architecture: str
    bits: int
    subsystem_version: tuple[int, int]
    os_version: tuple[int, int]
    subsystem: int

    def as_dict(self) -> dict:
        return asdict(self)


def inspect_pe(path: Path) -> PEInfo:
    """Read less than 1 KiB, even when given a large executable."""
    try:
        with path.open("rb") as stream:
            dos = stream.read(64)
            if len(dos) != 64 or dos[:2] != b"MZ":
                raise BridgeError("Not a Windows PE executable (missing MZ header).")
            offset = struct.unpack_from("<I", dos, 60)[0]
            if not 64 <= offset <= MAX_PE_OFFSET:
                raise BridgeError("PE header offset is invalid or exceeds the inspection limit.")
            stream.seek(offset)
            header = stream.read(24)
            if len(header) != 24 or header[:4] != b"PE\0\0":
                raise BridgeError("Invalid or truncated PE header.")
            machine, sections = struct.unpack_from("<HH", header, 4)
            optional_size = struct.unpack_from("<H", header, 20)[0]
            if not 1 <= sections <= 96 or not 70 <= optional_size <= 512:
                raise BridgeError("Invalid PE section count or optional header size.")
            optional = stream.read(optional_size)
            if len(optional) != optional_size:
                raise BridgeError("Truncated PE optional header.")
            magic = struct.unpack_from("<H", optional, 0)[0]
            if magic not in (0x10B, 0x20B):
                raise BridgeError("Unsupported PE optional header format.")
            bits = 32 if magic == 0x10B else 64
            if machine in (0x14C, 0x1C4) and bits != 32 or machine in (0x8664, 0xAA64) and bits != 64:
                raise BridgeError("PE machine and optional header disagree about bitness.")
            return PEInfo(
                MACHINES.get(machine, "unknown-0x%04x" % machine), bits,
                struct.unpack_from("<HH", optional, 48),
                struct.unpack_from("<HH", optional, 40),
                struct.unpack_from("<H", optional, 68)[0],
            )
    except OSError as exc:
        raise BridgeError("Cannot read executable: %s" % exc.strerror) from exc
