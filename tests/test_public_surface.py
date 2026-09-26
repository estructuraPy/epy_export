"""The facade's public surface, as a sibling library may import it.

The suite forbids one library reaching another through a private path, so
the pieces epy_reports, epy_slides and epy_papers need are published here
by name: the backend module, the ePy Docs adapter module, and -- through a
PEP 562 ``__getattr__`` -- the shared dialog module and its two Qt-backed
classes. The two Qt names CANNOT be a top-level import: PySide6 only loads
after ``pin_system_icu()`` has run and epy_export merely DEFINES it, so an
eager import here would load Qt before any consumer could pin and break
the pin for the whole suite.

That laziness is easy to destroy by "simplifying" the ``__getattr__``,
which is why each branch is measured rather than trusted.
"""

from __future__ import annotations

import pytest

from epy_export._core._runtime import pin_system_icu

# Before any PySide6 import in this process, exactly as the consumers do.
pin_system_icu()


def test_the_engine_backends_module_is_public() -> None:
    from epy_export import backends
    from epy_export._core import _backends

    assert backends is _backends


def test_the_docs_engine_adapter_module_is_public() -> None:
    from epy_export import docs_adapter
    from epy_export.epy_suite_connect._adapters import _docs

    assert docs_adapter is _docs


def test_the_dialog_module_is_public() -> None:
    import epy_export
    from epy_export._ui import docs_export_dialog

    assert epy_export.docs_export_dialog is docs_export_dialog


def test_the_qt_names_resolve_to_the_dialog_classes() -> None:
    import epy_export
    from epy_export._ui import docs_export_dialog

    assert epy_export.DocsExportDialog is docs_export_dialog.DocsExportDialog
    assert epy_export.RenderWorker is docs_export_dialog.RenderWorker


def test_an_unknown_attribute_still_raises() -> None:
    import epy_export

    with pytest.raises(AttributeError):
        _ = epy_export.not_a_public_name
