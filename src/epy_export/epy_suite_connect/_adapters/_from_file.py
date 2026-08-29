"""The engines opened from a file and asked for a format by name.

epy_reports and epy_slides share one shape exactly: ``Factory.from_file(
source, theme=...)`` then ``document.to_{fmt}(target)``. They get one
adapter between them rather than one each, because two modules that
would be identical is the duplication this library exists to end.

epy_papers does NOT fit here -- it takes a journal profile instead of a
theme and exports through a single ``to_draft`` -- and neither does
epy_docs, whose writer has no ``from_file`` at all. Each has its own
module. That is what dissolves the ``if engine_id == "papers"`` chain
the dispatcher used to carry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..._core._backends import load_backend
from .._contract._engine import Engine, RenderOptions

__all__ = ["FACTORIES", "emit", "understands"]

FACTORIES = {"reports": "Report", "slides": "SlideDeck"}
"""The attribute on each module that opens a source file."""

_UNDERSTOOD = ("appearance", "source_kind")
"""What these engines read. Everything else is refused by name.

They are opened from a path and read what the document itself carries,
so author, language and project type reach them through the document's
front matter and not through this call. Accepting them here and dropping
them is how a caller comes to believe a cover was set.
"""


def understands() -> tuple[str, ...]:
    """Return the option fields these engines accept."""
    return _UNDERSTOOD


def emit(
    spec: Engine, source: Path, target: Path, fmt: str, opts: RenderOptions
) -> Path:
    """Render ``source`` to ``target`` in ``fmt`` through ``spec``.

    Args:
        spec: The engine row, which names the module to import.
        source: The document to render.
        target: Where the result goes.
        fmt: One of the engine's formats; already validated upstream.
        opts: The caller's options; only ``appearance`` is used.

    Returns:
        ``target``.

    Raises:
        BackendUnavailableError: When the engine is not installed.
    """
    module = load_backend(spec.module, why=f"rendering through {spec.label}")
    # getattr on a dynamically imported module is exactly the boundary a
    # type checker cannot see across; the catalog is what guarantees the
    # attribute name, and a missing one raises here rather than later.
    factory: Any = getattr(module, FACTORIES[spec.engine_id])
    document: Any = (
        factory.from_file(source, theme=opts.appearance)
        if spec.themed
        else factory.from_file(source)
    )
    getattr(document, f"to_{fmt}")(target)
    return target
