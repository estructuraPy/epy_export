"""The suite-wide provider preference is small, durable and key-free."""

from __future__ import annotations

from pathlib import Path

import pytest

from epy_export._core import _provider_prefs as prefs


def test_the_default_is_deepseek(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EPY_SUITE_HOME", str(tmp_path))
    assert prefs.load() == prefs.ProviderPreference()
    assert prefs.ensure_default().provider == "deepseek"
    assert (tmp_path / "provider.json").is_file()


def test_a_saved_choice_is_read_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EPY_SUITE_HOME", str(tmp_path))
    prefs.save("deepseek", "deepseek-v4-pro")
    assert prefs.load() == prefs.ProviderPreference(
        "deepseek", "deepseek-v4-pro"
    )


def test_a_corrupt_file_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EPY_SUITE_HOME", str(tmp_path))
    (tmp_path / "provider.json").write_text("not json", encoding="utf-8")
    assert prefs.load() == prefs.ProviderPreference()


def test_a_later_choice_survives_ensure_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EPY_SUITE_HOME", str(tmp_path))
    prefs.save("openai", "gpt-4o")
    assert prefs.ensure_default() == prefs.ProviderPreference(
        "openai", "gpt-4o"
    )
