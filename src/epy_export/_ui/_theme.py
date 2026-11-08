"""One palette and one stylesheet for the whole family.

The default Qt style on Windows is the one shipped with the operating
system, and it is the reason every ePy window looked like a program from
2001. This module does not restyle each widget by hand: it builds ONE
stylesheet from a small palette and hands it to ``QApplication``, so a
window and every dialog it opens share the same surface, accent and
spacing.

The palettes are named after the document layouts the suite already
standardises (``corporate``, ``academic``, ``classic``, ``minimal``,
``technical``), so choosing a look is choosing one of the names a reader
already meets in epy_docs. Nothing here imports Qt: :func:`apply` takes
any object with ``setStyleSheet``, which keeps this module safe to import
from a package that never draws anything.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_THEME",
    "PALETTES",
    "apply",
    "apply_chrome",
    "bundled_names",
    "delete_user_theme",
    "display_name",
    "is_user_theme",
    "names",
    "palette",
    "qss",
    "reload_user_themes",
    "save_user_theme",
    "user_theme_ids",
    "user_themes_dir",
    "namespace",
    "use_namespace",
    "document_layout",
    "validate_palette",
]

Theme = dict[str, str]

PALETTES: dict[str, Theme] = {
    "corporate": {
        "primary": "#00217e",
        "accent": "#0b5cff",
        "surface": "#ffffff",
        "surface_alt": "#f4f6fb",
        "text": "#111827",
        "muted": "#5f636f",
        "border": "#d5daea",
        "on_primary": "#ffffff",
    },
    "academic": {
        "primary": "#1f4e5f",
        "accent": "#2a9d8f",
        "surface": "#ffffff",
        "surface_alt": "#eef5f4",
        "text": "#132a30",
        "muted": "#55707a",
        "border": "#cfe0dd",
        "on_primary": "#ffffff",
    },
    "classic": {
        "primary": "#6b4f2a",
        "accent": "#a4713b",
        "surface": "#fffdf8",
        "surface_alt": "#f6efe3",
        "text": "#2b2014",
        "muted": "#7a6a55",
        "border": "#e3d6c2",
        "on_primary": "#ffffff",
    },
    "minimal": {
        "primary": "#222222",
        "accent": "#4a4a4a",
        "surface": "#ffffff",
        "surface_alt": "#f3f3f3",
        "text": "#191919",
        "muted": "#6b6b6b",
        "border": "#dedede",
        "on_primary": "#ffffff",
    },
    "technical": {
        "primary": "#0f3d3e",
        "accent": "#00a8a8",
        "surface": "#ffffff",
        "surface_alt": "#eef6f6",
        "text": "#0d2425",
        "muted": "#4f6b6c",
        "border": "#c9dede",
        "on_primary": "#ffffff",
    },
    "craft": {
        "primary": "#0b1b3a",
        "accent": "#1d5fd1",
        "surface": "#ffffff",
        "surface_alt": "#e9eef6",
        "text": "#0f172a",
        "muted": "#475569",
        "border": "#7c8da8",
        "on_primary": "#ffffff",
    },
    "handwritten": {
        "primary": "#464646",
        "accent": "#696969",
        "surface": "#f0f0f0",
        "surface_alt": "#ebe6d7",
        "text": "#323232",
        "muted": "#5a5a5a",
        "border": "#a9a9a9",
        "on_primary": "#ffffff",
    },
    "creative": {
        "primary": "#6d28d9",
        "accent": "#f59e0b",
        "surface": "#fffdf9",
        "surface_alt": "#f5edff",
        "text": "#241b32",
        "muted": "#6b5b7a",
        "border": "#c9b6e4",
        "on_primary": "#ffffff",
    },
    "professional": {
        "primary": "#1e3a5f",
        "accent": "#2f7d8c",
        "surface": "#ffffff",
        "surface_alt": "#eef3f7",
        "text": "#14202b",
        "muted": "#536575",
        "border": "#b9c8d4",
        "on_primary": "#ffffff",
    },
    "scientific": {
        "primary": "#12355b",
        "accent": "#0f8b8d",
        "surface": "#ffffff",
        "surface_alt": "#edf5f7",
        "text": "#102a3a",
        "muted": "#526b78",
        "border": "#b8d2d8",
        "on_primary": "#ffffff",
    },
    "quotation": {
        "primary": "#7a1f3d",
        "accent": "#b8862b",
        "surface": "#fffdf8",
        "surface_alt": "#f7efe4",
        "text": "#2d1b20",
        "muted": "#725b58",
        "border": "#d8c3b6",
        "on_primary": "#ffffff",
    },
    "craft_dark": {
        "primary": "#e3ebff",
        "accent": "#7aa7ff",
        "surface": "#111827",
        "surface_alt": "#0d1728",
        "text": "#f1f5fb",
        "muted": "#b4c2d7",
        "border": "#3a4c68",
        "on_primary": "#0b1b3a",
    },
}
"""Theme name -> colour table. The names are the standard layout names."""

DEFAULT_THEME = "craft"
"""What a window uses until the reader picks another."""

PALETTE_KEYS = (
    "primary",
    "accent",
    "surface",
    "surface_alt",
    "text",
    "muted",
    "border",
    "on_primary",
)
"""Every colour a complete suite theme declares."""

USER_THEMES: dict[str, Theme] = {}
"""Custom themes loaded from the active application directory."""

_NAMESPACE = ""
"""Which application owns the active custom-theme catalogue."""


def use_namespace(namespace: str) -> None:
    """Select one application's private theme catalogue."""
    global _NAMESPACE
    _NAMESPACE = namespace.strip()
    reload_user_themes()


