"""Asking whether an engine is here, and getting hold of it."""

from __future__ import annotations

import sys

import pytest

from epy_export._core import _backends


def test_a_present_package_is_reported_present() -> None:
    assert _backends.backend_present("json")


def test_an_absent_package_is_reported_absent() -> None:
    assert not _backends.backend_present("epy_not_a_real_package")


def test_asking_does_not_import(monkeypatch: pytest.MonkeyPatch) -> None:
    # The property the whole design rests on: a menu asks about four
    # engines while it is being built, and importing one to find out
    # whether it exists pulls its entire stack in to draw a menu item.
    monkeypatch.delitem(sys.modules, "wave", raising=False)
    assert _backends.backend_present("wave")
    assert "wave" not in sys.modules


def test_a_bare_directory_is_not_a_backend(tmp_path, monkeypatch) -> None:
    # A namespace package -- any directory of that name on the path,
    # PEP 420 -- satisfies find_spec and imports to an empty module, so
    # the caller reaches for an attribute that was never there. The
    # loader check is what tells the two apart.
    (tmp_path / "epy_phantom").mkdir()
    monkeypatch.syspath_prepend(str(tmp_path))
    import importlib.util

    assert importlib.util.find_spec("epy_phantom") is not None
    assert not _backends.backend_present("epy_phantom")


def test_loading_an_absent_backend_names_it_and_the_reason() -> None:
    with pytest.raises(_backends.BackendUnavailableError) as raised:
        _backends.load_backend("epy_not_real", why="rendering a deck")
    message = str(raised.value)
    assert "epy_not_real" in message
    assert "rendering a deck" in message


def test_loading_a_present_backend_returns_it() -> None:
    # The control. Without it, raising unconditionally satisfies the
    # test above and the loader is retired.
    assert _backends.load_backend("json", why="x").dumps({}) == "{}"


def test_the_two_failures_are_different_types() -> None:
    # They were one. The check that refuses a truncated PDF raised the
    # "engine unavailable" error, so a partial document was reported as
    # "epy_docs is not installed" -- one of those is fixed by installing
    # something and the other never is.
    assert not issubclass(
        _backends.RenderFailedError, _backends.BackendUnavailableError
    )
    assert not issubclass(
        _backends.BackendUnavailableError, _backends.RenderFailedError
    )


def test_the_engine_name_and_the_backend_name_are_one_condition() -> None:
    # They were two classes for one fact, and a consumer's test proved
    # why that is a defect: it asked for EngineUnavailableError and got
    # BackendUnavailableError, raised two frames deeper. A caller cannot
    # know which of two names to catch, so it catches one and the other
    # escapes.
    from epy_export import BackendUnavailableError, EngineUnavailableError

    assert EngineUnavailableError is BackendUnavailableError


def test_a_render_failure_is_still_a_different_condition() -> None:
    # The control for the merge above. Collapsing every error into one
    # name would satisfy that test too, and would undo the split that
    # stopped a truncated PDF being reported as "not installed".
    from epy_export import BackendUnavailableError, RenderFailedError

    assert RenderFailedError is not BackendUnavailableError
