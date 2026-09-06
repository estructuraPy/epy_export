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

import json
import os
import subprocess
from collections.abc import Collection
from pathlib import Path
from typing import Any

from ..._core._backends import (
    RenderFailedError,
    backend_route,
    load_backend,
)
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


def staged_for_latex(source: Path, output_dir: Path) -> tuple[Path, int]:
    """Return a copy of ``source`` a LaTeX typesetter can read.

    Measured: the same document that ePy Reports renders in three
    formats produced NOTHING through the two LaTeX-based engines --
    "Missing $ inserted", no file -- until 204 math delimiters were
    rewritten. The engines that need this are the ones that go through
    LaTeX, and only those; rewriting a source for an engine that
    already reads it is a change nobody asked for.

    A COPY, never the source. The document the author wrote stays where
    they put it, and the count comes back so the caller can say how many
    repairs it needed rather than quietly improving it.

    Args:
        source: The document to render.
        output_dir: Where the render is going; the copy is staged there.

    Returns:
        The path to hand the engine, and how many delimiters moved. Zero
        means the source was already readable and IS the returned path.
    """
    from ..._core._markdown import normalize_math  # noqa: PLC0415

    repair = normalize_math(source.read_text(encoding="utf-8"))
    if not repair.math_delimiters:
        return source, 0
    staged_dir = output_dir / "_staged"
    staged_dir.mkdir(parents=True, exist_ok=True)
    staged = staged_dir / source.name
    staged.write_text(repair.text, encoding="utf-8", newline="\n")
    return staged, repair.math_delimiters


# The call sequence, as DATA. Both executions read this and neither
# owns it, so the document cannot change because the renderer moved to
# another process. The applier below is six lines precisely so that the
# copy of it inside the child script is small enough to be obviously the
# same thing.
Step = tuple[str, dict[str, Any]]

_CHILD = """
import json, logging, sys
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
job = json.loads(sys.stdin.read())
import epy_docs
writer = epy_docs.DocumentWriter(**job["constructor"])
for name, kwargs in job["steps"]:
    getattr(writer, name)(**kwargs)
writer.generate(**job["generate"])
"""
"""What runs in the interpreter that has ePy Docs.

Sent with ``-c`` and handed the job on STDIN, never on the command line:
a job carries absolute paths, author names and a footer, and a command
line is length-limited, quoted by the shell and visible in the process
list.

It configures logging to stderr because the library reports a failed
render at INFO level and returns normally. It prints NOTHING on success:
what the library returns is not evidence -- without Quarto it returns a
mapping of ``None`` and exits zero -- so the parent looks at the files
on disk instead.
"""

_CHILD_TIMEOUT = 900.0
"""Seconds. A PDF through Quarto and LaTeX is minutes, not seconds, and
a wrong interpreter that hangs must not hang the application for ever.
"""


def _job(
    source: Path,
    output_dir: Path,
    formats: Collection[str],
    opts: RenderOptions,
    *,
    document_type: str,
    title: str | None,
    client: dict[str, str] | None,
    footer: str,
    bibliography: Path | None,
    csl: Path | None,
) -> dict[str, Any]:
    """Return the whole render as data, ready for either execution.

    Args:
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
        ``{"constructor": {...}, "steps": [[name, kwargs], ...],
        "generate": {...}}``, all values JSON-serialisable.

    Raises:
        ValueError: When a named bibliography or CSL file is absent.
    """
    steps: list[Step] = []
    if opts.author:
        steps.append(("set_author", dict(opts.author)))
    project: dict[str, Any] = {"name": title or source.stem}
    if opts.project_type:
        project["project_type"] = opts.project_type
    steps.append(("set_project_info", project))
    if client:
        steps.append((
            "set_client_info",
            {"name": client.get("name", ""),
             "company": client.get("company", "")},
        ))
    if footer:
        steps.append(("add_page_footer", {"content": footer}))

    # Explicit, never guessed from the suffix: a Quarto source fed to the
    # Markdown reader leaks its directives into the body as literal text.
    if opts.source_kind == "quarto":
        steps.append((
            "add_quarto_file",
            {"file_path": str(source), "convert_tables": False,
             "execute_code_blocks": False},
        ))
    else:
        steps.append((
            "add_markdown_file",
            {"file_path": str(source), "convert_tables": False},
        ))

    generate: dict[str, Any] = {
        "pdf": "pdf" in formats,
        "docx": "docx" in formats,
        "html": "html" in formats,
        "qmd": False,
        "output_filename": source.stem,
    }
    if bibliography is not None:
        if not bibliography.is_file():
            raise ValueError(f"Bibliography not found: {bibliography}")
        generate["bibliography_path"] = str(bibliography)
    if csl is not None:
        if not csl.is_file():
            raise ValueError(f"CSL file not found: {csl}")
        generate["csl_path"] = str(csl)

    return {
        "constructor": {
            "document_type": document_type,
            "layout_style": opts.appearance,
            "language": opts.language,
            "output_dir": str(output_dir),
        },
        "steps": [list(step) for step in steps],
        "generate": generate,
    }


def _in_process(spec: Engine, job: dict[str, Any]) -> None:
    """Apply the job to a writer imported here."""
    docs = load_backend(spec.module, why=f"rendering through {spec.label}")
    writer_factory: Any = docs.DocumentWriter
    writer: Any = writer_factory(**job["constructor"])
    for name, kwargs in job["steps"]:
        getattr(writer, name)(**kwargs)
    writer.generate(**job["generate"])


def _out_of_process(spec: Engine, job: dict[str, Any], python: str) -> None:
    """Apply the job in the interpreter that carries the engine.

    Inside a frozen bundle this is the ONLY way the engine can be
    reached: PyInstaller closes ``sys.path`` to the bundle, so importing
    it here can never work however the spec is written.

    Args:
        spec: The engine row, for the message.
        job: What :func:`_job` built.
        python: The interpreter to run it in.

    Raises:
        RenderFailedError: When the child could not be started, timed
            out, or exited non-zero -- carrying its stderr, which is
            where the library's own diagnosis goes.

    Note:
        A child that exits ZERO has still proven nothing. Without Quarto
        the library swallows the failure, logs it at INFO and returns a
        mapping whose values are ``None``; the caller checks the files on
        disk afterwards, which is the only honest signal.
    """
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        finished = subprocess.run(
            [python, "-c", _CHILD],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=_CHILD_TIMEOUT,
            env=env,
            check=False,
        )
    except OSError as exc:
        raise RenderFailedError(
            f"{spec.label} could not be started in {python}: {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderFailedError(
            f"{spec.label} did not finish within {_CHILD_TIMEOUT:.0f}s "
            f"in {python}."
        ) from exc
    if finished.returncode != 0:
        tail = (finished.stderr or "").strip().splitlines()[-12:]
        raise RenderFailedError(
            f"{spec.label} failed in {python}:\n" + "\n".join(tail)
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
    source, _repaired = staged_for_latex(source, output_dir)
    job = _job(
        source, output_dir, formats, opts,
        document_type=document_type,
        title=title,
        client=client,
        footer=footer,
        bibliography=bibliography,
        csl=csl,
    )
    route = backend_route(spec.module)
    if route.mode == "subprocess":
        _out_of_process(spec, job, route.python)
    else:
        # load_backend raises BackendUnavailableError, by name, when the
        # route said none: that message is the one a reader can act on.
        _in_process(spec, job)

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
