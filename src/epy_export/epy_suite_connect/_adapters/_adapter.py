"""Render one document, through whichever engine was chosen.

What is left of the dispatcher once every engine has its own adapter:
validate, make the directory, delegate, check something arrived. The
``if engine_id == "papers"`` / ``== "docs"`` chain it used to carry is
gone -- not by making the engines alike, which they are not, but by
letting each say its own shape in its own module.

What deliberately did NOT move here from the application it came from:
choosing an engine from a prompt, the default engine, and the refusal to
render a review checklist. Those are one application's policy over its
own prompt library. A neutral export library has no concept of "the
review checklist", and the day it grows one it will be wrong for
somebody.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..._core._backends import backend_present
from .._contract._engine import (
    APPEARANCES,
    Engine,
    EngineUnavailableError,
    RenderOptions,
)
from .._data._catalog import ENGINES, engine
from . import _docs, _from_file, _papers

__all__ = ["available", "installed", "render", "understood_by"]

# Static, never importlib on a computed name: a dynamic import here is
# invisible to PyInstaller's dependency graph, and the adapter would
# simply be missing from a frozen build. The BACKENDS stay dynamic --
# they are meant to be absent.
_ADAPTERS = {
    "reports": _from_file,
    "slides": _from_file,
    "papers": _papers,
    "docs": _docs,
}


def understood_by(engine_id: str) -> tuple[str, ...]:
    """Return the option fields this engine reads."""
    return tuple(_ADAPTERS[engine(engine_id).engine_id].understands())


def available(engine_id: str) -> bool:
    """Report whether this engine can be reached on this machine.

    Cheap on purpose: it answers "should I offer this?" while a menu is
    being built, and importing an engine to find out whether it exists
    pulls its whole stack in to draw a menu item.
    """
    return backend_present(engine(engine_id).module)


def installed() -> tuple[str, ...]:
    """Return the ids of every engine present, in offer order."""
    return tuple(
        item.engine_id for item in ENGINES if available(item.engine_id)
    )


def _refuse_foreign_options(spec: Engine, opts: RenderOptions) -> None:
    """Raise when an option was set that this engine cannot read.

    Args:
        spec: The chosen engine.
        opts: What the caller passed.

    Raises:
        ValueError: Naming the field AND the engine that reads it. A
            journal profile passed to ePy Reports used to be dropped in
            silence, so a caller who believed they had asked for a
            journal draft received a report and no signal.
    """
    understood = set(understood_by(spec.engine_id))
    foreign = [
        name for name in opts.named_fields() if name not in understood
    ]
    if not foreign:
        return
    elsewhere = {
        name: ", ".join(
            item.engine_id
            for item in ENGINES
            if name in understood_by(item.engine_id)
        )
        for name in foreign
    }
    detail = "; ".join(
        f"{name} is read by {who or 'no engine'}"
        for name, who in elsewhere.items()
    )
    raise ValueError(
        f"{spec.label} does not read {', '.join(foreign)}. {detail}."
    )


def render(
    source: Path,
    output_dir: Path,
    *,
    engine_id: str,
    formats: Sequence[str],
    options: RenderOptions | None = None,
) -> list[Path]:
    """Render one document and return what was produced.

    Args:
        source: The source document.
        output_dir: Where the results go; created when absent.
        engine_id: Which engine to use.
        formats: Which formats to produce. A format the engine cannot
            make is refused BY NAME rather than skipped: silently
            producing two of three requested files is how a caller comes
            to believe it has a .docx it never got.
        options: Appearance, journal, cover metadata. An option this
            engine does not read is refused, for the same reason.

    Returns:
        One path per format produced, in the order requested.

    Raises:
        ValueError: When the source is not a file, no format was asked
            for, a format is outside this engine's set, or an option
            belongs to another engine.
        EngineUnavailableError: When the engine is not installed.
        RenderFailedError: When it ran and produced nothing sound.
    """
    spec = engine(engine_id)
    opts = options or RenderOptions()
    if not source.is_file():
        raise ValueError(f"source is not a file: {source}")
    unsupported = [item for item in formats if item not in spec.formats]
    if not formats or unsupported:
        offered = ", ".join(spec.formats)
        asked = ", ".join(sorted(unsupported)) or "(none)"
        raise ValueError(
            f"{spec.label} cannot produce {asked}; it produces {offered}."
        )
    if opts.appearance and spec.themed:
        _refuse_unknown_appearance(spec, opts.appearance)
    _refuse_foreign_options(spec, opts)
    if not available(engine_id):
        raise EngineUnavailableError(
            f"{spec.label} is not installed, so this document cannot be "
            f"rendered through it. Install {spec.module}, or choose "
            f"another engine."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    adapter = _ADAPTERS[spec.engine_id]
    if adapter is _docs:
        return _docs.emit_all(spec, source, output_dir, formats, opts)
    produced: list[Path] = []
    for fmt in formats:
        target = output_dir / f"{source.stem}.{fmt}"
        adapter.emit(spec, source, target, fmt, opts)
        # The engine can report success and write nothing. Checking here
        # rather than trusting the return is the same lesson the LaTeX
        # log scan records, applied to every engine.
        if not target.is_file():
            raise EngineUnavailableError(
                f"{spec.label} reported success but wrote no {fmt} at "
                f"{target}."
            )
        produced.append(target)
    return produced


def _refuse_unknown_appearance(spec: Engine, appearance: str) -> None:
    """Raise when the appearance is not one the family publishes.

    Args:
        spec: The chosen engine.
        appearance: The layout name asked for.

    Raises:
        ValueError: Naming what is offered. A misspelled layout
            otherwise reaches the engine, which falls back to its own
            default, and the document arrives looking almost right.
    """
    if appearance in APPEARANCES:
        return
    raise ValueError(
        f"{spec.label} has no appearance {appearance!r}; the family "
        f"offers: {', '.join(APPEARANCES)}."
    )
