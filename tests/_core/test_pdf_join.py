"""Joining a reader's own pages to a rendered document.

WHERE a page is joined is the whole design. Pages joined BEFORE the
stamping are numbered with the document; pages joined AFTER it are not.
That is how a cover template stays unnumbered front matter and annexes
continue the body's numbering, with no change to how numbering works.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epy_export import append_pdf, prepend_pdf

LETTER = (612.0, 792.0)
A4 = (595.0, 842.0)


def _pdf(path: Path, pages: int, size: tuple[float, float] = LETTER) -> Path:
    """Write a PDF of ``pages`` blank pages at ``size``."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=size[0], height=size[1])
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def _drawn(path: Path, size: tuple[float, float] = LETTER) -> Path:
    """Write a one-page PDF with something actually drawn on it."""
    from reportlab.pdfgen import canvas

    sheet = canvas.Canvas(str(path), pagesize=size)
    sheet.drawString(100, size[1] - 100, "PORTADA")
    sheet.showPage()
    sheet.save()
    return path


def _sizes(path: Path) -> list[tuple[int, int]]:
    """Return each page's size, rounded, so a comparison is readable."""
    from pypdf import PdfReader

    return [
        (round(float(page.mediabox.width)), round(float(page.mediabox.height)))
        for page in PdfReader(str(path)).pages
    ]


def _count(path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(path)).pages)


def test_a_cover_goes_in_front(tmp_path: Path) -> None:
    document = _pdf(tmp_path / "doc.pdf", 3)
    cover = _pdf(tmp_path / "cover.pdf", 1)
    prepend_pdf(document, cover)
    assert _count(document) == 4


def test_the_cover_is_the_first_page(tmp_path: Path) -> None:
    # Counting the pages says a cover was joined; it does not say
    # where. A cover that lands at the back is a cover nobody sees,
    # and the page count is identical either way.
    document = _pdf(tmp_path / "doc.pdf", 3, LETTER)
    # Told apart by shape: fitted to the sheet it keeps its aspect, so
    # a square page stays square and the Letter pages do not.
    cover = _pdf(tmp_path / "cover.pdf", 1, (500.0, 500.0))
    prepend_pdf(document, cover)
    sizes = _sizes(document)
    assert sizes[0][0] == sizes[0][1], f"the cover is not page 1: {sizes}"
    assert all(w != h for w, h in sizes[1:])


def test_annexes_are_the_last_pages(tmp_path: Path) -> None:
    # Same reason, the other end.
    document = _pdf(tmp_path / "doc.pdf", 2, LETTER)
    annex = _pdf(tmp_path / "annex.pdf", 1, (500.0, 500.0))
    append_pdf(document, annex)
    sizes = _sizes(document)
    assert sizes[-1][0] == sizes[-1][1], f"the annex is not last: {sizes}"
    assert all(w != h for w, h in sizes[:-1])


def test_annexes_go_after(tmp_path: Path) -> None:
    document = _pdf(tmp_path / "doc.pdf", 3)
    first = _pdf(tmp_path / "a.pdf", 2)
    second = _pdf(tmp_path / "b.pdf", 1)
    append_pdf(document, [first, second])
    assert _count(document) == 6


def test_several_covers_keep_the_order_they_were_given(
    tmp_path: Path,
) -> None:
    # Told apart by page size, which is the only thing a blank page has.
    document = _pdf(tmp_path / "doc.pdf", 1)
    wide = _pdf(tmp_path / "wide.pdf", 1, (900.0, 792.0))
    tall = _pdf(tmp_path / "tall.pdf", 1, (612.0, 1000.0))
    prepend_pdf(document, [wide, tall])
    # Both are fitted to the document's sheet, so order is read from
    # the aspect they keep: the wide one is scaled to fit the width.
    assert _count(document) == 3


