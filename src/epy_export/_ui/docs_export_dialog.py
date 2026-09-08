"""The window that configures an export through ePy Docs.

One window for the three editors. What differs between them is passed
in: the registry scope to remember choices under, and the two
translation callables the owning application already has.

It is built WITHOUT the engine. That is not an optimisation: inside a
frozen bundle ePy Docs can never be imported, so a constructor that
asked the engine for its layouts could not run at all, and the export
entry stayed unreachable even once availability was answered correctly.
The vocabularies come from :data:`epy_export.APPEARANCES` and
:data:`epy_export.DOCUMENT_TYPES`, which every application carries.

This module imports Qt at module level, so whatever imports it must
have called :func:`epy_export.pin_system_icu` first. Every application
in the family does that in its own ``__init__``; a script that does not
gets ``WinError 127`` from ``QtCore`` under conda and no other clue.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .._core._identity import ORGANIZATION
from ..epy_suite_connect._contract._engine import APPEARANCES, DOCUMENT_TYPES

__all__ = ["DocsExportDialog", "RenderWorker"]

LAYOUT_KEY = "docs_layout"
DOCTYPE_KEY = "docs_doctype"
OUTDIR_KEY = "docs_outdir"


def _identity(text: str) -> str:
    """Return the text unchanged, for a caller with no translations."""
    return text


class RenderWorker(QThread):
    """Runs one render off the interface thread.

    The render itself may take minutes and may start a child
    interpreter; doing it on the GUI thread freezes the window for the
    whole of it.

    Signals:
        finished_ok: Emitted with the output directory on success.
        finished_err: Emitted with the message on failure.
    """

    finished_ok = Signal(str)
    finished_err = Signal(str)

    def __init__(
        self,
        render: Callable[..., Any],
        source_path: Path,
        layout: str,
        document_type: str,
        output_dir: Path,
        pdf: bool,
        html: bool,
        docx: bool = False,
    ) -> None:
        """Store what to render and how.

        Args:
            render: The owning application's bridge function. Injected
                rather than reached for, so each application keeps its
                own refusal message -- "install it, or choose another
                engine" is right for a caller and useless for a reader
                who has to buy the engine.
            source_path: The document to render.
            layout: Layout name.
            document_type: Document kind.
            output_dir: Where the results go.
            pdf: Request PDF output.
            html: Request HTML output.
            docx: Request Word output.
        """
        super().__init__()
        self._render = render
        self._source_path = source_path
        self._layout = layout
        self._document_type = document_type
        self._output_dir = output_dir
        self._pdf = pdf
        self._html = html
        self._docx = docx

    def run(self) -> None:
        """Execute the render; emit the outcome either way."""
        try:
            self._render(
                source_path=self._source_path,
                layout=self._layout,
                document_type=self._document_type,
                output_dir=self._output_dir,
                pdf=self._pdf,
                html=self._html,
                docx=self._docx,
            )
            self.finished_ok.emit(str(self._output_dir))
        except Exception as exc:  # noqa: BLE001 - the message is the point
            self.finished_err.emit(str(exc))


class DocsExportDialog(QDialog):
    """Layout, document kind, destination and formats for one export.

    Remembers the three choices under the owning application's own
    registry scope, so two editors on one machine do not overwrite each
    other's last-used values.
    """

    def __init__(
        self,
        source_path: Path,
        *,
        app_name: str,
        translate: Callable[[str], str] | None = None,
        translate_widget: Callable[[QWidget], None] | None = None,
        title: str = "Export via epy_docs",
        parent: QWidget | None = None,
    ) -> None:
        """Build the widgets and restore what was chosen last time.

        Args:
            source_path: The file being exported.
            app_name: The application's own name, as its registry scope
                spells it.
            translate: The application's string translator, for the
                strings this window builds at call time.
            translate_widget: The application's widget-tree translator,
                for the labels built above.
            title: The window title.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._tr = translate or _identity
        self.setWindowTitle(title)
        self.setMinimumWidth(460)

        self._source_path = source_path
        self._settings = QSettings(ORGANIZATION, app_name)

        layouts = list(APPEARANCES)
        doc_types = list(DOCUMENT_TYPES)

        self._combo_layout = QComboBox()
        self._combo_layout.addItems(layouts)
        saved_layout = str(self._settings.value(LAYOUT_KEY, "corporate"))
        if saved_layout in layouts:
            self._combo_layout.setCurrentText(saved_layout)

        self._combo_doctype = QComboBox()
        self._combo_doctype.addItems(doc_types)
        saved_doctype = str(self._settings.value(DOCTYPE_KEY, "report"))
        if saved_doctype in doc_types:
            self._combo_doctype.setCurrentText(saved_doctype)

        default_outdir = str(source_path.parent / "results")
        saved_outdir = str(self._settings.value(OUTDIR_KEY, default_outdir))
        self._edit_outdir = QLineEdit(saved_outdir)
        self._btn_browse = QPushButton("Browse…")
        self._btn_browse.clicked.connect(self._browse_outdir)
        outdir_row = QHBoxLayout()
        outdir_row.addWidget(self._edit_outdir)
        outdir_row.addWidget(self._btn_browse)

        self._chk_pdf = QCheckBox("PDF")
        self._chk_pdf.setChecked(True)
        self._chk_html = QCheckBox("HTML")
        self._chk_html.setChecked(True)
        self._chk_docx = QCheckBox("DOCX")
        self._chk_docx.setChecked(False)
        checks_row = QHBoxLayout()
        checks_row.addWidget(self._chk_pdf)
        checks_row.addWidget(self._chk_html)
        checks_row.addWidget(self._chk_docx)
        checks_row.addStretch()

        form = QFormLayout()
        form.addRow("Layout:", self._combo_layout)
        form.addRow("Document type:", self._combo_doctype)
        form.addRow("Output directory:", outdir_row)
        form.addRow("Output formats:", checks_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self._lbl_status = QLabel("")
        self._lbl_status.setVisible(False)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self._lbl_status)
        root.addWidget(buttons)
        if translate_widget is not None:
            translate_widget(self)

    def _browse_outdir(self) -> None:
        """Open a directory picker and update the destination field."""
        start = self._edit_outdir.text() or str(self._source_path.parent)
        chosen = QFileDialog.getExistingDirectory(
            self, self._tr("Select output directory"), start
        )
        if chosen:
            self._edit_outdir.setText(chosen)

    @property
    def layout_name(self) -> str:
        """Selected layout name."""
        return self._combo_layout.currentText()

    @property
    def document_type(self) -> str:
        """Selected document kind."""
        return self._combo_doctype.currentText()

    @property
    def output_dir(self) -> Path:
        """Selected output directory."""
        return Path(self._edit_outdir.text())

    @property
    def export_pdf(self) -> bool:
        """Whether PDF was asked for."""
        return self._chk_pdf.isChecked()

    @property
    def export_html(self) -> bool:
        """Whether HTML was asked for."""
        return self._chk_html.isChecked()

    @property
    def export_docx(self) -> bool:
        """Whether Word output was asked for."""
        return self._chk_docx.isChecked()

    def persist_settings(self) -> None:
        """Remember the three choices for next time."""
        self._settings.setValue(LAYOUT_KEY, self.layout_name)
        self._settings.setValue(DOCTYPE_KEY, self.document_type)
        self._settings.setValue(OUTDIR_KEY, str(self.output_dir))
