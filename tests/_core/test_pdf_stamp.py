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
