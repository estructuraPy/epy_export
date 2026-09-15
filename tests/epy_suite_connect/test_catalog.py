"""The catalog of engines this family knows how to reach."""

from __future__ import annotations

import pytest

from epy_export.epy_suite_connect._data._catalog import ENGINES, engine


def test_a_known_engine_id_returns_its_row() -> None:
    assert engine("reports") is ENGINES[0]


def test_an_unknown_engine_id_names_itself_and_what_is_available() -> None:
    # A typo in a catalog file otherwise surfaces much later, as a
    # document that was never produced -- the message has to name both
    # the typo AND what the caller could have meant.
    with pytest.raises(KeyError) as raised:
        engine("reportz")
    message = str(raised.value)
    assert "reportz" in message
    assert "reports" in message
