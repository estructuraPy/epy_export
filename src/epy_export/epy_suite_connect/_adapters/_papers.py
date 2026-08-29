"""ePy Papers: a journal draft, which needs a journal.

Its own module because its shape genuinely differs. There is no
``to_pdf``/``to_docx`` on ``Paper``; there is one ``to_draft(journal_id,
target, fmt=)``, and the profile takes the place of an appearance. In
the dispatcher that divergence was an ``if engine_id == "papers"``;
here it is simply what this module does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..._core._backends import load_backend
from .._contract._engine import Engine, RenderOptions

__all__ = ["emit", "understands"]

_UNDERSTOOD = ("journal_id", "source_kind")


def understands() -> tuple[str, ...]:
    """Return the option fields this engine accepts."""
    return _UNDERSTOOD


def emit(
    spec: Engine, source: Path, target: Path, fmt: str, opts: RenderOptions
) -> Path:
    """Render ``source`` as a submission draft for ``opts.journal_id``.

    Args:
        spec: The engine row.
        source: The manuscript source.
        target: Where the draft goes.
        fmt: One of the engine's formats; already validated upstream.
        opts: Must carry a journal id.

    Returns:
        ``target``.

    Raises:
        ValueError: When no journal id was given. Measured: an empty id
            reaches ``profile("")`` and comes back as a bare ``KeyError:
            ''``, which tells the reader nothing about what they failed
            to choose. A journal draft with no journal is not a default
            this library is entitled to invent.
        BackendUnavailableError: When the engine is not installed.
    """
    if not opts.journal_id:
        raise ValueError(
            f"{spec.label} needs a journal profile: a submission draft "
            f"takes its shape from the journal, so there is no sensible "
            f"default. Pass journal_id."
        )
    module = load_backend(spec.module, why=f"rendering through {spec.label}")
    factory: Any = module.Paper
    document: Any = factory.from_file(source)
    document.to_draft(opts.journal_id, target, fmt=fmt)
    return target
