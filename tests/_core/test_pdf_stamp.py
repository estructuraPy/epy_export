"""What every stamper must not destroy.

The module's docstring is about one invariant: each stamper clones the
source document, because a fresh ``PdfWriter`` fed page by page drops
the catalog -- and with it the outline and the named destinations every
internal link resolves through. The links stay visible and stop working.

That invariant was asserted in one place, for one stamper. Here it is
asserted for all of them.

**On the fixture.** The named destinations the docstring names are the
ones Chromium emits for anchored headings, and reportlab does not write
a ``/Names /Dests`` tree at all -- measured, when the control test below
caught a fixture whose destination set was empty and would therefore
have let every stamper pass by comparing nothing to nothing. What
reportlab does write is an outline, which lives in the same catalog and
is destroyed by the same mistake. So the outline is what is asserted
here, and the control is what keeps that honest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epy_export._core import _pdf_stamp

pypdf = pytest.importorskip("pypdf")
pytest.importorskip("reportlab")


@pytest.fixture
def outlined_pdf(tmp_path: Path) -> Path:
    """A three-page PDF whose catalog carries an outline."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path = tmp_path / "outlined.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for number in range(3):
        pdf.bookmarkPage(f"sec-{number}")
        pdf.addOutlineEntry(f"Section {number}", f"sec-{number}", level=0)
        pdf.drawString(72, 720, f"Section {number}")
        pdf.showPage()
    pdf.save()
    return path


@pytest.fixture
def stamp_png(tmp_path: Path) -> Path:
    """A small opaque image to watermark with."""
    from PIL import Image

    path = tmp_path / "mark.png"
    Image.new("RGB", (64, 64), (128, 128, 128)).save(path)
    return path


def _outline_titles(path: Path) -> list[str]:
    reader = pypdf.PdfReader(str(path))
    return [
        str(item.get("/Title", ""))
        for item in reader.outline
        if isinstance(item, dict)
    ]


def test_the_fixture_actually_carries_an_outline(outlined_pdf: Path) -> None:
    # The control that makes every test below mean something. Written
    # first, and it earned its place immediately: the original fixture
    # asserted named destinations, reportlab writes none, and every
    # other test in this file passed by comparing an empty set to an
    # empty set.
    assert _outline_titles(outlined_pdf) == [
        "Section 0",
        "Section 1",
        "Section 2",
    ]


def test_metadata_keeps_the_outline(outlined_pdf: Path) -> None:
    before = _outline_titles(outlined_pdf)
    _pdf_stamp.add_metadata(
        outlined_pdf,
        title="T",
        creator="epy_export tests",
        producer="epy_export tests",
    )
    assert _outline_titles(outlined_pdf) == before


def test_watermark_keeps_the_outline(
    outlined_pdf: Path, stamp_png: Path
) -> None:
    before = _outline_titles(outlined_pdf)
    _pdf_stamp.add_watermark(outlined_pdf, stamp_png)
    assert _outline_titles(outlined_pdf) == before


def test_background_keeps_the_outline(outlined_pdf: Path) -> None:
    before = _outline_titles(outlined_pdf)
    _pdf_stamp.add_page_background(outlined_pdf, "#f5f5f5")
    assert _outline_titles(outlined_pdf) == before


def test_footer_keeps_the_outline(outlined_pdf: Path) -> None:
    before = _outline_titles(outlined_pdf)
    _pdf_stamp.add_footer(outlined_pdf, "footer text", page_numbers=True)
    assert _outline_titles(outlined_pdf) == before


def test_header_keeps_the_outline(outlined_pdf: Path) -> None:
    before = _outline_titles(outlined_pdf)
    _pdf_stamp.add_header(outlined_pdf, ["left", "middle", "right"])
    assert _outline_titles(outlined_pdf) == before


def test_scaling_keeps_the_outline(outlined_pdf: Path) -> None:
    before = _outline_titles(outlined_pdf)
    _pdf_stamp.scale_pages_to_width(outlined_pdf, 13.333)
    assert _outline_titles(outlined_pdf) == before


def test_the_whole_chain_keeps_it(
    outlined_pdf: Path, stamp_png: Path
) -> None:
    # Stamping once proves less than stamping the way an application
    # does: each stamper rewrites the file the previous one produced, so
    # a loss anywhere along the chain surfaces here and nowhere else.
    before = _outline_titles(outlined_pdf)
    _pdf_stamp.add_page_background(outlined_pdf, "#f5f5f5")
    _pdf_stamp.add_watermark(outlined_pdf, stamp_png)
    _pdf_stamp.add_header(outlined_pdf, ["a", "b", "c"])
    _pdf_stamp.add_footer(outlined_pdf, "footer", page_numbers=True)
    _pdf_stamp.add_metadata(
        outlined_pdf, creator="epy_export", producer="epy_export"
    )
    assert _outline_titles(outlined_pdf) == before
    assert len(pypdf.PdfReader(str(outlined_pdf)).pages) == 3


