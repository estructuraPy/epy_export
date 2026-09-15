"""The from-file adapter shared by ePy Reports and ePy Slides.

Neither sibling package is installed in this environment, so ``emit()``
is exercised against a stand-in module returned by a mocked
``load_backend`` -- the real boundary this adapter crosses.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from epy_export.epy_suite_connect._adapters import _from_file
from epy_export.epy_suite_connect._contract._engine import (
    Engine,
    RenderOptions,
)


def _engine(**overrides: object) -> Engine:
    defaults: dict[str, object] = {
        "engine_id": "reports",
        "label": "ePy Reports",
        "module": "epy_reports",
        "formats": ("pdf", "docx", "html"),
        "themed": True,
        "purpose": "x",
    }
    defaults.update(overrides)
    return Engine(**defaults)


def test_a_themed_engine_opens_with_the_chosen_appearance(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    written: list[object] = []

    class _Document:
        @staticmethod
        def to_pdf(target: object) -> None:
            written.append(target)

    class _Report:
        @staticmethod
        def from_file(_source: object, theme: str | None = None) -> object:
            assert theme == "classic"
            return _Document()

    monkeypatch.setattr(
        _from_file,
        "load_backend",
        lambda *_a, **_k: SimpleNamespace(Report=_Report),
    )
    source = tmp_path / "doc.md"
    target = tmp_path / "doc.pdf"

    result = _from_file.emit(
        _engine(), source, target, "pdf", RenderOptions(appearance="classic")
    )

    assert result == target
    assert written == [target]


def test_an_unthemed_engine_opens_without_a_theme(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # No engine in the real catalog uses this adapter unthemed (reports
    # and slides both set themed=True), but the adapter's own contract
    # supports it -- exercised directly against a synthetic engine row
    # rather than left unmeasured because today's catalog never asks.
    class _Document:
        @staticmethod
        def to_html(target) -> None:
            target.write_text("x", encoding="utf-8")

    class _SlideDeck:
        @staticmethod
        def from_file(_source: object) -> object:
            return _Document()

    monkeypatch.setattr(
        _from_file,
        "load_backend",
        lambda *_a, **_k: SimpleNamespace(SlideDeck=_SlideDeck),
    )
    source = tmp_path / "deck.md"
    target = tmp_path / "deck.html"

    result = _from_file.emit(
        _engine(engine_id="slides", themed=False),
        source, target, "html", RenderOptions(),
    )

    assert result == target
    assert target.is_file()
