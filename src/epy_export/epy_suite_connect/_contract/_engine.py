"""What an engine is, and what a caller may ask one for.

Types only. No engine is named here and nothing is imported from a
sibling: the catalog names them and the adapters reach them, so a
machine with none of the family installed still loads this module and
can still say what it would need.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..._core._backends import BackendUnavailableError

__all__ = [
    "APPEARANCES",
    "Engine",
    "EngineUnavailableError",
    "RenderOptions",
]

APPEARANCES: tuple[str, ...] = (
    "academic",
    "classic",
    "corporate",
    "creative",
    "handwritten",
    "minimal",
    "professional",
    "scientific",
    "technical",
)
"""The layout vocabulary shared across the family.

Nine names a user learns once and knows everywhere. This tuple is the
answer for a machine with no engine installed to publish its own; where
an engine does publish one, the adapter asks it rather than trusting
this copy.
"""


# One condition, one name. "The engine is not installed" and "the
# backend could not be loaded" are the same fact, and giving it two
# classes is exactly the duplication this library exists to end -- a
# caller cannot know which of the two to catch, so it catches one and
# the other escapes. Measured: a consumer's test asked for
# EngineUnavailableError and got BackendUnavailableError from a code
# path two frames deeper.
#
# The alias is kept because "engine" is the word this layer speaks in,
# and the dispatcher's message says which ENGINE is missing.
EngineUnavailableError = BackendUnavailableError


@dataclass(frozen=True)
class Engine:
    """One way of turning a source document into a finished one.

    Attributes:
        engine_id: Short id, as a catalog and an interface use it.
        label: What a person reads in a menu.
        module: The importable package that does the work.
        formats: Formats this engine can produce, in offer order.
        themed: Whether it accepts an appearance name.
        purpose: One line saying what kind of document it makes, shown
            beside the choice so the choice can be made knowingly.
    """

    engine_id: str
    label: str
    module: str
    formats: tuple[str, ...]
    themed: bool
    purpose: str


@dataclass(frozen=True)
class RenderOptions:
    """Everything an engine might need beyond the source and the format.

    Bundled rather than passed as a widening list of keywords, for one
    reason: an adapter can then say which fields it understands, and the
    dispatcher can REFUSE a field meant for a different engine instead of
    dropping it.

    That refusal is the point. Asking ePy Reports for a journal profile
    used to be silently ignored, so a caller who believed they had asked
    for a journal draft got a report and no signal. It is the same
    failure the format check already refuses by name -- "silently
    producing two of three requested files is how a caller comes to
    believe it has a .docx it never got" -- and it deserves the same
    answer.

    Attributes:
        appearance: Layout name, for the engines that take one.
        journal_id: Journal profile, for ePy Papers only.
        author: Cover metadata, for the engines whose entry point
            accepts it. Reports and Slides are opened from a file and
            read what the document itself carries, so a deck takes its
            author from front matter and a report takes none.
        language: Document language.
        project_type: Cover subtitle.
        source_kind: Whether the source is plain Markdown or Quarto.
            Explicit, never guessed from the suffix: epy_reports feeds
            Quarto with directives in it and epy_craft feeds plain
            Markdown, and the two entry points into epy_docs are
            different methods. Guessing means one of them silently gets
            the wrong reader.
    """

    appearance: str = "corporate"
    journal_id: str = ""
    author: Mapping[str, str] | None = None
    language: str = "es"
    project_type: str = ""
    source_kind: str = "markdown"

    def named_fields(self) -> tuple[str, ...]:
        """Return the fields carrying something other than their default.

        Returns:
            Field names the caller actually set, so an adapter can name
            the ones it does not understand.
        """
        empty = RenderOptions()
        return tuple(
            name
            for name in (
                "appearance",
                "journal_id",
                "author",
                "language",
                "project_type",
                "source_kind",
            )
            if getattr(self, name) != getattr(empty, name)
        )
