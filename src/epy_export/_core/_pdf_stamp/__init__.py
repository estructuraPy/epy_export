"""Stamp backgrounds, watermarks, headers, footers and metadata on a PDF.

One owner for what every app in the ePy document family does to a
finished PDF. It lived twice -- ``epy_reports._core._pdf_footer`` and
``epy_slides._core._pdf_footer`` -- as 546 lines that differed in eight,
and all eight were comment text. A fix to one silently did not reach the
other, which is the whole reason this module exists here instead.

Named ``_pdf_stamp`` and not ``_pdf_footer``: it stamps five things and
the footer is one of them. The name was misleading in both copies.

The PDF is rewritten in place: every page gets an overlay canvas (drawn
with :mod:`reportlab`) merged on top of it (via :mod:`pypdf`). Both are
BSD-licensed and so compatible with this suite's MIT license.
PyMuPDF/fitz is deliberately avoided because of its AGPL licensing.

**Every stamper clones the source document** (``PdfWriter(clone_from=)``)
and merges its overlay onto the cloned pages. A fresh ``PdfWriter()`` fed
page-by-page would drop the document catalog -- including the named
destinations Chromium emits for every anchored heading, figure and table
-- leaving the TOC, index and cross-reference link annotations pointing
at destinations that no longer exist. The links stay visible and stop
working, which is why a test asserts the destinations survive rather
than asserting the file opens.

**Order is not commutative and is the caller's to choose.**
:func:`add_page_background` merges UNDER the page; :func:`add_watermark`
merges over it. A watermark stamped before a background disappears
behind it, and the PDF still opens with the right page count. The two
apps genuinely differ here -- reports stamps background, watermark,
header, footer, metadata; slides stamps watermark and metadata only --
so this module does not impose an order. It only refuses to hide that
one exists.

The heavy dependencies are imported lazily inside each function, so this
module imports cleanly without them; a named :class:`RuntimeError` is
raised only when a function that needs them is actually called.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

# Footer geometry / styling.
_MARGIN_MM = 15.0
_MM_TO_PT = 72.0 / 25.4
_FONT_NAME = "Helvetica"
_FONT_SIZE = 8.0
_GRAY = 0.45  # muted gray (0 = black, 1 = white)

# Localized "Page X of Y" templates.
_PAGE_LABELS: dict[str, str] = {
    "en": "Page {current} of {total}",
    "es": "Pág. {current} de {total}",
}


def _page_label(lang: str, current: int, total: int) -> str:
    """Return the localized page-number string for one page."""
    key = lang[:2].lower() if lang else "en"
    template = _PAGE_LABELS.get(key, _PAGE_LABELS["en"])
    return template.format(current=current, total=total)


_ROMAN_STEPS = [
    (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"),
    (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"),
    (5, "v"), (4, "iv"), (1, "i"),
]


def _roman(number: int) -> str:
    """Return ``number`` as a lowercase Roman numeral (front-matter style)."""
    if number <= 0:
        return str(number)
    out: list[str] = []
    for value, glyph in _ROMAN_STEPS:
        while number >= value:
            out.append(glyph)
            number -= value
    return "".join(out)


def extract_anchor_pages(pdf_path: Path) -> dict[str, int]:
    """Return ``anchor id → 1-based page`` from a Qt-generated PDF.

    Qt WebEngine records HTML element ids as PDF named destinations, so a
    first export pass yields the physical page of every anchored heading,
    figure, table and equation. The index blocks emit only links (no
    destinations), so every entry here points into the document body —
    ``min(result.values())`` is therefore the first content page.

    Returns an empty dict when :mod:`pypdf` is missing or the PDF has no
    named destinations (older Qt), so the caller can skip the second pass
    gracefully.
    """
    try:
        from pypdf import PdfReader  # noqa: PLC0415
    except ImportError:  # pragma: no cover - env guard
        return {}
    try:
        reader = PdfReader(str(pdf_path))
        result: dict[str, int] = {}
        for name, dest in reader.named_destinations.items():
            # Individual destinations may reference a missing page —
            # suppress only the specific lookup errors pypdf raises.
            with contextlib.suppress(KeyError, IndexError, TypeError):
                # pypdf answers None for a destination it cannot place;
                # the anchor is simply unusable, and the caller's second
                # pass is built to work from whatever survives here.
                page = reader.get_destination_page_number(dest)
                if page is None:
                    continue
                result[name.lstrip("/")] = page + 1
        return result
    except Exception:  # noqa: BLE001
        # pypdf.PdfReadError (and other internal parse exceptions) are
        # raised for structurally corrupt or truncated PDFs. We cannot
        # enumerate all pypdf-internal exception subclasses here, so
        # Exception is intentional: a bad PDF must not crash the export.
        return {}


def add_page_background(
    pdf_path: Path,
    color: str,
    *,
    start_page: int = 1,
) -> None:
    """Paint a solid full-sheet background behind every page, in place.

    Qt WebEngine lays out the body inside the printer margin, so the margin
    band of every page is left unpainted (white) even for colored themes —
    Chromium never paints the printer-margin area. This draws a ``color``
    rectangle covering the whole media box *below* the existing page
    content, so the theme background reaches the paper edges without
    touching the already-laid-out body, footnotes or overlays. The page
    keeps its links because the backdrop is merged under it (``over=False``).

    Args:
        pdf_path: Path to an existing PDF; overwritten with the result.
        color: CSS hex color (``#RRGGBB``) of the theme page background.
            An empty or unparseable value leaves the PDF untouched.
        start_page: First 1-based page to paint (defaults to every page,
            cover and index pages included).

    Raises:
        RuntimeError: When :mod:`pypdf` or :mod:`reportlab` is not installed.
    """
    if not color:
        return
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        from reportlab.lib.colors import HexColor  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env guard
        raise RuntimeError(
            "PDF backgrounds require the 'pypdf' and 'reportlab' packages. "
            "Install them with: pip install pypdf reportlab"
        ) from exc

    try:
        fill = HexColor(color)
    except (ValueError, TypeError):
        return  # unparseable color → leave the PDF as-is

    writer = PdfWriter(clone_from=str(pdf_path))
    for index, page in enumerate(writer.pages, start=1):
        if index >= start_page:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            buffer = io.BytesIO()
            backdrop_canvas = canvas.Canvas(buffer, pagesize=(width, height))
            backdrop_canvas.setFillColor(fill)
            backdrop_canvas.rect(0, 0, width, height, fill=1, stroke=0)
            backdrop_canvas.showPage()
            backdrop_canvas.save()
            buffer.seek(0)
            backdrop = PdfReader(buffer).pages[0]
            # over=False → backdrop goes underneath, page content (and its
            # link annotations) stay on top.
            page.merge_page(backdrop, over=False)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


def add_watermark(
    pdf_path: Path,
    image_path: Path,
    *,
    opacity: float = 0.12,
    width_ratio: float = 0.7,
) -> None:
    """Stamp a faint grayscale watermark image onto every page, in place.

    The source image is desaturated to grayscale (so it never clashes with
    the document's colors) and drawn centered and translucent, washed out
    behind the text like a classic watermark. The original alpha channel is
    preserved and scaled by ``opacity`` so transparent logos stay clean.

    Args:
        pdf_path: Path to an existing PDF; overwritten with the result.
        image_path: Any raster/vector image readable by Pillow.
        opacity: Watermark strength in [0, 1] (default faint 0.12).
        width_ratio: Watermark width as a fraction of the page width.

    Raises:
        RuntimeError: When Pillow, pypdf or reportlab is not installed.
    """
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env guard
        raise RuntimeError(
            "Watermarks require the 'Pillow' package. "
            "Install it with: pip install Pillow"
        ) from exc
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        from reportlab.lib.utils import ImageReader  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env guard
        raise RuntimeError(
            "Watermarks require the 'pypdf' and 'reportlab' packages. "
            "Install them with: pip install pypdf reportlab"
        ) from exc

    if not Path(image_path).is_file():
        return  # nothing to stamp

    # Desaturate to grayscale, then rebuild as a translucent RGBA image so
    # only a faint gray ghost of the artwork remains.
    source = Image.open(str(image_path)).convert("RGBA")
    r, g, b, alpha = source.split()
    luminance = Image.merge("RGB", (r, g, b)).convert("L")
    faint = Image.merge("RGB", (luminance, luminance, luminance)).convert(
        "RGBA"
    )
    faint.putalpha(alpha.point(lambda v: int(v * opacity)))
    img_w, img_h = faint.size
    writer = PdfWriter(clone_from=str(pdf_path))
    for page in writer.pages:
        page_w = float(page.mediabox.width)
        page_h = float(page.mediabox.height)
        draw_w = page_w * width_ratio
        draw_h = draw_w * img_h / img_w
        x = (page_w - draw_w) / 2.0
        y = (page_h - draw_h) / 2.0
        buffer = io.BytesIO()
        wm_canvas = canvas.Canvas(buffer, pagesize=(page_w, page_h))
        wm_canvas.drawImage(
            ImageReader(faint), x, y, draw_w, draw_h, mask="auto"
        )
        wm_canvas.showPage()
        wm_canvas.save()
        buffer.seek(0)
        overlay = PdfReader(buffer).pages[0]
        page.merge_page(overlay)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


def _page_stamp(
    index: int,
    start_page: int,
    content_total: int,
    lang: str,
    segments: list[tuple[int, str]] | None,
    page_numbers: bool,
) -> tuple[bool, str | None]:
    """Return ``(stamp, label)`` for one physical page.

    ``stamp`` is True when the page belongs to a numbered section (so the
    footer text is drawn); ``label`` is the page-number string, or None when
    numbering is off or the page is unnumbered front matter.

    With ``segments`` (sorted ``(start_page, style)`` boundaries), each
    section numbers from 1 in its own style (``roman`` or ``arabic``),
    restarting at every boundary; pages before the first boundary are
    unnumbered front matter. Without segments, the legacy single-run
    behaviour applies: Arabic "Page X of Y" from ``start_page``.
    """
    if segments:
        current_segment: tuple[int, str] | None = None
        for seg_start, style in segments:
            if index >= seg_start:
                current_segment = (seg_start, style)
            else:
                break
        if current_segment is None:
            return (False, None)
        seg_start, style = current_segment
        if not page_numbers:
            return (True, None)
        number = index - seg_start + 1
        return (True, _roman(number) if style == "roman" else str(number))

    if index >= start_page:
        if not page_numbers:
            return (True, None)
        return (True, _page_label(lang, index - start_page + 1, content_total))
    return (False, None)


def add_footer(
    pdf_path: Path,
    footer_text: str,
    *,
    page_numbers: bool,
    lang: str = "en",
    start_page: int = 1,
    segments: list[tuple[int, str]] | None = None,
) -> None:
    """Stamp pages of ``pdf_path`` with a footer, in place.

    Draws ``footer_text`` at the bottom-left and, when ``page_numbers`` is
    ``True``, a page-number string at the bottom-right.

    Args:
        pdf_path: Path to an existing PDF; overwritten with the stamped
            version.
        footer_text: Static text drawn at the bottom-left.  May be empty.
        page_numbers: When ``True``, draw the page number at bottom-right.
        lang: Two-letter language tag selecting the page-number wording.
        start_page: First 1-based physical page to stamp.  Pages before
            this (cover and index pages — TOC / LOF / LOT / LOE) are
            passed through unchanged and carry no footer or page number.
            Page numbering restarts at 1 on ``start_page`` and the
            "of Y" total counts only the stamped (content) pages, so the
            front matter is effectively unnumbered.
        segments: Optional sorted list of ``(start_page, style)`` section
            boundaries (``style`` is ``"roman"`` or ``"arabic"``). When
            given, numbering restarts in each section's style — front matter
            in Roman, the body in Arabic, for example — and a bare numeral
            (``i``/``1``) is drawn instead of "Page X of Y".

    Raises:
        RuntimeError: When :mod:`pypdf` or :mod:`reportlab` is not installed.
    """
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env guard
        raise RuntimeError(
            "PDF footers require the 'pypdf' and 'reportlab' packages. "
            "Install them with: pip install pypdf reportlab"
        ) from exc

    if not footer_text and not page_numbers:
        return  # nothing to stamp

    sorted_segments = sorted(segments) if segments else None

    writer = PdfWriter(clone_from=str(pdf_path))
    total = len(writer.pages)
    # Page numbers restart at 1 on the first stamped (content) page and the
    # "of Y" total counts only those pages, so cover + index front matter
    # stays unnumbered instead of forcing the body to start at "Page N".
    content_total = max(total - start_page + 1, 0)
    margin = _MARGIN_MM * _MM_TO_PT

    for index, page in enumerate(writer.pages, start=1):
        stamp, label = _page_stamp(
            index, start_page, content_total, lang,
            sorted_segments, page_numbers,
        )
        if stamp and (footer_text or label):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=(width, height))
            pdf.setFont(_FONT_NAME, _FONT_SIZE)
            pdf.setFillGray(_GRAY)
            if footer_text:
                pdf.drawString(margin, margin, footer_text)
            if label:
                pdf.drawRightString(width - margin, margin, label)
            pdf.showPage()
            pdf.save()
            buffer.seek(0)
            overlay = PdfReader(buffer).pages[0]
            page.merge_page(overlay)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


# Header geometry
_HEADER_ROW_H_PT = 12.0  # height of each row in points (~4.2 mm)
_HEADER_COLS = 3
_STROKE_GRAY = 0.70


def add_header(
    pdf_path: Path,
    cells: list[str],
    *,
    lang: str = "en",  # noqa: ARG001 — reserved for future l10n
    start_page: int = 1,
) -> None:
    """Stamp a 2-row × 3-column grid header onto pages of ``pdf_path``.

    Up to 6 strings may be provided.  Cells are filled in row-major order::

        [cells[0]]  [cells[1]]  [cells[2]]   ← row 1
        [cells[3]]  [cells[4]]  [cells[5]]   ← row 2

    If only 3 values are given, a single-row header is drawn.  Columns are
    left-, center-, and right-aligned respectively.  The grid is placed in
    the top page margin (≈15 mm from the paper edge) so it never overlaps
    the document body.

    Args:
        pdf_path: Path to an existing PDF; overwritten with the stamped
            version.
        cells: Up to 6 strings for the header grid.  Missing cells default to
            empty strings.
        lang: Two-letter language tag (reserved; not used currently).
        start_page: First 1-based page number to stamp.  Pages before this
            (e.g. a cover page) are passed through unchanged.

    Raises:
        RuntimeError: When :mod:`pypdf` or :mod:`reportlab` is not installed.
    """
    cells = list(cells or [])
    if not any(cells):
        return

    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        from reportlab.pdfgen import canvas as rl_canvas  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PDF headers require the 'pypdf' and 'reportlab' packages. "
            "Install them with: pip install pypdf reportlab"
        ) from exc

    # Pad / truncate to exactly 6 cells
    cells = (cells + [""] * 6)[:6]
    has_row2 = any(cells[3:])
    n_rows = 2 if has_row2 else 1

    writer = PdfWriter(clone_from=str(pdf_path))
    margin = _MARGIN_MM * _MM_TO_PT
    row_h = _HEADER_ROW_H_PT

    for page_index, page in enumerate(writer.pages, start=1):
        if page_index < start_page:
            continue
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        buffer = io.BytesIO()
        c = rl_canvas.Canvas(buffer, pagesize=(width, height))
        c.setFont(_FONT_NAME, _FONT_SIZE)

        grid_x = margin
        grid_w = width - 2 * margin
        col_w = grid_w / _HEADER_COLS
        grid_top = height - margin          # top edge of grid (near paper top)
        grid_h = n_rows * row_h
        grid_bot = grid_top - grid_h

        # Border
        c.setStrokeGray(_STROKE_GRAY)
        c.setLineWidth(0.5)
        c.rect(grid_x, grid_bot, grid_w, grid_h, fill=0, stroke=1)

        # Column dividers
        for col in range(1, _HEADER_COLS):
            x = grid_x + col * col_w
            c.line(x, grid_bot, x, grid_top)

        # Row divider (only when 2 rows)
        if n_rows == 2:
            mid_y = grid_bot + row_h
            c.line(grid_x, mid_y, grid_x + grid_w, mid_y)

        # Cell text
        c.setFillGray(_GRAY)
        for i, text in enumerate(cells[: n_rows * _HEADER_COLS]):
            if not text:
                continue
            row = i // _HEADER_COLS
            col = i % _HEADER_COLS
            y_top = grid_top - row * row_h
            y_base = y_top - row_h / 2 - _FONT_SIZE / 4
            x_left = grid_x + col * col_w
            pad = 3  # inner horizontal padding in points
            if col == 0:
                c.drawString(x_left + pad, y_base, text)
            elif col == 1:
                c.drawCentredString(x_left + col_w / 2, y_base, text)
            else:
                c.drawRightString(x_left + col_w - pad, y_base, text)

        c.showPage()
        c.save()
        buffer.seek(0)
        overlay = PdfReader(buffer).pages[0]
        page.merge_page(overlay)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


def add_metadata(
    pdf_path: Path,
    *,
    title: str = "",
    author: str = "",
    subject: str = "",
    keywords: str = "",
    rights: str = "",
    creator: str,
    producer: str,
) -> None:
    """Embed document metadata (including copyright) into a PDF, in place.

    Writes the standard PDF ``/Info`` entries — title, author, subject,
    keywords, creator, producer — plus a custom ``/Copyright`` key, so the
    exported file always carries authorship and rights information. This is
    both attribution and a lightweight ownership marker: the rights notice
    travels with the file. Empty values are skipped; ``creator`` and
    ``producer`` are always set.

    The document is cloned (pages, links, named destinations and outline are
    preserved) and only its metadata dictionary is updated.

    Args:
        pdf_path: Path to an existing PDF; overwritten with the result.
        title: Document title.
        author: Document author.
        subject: Short description / subtitle.
        keywords: Comma-separated keywords.
        rights: Copyright / rights notice (e.g. ``"© 2026 ACME"``).
        creator: Authoring application name. Required, with no
            default: four applications share one frozen runtime, so
            a default here is a global that silently mislabels a PDF
            the day the wrong caller omits it. Omitting it now is a
            TypeError at test time instead.
        producer: Producing application and organisation. Required,
            for the same reason.

    Raises:
        RuntimeError: When :mod:`pypdf` is not installed.
    """
    try:
        from pypdf import PdfWriter  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env guard
        raise RuntimeError(
            "PDF metadata requires the 'pypdf' package. "
            "Install it with: pip install pypdf"
        ) from exc

    info: dict[str, str] = {"/Creator": creator, "/Producer": producer}
    if title:
        info["/Title"] = title
    if author:
        info["/Author"] = author
    if subject:
        info["/Subject"] = subject
    if keywords:
        info["/Keywords"] = keywords
    if rights:
        info["/Copyright"] = rights

    writer = PdfWriter(clone_from=str(pdf_path))
    writer.add_metadata(info)
    with pdf_path.open("wb") as handle:
        writer.write(handle)


def scale_pages_to_width(
    pdf_path: Path, target_width_in: float
) -> None:
    """Scale every page of ``pdf_path`` to ``target_width_in``, vector-safe.

    reveal sizes the print page to the 960 px deck, which Qt prints a touch
    under the 16:9 PowerPoint size; the exact printed width also drifts a few
    percent from the requested page layout. Scaling the finished *vector* PDF
    to the target width (computed per page from its real media box, so the
    drift is absorbed) keeps the text crisp and gives the deck the larger
    widescreen sheet. The aspect ratio is preserved (one uniform scale).
    """
    from pypdf import PdfWriter  # noqa: PLC0415

    target_pt = target_width_in * 72.0
    # Clone (not reader -> fresh writer): a fresh PdfWriter drops the
    # document catalog, killing link annotations' named destinations.
    writer = PdfWriter(clone_from=str(pdf_path))
    for page in writer.pages:
        width_pt = float(page.mediabox.width)
        if width_pt > 0:
            page.scale_by(target_pt / width_pt)
    with pdf_path.open("wb") as handle:
        writer.write(handle)
