"""One window for three editors, and it builds without the engine.

The dialog that configures an ePy Docs export used to ask the ENGINE
for its layouts and document kinds in its constructor. Inside a frozen
bundle the engine can never be imported, so the window could not be
built at all and the export entry was unreachable even once
availability was answered correctly.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from epy_export import APPEARANCES, DOCUMENT_TYPES
from epy_export._core._runtime import pin_system_icu

# Qt does not import at all in a conda environment until ICU is pinned,
# which is what that function is for. Before any PySide6 import here.
pin_system_icu()


class _Blocker:
    """Makes ``epy_docs`` genuinely unimportable, as a bundle does."""

    def find_spec(self, name, path=None, target=None):  # noqa: ANN001, ANN201
        if name == "epy_docs" or name.startswith("epy_docs."):
            raise ImportError("epy_docs is not importable in this process")
        return None


@pytest.fixture()
def engine_hidden():
    """Hide the engine from every import in this process."""
    saved = sys.modules.pop("epy_docs", None)
    blocker = _Blocker()
    sys.meta_path.insert(0, blocker)
    try:
        yield
    finally:
        sys.meta_path.remove(blocker)
        if saved is not None:
            sys.modules["epy_docs"] = saved


@pytest.fixture(scope="module")
def qt_app():
    """One offscreen QApplication for this file."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture()
def scratch_settings(tmp_path, monkeypatch):
    """Send QSettings to an INI file so the real registry is untouched."""
    from PySide6 import QtCore

    real = QtCore.QSettings

    def scratch(organisation: str, name: str) -> object:
        return real(
            str(tmp_path / f"{organisation}__{name}.ini"),
            real.Format.IniFormat,
        )

    monkeypatch.setattr(QtCore, "QSettings", scratch)
    from epy_export._ui import docs_export_dialog as module

    monkeypatch.setattr(module, "QSettings", scratch)
    return scratch


def _dialog(tmp_path: Path, app_name: str = "epy_slides"):
    from epy_export._ui.docs_export_dialog import DocsExportDialog

    source = tmp_path / "documento.md"
    source.write_text("# T\n", encoding="utf-8")
    return DocsExportDialog(source, app_name=app_name)


def test_it_is_built_with_no_engine_on_the_machine(
    qt_app, scratch_settings, engine_hidden, tmp_path: Path
) -> None:
    dialog = _dialog(tmp_path)
    assert dialog.windowTitle()
    assert dialog.output_dir == tmp_path / "results"


def test_both_combos_carry_the_family_vocabulary(
    qt_app, scratch_settings, engine_hidden, tmp_path: Path
) -> None:
    dialog = _dialog(tmp_path)
    layouts = [
        dialog._combo_layout.itemText(index)
        for index in range(dialog._combo_layout.count())
    ]
    kinds = [
        dialog._combo_doctype.itemText(index)
        for index in range(dialog._combo_doctype.count())
    ]
    assert layouts == list(APPEARANCES)
    assert kinds == list(DOCUMENT_TYPES)


def test_the_defaults_are_pdf_and_html(
    qt_app, scratch_settings, tmp_path: Path
) -> None:
    dialog = _dialog(tmp_path)
    assert dialog.export_pdf is True
    assert dialog.export_html is True
    assert dialog.export_docx is False


def test_each_application_remembers_in_its_own_scope(
    qt_app, scratch_settings, tmp_path: Path
) -> None:
    # Two editors on one machine must not overwrite each other's
    # last-used values, which is why the scope is passed in rather than
    # fixed. The window is the same; the memory is not.
    slides = _dialog(tmp_path, "epy_slides")
    slides._combo_layout.setCurrentText("academic")
    slides.persist_settings()

    papers = _dialog(tmp_path, "epy_papers")
    assert papers.layout_name == "corporate"

    again = _dialog(tmp_path, "epy_slides")
    assert again.layout_name == "academic"


