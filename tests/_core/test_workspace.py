"""The shared workspace roots allocate cases without overwriting."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from epy_export._core._workspace import (
    Workspace,
    WorkspaceError,
    allocate_folder,
    config_home,
    root_for,
    set_root,
    write_markdown,
    write_unique_text,
)


def test_root_is_remembered_per_interface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two interfaces keep two roots in the same user configuration."""
    monkeypatch.setenv("EPY_WORKSPACE_HOME", str(tmp_path / "config"))
    first = set_root("epy_project", tmp_path / "projects")
    second = set_root("epy_quoting", tmp_path / "cotizaciones")
    assert first.is_dir()
    assert second.is_dir()
    assert root_for("epy_project") == first
    assert root_for("epy_quoting") == second


def test_an_empty_root_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An interface cannot be pointed at a file."""
    monkeypatch.setenv("EPY_WORKSPACE_HOME", str(tmp_path / "config"))
    file = tmp_path / "file.txt"
    file.write_text("x", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="not a folder"):
        set_root("epy_project", file)


def test_folders_are_consecutive(tmp_path: Path) -> None:
    """The next case takes the next number and never reuses a folder."""
    first = allocate_folder(tmp_path, "PRY", year=2026)
    second = allocate_folder(tmp_path, "PRY", year=2026)
    assert first.name == "PRY-2026-0001"
    assert second.name == "PRY-2026-0002"
    (tmp_path / "PRY-2026-0004").mkdir()
    third = allocate_folder(tmp_path, "PRY", year=2026, label="Cliente")
    assert third.name == "PRY-2026-0005_Cliente"


def test_the_same_text_is_not_duplicated(tmp_path: Path) -> None:
    """Writing equal content twice returns the original path."""
    target = tmp_path / "report.md"
    first = write_unique_text(target, "text\n")
    second = write_unique_text(target, "text\n")
    assert first == second
    assert target.read_text(encoding="utf-8") == "text\n"
    assert [path.name for path in tmp_path.iterdir()] == ["report.md"]


def test_different_text_gets_a_version(tmp_path: Path) -> None:
    """Different content is versioned instead of replacing the first."""
    target = tmp_path / "report.md"
    write_unique_text(target, "uno\n")
    second = write_unique_text(target, "dos\n")
    assert second.name == "report-002.md"
    assert target.read_text(encoding="utf-8") == "uno\n"
    assert second.read_text(encoding="utf-8") == "dos\n"


def test_config_home_uses_the_platform_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The configuration directory follows Windows and XDG defaults."""
    monkeypatch.delenv("EPY_WORKSPACE_HOME", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    assert config_home() == tmp_path / "roaming" / "ePy Suite"
    monkeypatch.delenv("APPDATA")
    assert config_home() == Path.home() / "AppData" / "Roaming" / "ePy Suite"
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert config_home() == tmp_path / "xdg" / "ePy Suite"
    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert config_home() == Path.home() / ".config" / "ePy Suite"


def test_a_corrupt_config_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken or misshaped workspaces.json reads as empty."""
    monkeypatch.setenv("EPY_WORKSPACE_HOME", str(tmp_path))
    config = tmp_path / "workspaces.json"
    config.write_text("not json", encoding="utf-8")
    assert root_for("epy_project") is None
    config.write_text("[]", encoding="utf-8")
    assert root_for("epy_project") is None
    config.write_text('{"roots": []}', encoding="utf-8")
    assert root_for("epy_project") is None
    config.write_text('{"roots": {"epy_project": ""}}', encoding="utf-8")
    assert root_for("epy_project") is None


def test_a_missing_configured_root_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unset root refuses a Workspace instead of guessing one."""
    monkeypatch.setenv("EPY_WORKSPACE_HOME", str(tmp_path))
    with pytest.raises(WorkspaceError, match="has no workspace root"):
        Workspace.configured("epy_project", "PRY")


def test_a_configured_workspace_allocates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Workspace reads its root and creates the next case."""
    monkeypatch.setenv("EPY_WORKSPACE_HOME", str(tmp_path / "config"))
    set_root("epy_project", tmp_path / "projects")
    workspace = Workspace.configured("epy_project", "PRY")
    assert workspace.allocate(year=2026).name == "PRY-2026-0001"


def test_an_empty_root_is_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Setting an empty root forgets the interface's old root."""
    monkeypatch.setenv("EPY_WORKSPACE_HOME", str(tmp_path / "config"))
    set_root("epy_project", tmp_path / "projects")
    with pytest.raises(WorkspaceError, match="empty"):
        set_root("epy_project", "")
    assert root_for("epy_project") is None


def test_allocation_refuses_a_root_that_is_a_file(tmp_path: Path) -> None:
    """A file cannot stand in for the root folder."""
    file = tmp_path / "file"
    file.write_text("x", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="not a folder"):
        allocate_folder(file, "PRY")


def test_allocation_skips_non_folders(tmp_path: Path) -> None:
    """A loose file with a matching name does not take a sequence."""
    (tmp_path / "PRY-2026-0009.txt").write_text("x", encoding="utf-8")
    assert allocate_folder(tmp_path, "PRY", year=2026).name == (
        "PRY-2026-0001"
    )


def test_allocation_retries_a_raced_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A folder created between scan and mkdir gets the next number."""
    original = Path.mkdir
    raced = {"done": False}

    def mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if (
            not raced["done"]
            and not kwargs.get("exist_ok")
            and self.name.startswith("PRY-2026-")
        ):
            raced["done"] = True
            original(self, parents=True, exist_ok=True)
            raise FileExistsError(self)
        return original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "mkdir", mkdir)
    assert allocate_folder(tmp_path, "PRY", year=2026).name == (
        "PRY-2026-0002"
    )


def test_allocation_reports_an_os_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A folder that cannot be created is reported, not swallowed."""
    original = Path.mkdir

    def mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if self.name.startswith("PRY-2026-"):
            raise OSError("denied")
        return original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "mkdir", mkdir)
    with pytest.raises(WorkspaceError, match="could not be created"):
        allocate_folder(tmp_path, "PRY", year=2026)


def test_a_file_that_cannot_be_read_gets_a_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable target is not overwritten or duplicated."""
    (tmp_path / "report.md").mkdir()
    second = write_unique_text(tmp_path / "report.md", "text\n")
    assert second.name == "report-002.md"


def test_write_unique_reports_a_parent_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A destination parent that cannot be made is named."""

    def mkdir(self: Path, *args: object, **kwargs: object) -> None:
        raise OSError("denied")

    monkeypatch.setattr(Path, "mkdir", mkdir)
    with pytest.raises(WorkspaceError, match="destination folder"):
        write_unique_text(tmp_path / "x" / "report.md", "text")


def test_markdown_names_and_suffix(tmp_path: Path) -> None:
    """Markdown gets its extension and refuses an empty name."""
    written = write_markdown(tmp_path, "tracking", "text")
    assert written.name == "tracking.md"
    with pytest.raises(WorkspaceError, match="needs a name"):
        write_markdown(tmp_path, " ", "text")
