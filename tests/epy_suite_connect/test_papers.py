"""The papers (journal-draft) adapter.

ePy Papers is not installed in this environment, so ``emit()`` is
exercised against a stand-in module returned by a mocked
``load_backend``. ``understands()`` and the "no journal" refusal are
already covered in ``test_adapter.py``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from epy_export.epy_suite_connect._adapters import _papers
from epy_export.epy_suite_connect._contract._engine import (
    Engine,
    RenderOptions,
)


def _engine() -> Engine:
    return Engine(
        engine_id="papers",
        label="ePy Papers",
        module="epy_papers",
        formats=("pdf", "docx"),
        themed=False,
        purpose="x",
    )


def test_emit_stages_the_source_and_drafts_for_the_chosen_journal(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    drafted: list[tuple[str, object, str]] = []

    class _Paper:
        @staticmethod
        def from_file(_source: object) -> _Paper:
            return _Paper()

        @staticmethod
        def to_draft(journal_id: str, target: object, fmt: str) -> None:
            drafted.append((journal_id, target, fmt))

    monkeypatch.setattr(
        _papers,
        "load_backend",
        lambda *_a, **_k: SimpleNamespace(Paper=_Paper),
    )
    monkeypatch.setattr(
        _papers, "staged_for_latex", lambda source, _out_dir: (source, 0)
    )
    source = tmp_path / "manuscript.md"
    source.write_text("# Manuscript\n", encoding="utf-8")
    target = tmp_path / "manuscript.pdf"

    result = _papers.emit(
        _engine(), source, target, "pdf", RenderOptions(journal_id="jse")
    )

    assert result == target
    assert drafted == [("jse", target, "pdf")]