def namespace() -> str:
    """Return the application that owns the active catalogue."""
    return _NAMESPACE


def _safe_stem(name: str) -> str:
    """Turn a display name into a stable file stem."""
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip().lower())
    return stem.strip("-._") or "custom-theme"


def user_themes_dir() -> Path:
    """Return the shared user-theme directory."""
    override = os.environ.get("EPY_SUITE_THEMES_DIR", "").strip()
    if override:
        root = Path(override)
    else:
        base = os.environ.get("APPDATA")
        home = Path(base) if base else Path.home() / "AppData" / "Roaming"
        root = home / "ePy Suite" / "themes"
    return root / _NAMESPACE if _NAMESPACE else root


def validate_palette(colors: dict[str, str]) -> dict[str, str]:
    """Return a complete palette or raise ``ValueError``."""
    clean: dict[str, str] = {}
    for key in PALETTE_KEYS:
        value = str(colors.get(key, "")).strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError(f"invalid colour for {key}: {value!r}")
        clean[key] = value
    return clean


def _read_theme(path: Path) -> tuple[str, str, Theme] | None:
    """Read one user theme file, returning ``(id, name, palette)``."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    colors = raw.get("palette")
    if not isinstance(colors, dict):
        return None
    try:
        palette = validate_palette(colors)
    except ValueError:
        return None
    name = str(raw.get("display_name") or path.stem).strip()
    layout = str(raw.get("document_layout") or "corporate").strip()
    return path.stem, name or path.stem, palette, layout


def reload_user_themes() -> dict[str, Theme]:
    """Reload the shared custom-theme catalogue."""
    USER_THEMES.clear()
    USER_NAMES.clear()
    USER_LAYOUTS.clear()
    directory = user_themes_dir()
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            loaded = _read_theme(path)
            if loaded is None:
                continue
            theme_id, name, colors, layout = loaded
            USER_THEMES[theme_id] = colors
            USER_NAMES[theme_id] = name
            USER_LAYOUTS[theme_id] = layout
    return USER_THEMES


USER_NAMES: dict[str, str] = {}
"""Custom theme id -> display name."""

USER_LAYOUTS: dict[str, str] = {}
"""Custom theme id -> epy_docs document layout."""


def bundled_names() -> list[str]:
    """Return the bundled palette names, in catalogue order."""
    return list(PALETTES)


_DOCUMENT_LAYOUTS = {
    "academic",
    "classic",
    "corporate",
    "creative",
    "handwritten",
    "minimal",
    "professional",
    "quotation",
    "scientific",
    "technical",
}


def document_layout(name: str) -> str:
    """Return the epy_docs layout a theme carries."""
    if name in USER_LAYOUTS:
        return USER_LAYOUTS[name]
    if name in _DOCUMENT_LAYOUTS:
        return name
    return "corporate"


def names() -> list[str]:
    """Return bundled and custom theme names."""
    return bundled_names() + [
        name for name in USER_THEMES if name not in PALETTES
    ]


def display_name(name: str) -> str:
    """Return the visible name of a bundled or custom theme."""
    return USER_NAMES.get(name) or name.replace("_", " ").title()


def is_user_theme(name: str) -> bool:
    """Whether ``name`` belongs to the user catalogue."""
    return name in USER_THEMES and name not in PALETTES


def user_theme_ids() -> set[str]:
    """Return the ids of the custom themes."""
    return set(USER_THEMES)


def save_user_theme(
    name: str,
    colors: dict[str, str],
    *,
    theme_id: str | None = None,
    document_layout: str = "corporate",
) -> str:
    """Persist one custom theme and return its id."""
    palette = validate_palette(colors)
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("a theme needs a display name")
    chosen = _safe_stem(theme_id or clean_name)
    if chosen in PALETTES:
        raise ValueError(f"{chosen!r} is a bundled theme")
    directory = user_themes_dir()
    directory.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "id": chosen,
        "display_name": clean_name,
        "palette": palette,
        "document_layout": document_layout or "corporate",
    }
    (directory / f"{chosen}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    reload_user_themes()
    return chosen


def delete_user_theme(theme_id: str) -> None:
    """Delete one custom theme from the shared catalogue."""
    if theme_id in PALETTES:
        raise ValueError("bundled themes cannot be deleted")
    (user_themes_dir() / f"{theme_id}.json").unlink(missing_ok=True)
    reload_user_themes()

_TEMPLATE = """
QWidget {{
    background: {surface};
    color: {text};
    font-size: 10pt;
}}
QMainWindow, QDialog {{
    background: {surface_alt};
}}
QMenuBar, QMenu, QStatusBar {{
    background: {surface};
    color: {text};
}}
QStatusBar {{
    color: {muted};
    border-top: 1px solid {border};
}}
QMenuBar::item:selected, QMenu::item:selected {{
    background: {surface_alt};
    color: {primary};
}}
QLabel {{
    background: transparent;
}}
QPushButton {{
    background: {surface};
    color: {text};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    border-color: {accent};
    color: {primary};
}}
QPushButton:pressed {{
    background: {surface_alt};
}}
QPushButton:disabled {{
    color: {muted};
    border-color: {border};
    background: {surface_alt};
}}
QPushButton:default {{
    background: {primary};
    color: {on_primary};
    border-color: {primary};
}}
QPushButton:default:hover {{
    background: {accent};
    border-color: {accent};
}}
QLineEdit, QPlainTextEdit, QTextBrowser, QTextEdit, QComboBox {{
    background: {surface};
    color: {text};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 5px 8px;
    selection-background-color: {accent};
    selection-color: {on_primary};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus,
QTextEdit:focus, QComboBox:focus {{
    border-color: {accent};
}}
QComboBox QAbstractItemView {{
    background: {surface};
    border: 1px solid {border};
    selection-background-color: {accent};
    selection-color: {on_primary};
}}
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: 9px;
    background: {surface};
}}
QTabBar::tab {{
    background: {surface_alt};
    color: {muted};
    padding: 7px 16px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{
    background: {surface};
    color: {primary};
    border-bottom: 2px solid {accent};
}}
QTabBar::tab:hover {{
    color: {primary};
}}
QTableWidget, QListWidget, QTreeWidget {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    gridline-color: {border};
    selection-background-color: {surface_alt};
    selection-color: {primary};
}}
QHeaderView::section {{
    background: {surface_alt};
    color: {muted};
    border: none;
    border-bottom: 1px solid {border};
    padding: 6px 8px;
    font-weight: 600;
}}
QScrollBar:vertical {{
    background: {surface_alt};
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {border};
    border-radius: 6px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {accent};
}}
QScrollBar:horizontal {{
    background: {surface_alt};
    height: 12px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {border};
    border-radius: 6px;
    min-width: 28px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}
QToolTip {{
    background: {primary};
    color: {on_primary};
    border: none;
    padding: 5px 8px;
}}
QSplitter::handle {{
    background: {border};
}}
QFrame#AppCard {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 14px;
}}
QFrame#AppCard:hover {{
    border-color: {accent};
}}
QLabel#AppBadge {{
    background: {primary};
    color: {on_primary};
    border-radius: 18px;
    font-size: 30px;
    font-weight: 800;
}}
QLabel#AppName {{
    font-size: 15px;
    font-weight: 700;
    color: {primary};
}}
QLabel#AppDesc {{
    color: {muted};
    font-size: 12px;
}}
QLabel#AppTitle {{
    font-size: 24px;
    font-weight: 800;
    color: {primary};
}}
QLabel#AppSubtitle {{
    color: {muted};
    font-size: 10pt;
}}
QPushButton#Primary {{
    background: {primary};
    color: {on_primary};
    border-color: {primary};
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    background: {accent};
    border-color: {accent};
}}

