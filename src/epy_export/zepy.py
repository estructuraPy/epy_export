"""The suite-wide ``.zepy`` package for a rendered report.

A ``.zepy`` is a ZIP with a manifest, not an application-specific
database. Any ePy library can read the manifest, verify the members and
materialise the folder without knowing which application wrote it.

The manifest is written before the members so a reader can identify the
package from the first entry. Every member is recorded with its size and
SHA-256; :func:`verify` recomputes them rather than trusting the package.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "FORMAT_VERSION",
    "MANIFEST_NAME",
    "ZEPY_SUFFIX",
    "open_folder",
    "pack",
    "read_manifest",
    "unpack",
    "verify",
]

ZEPY_SUFFIX = ".zepy"
MANIFEST_NAME = "zepy.json"
FORMAT_VERSION = 1

_SKIP_DIRS = frozenset(
    {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"}
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _members(folder: Path) -> list[tuple[Path, str]]:
    members: list[tuple[Path, str]] = []
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        if not path.is_file():
            continue
        if path.name in {MANIFEST_NAME} or path.suffix.lower() in {
            ".zepy",
            ".part",
        }:
            continue
        members.append((path, relative.as_posix()))
    return members


def pack(
    folder: str | Path,
    target: str | Path,
    *,
    kind: str = "report",
    app: str = "",
    title: str = "",
    store: str = "",
    views: tuple[str, ...] | list[str] = (),
    formats: tuple[str, ...] | list[str] = (),
    version: str = "",
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Package ``folder`` as a ``.zepy`` and return the archive path.

    Args:
        folder: Folder to seal.
        target: Destination archive.
        kind: What the package holds, e.g. ``"report"``.
        app: The application that produced it.
        title: Human title for the manifest.
        store: The suite ``.kepy`` member this package carries, if any.
        views: Views included in the report.
        formats: Formats included in the package.
        version: Optional version label (for example a timestamp).
        metadata: Extra JSON-serialisable fields.
    """
    source = Path(folder)
    if not source.is_dir():
        raise FileNotFoundError(f"folder not found: {source}")
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    members = _members(source)
    files: dict[str, dict[str, Any]] = {}
    payloads: list[tuple[str, bytes]] = []
    for path, name in members:
        data = path.read_bytes()
        files[name] = {"bytes": len(data), "sha256": _digest(data)}
        payloads.append((name, data))
    manifest = {
        "format": "zepy",
        "format_version": FORMAT_VERSION,
        "kind": kind,
        "app": app,
        "title": title,
        "views": list(views),
        "formats": list(formats),
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        # Kept for readers that already know the project archive shape.
        "project": title,
        "store": store,
        "written_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "files": files,
    }
    if metadata:
        manifest.update(metadata)
    scratch = output.with_name(output.name + ".part")
    try:
        with zipfile.ZipFile(
            scratch, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr(
                MANIFEST_NAME,
                json.dumps(
                    manifest, ensure_ascii=False, indent=2
                )
                + "\n",
            )
            for name, data in payloads:
                archive.writestr(name, data)
        scratch.replace(output)
    except BaseException:
        scratch.unlink(missing_ok=True)
        raise
    return output


def read_manifest(path: str | Path) -> dict[str, Any]:
    """Read a package manifest without unpacking the archive."""
    archive = Path(path)
    try:
        with zipfile.ZipFile(archive) as handle:
            body = json.loads(handle.read(MANIFEST_NAME).decode("utf-8"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise ValueError(
            f"{archive.name} is not a readable .zepy: {exc}"
        ) from exc
    if not isinstance(body, dict) or body.get("format") != "zepy":
        raise ValueError(f"{archive.name} does not contain a zepy manifest")
    return body


def verify(path: str | Path) -> list[str]:
    """Return every member whose bytes disagree with the manifest."""
    archive = Path(path)
    manifest = read_manifest(archive)
    problems: list[str] = []
    files = manifest.get("files", {})
    if not isinstance(files, dict):
        return ["manifest files is not an object"]
    with zipfile.ZipFile(archive) as handle:
        present = set(handle.namelist()) - {MANIFEST_NAME}
        for name, entry in files.items():
            if name not in present:
                problems.append(f"{name}: named in the manifest, missing")
                continue
            data = handle.read(name)
            size = entry.get("bytes") if isinstance(entry, dict) else None
            digest = (
                entry.get("sha256") if isinstance(entry, dict) else None
            )
            if size is not None and len(data) != int(size):
                problems.append(
                    f"{name}: {len(data)} bytes, manifest says {size}"
                )
            elif digest is not None and _digest(data) != digest:
                problems.append(f"{name}: contents differ from the manifest")
        for name in sorted(present - set(files)):
            problems.append(f"{name}: present, not named in the manifest")
    return problems


def unpack(path: str | Path, destination: str | Path) -> Path:
    """Verify and extract a package into ``destination``."""
    archive = Path(path)
    problems = verify(archive)
    if problems:
        raise ValueError(
            f"{archive.name} is not intact: " + "; ".join(problems[:5])
        )
    output = Path(destination)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"{output} is not empty")
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as handle:
        for name in handle.namelist():
            if name == MANIFEST_NAME:
                continue
            target = (output / name).resolve()
            if output.resolve() not in target.parents:
                raise ValueError(f"unsafe member in package: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(handle.read(name))
    return output


def open_folder(path: str | Path) -> Path:
    """Extract a package beside itself and return the folder."""
    archive = Path(path)
    folder = archive.with_suffix("")
    if folder.is_dir() and any(folder.iterdir()):
        return folder
    return unpack(archive, folder)
