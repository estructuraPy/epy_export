"""The suite's durable AI-provider preference.

Studio owns the choice, and every application reads the same small JSON
file. No key is stored here: credentials remain in the provider's
environment variable or the operating-system vault.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .._files import write_text_atomic

__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_PROVIDER",
    "ProviderPreference",
    "config_home",
    "ensure_default",
    "load",
    "save",
]

DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-v4-flash"


@dataclass(frozen=True)
class ProviderPreference:
    """The provider and model every assistant should start with."""

    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL


def config_home() -> Path:
    """Return the writable directory holding the suite preference."""
    override = os.environ.get("EPY_SUITE_HOME")
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


def _path() -> Path:
    return config_home() / "provider.json"


def load() -> ProviderPreference:
    """Return the stored provider preference, or the DeepSeek default."""
    path = _path()
    if not path.is_file():
        return ProviderPreference()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ProviderPreference()
    provider = str(data.get("provider") or DEFAULT_PROVIDER).strip()
    model = str(data.get("model") or DEFAULT_MODEL).strip()
    return ProviderPreference(
        provider or DEFAULT_PROVIDER, model or DEFAULT_MODEL
    )


def save(provider: str, model: str) -> ProviderPreference:
    """Persist one provider/model choice for the whole suite."""
    pref = ProviderPreference(
        provider.strip() or DEFAULT_PROVIDER,
        model.strip() or DEFAULT_MODEL,
    )
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(
        path,
        json.dumps(
            {"provider": pref.provider, "model": pref.model},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return pref


def ensure_default() -> ProviderPreference:
    """Seed DeepSeek once, without overwriting a later choice."""
    if not _path().is_file():
        return save(DEFAULT_PROVIDER, DEFAULT_MODEL)
    return load()