QToolBar {{
    background: {surface};
    border: none;
    border-bottom: 1px solid {border};
    padding: 7px 10px;
    spacing: 3px;
}}
QToolBar::separator {{
    background: {border};
    width: 1px;
    margin: 6px 8px;
}}
QToolButton {{
    background: transparent;
    color: {text};
    border: none;
    border-radius: 7px;
    padding: 7px 12px;
}}
QToolButton:hover {{
    background: {surface_alt};
    color: {primary};
}}
QToolButton:pressed {{
    background: {border};
}}
QToolButton:checked {{
    background: {surface_alt};
    color: {primary};
}}
QToolButton::menu-indicator {{
    image: none;
    width: 0;
}}
QFrame#HeaderCard {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 16px;
}}
QFrame#Footer {{
    background: {surface_alt};
    border: 1px solid {border};
    border-radius: 12px;
}}
QLabel#Eyebrow {{
    color: {accent};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#SectionTitle {{
    color: {primary};
    font-size: 16px;
    font-weight: 700;
}}
QLabel#Muted {{
    color: {muted};
    font-size: 10pt;
}}
QDialog QLabel#DialogTitle {{
    color: {primary};
    font-size: 20px;
    font-weight: 700;
}}
QPushButton#Quiet {{
    background: transparent;
    color: {muted};
    border: none;
    padding: 6px 10px;
}}
QPushButton#Quiet:hover {{
    background: {surface_alt};
    color: {primary};
}}
QWidget#AppHeader {{
    background: {surface};
    border-bottom: 1px solid {border};
}}
QLabel#AppHeaderLogo {{
    background: transparent;
    border-radius: 9px;
}}
QLabel#AppHeaderTitle {{
    color: {primary};
    font-size: 15px;
    font-weight: 800;
}}
QLabel#AppHeaderSubtitle {{
    color: {muted};
    font-size: 10pt;
}}
QDockWidget {{
    color: {text};
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background: {surface_alt};
    color: {muted};
    padding: 7px 10px;
    border-bottom: 1px solid {border};
    font-weight: 600;
}}
QGroupBox {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 10px;
    font-weight: 700;
    color: {primary};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}}
