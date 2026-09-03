"""The one organisation name every application stores settings under.

Five programs wrote their ``QSettings`` under two spellings of the same
organisation: ``ANM Ingeniería`` (epy_reports, epy_slides, epy_papers)
and ``ANM Ingenieria`` (epy_draft, ePy Studio). On Windows those are two
registry trees, so the Studio selector -- which reads the language the
person already chose in an editor so it does not ask again -- never
found what three of the four editors had saved, and asked anyway. One
constant here, imported by all five, is what ends that; the legacy
spelling stays named so a first start after the change can copy what
was stored under it.
"""

from __future__ import annotations

ORGANIZATION = "ANM Ingeniería"
"""Organisation segment of every application's settings scope."""

LEGACY_ORGANIZATIONS: tuple[str, ...] = ("ANM Ingenieria",)
"""Spellings settings were stored under before, most recent first."""

__all__ = ["LEGACY_ORGANIZATIONS", "ORGANIZATION"]
