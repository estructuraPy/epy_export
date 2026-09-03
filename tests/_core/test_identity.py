"""One organisation name, and the spelling it replaces.

Two spellings of the organisation put the five applications' settings
in two registry trees: the Studio selector read one and three editors
wrote the other, so the language a person had already chosen was never
found. These pin the constant the family now shares and keep the old
spelling named, so the copy-once migration in each application has a
source.
"""

from __future__ import annotations

from epy_export import LEGACY_ORGANIZATIONS, ORGANIZATION
from epy_export._core import _identity


def test_organization_carries_the_accent() -> None:
    # The three editors' settings already live under the accented
    # spelling; a constant without it would move their themes, languages
    # and autosave choice into an empty tree on the next start.
    assert ORGANIZATION == "ANM Ingeniería"
    assert ORGANIZATION is _identity.ORGANIZATION


def test_legacy_spelling_is_named_and_distinct() -> None:
    # epy_draft and Studio wrote under the unaccented spelling; the
    # migration copies from it once and must never read it as current.
    assert LEGACY_ORGANIZATIONS == ("ANM Ingenieria",)
    assert ORGANIZATION not in LEGACY_ORGANIZATIONS
