"""The words a window is drawn from, against the engine that owns them.

Inside a frozen bundle the engine cannot be imported at all, so a dialog
that asked IT for its layouts and document types could not be built and
the whole export entry stayed unreachable. The vocabularies therefore
live in this package, which every application already carries -- and a
copy is only safe while something compares it with the original.
"""

from __future__ import annotations

from epy_export import APPEARANCES, DOCUMENT_TYPES


def test_the_vocabularies_are_pinned() -> None:
    # Pinned here as well as against the engine below: a list that is
    # only checked against something else is not pinned at all.
    assert APPEARANCES == (
        "academic", "classic", "corporate", "creative", "handwritten",
        "minimal", "professional", "scientific", "technical",
    )
    assert DOCUMENT_TYPES == ("report", "paper", "book", "notebook")


def test_the_layouts_still_match_the_engine() -> None:
    import epy_docs  # noqa: PLC0415 - the engine whose layouts these mirror

    assert sorted(APPEARANCES) == sorted(epy_docs.available_layouts())


def test_the_document_types_still_match_the_engine() -> None:
    import epy_docs  # noqa: PLC0415 - the engine whose types these mirror

    assert sorted(DOCUMENT_TYPES) == sorted(
        epy_docs.available_document_types()
    )
