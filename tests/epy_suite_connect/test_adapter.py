"""What the dispatcher refuses, and what it lets through."""

from __future__ import annotations

from pathlib import Path

import pytest

from epy_export import RenderOptions, render
from epy_export.epy_suite_connect._adapters import _adapter


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "doc.md"
    path.write_text("# Title\n\ntext\n", encoding="utf-8")
    return path


def test_a_format_the_engine_cannot_make_is_refused_by_name(
    source: Path, tmp_path: Path
) -> None:
    # Refused, never skipped: silently producing two of three requested
    # files is how a caller comes to believe it has a .docx it never got.
    with pytest.raises(ValueError) as raised:
        render(
            source, tmp_path, engine_id="slides", formats=("docx",)
        )
    message = str(raised.value)
    assert "docx" in message
    assert "pptx" in message


def test_no_format_at_all_is_refused(source: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        render(source, tmp_path, engine_id="reports", formats=())


def test_a_missing_source_is_refused_before_anything_is_imported(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="not a file"):
        render(
            tmp_path / "absent.md",
            tmp_path,
            engine_id="reports",
            formats=("pdf",),
        )


def test_an_option_another_engine_reads_is_refused_by_name(
    source: Path, tmp_path: Path
) -> None:
    # A journal profile passed to ePy Reports used to be dropped in
    # silence, so a caller who believed they had asked for a journal
    # draft received a report and no signal.
    with pytest.raises(ValueError) as raised:
        render(
            source,
            tmp_path,
            engine_id="reports",
            formats=("pdf",),
            options=RenderOptions(journal_id="jse"),
        )
    message = str(raised.value)
    assert "journal_id" in message
    assert "papers" in message


def test_an_option_this_engine_does_read_is_accepted(
    source: Path, tmp_path: Path
) -> None:
    # The control. Without it, refusing every option satisfies the test
    # above and no caller can set anything.
    assert "appearance" in _adapter.understood_by("reports")
    assert "author" in _adapter.understood_by("docs")
    assert "journal_id" in _adapter.understood_by("papers")


def test_a_misspelled_appearance_is_refused(
    source: Path, tmp_path: Path
) -> None:
    # It otherwise reaches the engine, which falls back to its own
    # default, and the document arrives looking almost right.
    with pytest.raises(ValueError, match="corporat"):
        render(
            source,
            tmp_path,
            engine_id="reports",
            formats=("pdf",),
            options=RenderOptions(appearance="corporat"),
        )


def test_an_absent_engine_is_named_with_what_to_install(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_adapter, "available", lambda _id: False)
    with pytest.raises(_adapter.EngineUnavailableError) as raised:
        render(source, tmp_path, engine_id="reports", formats=("pdf",))
    assert "epy_reports" in str(raised.value)


def test_papers_refuses_to_invent_a_journal(
    source: Path, tmp_path: Path
) -> None:
    # Measured: an empty id reaches profile("") and comes back as a bare
    # KeyError: '', which tells the reader nothing about what they did
    # not choose.
    with pytest.raises(ValueError, match="journal"):
        render(source, tmp_path, engine_id="papers", formats=("pdf",))


def test_every_engine_has_exactly_one_adapter() -> None:
    from epy_export import engine_ids

    assert set(_adapter._ADAPTERS) == set(engine_ids())
