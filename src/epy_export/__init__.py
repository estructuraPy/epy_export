"""The shared export engine of the ePy document family.

epy_reports, epy_slides, epy_papers, epy_draft and epy_docs make
different documents through genuinely different technology -- Paged.js,
reveal.js, LaTeX -- and this library does not try to make them one. What
it owns is everything they were doing IDENTICALLY in separate copies:
stamping a finished PDF, reading front matter, pinning ICU before Qt
loads, driving a headless print, deciding whether a sibling is here, and
naming which engine turns a source into which format.

The measured starting point: ``_pdf_footer`` existed twice as 546 lines
differing in eight, all of them comment text; the front-matter parser
existed twice byte for byte; the ICU workaround three times, two of its
copies documenting that they mirrored the first; and the bridge to
epy_docs twice, incompatibly, with two of the four apps unable to reach
it at all. A fix to any one of those reached the others only if somebody
remembered.

**Nothing here imports a sibling at module level.** Every engine is
reached by module name at call time and reported absent by name, so this
library loads on a machine with none of the family installed and still
says what would be needed. That is also what keeps the dependency graph
a tree: applications import this, this imports no application.

**Nothing here imports Qt or pypdf at module level either.** The heavy
work lives behind extras (``epy_export[pdf]``, ``epy_export[qt]``) and
is imported inside the functions that need it, so a caller who only
wants to read a document's front matter pays nothing for the rest.
"""

from __future__ import annotations

from ._core._backends import (
    ENV_DOCS_PYTHON,
    BackendUnavailableError,
    RenderFailedError,
    Route,
    backend_present,
    backend_route,
    load_backend,
)
from ._core._files import write_text_atomic
from ._core._frontmatter import (
    is_truthy,
    parse_front_matter,
    parse_header_cells,
    set_metadata_field,
    strip_front_matter,
)
from ._core._identity import LEGACY_ORGANIZATIONS, ORGANIZATION
from ._core._pdf_stamp import (
    add_footer,
    add_header,
    add_metadata,
    add_page_background,
    add_watermark,
    append_pdf,
    extract_anchor_pages,
    prepend_pdf,
    require_pdfs,
    scale_pages_to_width,
)
from ._core._qt_print import (
    eval_js,
    print_to_pdf,
    pump,
    remove_temp,
    wait_until,
)
from ._core._runtime import pin_system_icu
from .epy_suite_connect._adapters._adapter import (
    available,
    installed,
    render,
    understood_by,
)
from .epy_suite_connect._contract._engine import (
    APPEARANCES,
    DOCUMENT_TYPES,
    Engine,
    EngineUnavailableError,
    RenderOptions,
)
from .epy_suite_connect._data._catalog import ENGINES, engine, engine_ids

__version__ = "0.4.0"
__author__ = "Ing. Angel Navarro-Mora M.Sc."

__all__ = [
    "APPEARANCES",
    "DOCUMENT_TYPES",
    "DocsExportDialog",
    "ENV_DOCS_PYTHON",
    "BackendUnavailableError",
    "ENGINES",
    "Engine",
    "EngineUnavailableError",
    "LEGACY_ORGANIZATIONS",
    "ORGANIZATION",
    "RenderFailedError",
    "RenderWorker",
    "RenderOptions",
    "Route",
    "add_footer",
    "add_header",
    "add_metadata",
    "add_page_background",
    "add_watermark",
    "append_pdf",
    "available",
    "backend_present",
    "backend_route",
    "engine",
    "engine_ids",
    "eval_js",
    "extract_anchor_pages",
    "installed",
    "is_truthy",
    "load_backend",
    "parse_front_matter",
    "parse_header_cells",
    "pin_system_icu",
    "prepend_pdf",
    "print_to_pdf",
    "pump",
    "remove_temp",
    "render",
    "require_pdfs",
    "scale_pages_to_width",
    "set_metadata_field",
    "strip_front_matter",
    "understood_by",
    "wait_until",
    "write_text_atomic",
]

#: Qt is NOT imported when this package is. Every consuming library calls
#: ``pin_system_icu()`` from its own ``__init__`` and PySide6 only loads
#: correctly AFTER that call, so importing the dialog eagerly here would
#: pull Qt in before any consumer could pin, and break the pin suite-wide.
#: These two are therefore published lazily (PEP 562): the names are part
#: of the public API, the import cost is paid by whoever touches them.
_QT_EXPORTS = frozenset({"DocsExportDialog", "RenderWorker"})


def __getattr__(name: str) -> object:
    """Resolve the Qt-backed exports on first use."""
    if name in _QT_EXPORTS:
        from epy_export._ui import docs_export_dialog

        return getattr(docs_export_dialog, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
