"""Every engine this family knows how to reach.

Python, not ``.epyson``, and that is a decision rather than an
oversight. Two reasons, in order of weight.

The four rows change about once a year; the mapping that DOES change
often -- which prompt renders through which engine -- stays in the
application that owns the prompt library, as catalog data, where it
belongs. Splitting them that way keeps the frequently-edited half a
one-line data change without making the stable half a file.

And a data file is a thing a frozen bundle can fail to carry. The
Studio spec walked ``_config`` narrowly once and lost all five of one
app's catalogs, whose loader then raised on first use rather than
defaulting. Shipping zero data files means that class of failure does
not exist for this library.
"""

from __future__ import annotations

from .._contract._engine import Engine

__all__ = ["ENGINES", "engine", "engine_ids"]

ENGINES: tuple[Engine, ...] = (
    Engine(
        engine_id="reports",
        label="ePy Reports",
        module="epy_reports",
        formats=("pdf", "docx", "html"),
        themed=True,
        purpose="Prose with headings, figures and tables. The default, "
        "because most documents are that.",
    ),
    Engine(
        engine_id="slides",
        label="ePy Slides",
        module="epy_slides",
        formats=("pdf", "pptx", "html"),
        themed=True,
        purpose="A deck. Section headings become slides, so an outline "
        "written slide by slide arrives as one.",
    ),
    Engine(
        engine_id="papers",
        label="ePy Papers",
        module="epy_papers",
        formats=("pdf", "docx"),
        themed=False,
        purpose="A journal draft in a named journal's shape. Needs a "
        "journal profile rather than an appearance.",
    ),
    Engine(
        engine_id="docs",
        label="ePy Docs",
        module="epy_docs",
        formats=("pdf", "docx", "html"),
        themed=True,
        purpose="The generic writer, with the corporate cover and the "
        "legal note. The only one whose entry point takes author "
        "metadata.",
    ),
)

_BY_ID = {item.engine_id: item for item in ENGINES}


def engine(engine_id: str) -> Engine:
    """Return one engine by id.

    Args:
        engine_id: The id to look up.

    Returns:
        Its :class:`Engine` row.

    Raises:
        KeyError: Naming the id AND what is available. A typo in a
            catalog file otherwise surfaces much later, as a document
            that was never produced.
    """
    try:
        return _BY_ID[engine_id]
    except KeyError:
        known = ", ".join(sorted(_BY_ID))
        raise KeyError(
            f"unknown render engine {engine_id!r}; known: {known}"
        ) from None


def engine_ids() -> tuple[str, ...]:
    """Return every engine id, in offer order."""
    return tuple(item.engine_id for item in ENGINES)
