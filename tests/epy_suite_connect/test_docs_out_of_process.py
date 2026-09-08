"""The same document, whether the engine is here or in another interpreter.

Inside a frozen bundle ePy Docs can never be imported, so the render has
to run in the interpreter ePy Studio found. The call sequence is
therefore built once as DATA and applied twice, and these tests hold the
two applications to the same sequence: a document must not change
because the renderer moved to another process.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from epy_export._core import _backends
from epy_export.epy_suite_connect._adapters import _docs
from epy_export.epy_suite_connect._contract._engine import (
    Engine,
    RenderOptions,
)

SPEC = Engine(
    engine_id="docs",
    label="ePy Docs",
    module="epy_docs",
    formats=("pdf", "docx", "html"),
    themed=True,
    purpose="The generic writer.",
)

OPTS = RenderOptions(
    appearance="corporate",
    author={"name": "Ing. Angel Navarro-Mora M.Sc.", "role": "Author"},
    language="es",
    project_type="Structural report",
    source_kind="markdown",
)

# A stand-in for the library, written into the child's import path. It
# records the sequence instead of rendering, and writes whatever files
# the job asked for so the caller's disk check can pass.
FAKE = '''
import json, os, pathlib

_CALLS = []


class DocumentWriter:
    def __init__(self, **kwargs):
        _CALLS.append(["__init__", kwargs])
        self._dir = pathlib.Path(kwargs["output_dir"])
        # A real writer makes its own output directory; the
        # stand-in has to as well or it measures the wrong thing.
        self._dir.mkdir(parents=True, exist_ok=True)

    def __getattr__(self, name):
        def record(**kwargs):
            _CALLS.append([name, kwargs])
            return self
        return record

    def generate(self, **kwargs):
        _CALLS.append(["generate", kwargs])
        stem = kwargs["output_filename"]
        made = {}
        for fmt in ("pdf", "docx", "html"):
            nothing = os.environ.get("EPY_FAKE_PRODUCES_NOTHING")
            if kwargs.get(fmt) and not nothing:
                target = self._dir / f"{stem}.{fmt}"
                target.write_bytes(b"x")
                made[fmt] = str(target)
            else:
                made[fmt] = None
        out = os.environ.get("EPY_FAKE_CALLS")
        if out:
            pathlib.Path(out).write_text(json.dumps(_CALLS), encoding="utf-8")
        return made
'''


@pytest.fixture()
def source(tmp_path: Path) -> Path:
    doc = tmp_path / "informe.md"
    doc.write_text("# Titulo\n\nUn parrafo.\n", encoding="utf-8")
    return doc


Calls = list[tuple[str, dict[str, Any]]]


def _read(path: Path) -> Calls:
    """Return the recorded sequence, typed rather than raw JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [(str(name), dict(kwargs)) for name, kwargs in raw]


