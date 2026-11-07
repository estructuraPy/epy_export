"""Launching a sibling application from a checkout or a frozen bundle."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from epy_export._core import _siblings


def test_a_script_on_path_wins(monkeypatch) -> None:
    """A console script is the first checkout choice."""
    monkeypatch.setattr(
        _siblings.shutil, "which", lambda _name: "C:/bin/epy_quoting"
    )
    assert _siblings.command("epy_quoting") == ["C:/bin/epy_quoting"]


def test_the_interpreters_scripts_directory_is_the_next_choice(
    monkeypatch, tmp_path: Path
) -> None:
    """The venv Scripts directory is used when the script is not on PATH."""
    monkeypatch.setattr(_siblings.shutil, "which", lambda _name: None)
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    exe = scripts / "epy_quoting.exe"
    exe.write_bytes(b"MZ")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python.exe"))
    assert _siblings.command("epy_quoting") == [str(exe)]


def test_a_checkout_falls_back_to_python_m(
    monkeypatch, tmp_path: Path
) -> None:
    """An uninstalled checkout still has a startable module."""
    monkeypatch.setattr(_siblings.shutil, "which", lambda _name: None)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python.exe"))
    assert _siblings.command("epy_quoting") == [
        sys.executable,
        "-m",
        "epy_quoting",
    ]


def test_a_frozen_bundle_uses_the_sibling_beside_it(
    monkeypatch, tmp_path: Path
) -> None:
    """The installed suite keeps every executable in one folder."""
    sibling = tmp_path / "epy_quoting.exe"
    sibling.write_bytes(b"MZ")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "epy_outreach.exe"))
    assert _siblings.command("epy_quoting") == [str(sibling)]


def test_a_frozen_bundle_narrows_a_missing_sibling(
    monkeypatch, tmp_path: Path
) -> None:
    """A missing sibling is named, not guessed from PATH."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "epy_outreach.exe"))
    with pytest.raises(_siblings.SiblingUnavailableError, match="not beside"):
        _siblings.command("epy_quoting")


def test_launch_starts_the_command_with_its_arguments(monkeypatch) -> None:
    """The launch helper starts exactly the resolved command and args."""
    seen: list[list[str]] = []

    def fake_popen(command):
        seen.append(command)
        return object()

    monkeypatch.setattr(_siblings, "command", lambda _module: ["app.exe"])
    monkeypatch.setattr(_siblings.subprocess, "Popen", fake_popen)
    started = _siblings.launch("epy_quoting", ["offer"])
    assert started is not None
    assert seen == [["app.exe", "offer"]]
