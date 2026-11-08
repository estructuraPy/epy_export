"""The shared header keeps its labels translatable."""

from __future__ import annotations

from epy_export._core._runtime import pin_system_icu

pin_system_icu()

from epy_export._ui.app_header import _labels  # noqa: E402


def test_spanish_labels_are_complete() -> None:
    labels = _labels("es")
    assert labels["guide"] == "Guía"
    assert labels["assistant"] == "Asistente"
    assert "guía" in labels["guide_tip"]
    assert "asistente" in labels["assistant_tip"]


def test_unknown_language_falls_back_to_english() -> None:
    assert _labels("xx") == _labels("en")
