"""The shared theme: palettes and the stylesheet built from them."""

from __future__ import annotations

from epy_export._ui import _theme


class _App:
    """A stand-in for ``QApplication`` that records the stylesheet."""

    def __init__(self) -> None:
        self.sheet: str | None = None

    def setStyleSheet(self, sheet: str) -> None:  # noqa: N802 - Qt spelling
        self.sheet = sheet

    def styleSheet(self) -> str:  # noqa: N802 - Qt spelling
        return self.sheet or ""


def test_names_are_the_standard_layouts() -> None:
    assert _theme.bundled_names() == [
        "corporate",
        "academic",
        "classic",
        "minimal",
        "technical",
        "craft",
        "handwritten",
        "creative",
        "professional",
        "scientific",
        "quotation",
        "craft_dark",
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


def test_apply_chrome_appends_and_replaces_the_block() -> None:
    app = _App()
    app.setStyleSheet("document theme")
    _theme.apply_chrome(app, "craft")
    first = app.sheet
    assert "document theme" in first
    assert "ePy craft chrome" in first
    _theme.apply_chrome(app, "craft_dark")
    assert app.sheet.count("ePy craft chrome") == 1
    assert "document theme" in app.sheet
    _theme.apply_chrome(None)


def test_a_user_theme_round_trips(tmp_path, monkeypatch) -> None:
    """A custom palette is saved, offered, applied and deleted."""
    monkeypatch.setenv("EPY_SUITE_THEMES_DIR", str(tmp_path))
    _theme.reload_user_themes()
    colors = dict(_theme.palette("craft"))
    colors["accent"] = "#123456"
    theme_id = _theme.save_user_theme("My custom theme", colors)
    assert theme_id in _theme.names()
    assert _theme.display_name(theme_id) == "My custom theme"
    assert _theme.palette(theme_id)["accent"] == "#123456"
    assert "#123456" in _theme.qss(theme_id)
    _theme.delete_user_theme(theme_id)
    assert theme_id not in _theme.names()


def test_each_app_owns_its_theme_catalogue(tmp_path, monkeypatch) -> None:
    """A theme created in one app is invisible in another."""
    monkeypatch.setenv("EPY_SUITE_THEMES_DIR", str(tmp_path))
    try:
        _theme.use_namespace("app_one")
        _theme.save_user_theme("Only here", dict(_theme.palette("craft")))
        _theme.use_namespace("app_two")
        assert "only-here" not in _theme.names()
        _theme.use_namespace("app_one")
        assert "only-here" in _theme.names()
        assert _theme.document_layout("only-here") == "corporate"
    finally:
        _theme.use_namespace("")
        _theme.reload_user_themes()
