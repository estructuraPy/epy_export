"""ePy Docs: the generic writer, reached through the one bridge.

There were two bridges to this engine and they disagreed on seven
points. epy_craft's fed ``add_markdown_file`` and scanned the LaTeX log;
epy_reports' fed ``add_quarto_file``, checked availability with a
different mechanism, returned a different type, passed no author, and
did not read the log at all. epy_slides and epy_papers had no bridge and
could not reach the engine except through epy_craft.

Duplicate *intent* implemented incompatibly is worse for the reader than
a literal copy, because nothing makes the two look related. This is the
reconciliation, built on the richer of the two.

``DocumentWriter`` is an incremental builder: no ``from_file``, no
``to_pdf``, and one ``generate()`` that emits every requested format at
once. That is why this engine cannot go through the uniform adapter --
the uniform path used to raise ``AttributeError`` on an engine the
catalog happily returned.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Any

from ..._core._backends import RenderFailedError, load_backend
from .._contract._engine import Engine, RenderOptions

__all__ = ["emit_all", "refuse_latex_errors", "understands"]

_UNDERSTOOD = (
    "appearance",
    "author",
    "language",
    "project_type",
    "source_kind",
)
"""Everything but the journal profile. This is the only engine whose
entry point takes cover metadata, which is why three prose documents
were once measured shipping without an author."""


def understands() -> tuple[str, ...]:
    """Return the option fields this engine accepts."""
    return _UNDERSTOOD


def refuse_latex_errors(log_path: Path) -> None:
    """Refuse a render whose LaTeX log records a hard error.

    The engine can leave a PDF on disk after LaTeX aborted mid-document
    -- measured: a draft referencing an image that did not exist
    produced a 3-page PDF out of a 10-page offer, and the file-exists
    check passed it as a success. The log is the only witness, so it is
    read: any line opening with ``!`` is a LaTeX error, and the first is
    quoted so the author knows what to fix.

    Kept, and now run for every caller. epy_reports had no equivalent,
    so it has been accepting exactly this class of partial document.

    Args:
        log_path: The ``<stem>.log`` the engine leaves beside the PDF.
            An absent log means nothing to judge, not a failure.

    Raises:
        RenderFailedError: Naming the first LaTeX error found. This used
            to raise the *engine unavailable* error, so a truncated
            document was reported as "epy_docs is not installed" -- one
            of those is fixed by installing something and the other
            never is.
    """
    if not log_path.is_file():
        return
    try:
        lines = log_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
    except OSError:
        return
    errors = [line for line in lines if line.startswith("! ")]
    if errors:
        raise RenderFailedError(
            f"LaTeX reported an error while rendering, so the PDF on "
            f"disk is partial: {errors[0].strip()} -- fix the document "
            f"(a missing image, a raw LaTeX block, an unescaped "
            f"character) and render again."
        )


def emit_all(
    spec: Engine,
    source: Path,
    output_dir: Path,
    formats: Collection[str],
    opts: RenderOptions,
    *,
    document_type: str = "report",
    title: str | None = None,
    client: dict[str, str] | None = None,
    footer: str = "",
    bibliography: Path | None = None,
    csl: Path | None = None,
) -> list[Path]:
    """Render every requested format in one pass, and check the result.

    Unlike the other adapters this one emits all formats together,
    because the writer does: ``generate()`` takes pdf/docx/html as flags.

    Args:
        spec: The engine row.
        source: The document to render.
        output_dir: Where the results go.
        formats: Which to produce.
        opts: Appearance, author, language, project type and source kind.
        document_type: Which of the writer's document types to build.
        title: Project name for the cover; the file stem when absent.
        client: Client cover block.
        footer: Page footer text.
        bibliography: A ``.bib`` to cite from.
        csl: A citation style to render it with.

    Returns:
        One path per requested format.

    Raises:
        ValueError: When a named bibliography or CSL file is absent.
        BackendUnavailableError: When epy_docs is not installed.
        RenderFailedError: When LaTeX errored, or a requested file is
            not on disk afterwards.
    """
    docs = load_backend(spec.module, why=f"rendering through {spec.label}")
    writer_factory: Any = docs.DocumentWriter
    writer: Any = writer_factory(
        document_type=document_type,
        layout_style=opts.appearance,
        language=opts.language,
        output_dir=str(output_dir),
    )
    if opts.author:
        writer.set_author(**dict(opts.author))
    writer.set_project_info(
        name=title or source.stem,
        **({"project_type": opts.project_type} if opts.project_type else {}),
    )
    if client:
        writer.set_client_info(
            name=client.get("name", ""), company=client.get("company", "")
        )
    if footer:
        writer.add_page_footer(footer)

    # Explicit, never guessed from the suffix: a Quarto source fed to the
    # Markdown reader leaks its directives into the body as literal text.
    if opts.source_kind == "quarto":
        writer.add_quarto_file(
            str(source), convert_tables=False, execute_code_blocks=False
        )
    else:
        writer.add_markdown_file(str(source), convert_tables=False)

    # Named apart from the project-info block above, which used to bind
    # a local called `extras` too. It worked only because the first was
    # consumed before the second was bound, which is how the next edit
    # inserted between them silently drops a cover field.
    citation_args: dict[str, Any] = {}
    if bibliography is not None:
        if not bibliography.is_file():
            raise ValueError(f"Bibliography not found: {bibliography}")
        citation_args["bibliography_path"] = str(bibliography)
    if csl is not None:
        if not csl.is_file():
            raise ValueError(f"CSL file not found: {csl}")
        citation_args["csl_path"] = str(csl)

    writer.generate(
        pdf="pdf" in formats,
        docx="docx" in formats,
        html="html" in formats,
        qmd=False,
        output_filename=source.stem,
        **citation_args,
    )

    refuse_latex_errors(output_dir / f"{source.stem}.log")
    produced = [
        output_dir / f"{source.stem}.{ext}"
        for ext in ("pdf", "docx", "html")
        if ext in formats
    ]
    missing = [path for path in produced if not path.is_file()]
    if missing:
        raise RenderFailedError(
            f"{spec.label} did not produce: "
            + ", ".join(str(path) for path in missing)
            + "; the underlying Quarto or LaTeX run failed."
        )
    return produced
