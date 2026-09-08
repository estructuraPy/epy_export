"""The package's version is one number, in two files that must agree.

``pyproject.toml`` carries a static version and ``__init__`` carries
``__version__``. The four applications install this package FROM A GIT
TAG and then declare a floor on it, so the number pip reads is the one
in pyproject -- and the number a human bumps is usually the other.

Measured: a release bumped ``__version__`` alone. The tag installed a
distribution still calling itself 0.2.0, the floor said 0.3.0, and pip
went looking on an index this package is published on nowhere. Four
pipelines went red on "No matching distribution found", which names
neither file.
"""

from __future__ import annotations

import re
from pathlib import Path

import epy_export

ROOT = Path(__file__).resolve().parents[1]


def _declared() -> str:
    """Return the version pyproject.toml declares."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert match, "pyproject.toml declares no static version"
    return match.group(1)


def test_the_two_files_agree() -> None:
    assert epy_export.__version__ == _declared()


def test_it_is_a_release_number() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", epy_export.__version__)


def test_the_changelog_has_a_heading_for_it() -> None:
    # A tag whose changelog says "Unreleased" is a release nobody can
    # read the notes for.
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{epy_export.__version__}]" in changelog