def test_branding_has_no_default() -> None:
    # Four applications share one frozen runtime. A default here is a
    # global that mislabels a PDF the day the wrong caller omits it;
    # with none, omitting it is a TypeError at test time.
    import inspect

    params = inspect.signature(_pdf_stamp.add_metadata).parameters
    assert params["creator"].default is inspect.Parameter.empty
    assert params["producer"].default is inspect.Parameter.empty


def test_the_metadata_written_is_the_metadata_asked_for(
    outlined_pdf: Path,
) -> None:
    _pdf_stamp.add_metadata(
        outlined_pdf,
        title="Título",
        author="ANM",
        rights="© 2026 ANM",
        creator="epy_export",
        producer="epy_export — ANM Ingeniería",
    )
    info = pypdf.PdfReader(str(outlined_pdf)).metadata
    assert info is not None
    assert info.title == "Título"
    assert info.author == "ANM"
    assert info["/Creator"] == "epy_export"


# --- named destinations, the real thing -------------------------------
#
# Moved here from epy_slides, which owned the only test of a function it
# does not use: extract_anchor_pages had zero callers in its src/ and
# lived entirely on the strength of this test. Deleting it with the
# module would have lost real coverage; the function's home is here now,
# and so is its test.
#
# It also supplies what the outline fixture above could not. reportlab
# writes no /Names /Dests tree, but pypdf's add_named_destination does --
# so this is the invariant the module docstring is actually about,
# asserted against a document that genuinely carries one.