def test_the_choices_survive_the_window(
    qt_app, scratch_settings, tmp_path: Path
) -> None:
    dialog = _dialog(tmp_path)
    dialog._combo_layout.setCurrentText("technical")
    dialog._combo_doctype.setCurrentText("notebook")
    dialog.persist_settings()
    assert _dialog(tmp_path).layout_name == "technical"
    assert _dialog(tmp_path).document_type == "notebook"


def test_a_translator_is_optional(
    qt_app, scratch_settings, tmp_path: Path
) -> None:
    # ePy Papers has no translation for these strings yet. A window that
    # required one would refuse to open there.
    dialog = _dialog(tmp_path, "epy_papers")
    assert dialog.windowTitle() == "Export via epy_docs"


def test_browse_outdir_updates_the_field_when_a_directory_is_chosen(
    qt_app, scratch_settings, tmp_path: Path, monkeypatch
) -> None:
    # Also the only call in this file that reaches self._tr(...), which
    # a dialog built with no translator resolves to _identity.
    from epy_export._ui import docs_export_dialog as module

    dialog = _dialog(tmp_path)
    chosen = str(tmp_path / "chosen")
    monkeypatch.setattr(
        module.QFileDialog,
        "getExistingDirectory",
        staticmethod(lambda *_a, **_k: chosen),
    )

    dialog._browse_outdir()

    assert dialog.output_dir == Path(chosen)


def test_browse_outdir_leaves_the_field_alone_when_cancelled(
    qt_app, scratch_settings, tmp_path: Path, monkeypatch
) -> None:
    from epy_export._ui import docs_export_dialog as module

    dialog = _dialog(tmp_path)
    original = dialog.output_dir
    monkeypatch.setattr(
        module.QFileDialog,
        "getExistingDirectory",
        staticmethod(lambda *_a, **_k: ""),
    )

    dialog._browse_outdir()

    assert dialog.output_dir == original


def test_a_widget_translator_is_applied_after_construction(
    qt_app, scratch_settings, tmp_path: Path
) -> None:
    from epy_export._ui.docs_export_dialog import DocsExportDialog

    source = tmp_path / "documento.md"
    source.write_text("# T\n", encoding="utf-8")
    seen: list[object] = []

    dialog = DocsExportDialog(
        source, app_name="epy_reports", translate_widget=seen.append,
    )

    assert seen == [dialog]


def test_the_worker_reports_both_outcomes(
    qt_app, tmp_path: Path
) -> None:
    # Run directly, with no event loop: the property is what it emits,
    # not how a thread schedules it.
    from epy_export._ui.docs_export_dialog import RenderWorker

    def _ok(**kwargs: object) -> None:
        return None

    def _boom(**kwargs: object) -> None:
        raise RuntimeError("the render exploded")

    seen: list[str] = []
    worker = RenderWorker(
        _ok, tmp_path / "a.md", "corporate", "report", tmp_path / "out",
        True, False,
    )
    worker.finished_ok.connect(seen.append)
    worker.run()
    assert seen == [str(tmp_path / "out")]

    errors: list[str] = []
    failing = RenderWorker(
        _boom, tmp_path / "a.md", "corporate", "report", tmp_path / "out",
        True, False,
    )
    failing.finished_err.connect(errors.append)
    failing.run()
    assert errors == ["the render exploded"]


def test_the_worker_asks_for_exactly_what_was_chosen(
    qt_app, tmp_path: Path
) -> None:
    from epy_export._ui.docs_export_dialog import RenderWorker

    seen: dict[str, object] = {}

    def _record(**kwargs: object) -> None:
        seen.update(kwargs)

    RenderWorker(
        _record, tmp_path / "a.md", "academic", "paper", tmp_path / "out",
        False, True, True,
    ).run()
    assert seen["layout"] == "academic"
    assert seen["document_type"] == "paper"
    assert seen["pdf"] is False
    assert seen["html"] is True
    assert seen["docx"] is True
