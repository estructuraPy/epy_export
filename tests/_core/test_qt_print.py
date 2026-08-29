"""The waits, and why each one owns its clock.

No Qt here. Every function takes the application and the page as
arguments, so a fake that counts pumps and answers JavaScript is enough
to state the property that matters -- and the property that matters is
about budgets, not about Chromium.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epy_export._core import _qt_print
from epy_export._core._runtime import pin_system_icu

# The waits use QElapsedTimer, and in a conda environment Qt does not
# import at all until ICU is pinned -- which is exactly what that
# function is for. Calling it here is the demonstration: measured, the
# import below fails with WinError 127 without this line and succeeds
# with it. importorskip stays as the honest answer for a machine with
# no PySide6 at all.
pin_system_icu()
pytest.importorskip("PySide6.QtCore", exc_type=ImportError)


class _FakeApp:
    """Counts how many times the loop was pumped."""

    def __init__(self) -> None:
        self.pumps = 0

    def processEvents(self, *_a: object, **_k: object) -> None:  # noqa: N802
        self.pumps += 1


class _FakeSignal:
    def __init__(self) -> None:
        self.slot = None

    def connect(self, slot: object) -> None:
        self.slot = slot


class _FakePage:
    """Answers JavaScript, and prints when asked."""

    def __init__(self, *, ready_after: int = 0, prints_ok: bool = True):
        self.pdfPrintingFinished = _FakeSignal()  # noqa: N815 (Qt name)
        self.asked = 0
        self.printed_to: Path | None = None
        self._ready_after = ready_after
        self._prints_ok = prints_ok

    def runJavaScript(self, _expr: str, callback) -> None:  # noqa: N802
        self.asked += 1
        callback(self.asked > self._ready_after)

    def printToPdf(self, path: str, _layout: object) -> None:  # noqa: N802
        self.printed_to = Path(path)
        if self.pdfPrintingFinished.slot is not None:
            self.pdfPrintingFinished.slot(path, self._prints_ok)


def test_a_wait_that_is_already_true_returns_at_once() -> None:
    app = _FakeApp()
    assert _qt_print.wait_until(app, lambda: True, timeout_ms=5000)


def test_a_wait_that_never_holds_reports_false() -> None:
    app = _FakeApp()
    assert not _qt_print.wait_until(app, lambda: False, timeout_ms=60)


def test_each_wait_starts_its_own_clock() -> None:
    # The property this module exists for. One shared QElapsedTimer made
    # every later budget the leftover of the earlier stage, so a slow
    # load bought the readiness wait nothing -- and what that produces
    # is a deck of one blank page reported as a success, because
    # printing nothing IS a successful print.
    #
    # Stated without measuring wall-clock: two waits that each fail in
    # turn must EACH have pumped, which is only true if the second got
    # a budget of its own.
    app = _FakeApp()
    _qt_print.wait_until(app, lambda: False, timeout_ms=60)
    after_first = app.pumps
    assert after_first > 0
    _qt_print.wait_until(app, lambda: False, timeout_ms=60)
    assert app.pumps > after_first


def test_javascript_answers_come_back() -> None:
    app, page = _FakeApp(), _FakePage()
    assert _qt_print.eval_js(app, page, "window.ready") is True


def test_printing_reports_what_the_engine_reported() -> None:
    app, page = _FakeApp(), _FakePage()
    assert _qt_print.print_to_pdf(
        app, page, Path("out.pdf"), object(), timeout_ms=500
    )
    assert page.printed_to == Path("out.pdf")


def test_a_refused_print_reports_false() -> None:
    app, page = _FakeApp(), _FakePage(prints_ok=False)
    assert not _qt_print.print_to_pdf(
        app, page, Path("out.pdf"), object(), timeout_ms=500
    )


def test_a_held_temporary_file_is_retried_then_given_up_on(
    tmp_path: Path,
) -> None:
    # On Windows the engine can still hold the HTML it loaded when the
    # unlink runs, and an OSError raised inside a finally REPLACES what
    # the export was about to report: a blank render once surfaced as
    # WinError 32, sending the reader after a file-locking problem that
    # was not the defect.
    staged = tmp_path / "deck.tmp.html"
    staged.write_text("x", encoding="utf-8")
    _qt_print.remove_temp(staged, lambda _ms: None)
    assert not staged.exists()


def test_giving_up_on_the_temporary_file_raises_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = tmp_path / "held.tmp.html"
    staged.write_text("x", encoding="utf-8")
    calls: list[int] = []

    def _locked(_self: Path, missing_ok: bool = False) -> None:
        raise OSError(32, "held by another process")

    monkeypatch.setattr(Path, "unlink", _locked)
    _qt_print.remove_temp(staged, calls.append)
    # It tried, and it stayed quiet. A leftover temporary file is not
    # worth losing the outcome over -- an OSError from inside a finally
    # replaces whatever the export was about to report.
    assert calls, "it did not retry at all"
