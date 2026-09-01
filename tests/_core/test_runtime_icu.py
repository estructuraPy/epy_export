"""The ICU pin, and the one thing it could not say before.

``pin_system_icu()`` has to run BEFORE Qt loads: Qt resolves ICU at load
time, and on a conda machine the loader binds a copy whose exports do
not match. Get the order wrong and every ``PySide6.Qt*`` import dies
with a raw Windows DLL error that names nothing -- not the pin, not the
ordering, not the package that should have been imported first.

Two shipped example scripts got that order wrong and failed exactly
that way. The scripts are fixed; this is about the pin being able to
SAY so when it happens again somewhere nobody has looked yet.
"""

from __future__ import annotations

import sys
import warnings

import pytest

from epy_export._core._runtime import pin_system_icu


def test_pinning_after_qt_is_already_loaded_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The whole point. Without this warning the next script that gets
    # the order wrong reports "DLL load failed" and the person has no
    # thread to pull: the message names no module, no package and no
    # ordering rule.
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", object())
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pin_system_icu()
    assert len(caught) == 1
    assert issubclass(caught[0].category, RuntimeWarning)
    said = str(caught[0].message)
    assert "PySide6" in said
    assert "import" in said


def test_pinning_before_qt_loads_is_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The control. A pin that warned unconditionally would satisfy the
    # test above while making every correct program noisy -- and a
    # warning every correct program prints is a warning nobody reads.
    monkeypatch.delitem(sys.modules, "PySide6.QtCore", raising=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pin_system_icu()
    assert not caught


def test_the_warning_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A process that already imported Qt successfully -- off conda, or
    # where the system ICU won anyway -- must keep working. The warning
    # is for the run that is about to fail mysteriously, not a refusal
    # of the run that is fine.
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", object())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pin_system_icu()