def _fake_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put the stand-in library where a child interpreter will find it."""
    home = tmp_path / "fakelib"
    home.mkdir(parents=True)
    (home / "epy_docs.py").write_text(FAKE, encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(home))
    calls = tmp_path / "calls.json"
    monkeypatch.setenv("EPY_FAKE_CALLS", str(calls))
    return calls


def _out_of_process_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> Calls:
    """Render through a real child interpreter; return what it was told."""
    calls = _fake_on_path(tmp_path, monkeypatch)
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setattr(_docs, "backend_route", _backends.backend_route)
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    _docs.emit_all(
        SPEC, source, tmp_path / "out", ("pdf", "html"), OPTS,
        title="Un proyecto", footer="pie",
    )
    return _read(calls)


def _in_process_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> Calls:
    """Render with the engine imported here; return what it was told."""
    calls = _fake_on_path(tmp_path, monkeypatch)
    # The REAL library may already be in sys.modules -- another test in
    # this suite imports it to check the vocabulary has not drifted --
    # and an import would then hand back that one and render for real.
    # Measured: this test passed alone and failed in company.
    saved = sys.modules.pop("epy_docs", None)
    sys.path.insert(0, str(tmp_path / "fakelib"))
    try:
        import epy_docs  # pyright: ignore[reportMissingImports] - epy_docs is a private commercial package, absent from the public CI by design  # noqa: PLC0415 - the stand-in written above

        monkeypatch.setattr(
            _docs, "load_backend", lambda module, why: epy_docs
        )
        here = _backends.Route("in_process")
        monkeypatch.setattr(_docs, "backend_route", lambda module: here)
        _docs.emit_all(
            SPEC, source, tmp_path / "out", ("pdf", "html"), OPTS,
            title="Un proyecto", footer="pie",
        )
    finally:
        sys.path.remove(str(tmp_path / "fakelib"))
        sys.modules.pop("epy_docs", None)
        if saved is not None:
            sys.modules["epy_docs"] = saved
    return _read(calls)


def test_both_executions_apply_the_same_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> None:
    # The requirement this whole design exists to keep. There is a
    # corpus of documents rendered in process; what reaches the writer
    # must not change because the renderer moved to another one.
    here = _in_process_calls(tmp_path / "a", monkeypatch, source)
    there = _out_of_process_calls(tmp_path / "b", monkeypatch, source)

    def without_dirs(calls: Calls) -> Calls:
        # The output directory is the only field that legitimately
        # differs: the two runs write into different folders.
        cleaned: Calls = []
        for name, kwargs in calls:
            trimmed = dict(kwargs)
            trimmed.pop("output_dir", None)
            cleaned.append((name, trimmed))
        return cleaned

    assert without_dirs(here) == without_dirs(there)
    assert [name for name, _ in here] == [
        "__init__", "set_author", "set_project_info", "add_page_footer",
        "add_markdown_file", "generate",
    ]


def test_the_job_carries_what_the_cover_needs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> None:
    # ePy Docs is the only engine whose entry point takes cover
    # metadata; that is why it is ePy Draft's default. Losing the author
    # across the process boundary would silently ship documents with no
    # author, which has happened before through a different route.
    calls = dict(_out_of_process_calls(tmp_path, monkeypatch, source))
    assert calls["set_author"]["name"].startswith("Ing. Angel")
    assert calls["set_project_info"]["name"] == "Un proyecto"
    assert calls["set_project_info"]["project_type"] == "Structural report"
    assert calls["add_page_footer"]["content"] == "pie"
    assert calls["__init__"]["layout_style"] == "corporate"
    assert calls["__init__"]["language"] == "es"


def test_a_quarto_source_takes_the_other_entry_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> None:
    # Explicit, never guessed from the suffix: the two entry points are
    # different methods and guessing gives one of them the wrong reader.
    opts = RenderOptions(
        appearance="corporate", language="es", source_kind="quarto"
    )
    calls = _fake_on_path(tmp_path, monkeypatch)
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setattr(_docs, "backend_route", _backends.backend_route)
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    _docs.emit_all(SPEC, source, tmp_path / "out", ("html",), opts)
    names = [name for name, _ in _read(calls)]
    assert "add_quarto_file" in names
    assert "add_markdown_file" not in names


def test_a_child_that_exits_zero_and_produces_nothing_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> None:
    # MEASURED in the real library: without Quarto it swallows the
    # failure, logs it at INFO, returns a mapping of None and exits
    # ZERO. The exit code is not the signal; the files on disk are.
    _fake_on_path(tmp_path, monkeypatch)
    monkeypatch.setenv("EPY_FAKE_PRODUCES_NOTHING", "1")
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setattr(_docs, "backend_route", _backends.backend_route)
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    with pytest.raises(_docs.RenderFailedError, match="did not produce"):
        _docs.emit_all(SPEC, source, tmp_path / "out", ("pdf",), OPTS)


def test_a_child_that_fails_reports_its_own_diagnosis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> None:
    # The library's own message is the one a reader can act on, so the
    # child's stderr travels back rather than a generic "render failed".
    monkeypatch.setattr(
        _docs, "_CHILD",
        "import sys; sys.exit(sys.stderr.write('QUARTO GONE'))",
    )
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setattr(_docs, "backend_route", _backends.backend_route)
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    with pytest.raises(_docs.RenderFailedError, match="QUARTO GONE"):
        _docs.emit_all(SPEC, source, tmp_path / "out", ("pdf",), OPTS)


def test_a_child_that_hangs_is_given_up_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> None:
    # A wrong interpreter that never returns must not hang the
    # application for ever.
    monkeypatch.setattr(_docs, "_CHILD", "import time; time.sleep(30)")
    monkeypatch.setattr(_docs, "_CHILD_TIMEOUT", 1.0)
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setattr(_docs, "backend_route", _backends.backend_route)
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    with pytest.raises(_docs.RenderFailedError, match="did not finish"):
        _docs.emit_all(SPEC, source, tmp_path / "out", ("pdf",), OPTS)


def test_an_absent_bibliography_is_refused_before_anything_runs(
    tmp_path: Path, source: Path
) -> None:
    # Built while the job is built, so a typo costs nothing and names
    # itself instead of dying inside a child process.
    with pytest.raises(ValueError, match="Bibliography not found"):
        _docs._job(
            source, tmp_path, ("pdf",), OPTS,
            document_type="report", title=None, client=None, footer="",
            bibliography=tmp_path / "absent.bib", csl=None,
        )


def test_the_job_is_json_serialisable(tmp_path: Path, source: Path) -> None:
    # It crosses a process boundary as JSON. A value that is not
    # serialisable would fail at the boundary and nowhere else, so it
    # would pass every in-process test.
    job = _docs._job(
        source, tmp_path, ("pdf", "docx"), OPTS,
        document_type="report", title="T", client={"name": "C"},
        footer="f", bibliography=None, csl=None,
    )
    assert json.loads(json.dumps(job)) == job


def test_the_chosen_document_kind_reaches_the_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: Path
) -> None:
    # The kind is chosen in a dialog and it is ePy Docs that reads it.
    # Before this it stopped at the dispatcher, which always passed the
    # default -- so a reader who asked for a notebook got a report and
    # no signal, which is the failure RenderOptions exists to refuse.
    from epy_export.epy_suite_connect._adapters import _adapter

    calls = _fake_on_path(tmp_path, monkeypatch)
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setattr(_docs, "backend_route", _backends.backend_route)
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    _adapter.render(
        source, tmp_path / "out",
        engine_id="docs",
        formats=["html"],
        options=RenderOptions(document_type="notebook"),
    )
    constructor = dict(_read(calls))["__init__"]
    assert constructor["document_type"] == "notebook"


def test_asking_another_engine_for_a_document_kind_is_refused(
    tmp_path: Path, source: Path
) -> None:
    # ePy Reports IS a document kind. Asking it for a notebook has no
    # answer, and dropping the field in silence is how a caller comes to
    # believe they asked for something they never got.
    from epy_export.epy_suite_connect._adapters import _adapter

    with pytest.raises(ValueError, match="document_type"):
        _adapter.render(
            source, tmp_path / "out",
            engine_id="reports",
            formats=["html"],
            options=RenderOptions(document_type="notebook"),
        )


def test_a_document_kind_nobody_publishes_is_refused(
    tmp_path: Path, source: Path
) -> None:
    # Symmetric with the appearance check. A typo reaching the writer
    # produces a document of the DEFAULT kind, which looks like a
    # correct render of the wrong thing.
    from epy_export.epy_suite_connect._adapters import _adapter

    with pytest.raises(ValueError, match="not a document kind"):
        _adapter.render(
            source, tmp_path / "out",
            engine_id="docs",
            formats=["html"],
            options=RenderOptions(document_type="memorandum"),
        )
