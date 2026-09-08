"""The words a window is drawn from, against the engine that owns them.

Inside a frozen bundle the engine cannot be imported at all, so a dialog
that asked IT for its layouts and document types could not be built and
the whole export entry stayed unreachable. The vocabularies therefore
live in this package, which every application already carries -- and a
copy is only safe while something compares it with the original.
"""

from __future__ import annotations

import pytest

from epy_export import APPEARANCES, DOCUMENT_TYPES, backend_present

# This package's own helper, not a naked find_spec. find_spec RAISES on
# an import hook that refuses the name -- which is how a machine without
# the private engine is simulated, and how some environments answer --
# and backend_present is the function that already catches it. A bare
# call here turned "the engine is absent" into a collection error, so
# the whole module failed instead of skipping.
_HAS_DOCS = backend_present("epy_docs")


def test_the_vocabularies_are_pinned() -> None:
    # Pinned even where the engine cannot be reached, which is every
    # public checkout and every CI run: a list that is only checked
    # against something absent is not checked at all.
    assert APPEARANCES == (
        "academic", "classic", "corporate", "creative", "handwritten",
        "minimal", "professional", "scientific", "technical",
    )
    assert DOCUMENT_TYPES == ("report", "paper", "book", "notebook")


@pytest.mark.skipif(
    not _HAS_DOCS,
    reason="ePy Docs is a private commercial package; absent here",
)
def test_the_layouts_still_match_the_engine() -> None:
    import epy_docs  # pyright: ignore[reportMissingImports] - epy_docs is a private commercial package, absent from the public CI by design  # noqa: PLC0415 - optional, guarded above

    assert sorted(APPEARANCES) == sorted(epy_docs.available_layouts())


@pytest.mark.skipif(
    not _HAS_DOCS,
    reason="ePy Docs is a private commercial package; absent here",
)
def test_the_document_types_still_match_the_engine() -> None:
    import epy_docs  # pyright: ignore[reportMissingImports] - epy_docs is a private commercial package, absent from the public CI by design  # noqa: PLC0415 - optional, guarded above

    assert sorted(DOCUMENT_TYPES) == sorted(
        epy_docs.available_document_types()
    )