@pytest.fixture
def destination_pdf(tmp_path: Path) -> Path:
    """A two-page PDF carrying a real named destination."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    source = tmp_path / "src.pdf"
    pdf = canvas.Canvas(str(source), pagesize=A4)
    for number in (1, 2):
        pdf.drawString(72, 720, f"page {number}")
        pdf.showPage()
    pdf.save()

    out = tmp_path / "named.pdf"
    writer = pypdf.PdfWriter()
    for page in pypdf.PdfReader(str(source)).pages:
        writer.add_page(page)
    writer.add_named_destination("intro", page_number=1)
    with out.open("wb") as handle:
        writer.write(handle)
    return out


def test_anchor_pages_are_read_one_based(destination_pdf: Path) -> None:
    anchors = _pdf_stamp.extract_anchor_pages(destination_pdf)
    assert anchors.get("intro") == 2


def test_the_fixture_really_carries_a_named_destination(
    destination_pdf: Path,
) -> None:
    # The control. The outline tests above exist because reportlab alone
    # produces none of these, and a fixture with an empty destination set
    # lets every stamper pass by comparing nothing to nothing.
    assert set(pypdf.PdfReader(str(destination_pdf)).named_destinations) == {
        "intro"
    }


def test_stamping_keeps_a_real_named_destination(
    destination_pdf: Path, stamp_png: Path
) -> None:
    # The claim the module docstring makes, against a document that has
    # what the docstring is talking about.
    before = set(pypdf.PdfReader(str(destination_pdf)).named_destinations)
    _pdf_stamp.add_watermark(destination_pdf, stamp_png)
    _pdf_stamp.add_metadata(
        destination_pdf, creator="epy_export", producer="epy_export"
    )
    after = set(pypdf.PdfReader(str(destination_pdf)).named_destinations)
    assert after == before == {"intro"}


# --- _roman -------------------------------------------------------------


def test_roman_numerals_for_ordinary_page_numbers() -> None:
    assert _pdf_stamp._roman(1) == "i"
    assert _pdf_stamp._roman(4) == "iv"
    assert _pdf_stamp._roman(14) == "xiv"
    assert _pdf_stamp._roman(1994) == "mcmxciv"


def test_roman_of_a_non_positive_number_is_its_own_string() -> None:
    # Page numbering never reaches zero or negative in practice, but the
    # function is defensive rather than silently producing an empty
    # string, which would read as a page carrying no number at all.
    assert _pdf_stamp._roman(0) == "0"
    assert _pdf_stamp._roman(-3) == "-3"


# --- extract_anchor_pages, the two failure paths ------------------------


def test_a_destination_pypdf_cannot_place_is_skipped(
    destination_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # "pypdf answers None for a destination it cannot place" -- the
    # module docstring's own words for a case the real fixture cannot
    # produce (its one destination resolves fine), so it is forced here.
    monkeypatch.setattr(
        pypdf.PdfReader,
        "get_destination_page_number",
        lambda self, dest: None,
    )
    assert _pdf_stamp.extract_anchor_pages(destination_pdf) == {}


def test_a_corrupt_pdf_yields_no_anchors_instead_of_raising(
    tmp_path: Path,
) -> None:
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a real PDF at all")
    assert _pdf_stamp.extract_anchor_pages(broken) == {}


# --- add_page_background, the two silent no-ops -------------------------


def test_background_with_no_color_does_nothing(outlined_pdf: Path) -> None:
    before = outlined_pdf.read_bytes()
    _pdf_stamp.add_page_background(outlined_pdf, "")
    assert outlined_pdf.read_bytes() == before


def test_background_with_an_unparseable_color_does_nothing(
    outlined_pdf: Path,
) -> None:
    before = outlined_pdf.read_bytes()
    _pdf_stamp.add_page_background(outlined_pdf, "not-a-color")
    assert outlined_pdf.read_bytes() == before


# --- add_watermark, the missing-image no-op ------------------------------


def test_watermark_with_a_missing_image_does_nothing(
    outlined_pdf: Path, tmp_path: Path
) -> None:
    before = outlined_pdf.read_bytes()
    _pdf_stamp.add_watermark(outlined_pdf, tmp_path / "absent.png")
    assert outlined_pdf.read_bytes() == before


# --- _page_stamp, both numbering schemes ---------------------------------


def test_page_stamp_with_segments_restarts_numbering_per_section() -> None:
    # Page 1-2 roman front matter; page 3+ arabic body, restarting at 1.
    segments = [(1, "roman"), (3, "arabic")]
    assert _pdf_stamp._page_stamp(1, 1, 10, "en", segments, True) == (
        True, "i",
    )
    assert _pdf_stamp._page_stamp(2, 1, 10, "en", segments, True) == (
        True, "ii",
    )
    assert _pdf_stamp._page_stamp(3, 1, 10, "en", segments, True) == (
        True, "1",
    )
    assert _pdf_stamp._page_stamp(4, 1, 10, "en", segments, True) == (
        True, "2",
    )


def test_page_stamp_with_segments_and_numbers_off_still_stamps() -> None:
    segments = [(1, "roman")]
    assert _pdf_stamp._page_stamp(1, 1, 10, "en", segments, False) == (
        True, None,
    )


def test_page_stamp_before_the_first_segment_is_unstamped() -> None:
    segments = [(3, "arabic")]
    assert _pdf_stamp._page_stamp(1, 1, 10, "en", segments, True) == (
        False, None,
    )


def test_page_stamp_without_segments_and_numbers_off_still_stamps() -> None:
    assert _pdf_stamp._page_stamp(2, 1, 5, "en", None, False) == (
        True, None,
    )


def test_page_stamp_without_segments_before_start_is_unstamped() -> None:
    assert _pdf_stamp._page_stamp(1, 3, 5, "en", None, True) == (
        False, None,
    )


# --- add_footer, the nothing-to-stamp no-op ------------------------------


def test_footer_with_nothing_to_stamp_does_nothing(
    outlined_pdf: Path,
) -> None:
    before = outlined_pdf.read_bytes()
    _pdf_stamp.add_footer(outlined_pdf, "", page_numbers=False)
    assert outlined_pdf.read_bytes() == before


# --- add_header ------------------------------------------------------


def test_header_with_no_cells_does_nothing(outlined_pdf: Path) -> None:
    before = outlined_pdf.read_bytes()
    _pdf_stamp.add_header(outlined_pdf, ["", "", ""])
    assert outlined_pdf.read_bytes() == before


def test_header_skips_pages_before_start_page(outlined_pdf: Path) -> None:
    # outlined_pdf carries 3 pages; start_page=2 must leave page 1 alone.
    _pdf_stamp.add_header(
        outlined_pdf, ["LEFT", "MID", "RIGHT"], start_page=2
    )
    reader = pypdf.PdfReader(str(outlined_pdf))
    texts = [page.extract_text() for page in reader.pages]
    assert "LEFT" not in texts[0]
    assert "LEFT" in texts[1]
    assert "LEFT" in texts[2]


def test_header_with_six_cells_draws_a_second_row(outlined_pdf: Path) -> None:
    _pdf_stamp.add_header(outlined_pdf, ["A", "B", "C", "D", "E", "F"])
    text = pypdf.PdfReader(str(outlined_pdf)).pages[0].extract_text()
    assert "D" in text
    assert "E" in text
    assert "F" in text


def test_header_skips_an_empty_cell_within_the_grid(
    outlined_pdf: Path,
) -> None:
    _pdf_stamp.add_header(outlined_pdf, ["A", "", "C"])
    text = pypdf.PdfReader(str(outlined_pdf)).pages[0].extract_text()
    assert "A" in text
    assert "C" in text


# --- add_metadata, the optional fields ------------------------------------


def test_metadata_writes_subject_and_keywords_when_given(
    outlined_pdf: Path,
) -> None:
    _pdf_stamp.add_metadata(
        outlined_pdf,
        subject="Structural report",
        keywords="concrete, seismic",
        creator="epy_export",
        producer="epy_export",
    )
    info = pypdf.PdfReader(str(outlined_pdf)).metadata
    assert info is not None
    assert info["/Subject"] == "Structural report"
    assert info["/Keywords"] == "concrete, seismic"


# --- _fit_to --------------------------------------------------------------


def test_fit_to_skips_a_page_with_a_degenerate_mediabox() -> None:
    class _Box:
        def __init__(self, width: float, height: float) -> None:
            self.width = width
            self.height = height

    class _Page:
        def __init__(self, width: float, height: float) -> None:
            self.mediabox = _Box(width, height)
            self.scaled = False

        def scale_by(self, _factor: float) -> None:
            self.scaled = True

    zero_width = _Page(0, 500)
    normal = _Page(400, 500)

    _pdf_stamp._fit_to([zero_width, normal], 400.0, 600.0)

    assert zero_width.scaled is False
    assert normal.scaled is True
