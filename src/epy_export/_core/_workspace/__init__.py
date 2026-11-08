"""Per-interface workspace roots and collision-free folder allocation.

Every ePy interface stores its own cases under a root the user chooses.
The root is shared between sessions, the case folder is numbered with a
stable prefix, and no operation overwrites a file: a second write with
the same content is a no-op, and a second write with different content
gets the next version instead of replacing the first.

The module deliberately has no Qt dependency, so the same rules apply to
the applications and to headless tests.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .._files import write_text_atomic

__all__ = [
    "Workspace",
    "WorkspaceError",
    "allocate_folder",
    "config_home",
    "root_for",
    "set_root",
    "write_markdown",
    "write_unique_text",
]


class WorkspaceError(RuntimeError):
    """A workspace root or a case folder could not be used safely."""


def config_home() -> Path:
    """Return the writable directory holding the interface roots.

    ``EPY_WORKSPACE_HOME`` wins, which is what tests point at a temporary
    directory. Otherwise the suite uses ``%APPDATA%/ePy Suite`` on Windows
    and ``~/.config/ePy Suite`` elsewhere.
    """
    override = os.environ.get("EPY_WORKSPACE_HOME")
    if override:
        return Path(override)
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = (
            Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        )
        return base / "ePy Suite"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "ePy Suite"


def _config_path() -> Path:
    return config_home() / "workspaces.json"


def _load() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {"roots": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"roots": {}}
    if not isinstance(data, dict):
        return {"roots": {}}
    roots = data.get("roots")
    if not isinstance(roots, dict):
        data["roots"] = {}
    return data


def _save(data: dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(
        path,
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def root_for(app_id: str) -> Path | None:
    """Return the saved root of one interface, or ``None`` when unset."""
    stored = _load()["roots"].get(str(app_id))
    if not isinstance(stored, str) or not stored.strip():
        return None
    return Path(stored)


def set_root(app_id: str, root: str | Path) -> Path:
    """Remember the root of one interface and create it.

    An empty value removes the root. A path that names a file is refused;
    a missing directory is created so the next allocation can use it.

    Args:
        app_id: Stable interface id, for example ``epy_project``.
        root: The directory where this interface files its cases.

    Returns:
        The resolved root.

    Raises:
        WorkspaceError: If the path exists and is not a directory.
    """
    data = _load()
    roots = data["roots"]
    text = str(root).strip()
    if not text:
        roots.pop(str(app_id), None)
        _save(data)
        raise WorkspaceError("the workspace root is empty.")
    path = Path(text).expanduser()
    if path.exists() and not path.is_dir():
        raise WorkspaceError(f"{path} exists and is not a folder.")
    path.mkdir(parents=True, exist_ok=True)
    roots[str(app_id)] = str(path)
    _save(data)
    return path


def _slug(value: Any, maxlen: int = 48) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text[:maxlen].strip("-") or "caso"


@dataclass(frozen=True)
class Workspace:
    """One interface's root and the prefix of its case folders."""

    app_id: str
    root: Path
    prefix: str

    @classmethod
    def configured(cls, app_id: str, prefix: str) -> Workspace:
        """Build a workspace from the saved root of one interface."""
        root = root_for(app_id)
        if root is None:
            raise WorkspaceError(
                f"{app_id} has no workspace root; choose one first."
            )
        return cls(app_id=app_id, root=root, prefix=prefix)

    def allocate(
        self,
        *,
        year: int | None = None,
        label: str | None = None,
    ) -> Path:
        """Create and return the next numbered case folder."""
        return allocate_folder(
            self.root,
            self.prefix,
            year=year,
            label=label,
        )


def allocate_folder(
    root: str | Path,
    prefix: str,
    *,
    year: int | None = None,
    label: str | None = None,
    width: int = 4,
) -> Path:
    """Create the next unused numbered folder under ``root``.

    The folder is named ``<prefix>-<year>-<number>`` and, when a label is
    supplied, ``_<slug>`` is appended after the number. Existing folders
    are never reused: the number is allocated with an exclusive
    ``mkdir``, so two callers cannot take the same one.

    Args:
        root: The interface's root directory.
        prefix: The interface's short prefix, for example ``PRY``.
        year: Four-digit year in the name; the current year when omitted.
        label: Optional human-readable suffix.
        width: Zero-padding of the sequence, four by default.

    Returns:
        The new folder.

    Raises:
        WorkspaceError: If the root is not a directory or allocation
            cannot be completed.
    """
    base = Path(root).expanduser()
    if base.exists() and not base.is_dir():
        raise WorkspaceError(f"{base} exists and is not a folder.")
    base.mkdir(parents=True, exist_ok=True)
    clean_prefix = _slug(prefix).upper()
    clean_year = int(year or _dt.date.today().year)
    stem = f"{clean_prefix}-{clean_year}-"
    suffix = f"_{_slug(label)}" if label and str(label).strip() else ""
    pattern = re.compile(
        rf"^{re.escape(stem)}(\d+)(?:_.*)?$", re.IGNORECASE
    )
    highest = 0
    for child in base.iterdir():
        if not child.is_dir():
            continue
        match = pattern.match(child.name)
        if match:
            highest = max(highest, int(match.group(1)))
    number = highest + 1
    while True:
        candidate = base / f"{stem}{number:0{width}d}{suffix}"
        try:
            candidate.mkdir(exist_ok=False)
            return candidate
        except FileExistsError:
            number += 1
        except OSError as exc:
            raise WorkspaceError(
                f"the case folder could not be created: {candidate}"
            ) from exc


def write_unique_text(
    path: str | Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> Path:
    """Write text without overwriting or duplicating a file.

    If the requested file already holds the same text nothing is written
    and its path is returned. If it holds different text, the next
    ``stem-002.ext`` (or ``stem-003.ext``, ...) is written instead. An
    existing file is never replaced.

    Args:
        path: Preferred destination.
        text: Complete text to write.
        encoding: Encoding used to compare and write.

    Returns:
        The path that holds the text.

    Raises:
        WorkspaceError: If the parent cannot be created or no candidate
            can be written.
    """
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError(
            f"the destination folder could not be created: {target.parent}"
        ) from exc
    candidate = target
    number = 1
    while True:
        if not candidate.exists():
            write_text_atomic(candidate, text, encoding=encoding)
            return candidate
        try:
            if candidate.read_text(encoding=encoding) == text:
                return candidate
        except (OSError, UnicodeError):
            pass
        number += 1
        candidate = target.with_name(
            f"{target.stem}-{number:03d}{target.suffix}"
        )


def write_markdown(
    folder: str | Path,
    stem: str,
    text: str,
) -> Path:
    """Write a Markdown file inside a case folder without duplicates.

    Args:
        folder: The case folder.
        stem: File name without extension; ``.md`` is added.
        text: Complete Markdown document.

    Returns:
        The path that holds the Markdown.
    """
    name = str(stem).strip()
    if not name:
        raise WorkspaceError("the Markdown file needs a name.")
    if not name.lower().endswith(".md"):
        name += ".md"
    return write_unique_text(Path(folder) / name, text)
