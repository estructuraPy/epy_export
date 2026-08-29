"""The boundary through which this library reaches its sibling engines.

Everything under here names epy_reports, epy_slides, epy_papers or
epy_docs. Nothing outside it does. That is the suite's own convention
(``epy_suite_connect`` is the sole cross-library boundary), and here it
carries its full weight: this library exists to BE that boundary for the
four applications, so the line has to be visible.

The three concerns are separated as the standard describes: what an
engine is (``_contract``), which engines exist (``_data``), and how each
one is actually driven (``_adapters``). One adapter per producing
sibling is what let the dispatcher stop asking which engine it was
holding.
"""

from __future__ import annotations

__all__ = ["get_suite_info"]


def get_suite_info() -> dict[str, str]:
    """Return package metadata for the cross-suite registry."""
    import epy_export as _pkg  # noqa: PLC0415

    return {
        "pkg": "epy_export",
        "version": getattr(_pkg, "__version__", "0.0.0"),
        "author": getattr(_pkg, "__author__", ""),
    }
