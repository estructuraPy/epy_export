"""The shared theme: palettes and the stylesheet built from them."""

from __future__ import annotations

from epy_export._ui import _theme


class _App:
    """A stand-in for ``QApplication`` that records the stylesheet."""

    def __init__(self) -> None:
        self.sheet: str | None = None

    def setStyleSheet(self, sheet: str) -> None:  # noqa: N802 - Qt spelling
        self.sheet = sheet


def test_names_are_the_standard_layouts() -> None:
    assert _theme.names() == [
        "corporate",
        "academic",
        "classic",
        "minimal",
        "technical",
    ]


def test_every_palette_is_complete() -> None:
    for name in _theme.names():
        table = _theme.palette(name)
        assert set(table) == {
            "primary",
            "accent",
            "surface",
            "surface_alt",
            "text",
            "muted",
            "border",
            "on_primary",
        }


def test_an_unknown_theme_falls_back() -> None:
    assert _theme.palette("nope") == _theme.palette(_theme.DEFAULT_THEME)


def test_qss_carries_the_palette_and_the_widgets() -> None:
    sheet = _theme.qss("technical")
    assert _theme.PALETTES["technical"]["accent"] in sheet
    assert "QPushButton" in sheet
    assert "QLineEdit" in sheet


def test_apply_sets_the_stylesheet() -> None:
    app = _App()
    _theme.apply(app)
    assert app.sheet == _theme.qss(_theme.DEFAULT_THEME)


def test_apply_without_an_application_is_a_no_op() -> None:
    _theme.apply(None)