QCheckBox {{
    spacing: 8px;
}}
QProgressBar {{
    background: {surface_alt};
    border: 1px solid {border};
    border-radius: 4px;
    text-align: center;
    color: {muted};
}}
QProgressBar::chunk {{
    background: {accent};
    border-radius: 4px;
}}
"""


def palette(name: str) -> Theme:
    """Return one palette, falling back to the default.

    Args:
        name: The theme name.

    Returns:
        Its colours, or the default theme's when the name is unknown.
        An unknown name is a stale stored choice, not an error worth
        refusing to draw a window over.
    """
    return dict(
        USER_THEMES.get(
            name, PALETTES.get(name, PALETTES[DEFAULT_THEME])
        )
    )


def qss(name: str = DEFAULT_THEME) -> str:
    """Build the stylesheet for one theme.

    Args:
        name: The theme name.

    Returns:
        The Qt Style Sheet text.
    """
    return _TEMPLATE.format(**palette(name))


def apply(app: object, name: str = DEFAULT_THEME) -> None:
    """Apply one theme to a running Qt application.

    Args:
        app: Any object with ``setStyleSheet`` -- normally a
            ``QApplication``. Kept duck-typed so this module never
            imports Qt.
        name: The theme name. An unknown one falls back to the default.
    """
    if app is None:
        # A window built without a live QApplication (a test, a headless
        # import) has nothing to paint; a missing app is not an error.
        return
    app.setStyleSheet(qss(name))  # type: ignore[attr-defined]


_CHROME_MARKER = "/* ePy craft chrome */"


def apply_chrome(app: object, name: str = DEFAULT_THEME) -> None:
    """Append the modern chrome over an application's document theme.

    Reports, Slides and Papers paint their document theme through their
    own catalogue. The chrome still needs one family look, so this adds
    the shared stylesheet after the document stylesheet without touching
    the document CSS. Re-applying replaces the previous chrome block
    instead of growing the stylesheet.
    """
    if app is None:
        return
    current = getattr(app, "styleSheet", lambda: "")()
    base = current.split(_CHROME_MARKER, 1)[0]
    app.setStyleSheet(base + _CHROME_MARKER + qss(name))  # type: ignore[attr-defined]


reload_user_themes()
