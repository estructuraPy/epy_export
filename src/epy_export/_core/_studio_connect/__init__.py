"""The official connection contract between ePy applications.

Every application-to-application hand-off goes through this module. It
resolves a sibling executable in a checkout or in an installed bundle,
launches it, and carries a versioned request envelope so the receiving
application can recognise what the caller asked for.

The module never imports another application. It is deliberately small
and stdlib-only so a core library can use it without loading Qt or a
provider SDK.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "Handoff",
    "StudioConnectError",
    "available",
    "command",
    "handoff",
    "open_app",
]

CONTRACT_VERSION = 1
"""The version of the request envelope this module writes."""


class StudioConnectError(RuntimeError):
    """A sibling application could not be found or started."""


@dataclass(frozen=True)
class Handoff:
    """One versioned request to another application."""

    source: str
    target: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
    version: int = CONTRACT_VERSION

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-ready envelope."""
        return asdict(self)


def command(app_id: str) -> list[str]:
    """Return the command that starts one ePy application."""
    suffix = ".exe" if os.name == "nt" else ""
    if getattr(sys, "frozen", False):
        sibling = Path(sys.executable).with_name(app_id + suffix)
        if not sibling.is_file():
            raise StudioConnectError(
                f"{app_id} is not beside {sys.executable}."
            )
        return [str(sibling)]
    found = shutil.which(app_id)
    if found:
        return [found]
    scripts = Path(sys.executable).parent / (
        "Scripts" if os.name == "nt" else "bin"
    )
    candidate = scripts / (app_id + suffix)
    if candidate.is_file():
        return [str(candidate)]
    module = app_id
    return [sys.executable, "-m", module]


def available(app_id: str) -> bool:
    """Return whether an application can be resolved on this machine."""
    try:
        command(app_id)
    except StudioConnectError:
        return False
    return True


def _envelope_file(payload: dict[str, Any]) -> Path:
    """Write a hand-off envelope to a temporary JSON file."""
    handle, name = tempfile.mkstemp(
        prefix="epy-handoff-", suffix=".json", text=True
    )
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return Path(name)


def open_app(
    app_id: str,
    args: Sequence[str] = (),
) -> subprocess.Popen[bytes]:
    """Launch an ePy application."""
    try:
        return subprocess.Popen([*command(app_id), *args])
    except OSError as exc:
        raise StudioConnectError(
            f"{app_id} could not be started: {exc}"
        ) from exc


def handoff(
    source: str,
    target: str,
    action: str,
    payload: dict[str, Any] | None = None,
    *,
    args: Sequence[str] = (),
) -> subprocess.Popen[bytes]:
    """Launch a target application with a versioned hand-off envelope.

    The envelope is written beside the request so the target can read
    ``--epy-handoff <file>`` when it implements the action. The path is
    also passed as the first argument for the applications that already
    open a folder directly, keeping the current flows working while the
    contract is adopted incrementally.
    """
    envelope = Handoff(
        source=source,
        target=target,
        action=action,
        payload=dict(payload or {}),
    )
    path = _envelope_file(envelope.as_dict())
    return open_app(target, [str(path), *args])
