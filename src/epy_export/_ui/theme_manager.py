"""Shared theme catalogue, editor, gallery and menu for the ePy suite."""

from __future__ import annotations

import os
from collections.abc import Callable

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import _theme

__all__ = [
    "ThemeController",
    "ThemeEditorDialog",
    "ThemeGalleryDialog",
    "initial_theme",
]

_LABELS = {
    "en": {
        "menu": "Theme",
        "browse": "Browse themes...",
        "new": "New theme...",
        "edit": "Edit current theme...",
        "delete": "Delete custom theme...",
        "default": "Use current theme as default",
        "saved": "Theme saved: {name}",
        "deleted": "Theme deleted: {name}",
        "no_custom": "No custom themes to delete.",
        "delete_title": "Delete custom theme",
        "delete_prompt": "Delete the custom theme {name}?",
        "gallery": "Themes",
        "choose": "Choose a theme:",
        "editor": "Theme editor",
        "name": "Name",
        "document_style": "Document style",
        "primary": "Primary",
        "accent": "Accent",
        "surface": "Surface",
        "surface_alt": "Secondary surface",
        "text": "Text",
        "muted": "Muted text",
        "border": "Border",
        "on_primary": "Text on primary",
        "invalid_name": "Enter a name for the theme.",
        "invalid_color": "Enter a six-digit colour such as #1d5fd1.",
        "custom": "Custom theme",
        "built_in": "Built-in theme",
    },
    "es": {
        "menu": "Tema",
        "browse": "Explorar temas...",
        "new": "Nuevo tema...",
        "edit": "Editar tema actual...",
        "delete": "Eliminar tema personalizado...",
        "default": "Usar el tema actual como predeterminado",
        "saved": "Tema guardado: {name}",
        "deleted": "Tema eliminado: {name}",
        "no_custom": "No hay temas personalizados para eliminar.",
        "delete_title": "Eliminar tema personalizado",
        "delete_prompt": "¿Eliminar el tema personalizado {name}?",
        "gallery": "Temas",
        "choose": "Elija un tema:",
        "editor": "Editor de temas",
        "name": "Nombre",
        "document_style": "Estilo del documento",
        "primary": "Primario",
        "accent": "Acento",
        "surface": "Superficie",
        "surface_alt": "Superficie secundaria",
        "text": "Texto",
        "muted": "Texto atenuado",
        "border": "Borde",
        "on_primary": "Texto sobre primario",
        "invalid_name": "Escriba un nombre para el tema.",
        "invalid_color": "Escriba un color de seis dígitos, "
        "por ejemplo #1d5fd1.",
        "custom": "Tema personalizado",
        "built_in": "Tema incluido",
    },
}

_DOCUMENT_STYLES = (
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
)

_COLOR_KEYS = (
    "primary",
    "accent",
    "surface",
    "surface_alt",
    "text",
    "muted",
    "border",
    "on_primary",
)


def _tr(language: str, key: str, **values: object) -> str:
    """Translate one shared label."""
    table = _LABELS.get(language, _LABELS["en"])
    text = table.get(key, _LABELS["en"].get(key, key))
    return text.format(**values) if values else text


def initial_theme(settings: QSettings, key: str = "theme") -> str:
    """Return the theme a window should use at startup."""
    choices = _theme.names()
    default = str(settings.value(f"{key}_default", "") or "")
    if default in choices:
        return default
    stored = str(settings.value(key, "") or "")
    if stored in choices:
        return stored
    return _theme.DEFAULT_THEME


def theme_swatch(name: str, size: int = 76) -> QPixmap:
    """Draw a small colour swatch for a theme."""
    colors = _theme.palette(name)
    pixmap = QPixmap(size, int(size * 0.68))
    pixmap.fill(QColor(colors["surface"]))
    from PySide6.QtGui import QPainter  # noqa: PLC0415

    painter = QPainter(pixmap)
    painter.fillRect(0, 0, size, int(size * 0.24), QColor(colors["primary"]))
    painter.fillRect(
        int(size * 0.08),
        int(size * 0.32),
        int(size * 0.84),
        int(size * 0.14),
        QColor(colors["surface_alt"]),
    )
    painter.fillRect(
        int(size * 0.08),
        int(size * 0.53),
        int(size * 0.52),
        int(size * 0.09),
        QColor(colors["muted"]),
    )
    painter.fillRect(
        int(size * 0.08),
        int(size * 0.66),
        int(size * 0.66),
        int(size * 0.08),
        QColor(colors["border"]),
    )
    painter.fillRect(
        int(size - 22),
        int(size * 0.32),
        14,
        14,
        QColor(colors["accent"]),
    )
    painter.end()
    return pixmap


