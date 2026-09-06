"""Can this process reach ePy Docs, and how?

Asking only whether the module imports HERE is a question with a
permanently wrong answer inside a frozen bundle: PyInstaller closes
``sys.path`` to the bundle, so a package installed in the user's own
Python is invisible however the spec is written. Every application asked
it that way, so every "export through ePy Docs" entry was greyed out in
every shipped executable -- including ePy Draft's DEFAULT engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from epy_export._core import _backends


def test_an_importable_engine_is_reached_in_this_process() -> None:
    # A source checkout: the cheapest route, and the one that needs no
    # interpreter hint at all.
    route = _backends.backend_route("epy_export")
    assert route.mode == "in_process"
    assert route.reachable
    assert route.python == ""


def test_an_absent_engine_with_no_hint_is_not_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_backends.ENV_DOCS_PYTHON, raising=False)
    route = _backends.backend_route("epy_docs_that_is_not_installed")
    assert route.mode == "none"
    assert not route.reachable


def test_the_hint_reaches_an_engine_this_process_cannot_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # THE discriminating case, and the whole reason this exists: the
    # module cannot be imported here and an interpreter that has it is
    # named. Every detection in the suite answered "not installed" to
    # exactly this, which is the state of every frozen bundle.
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    route = _backends.backend_route("epy_docs")
    assert route.mode == "subprocess"
    assert route.reachable
    assert route.python == sys.executable


def test_importing_here_wins_over_the_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Cheaper, and it is this process's own version rather than whatever
    # another interpreter happens to carry.
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    assert _backends.backend_route("epy_export").mode == "in_process"


def test_a_hint_naming_an_interpreter_that_is_not_there_is_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A stale variable from an install that was removed. Answering
    # "subprocess" would trade a greyed menu entry for one that fails
    # on click, which is worse.
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setenv(
        _backends.ENV_DOCS_PYTHON, str(tmp_path / "gone" / "python.exe")
    )
    assert _backends.backend_route("epy_docs").mode == "none"


def test_only_the_engine_that_can_live_elsewhere_takes_a_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The other three engines ARE the applications this bundle carries.
    # A hint would point at an interpreter that does not have them, and
    # the render would fail after the menu promised it.
    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    for module in ("epy_reports", "epy_slides", "epy_papers"):
        assert _backends.backend_route(module).mode == "none", module


def test_the_variable_has_one_home() -> None:
    # ePy Studio publishes it and the applications read it, and neither
    # package depends on the other. Named here, where both already
    # depend, a rename cannot leave one side listening for a variable
    # the other stopped setting.
    import epy_export

    assert epy_export.ENV_DOCS_PYTHON == "EPY_DOCS_PYTHON"
    assert "ENV_DOCS_PYTHON" in epy_export.__all__


def test_the_dispatcher_offers_what_the_route_can_reach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The consequence that matters to a person: the menu entry. Asking
    # the import rather than the route is what greyed it out in every
    # shipped executable, ePy Draft's default engine included.
    from epy_export.epy_suite_connect._adapters import _adapter

    monkeypatch.setattr(_backends, "backend_present", lambda module: False)
    monkeypatch.delenv(_backends.ENV_DOCS_PYTHON, raising=False)
    assert not _adapter.available("docs")
    assert "docs" not in _adapter.installed()

    monkeypatch.setenv(_backends.ENV_DOCS_PYTHON, sys.executable)
    assert _adapter.available("docs")
    assert "docs" in _adapter.installed()
