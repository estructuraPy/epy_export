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
