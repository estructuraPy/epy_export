"""Driving a headless Qt WebEngine print, once instead of twice.

epy_reports and epy_slides each print a page to PDF through an offscreen
``QWebEngineView``, and the documents they print are genuinely different
-- Paged.js with a two-pass page-number injection on one side, reveal.js
in print mode on the other. Those renderers stay where they are.

What was reimplemented on both sides, and is here, is the plumbing: the
event-loop pump, the JavaScript round trip, the waits, and the temporary
file. Reimplemented, not copied -- which is worse, because the two
versions DIVERGED and one of them was wrong.

**A clock per wait, which is the slides semantics and not the reports
one.** Sharing a single ``QElapsedTimer`` across load, readiness and
print makes every later budget the leftover of the earlier stage, so a
slow load silently buys the readiness wait nothing. What that produces
is a deck of one blank page, reported as a success -- because printing
nothing IS a successful print, and a file-exists check cannot tell the
difference. Folding onto the reports version would re-import that.

**The readiness check ASSERTS.** A wait that times out and then prints
anyway is not a guard. Callers pass their own readiness expression; this
module only guarantees that failing it raises instead of printing.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = [
    "eval_js",
    "print_to_pdf",
    "pump",
    "readiness_report",
    "remove_temp",
    "wait_until",
]


def pump(app: Any, ms: int) -> None:
    """Run the event loop for ``ms`` milliseconds.

    Args:
        app: The ``QApplication``.
        ms: How long to spin.
    """
    from PySide6.QtCore import QElapsedTimer, QEventLoop  # noqa: PLC0415

    clock = QElapsedTimer()
    clock.start()
    while clock.elapsed() < ms:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)


def eval_js(
    app: Any, page: Any, expr: str, *, timeout_ms: int = 4000
) -> object:
    """Evaluate ``expr`` in the page and return its result.

    Args:
        app: The ``QApplication``.
        page: The ``QWebEnginePage``.
        expr: JavaScript to evaluate.
        timeout_ms: How long to wait for the answer.

    Returns:
        Whatever the expression evaluated to, or None on timeout. Note
        that JavaScript ``undefined`` also arrives as None, so a caller
        distinguishing "not answered" from "undefined" must ask for an
        expression that cannot be undefined.
    """
    from PySide6.QtCore import QElapsedTimer, QEventLoop  # noqa: PLC0415

    box: dict[str, object] = {"value": None}
    page.runJavaScript(expr, lambda v: box.__setitem__("value", v))
    clock = QElapsedTimer()
    clock.start()
    while box["value"] is None and clock.elapsed() < timeout_ms:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
    return box["value"]


def wait_until(
    app: Any, predicate: Callable[[], bool], *, timeout_ms: int
) -> bool:
    """Spin the event loop until ``predicate`` holds or the budget ends.

    Its OWN clock, started here. That is the whole point of the function
    existing: a caller that reuses one timer across several waits gives
    the later ones whatever the earlier ones left, which is how a wait
    silently gets no budget at all.

    Args:
        app: The ``QApplication``.
        predicate: Checked between pumps.
        timeout_ms: This wait's budget, in full.

    Returns:
        Whether the predicate held before the budget ran out. The caller
        decides what a False means; this module never prints on one.
    """
    from PySide6.QtCore import QElapsedTimer, QEventLoop  # noqa: PLC0415

    clock = QElapsedTimer()
    clock.start()
    while clock.elapsed() < timeout_ms:
        if predicate():
            return True
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
    return predicate()


def print_to_pdf(
    app: Any, page: Any, out_path: Path, layout: Any, *, timeout_ms: int
) -> bool:
    """Print the loaded page and wait, on this wait's own clock.

    Args:
        app: The ``QApplication``.
        page: The ``QWebEnginePage``, already loaded and ready.
        out_path: Where the PDF goes.
        layout: The ``QPageLayout``.
        timeout_ms: This wait's budget.

    Returns:
        What the engine reported. Note that it reports success for a
        blank page too, so the caller must have established readiness
        BEFORE calling this -- success here is not evidence of content.
    """
    state = {"printed": False, "ok": False}

    def on_printed(_path: str, ok: bool) -> None:
        state["ok"] = ok
        state["printed"] = True

    page.pdfPrintingFinished.connect(on_printed)
    page.printToPdf(str(out_path), layout)
    wait_until(app, lambda: state["printed"], timeout_ms=timeout_ms)
    return bool(state["ok"])


def readiness_report(js: Callable[[str], object]) -> str:
    """Say which readiness signal never came up.

    Reached only on failure, so four extra JS round-trips cost nothing
    that matters, and the message is the difference between "the deck
    came out blank" and knowing whether reveal, MathJax, the diagrams
    or the per-page wrappers were the one still missing.
    """
    parts = [
        f"window.{flag}={js('window.' + flag)!r}"
        for flag in ("_reveal_done", "_mathjax_done", "_diagrams_done")
    ]
    count = js('document.querySelectorAll(".pdf-page").length')
    parts.append(f"pdf-page count={count!r}")
    return "deck never became ready to print (" + ", ".join(parts) + ")"


def remove_temp(tmp: Path, pump: Callable[[int], None]) -> None:
    """Delete the staged HTML, waiting for the engine to release it.

    On Windows the web engine can still hold the file it loaded some
    hundreds of milliseconds after the view is scheduled for deletion.
    The unlink then raises WinError 32 from inside a ``finally``, which
    REPLACES whatever the export was about to report: a real render
    failure surfaced as a file-locking error. Measured on a 3 MB deck,
    that is exactly how one blank export was reported.

    Retry briefly, then give up quietly. A leftover temporary file is
    not worth losing the outcome over.
    """
    for _ in range(20):
        try:
            tmp.unlink(missing_ok=True)
            return
        except OSError:
            pump(100)
