"""The shared identity bar of every ePy application.

The bar gives the family one recognizable top edge: the application's
own mark, its name, the context it is working on, and the two doors a
reader needs from anywhere -- back to ePy Studio and the step-by-step
guide or assistant. It is deliberately a widget, not a second window.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

__all__ = ["AppHeader", "install_header"]


class AppHeader(QWidget):
    """One compact identity bar shared by the suite."""

    def __init__(
        self,
        *,
        title: str,
        subtitle: str = "",
        logo_path: str | Path | None = None,
        guide_dock: QWidget | None = None,
        assistant_dock: QWidget | None = None,
        on_studio: Callable[[], None] | None = None,
        language: str = "en",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("AppHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        self.logo = QLabel(self)
        self.logo.setObjectName("AppHeaderLogo")
        self.logo.setFixedSize(36, 36)
        self.logo.setAccessibleName(title)
        self._set_logo(logo_path, title)
        layout.addWidget(self.logo)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(1)
        self.title = QLabel(title, self)
        self.title.setObjectName("AppHeaderTitle")
        self.title.setAccessibleName(title)
        copy.addWidget(self.title)
        self.subtitle = QLabel(subtitle, self)
        self.subtitle.setObjectName("AppHeaderSubtitle")
        self.subtitle.setWordWrap(True)
        copy.addWidget(self.subtitle)
        layout.addLayout(copy, 1)

        self._studio_button: QPushButton | None = None
        self._guide_button: QPushButton | None = None
        self._assistant_button: QPushButton | None = None
        labels = _labels(language)
        if on_studio is not None:
            studio = QPushButton(labels["studio"], self)
            studio.setObjectName("Quiet")
            studio.setToolTip(labels["studio_tip"])
            studio.setAccessibleName(labels["studio_tip"])
            studio.clicked.connect(on_studio)
            layout.addWidget(studio)
            self._studio_button = studio
        if guide_dock is not None:
            guide = QPushButton(labels["guide"], self)
            guide.setObjectName("Quiet")
            guide.setToolTip(labels["guide_tip"])
            guide.setAccessibleName(labels["guide_tip"])
            guide.setCheckable(True)
            guide.setChecked(True)
            guide.toggled.connect(guide_dock.setVisible)
            guide_dock.visibilityChanged.connect(guide.setChecked)
            layout.addWidget(guide)
            self._guide_button = guide
        if assistant_dock is not None:
            assistant = QPushButton(labels["assistant"], self)
            assistant.setObjectName("Quiet")
            assistant.setToolTip(labels["assistant_tip"])
            assistant.setAccessibleName(labels["assistant_tip"])
            assistant.setCheckable(True)
            assistant.setChecked(False)
            assistant.toggled.connect(assistant_dock.setVisible)
            assistant_dock.visibilityChanged.connect(assistant.setChecked)
            layout.addWidget(assistant)
            self._assistant_button = assistant

    def set_texts(self, title: str, subtitle: str = "") -> None:
        """Update the identity text without rebuilding the header."""
        self.title.setText(title)
        self.title.setAccessibleName(title)
        self.logo.setAccessibleName(title)
        self.subtitle.setText(subtitle)

    def set_language(self, language: str) -> None:
        """Retranslate the header buttons without rebuilding them."""
        labels = _labels(language)
        for button, label, tip in (
            (self._studio_button, "studio", "studio_tip"),
            (self._guide_button, "guide", "guide_tip"),
            (self._assistant_button, "assistant", "assistant_tip"),
        ):
            if button is None:
                continue
            button.setText(labels[label])
            button.setToolTip(labels[tip])
            button.setAccessibleName(labels[tip])

    def _set_logo(
        self, logo_path: str | Path | None, title: str
    ) -> None:
        path = Path(logo_path) if logo_path else None
        if path is not None and path.is_file():
            icon = QIcon(str(path))
            pixmap = icon.pixmap(36, 36)
            if not pixmap.isNull():
                self.logo.setPixmap(pixmap)
                return
        self.logo.setText(title[:1].upper())
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)


_LABELS = {
    "en": {
        "studio": "ePy Studio",
        "studio_tip": "Open the ePy Studio selector.",
        "guide": "Guide",
        "guide_tip": "Show or hide the step-by-step guide.",
        "assistant": "Assistant",
        "assistant_tip": "Show or hide the assistant.",
    },
    "es": {
        "studio": "ePy Studio",
        "studio_tip": "Abrir el selector de ePy Studio.",
        "guide": "Guía",
        "guide_tip": "Mostrar u ocultar la guía paso a paso.",
        "assistant": "Asistente",
        "assistant_tip": "Mostrar u ocultar el asistente.",
    },
}


def _labels(language: str) -> dict[str, str]:
    """Return the header labels for one language."""
    return _LABELS.get(language, _LABELS["en"])


def install_header(
    window: QWidget,
    *,
    title: str,
    subtitle: str = "",
    logo_path: str | Path | None = None,
    guide_dock: QWidget | None = None,
    assistant_dock: QWidget | None = None,
    on_studio: Callable[[], None] | None = None,
    language: str = "en",
) -> AppHeader | None:
    """Place the identity bar above the window's existing central widget."""
    if not isinstance(window, QWidget):
        return None
    existing = window.centralWidget()  # type: ignore[attr-defined]
    header = AppHeader(
        title=title,
        subtitle=subtitle,
        logo_path=logo_path,
        guide_dock=guide_dock,
        assistant_dock=assistant_dock,
        on_studio=on_studio,
        language=language,
        parent=window,
    )
    if logo_path and Path(logo_path).is_file():
        window.setWindowIcon(QIcon(str(logo_path)))  # type: ignore[attr-defined]
    if existing is None:
        window.setCentralWidget(header)  # type: ignore[attr-defined]
        return header
    container = QWidget(window)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(header)
    layout.addWidget(existing, 1)
    window.setCentralWidget(container)  # type: ignore[attr-defined]
    return header