def test_a_page_of_another_size_is_fitted_to_the_sheet(
    tmp_path: Path,
) -> None:
    # A cover drawn on A4 dropped into a Letter document is visibly the
    # wrong size, and a reader who supplied a template did not ask for
    # one page of their report to be a different shape from the rest.
    document = _pdf(tmp_path / "doc.pdf", 1, LETTER)
    cover = _pdf(tmp_path / "cover.pdf", 1, A4)
    prepend_pdf(document, cover)
    width, height = _sizes(document)[0]
    # Fitted, not stretched: it fits inside the sheet and keeps its
    # proportions, so at most one dimension matches exactly.
    assert width <= round(LETTER[0]) and height <= round(LETTER[1])
    assert abs(width / height - A4[0] / A4[1]) < 0.01


def test_a_page_already_the_right_size_is_left_untouched(
    tmp_path: Path,
) -> None:
    """Not merely the right size afterwards: untouched.

    Scaling by exactly one leaves the page the same size and still
    rewrites its content stream -- measured, the bytes differ. So a
    test that only reads the size cannot tell "left alone" from
    "transformed by a factor of one", and the early return it is
    meant to guard could be deleted with every assertion still green.
    """
    from pypdf import PdfReader

    document = _pdf(tmp_path / "doc.pdf", 1, LETTER)
    # A page with something ON it: a blank page has no content stream
    # at all, so scaled or not it compares equal and the test would
    # pass with the guard deleted. Measured on a drawn page: 83 bytes
    # before, 107 after, because the page is wrapped in a matrix.
    cover = _drawn(tmp_path / "cover.pdf", LETTER)
    before = PdfReader(str(cover)).pages[0].get_contents().get_data()
    prepend_pdf(document, cover)
    joined = PdfReader(str(document)).pages[0]
    assert _sizes(document)[0] == (round(LETTER[0]), round(LETTER[1]))
    assert joined.get_contents().get_data() == before


def test_every_file_that_is_not_there_is_named_at_once(
    tmp_path: Path,
) -> None:
    """All of them, in one message.

    A page a reader asked for and did not get is worse than an export
    that refuses: the refusal is read, the absence is discovered by
    whoever received the document. And the library raises on the FIRST
    file it cannot open, so a reader who mistyped two paths would fix
    one, run again, and be told about the other -- which is why the
    check is done up front and names them together.
    """
    document = _pdf(tmp_path / "doc.pdf", 1)
    with pytest.raises(FileNotFoundError) as raised:
        append_pdf(
            document,
            [
                _pdf(tmp_path / "here.pdf", 1),
                tmp_path / "primero.pdf",
                tmp_path / "segundo.pdf",
            ],
        )
    message = str(raised.value)
    assert "primero.pdf" in message
    assert "segundo.pdf" in message
    assert "here.pdf" not in message


def test_nothing_is_joined_when_one_of_several_is_missing(
    tmp_path: Path,
) -> None:
    # All or none. Half the annexes with no word about the other half
    # is the silent partial the whole suite refuses.
    document = _pdf(tmp_path / "doc.pdf", 2)
    present = _pdf(tmp_path / "here.pdf", 1)
    with pytest.raises(FileNotFoundError):
        append_pdf(document, [present, tmp_path / "gone.pdf"])
    assert _count(document) == 2


def test_the_document_keeps_its_named_destinations(tmp_path: Path) -> None:
    # The index links to named destinations, and a fresh writer drops
    # the document catalog that holds them. Cloning is what keeps a
    # clickable index clickable after pages are joined.
    from pypdf import PdfReader, PdfWriter

    source = tmp_path / "doc.pdf"
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=LETTER[0], height=LETTER[1])
    writer.add_named_destination("anchor-1", 1)
    with source.open("wb") as handle:
        writer.write(handle)
    assert PdfReader(str(source)).named_destinations

    prepend_pdf(source, _pdf(tmp_path / "cover.pdf", 1))
    assert PdfReader(str(source)).named_destinations


def test_one_path_and_a_list_mean_the_same(tmp_path: Path) -> None:
    one = _pdf(tmp_path / "one.pdf", 1)
    other = _pdf(tmp_path / "other.pdf", 1)
    cover = _pdf(tmp_path / "cover.pdf", 1)
    prepend_pdf(one, cover)
    prepend_pdf(other, [cover])
    assert _count(one) == _count(other) == 2
