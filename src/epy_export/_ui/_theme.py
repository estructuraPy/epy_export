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

__all__ = [
    "DEFAULT_THEME",
    "PALETTES",
    "apply",
    "names",
    "palette",
    "qss",
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
}
"""Theme name -> colour table. The names are the standard layout names."""

DEFAULT_THEME = "corporate"
"""What a window uses until the reader picks another."""

_TEMPLATE = """
QWidget {{
    background: {surface};
    color: {text};
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background: {surface_alt};
}}
QMenuBar, QMenu, QStatusBar {{
    background: {surface};
    color: {text};
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
    font-size: 13px;
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
"""


def names() -> list[str]:
    """Return the theme names, in catalog order.

    Returns:
        The palette names the interface may offer.
    """
    return list(PALETTES)


def palette(name: str) -> Theme:
    """Return one palette, falling back to the default.

    Args:
        name: The theme name.

    Returns:
        Its colours, or the default theme's when the name is unknown.
        An unknown name is a stale stored choice, not an error worth
        refusing to draw a window over.
    """
    return dict(PALETTES.get(name, PALETTES[DEFAULT_THEME]))


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
