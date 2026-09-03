"""Atomic saves, and why every editor needs a sibling temporary file.

The three editors used to save a document with the identical line
``self._path.write_text(...)``. Writing into place means a process that
dies mid-write leaves the document truncated on disk, and that
truncated file is the only copy. The helper under test writes a
complete sibling first and then asks the filesystem to swap it into
place, so the final path is either the old complete document or the new
one -- never a fraction of one.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from epy_export import write_text_atomic
from epy_export._core import _files


def test_write_text_atomic_leaves_exact_content_at_path(
    tmp_path: Path,
) -> None:
    # An editor opening the file again expects exactly the text it had
    # in memory. If newlines are translated on Windows or the encoding
    # is ignored, a slide deck or paper is corrupted after every save.
    target = tmp_path / "report.md"
    text = "α\nβ\n"

    write_text_atomic(target, text, encoding="utf-8")

    assert target.read_text(encoding="utf-8") == text
    assert [p.name for p in tmp_path.iterdir()] == ["report.md"]


def test_write_text_atomic_stages_a_sibling_and_replaces_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Atomic replacement only works when the temporary file lives on
    # the same filesystem as the destination. Moving a file from
    # another directory would fall back to copy+delete and could leave
    # the same truncation window the helper exists to close.
    target = tmp_path / "deck.html"
    swaps: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def _spy_replace(src: os.PathLike[str], dst: os.PathLike[str]) -> None:
        swaps.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(_files.os, "replace", _spy_replace)

    write_text_atomic(target, "deck", encoding="utf-8")

    src, dst = swaps[0]
    assert src.parent == target.parent
    assert src.name.startswith(f".{target.name}.")
    assert src.name.endswith(".tmp")
    assert dst == target
    assert target.read_text(encoding="utf-8") == "deck"
    assert not src.exists()


def test_failed_replace_leaves_the_original_document_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This is the control. A helper that wrote straight into path would
    # pass every test above; only this one catches the truncation that
    # prompted the helper in the first place.
    target = tmp_path / "paper.tex"
    original = "last good save\n"
    target.write_text(original, encoding="utf-8")

    def _explode_replace(
        _src: os.PathLike[str], _dst: os.PathLike[str]
    ) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(_files.os, "replace", _explode_replace)

    with pytest.raises(OSError, match="replace failed"):
        write_text_atomic(target, "truncated", encoding="utf-8")

    assert target.read_text(encoding="utf-8") == original
    assert [p.name for p in tmp_path.iterdir()] == ["paper.tex"]


def test_temp_name_is_unique_and_cleaned_up_on_failed_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Autosave fires repeatedly. If two attempts reused the same
    # temporary name, a stale file from a previous crash could be
    # mistaken for a document; if a failed attempt litters a .tmp file,
    # the folder fills with names the user never chose.
    target = tmp_path / "slides.html"
    target.write_text("old", encoding="utf-8")
    seen: list[Path] = []

    def _explode_replace(
        src: os.PathLike[str], _dst: os.PathLike[str]
    ) -> None:
        seen.append(Path(src))
        raise OSError("replace failed")

    monkeypatch.setattr(_files.os, "replace", _explode_replace)

    for _ in range(2):
        with pytest.raises(OSError, match="replace failed"):
            write_text_atomic(target, "new", encoding="utf-8")

    assert seen[0] != seen[1]
    assert target.read_text(encoding="utf-8") == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["slides.html"]


def test_missing_parent_directory_raises_and_is_not_created(
    tmp_path: Path,
) -> None:
    # A vanished save target is an unplugged drive, not a typo. An
    # editor must surface the error instead of silently creating a new
    # folder beside the old one and saving into the wrong place.
    target = tmp_path / "gone" / "doc.txt"

    with pytest.raises(OSError):
        write_text_atomic(target, "x", encoding="utf-8")

    assert not (tmp_path / "gone").exists()