class ThemeEditorDialog(QDialog):
    """Create or edit one custom suite theme."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        base_theme_id: str | None = None,
        edit_id: str | None = None,
        language: str = "es",
    ) -> None:
        super().__init__(parent)
        self._language = language
        self._edit_id = edit_id
        self._colors: dict[str, str] = dict(
            _theme.palette(edit_id or base_theme_id or _theme.DEFAULT_THEME)
        )
        self.setWindowTitle(_tr(language, "editor"))
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(self)
        if edit_id:
            self.name_edit.setText(_theme.display_name(edit_id))
        form.addRow(QLabel(_tr(language, "name")), self.name_edit)
        self.layout_combo = QComboBox(self)
        self.layout_combo.addItems(_DOCUMENT_STYLES)
        chosen_layout = (
            _theme.document_layout(edit_id)
            if edit_id
            else (
                base_theme_id
                if base_theme_id in _DOCUMENT_STYLES
                else "corporate"
            )
        )
        self.layout_combo.setCurrentText(chosen_layout)
        form.addRow(
            QLabel(_tr(language, "document_style")), self.layout_combo
        )
        self._buttons: dict[str, QPushButton] = {}
        for key in _COLOR_KEYS:
            button = QPushButton(self)
            button.setFixedHeight(30)
            button.clicked.connect(
                lambda _checked=False, color_key=key: self._pick(color_key)
            )
            self._buttons[key] = button
            form.addRow(QLabel(_tr(language, key)), button)
            self._paint(key)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _paint(self, key: str) -> None:
        self._buttons[key].setText(self._colors[key])
        self._buttons[key].setStyleSheet(
            f"background: {self._colors[key]}; "
            f"color: {_contrast(self._colors[key])};"
        )

    def _pick(self, key: str) -> None:
        chosen = QColorDialog.getColor(
            QColor(self._colors[key]),
            self,
            _tr(self._language, key),
        )
        if chosen.isValid():
            self._colors[key] = chosen.name()
            self._paint(key)

    def _accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self,
                _tr(self._language, "editor"),
                _tr(self._language, "invalid_name"),
            )
            return
        try:
            _theme.validate_palette(self._colors)
        except ValueError:
            QMessageBox.warning(
                self,
                _tr(self._language, "editor"),
                _tr(self._language, "invalid_color"),
            )
            return
        self.accept()

    def theme_name(self) -> str:
        """Return the typed display name."""
        return self.name_edit.text().strip()

    def palette_values(self) -> dict[str, str]:
        """Return the eight selected colours."""
        return dict(self._colors)

    def edit_id(self) -> str | None:
        """Return the custom id being edited."""
        return self._edit_id

    def document_layout(self) -> str:
        """Return the chosen epy_docs layout."""
        return self.layout_combo.currentText()


def _contrast(color: str) -> str:
    """Return readable text for a background colour."""
    value = color.lstrip("#")
    if len(value) != 6:
        return "#000000"
    red, green, blue = (
        int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)
    )
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#ffffff" if luminance < 0.45 else "#000000"


class ThemeGalleryDialog(QDialog):
    """Pick a theme from visual swatches."""

    _ROLE = 0x0100

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        current_id: str | None = None,
        language: str = "es",
    ) -> None:
        super().__init__(parent)
        self._language = language
        self.setWindowTitle(_tr(language, "gallery"))
        self.setMinimumSize(620, 450)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(_tr(language, "choose")))
        self._list = QListWidget(self)
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(theme_swatch("craft").size())
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setSpacing(14)
        self._list.setUniformItemSizes(True)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())
        for name in _theme.names():
            item = QListWidgetItem(_theme.display_name(name))
            item.setIcon(QIcon(theme_swatch(name)))
            item.setData(self._ROLE, name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self._list.addItem(item)
            if name == current_id:
                self._list.setCurrentItem(item)
        if self._list.currentItem() is None and self._list.count():
            self._list.setCurrentRow(0)
        layout.addWidget(self._list)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_theme_id(self) -> str | None:
        """Return the selected theme id, if any."""
        item = self._list.currentItem()
        return None if item is None else str(item.data(self._ROLE))


class ThemeController:
    """One app's theme menu, persisted selection and default."""

    def __init__(
        self,
        app: object | None,
        settings: QSettings,
        *,
        key: str = "theme",
        namespace: str | None = None,
        language: str = "es",
        on_apply: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        if namespace:
            _theme.use_namespace(namespace)
        if app is None:
            from PySide6.QtWidgets import QApplication  # noqa: PLC0415

            app = QApplication.instance()
        self.app = app
        self.settings = settings
        self.key = key
        self.language = language
        self._on_apply = on_apply
        self._parent = parent
        self.menu: QMenu | None = None
        self.actions: dict[str, QAction] = {}

    def current(self) -> str:
        """Return the theme in force."""
        choices = _theme.names()
        stored = str(self.settings.value(self.key, "") or "")
        if stored in choices:
            return stored
        return initial_theme(self.settings, self.key)

    def default(self) -> str:
        """Return the explicitly selected default theme."""
        value = str(self.settings.value(f"{self.key}_default", "") or "")
        return value if value in _theme.names() else ""

    def attach(self, menu: QMenu) -> None:
        """Populate and keep one application menu in sync."""
        self.menu = menu
        menu.setTitle(_tr(self.language, "menu"))
        self.populate()

    def populate(self) -> None:
        """Rebuild the theme menu from the current catalogue."""
        if self.menu is None:
            return
        self.menu.clear()
        self.actions = {}
        self.group = QActionGroup(self.menu)
        self.group.setExclusive(True)
        current = self.current()
        for name in _theme.names():
            action = QAction(_theme.display_name(name), self.menu)
            action.setCheckable(True)
            action.setChecked(name == current)
            action.triggered.connect(
                lambda _checked=False, chosen=name: self.apply(chosen)
            )
            self.group.addAction(action)
            self.menu.addAction(action)
            self.actions[name] = action
        self.menu.addSeparator()
        browse = QAction(_tr(self.language, "browse"), self.menu)
        browse.triggered.connect(self.browse)
        self.menu.addAction(browse)
        new = QAction(_tr(self.language, "new"), self.menu)
        new.triggered.connect(self.create)
        self.menu.addAction(new)
        edit = QAction(_tr(self.language, "edit"), self.menu)
        edit.triggered.connect(self.edit)
        self.menu.addAction(edit)
        delete = QAction(_tr(self.language, "delete"), self.menu)
        delete.triggered.connect(self.delete)
        self.menu.addAction(delete)
        self.menu.addSeparator()
        self.default_action = QAction(
            _tr(self.language, "default"), self.menu
        )
        self.default_action.setCheckable(True)
        self.default_action.setChecked(
            bool(self.default()) and self.default() == current
        )
        self.default_action.triggered.connect(self.set_default)
        self.menu.addAction(self.default_action)

    def sync(self) -> None:
        """Tick the active theme and the default marker."""
        current = self.current()
        for name, action in self.actions.items():
            action.setChecked(name == current)
        if getattr(self, "default_action", None) is not None:
            self.default_action.setChecked(
                bool(self.default()) and self.default() == current
            )

    def apply(self, name: str, *, persist: bool = True) -> None:
        """Apply and remember one theme."""
        if name not in _theme.names():
            return
        if persist:
            self.settings.setValue(self.key, name)
        os.environ["EPY_SUITE_DOCUMENT_LAYOUT"] = _theme.document_layout(name)
        if self._on_apply is not None:
            self._on_apply(name)
        else:
            from epy_export import apply_theme  # noqa: PLC0415

            apply_theme(self.app, name)
        self.sync()

    def apply_initial(self) -> None:
        """Apply the startup theme."""
        self.apply(initial_theme(self.settings, self.key), persist=False)

    def browse(self) -> None:
        """Apply a theme chosen from the gallery."""
        dialog = ThemeGalleryDialog(
            self._parent,
            current_id=self.current(),
            language=self.language,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            chosen = dialog.selected_theme_id()
            if chosen:
                self.apply(chosen)

    def create(self) -> None:
        """Create a custom theme."""
        dialog = ThemeEditorDialog(
            self._parent,
            base_theme_id=self.current(),
            language=self.language,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            theme_id = _theme.save_user_theme(
                dialog.theme_name(),
                dialog.palette_values(),
                document_layout=dialog.document_layout(),
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self._parent, _tr(self.language, "editor"), str(exc)
            )
            return
        self.populate()
        self.apply(theme_id)

    def edit(self) -> None:
        """Edit a custom theme, or clone a bundled one."""
        current = self.current()
        custom = _theme.is_user_theme(current)
        dialog = ThemeEditorDialog(
            self._parent,
            base_theme_id=None if custom else current,
            edit_id=current if custom else None,
            language=self.language,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            theme_id = _theme.save_user_theme(
                dialog.theme_name(),
                dialog.palette_values(),
                theme_id=dialog.edit_id(),
                document_layout=dialog.document_layout(),
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self._parent, _tr(self.language, "editor"), str(exc)
            )
            return
        self.populate()
        self.apply(theme_id)

    def delete(self) -> None:
        """Delete one custom theme."""
        custom = sorted(_theme.user_theme_ids())
        if not custom:
            QMessageBox.information(
                self._parent,
                _tr(self.language, "menu"),
                _tr(self.language, "no_custom"),
            )
            return
        labels = [_theme.display_name(name) for name in custom]
        choice, accepted = QInputDialog.getItem(
            self._parent,
            _tr(self.language, "delete_title"),
            _tr(self.language, "menu"),
            labels,
            0,
            False,
        )
        if not accepted or not choice:
            return
        theme_id = custom[labels.index(choice)]
        if (
            QMessageBox.question(
                self._parent,
                _tr(self.language, "delete_title"),
                _tr(self.language, "delete_prompt", name=choice),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        _theme.delete_user_theme(theme_id)
        if self.settings.value(self.key, "") == theme_id:
            self.settings.setValue(self.key, _theme.DEFAULT_THEME)
        if self.settings.value(f"{self.key}_default", "") == theme_id:
            self.settings.setValue(f"{self.key}_default", "")
        self.populate()
        self.apply(self.current())

    def set_default(self) -> None:
        """Remember the current theme as this app's default."""
        self.settings.setValue(f"{self.key}_default", self.current())
        self.sync()

    def set_language(self, language: str) -> None:
        """Retranslate the menu without changing the theme."""
        self.language = language
        if self.menu is not None:
            self.menu.setTitle(_tr(language, "menu"))
        self.populate()
