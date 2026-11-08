"""The Studio contract resolves siblings and carries versioned hand-offs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from epy_export._core import _studio_connect as studio


def test_frozen_command_uses_the_neighbouring_exe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "epy_quoting.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "epy_outreach.exe"))
    assert studio.command("epy_quoting") == [str(exe)]


def test_frozen_command_names_the_missing_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "epy_outreach.exe"))
    with pytest.raises(studio.StudioConnectError, match="not beside"):
        studio.command("epy_project")


def test_source_command_falls_back_to_the_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(studio.shutil, "which", lambda _name: None)
    monkeypatch.setattr(sys, "executable", "python.exe")
    assert studio.command("epy_project") == [
        "python.exe",
        "-m",
        "epy_project",
    ]


def test_source_command_prefers_a_script_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(studio.shutil, "which", lambda _name: "C:/bin/app.exe")
    assert studio.command("epy_project") == ["C:/bin/app.exe"]


def test_source_command_finds_the_scripts_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(studio.shutil, "which", lambda _name: None)
    executable = tmp_path / "python.exe"
    executable.write_text("", encoding="utf-8")
    candidate = tmp_path / "Scripts" / "epy_project.exe"
    candidate.parent.mkdir()
    candidate.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(executable))
    assert studio.command("epy_project") == [str(candidate)]


def test_available_accepts_a_resolved_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(studio, "command", lambda _app: ["app.exe"])
    assert studio.available("epy_project") is True


def test_available_refuses_a_missing_frozen_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "epy_outreach.exe"))
    assert studio.available("epy_project") is False


def test_open_app_starts_the_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[list[str]] = []

    class _Process:
        pass

    def popen(args: list[str]) -> _Process:
        seen.append(args)
        return _Process()

    monkeypatch.setattr(studio, "command", lambda _app: ["app.exe"])
    monkeypatch.setattr(studio.subprocess, "Popen", popen)
    assert isinstance(studio.open_app("epy_project", ["x"]), _Process)
    assert seen == [["app.exe", "x"]]


def test_open_app_wraps_an_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(studio, "command", lambda _app: ["app.exe"])

    def boom(_args: list[str]) -> None:
        raise OSError("no")

    monkeypatch.setattr(studio.subprocess, "Popen", boom)
    with pytest.raises(studio.StudioConnectError, match="could not"):
        studio.open_app("epy_project")


def test_handoff_writes_a_versioned_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[list[str]] = []

    class _Process:
        pass

    def open_app(app: str, args: list[str]) -> _Process:
        assert app == "epy_quoting"
        seen.append(list(args))
        return _Process()

    monkeypatch.setattr(studio, "open_app", open_app)
    process = studio.handoff(
        "epy_outreach",
        "epy_quoting",
        "send_contact",
        {"contact_id": "ana"},
        args=["folder"],
    )
    assert isinstance(process, _Process)
    envelope = json.loads(Path(seen[0][0]).read_text(encoding="utf-8"))
    assert envelope == {
        "source": "epy_outreach",
        "target": "epy_quoting",
        "action": "send_contact",
        "payload": {"contact_id": "ana"},
        "version": 1,
    }
    assert seen[0][1] == "folder"
