"""Serializable, read-only plans shared by the desktop app and CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Finding:
    code: str
    level: str
    message: str
    action: str = ""


@dataclass(frozen=True)
class Plan:
    kind: str
    argv: tuple[str, ...]
    cwd: str
    env: dict[str, str] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return asdict(self)


class BridgeError(ValueError):
    """A user-facing validation error."""
