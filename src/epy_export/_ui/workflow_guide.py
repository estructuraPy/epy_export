"""The shared step-by-step guide of the ePy suite.

Every application that has a sequence of work shows the same panel: the
stages, the steps in order, the instruction for the current one, a
progress line, and one clear way forward. The panel is deliberately
generic: each application supplies its own steps and the callable that
opens one, so the guide cannot drift from the tabs or actions it names.

The labels are passed through the caller's translation function. The
caller also registers the panel for language changes, because a guide
that stays in one language while its window changes is worse than no
guide at all.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

Translator = Callable[[str], str]
Step = tuple[str, str]
Stage = tuple[int, str]

_BUTTON = "text-align: left; padding: 0; border: none;"
_BUTTON_CURRENT = (
    "text-align: left; padding: 0; border: none; font-weight: 700;"
)


def _identity(text: str) -> str:
    """Return the text unchanged, for callers with no translator."""
    return text


class WorkflowGuide(QWidget):
    """A vertical, grouped guide over one application workflow."""

    collapse_requested = Signal()

    def __init__(
        self,
        steps: Sequence[Step],
        stages: Sequence[Stage],
        on_go: Callable[[int], None],
        *,
        translate: Translator | None = None,
        on_language_changed: Callable[
            [Callable[[], None]], None
        ] | None = None,
        eyebrow: str = "GUIDED WORKFLOW",
        title: str = "Step by step",
        subtitle: str = "Follow the workflow from start to finish.",
    ) -> None:
        """Build the guide.

        Args:
            steps: English title and instruction per step.
            stages: ``(first step index, English stage title)`` pairs.
            on_go: Called with a step index when the user opens one.
            translate: The application's translation function.
            on_language_changed: Registers a relabel callback, normally
                the application's ``on_language_changed``.
            eyebrow: Small heading above the title.
            title: Guide title.
            subtitle: One line explaining the guide.
        """
        super().__init__()
        self._steps = tuple(steps)
        self._stages = tuple(stages)
        self._on_go = on_go
        self._translate = translate or _identity
        self._current = 0
        self._buttons: list[QPushButton] = []
        self._rows: list[QFrame] = []
        self._numbers: list[QLabel] = []
        self._descriptions: list[QLabel] = []
        self._stage_labels: list[QLabel] = []
        self._header_labels: list[QLabel] = []
        self.setMinimumWidth(330)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        header = QFrame(self)
        header.setObjectName("HeaderCard")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(4)

        self._eyebrow = QLabel(header)
        self._eyebrow.setObjectName("Eyebrow")
        self._header_labels.append(self._eyebrow)
        eyebrow_row = QHBoxLayout()
        eyebrow_row.addWidget(self._eyebrow)
        eyebrow_row.addStretch(1)
        self._collapse_button = QToolButton(header)
        self._collapse_button.setText("\u2192")
        self._collapse_button.setAutoRaise(True)
        self._collapse_button.clicked.connect(
            self.collapse_requested.emit
        )
        eyebrow_row.addWidget(self._collapse_button)
        header_layout.addLayout(eyebrow_row)

        self._title = QLabel(header)
        self._title.setObjectName("SectionTitle")
        self._header_labels.append(self._title)
        header_layout.addWidget(self._title)

        self._subtitle = QLabel(header)
        self._subtitle.setObjectName("Muted")
        self._subtitle.setWordWrap(True)
        self._header_labels.append(self._subtitle)
        header_layout.addWidget(self._subtitle)

        self._progress_label = QLabel(header)
        self._progress_label.setObjectName("Muted")
        header_layout.addWidget(self._progress_label)

        self._progress = QProgressBar(header)
        self._progress.setRange(0, len(self._steps))
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        header_layout.addWidget(self._progress)
        layout.addWidget(header)

        self._eyebrow_key = eyebrow
        self._title_key = title
        self._subtitle_key = subtitle

        self._hint = QLabel(self)
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(
            "color: palette(highlight); font-weight: 600;"
        )
        layout.addWidget(self._hint)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        content = QWidget()
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        steps_layout = QVBoxLayout(content)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        steps_layout.setSpacing(3)

        stage_starts = {start for start, _label in self._stages}
        for index, (_name, _hint) in enumerate(self._steps):
            if index in stage_starts:
                group = QLabel(content)
                group.setObjectName("Eyebrow")
                group.setWordWrap(True)
                group.setContentsMargins(8, 8, 0, 2)
                steps_layout.addWidget(group)
                self._stage_labels.append(group)

            row = QFrame(content)
            row.setObjectName("StepRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)

            number = QLabel(str(index + 1), row)
            number.setObjectName("StepNumber")
            number.setAlignment(Qt.AlignmentFlag.AlignTop)
            number.setFixedWidth(22)

            column = QVBoxLayout()
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(1)
            button = QPushButton(row)
            button.setFlat(True)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            button.clicked.connect(
                lambda _checked=False, i=index: self._on_go(i)
            )
            column.addWidget(button)

            description = QLabel(row)
            description.setObjectName("Muted")
            description.setWordWrap(True)
            description.setMinimumWidth(0)
            description.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
            description.setStyleSheet("font-size: 9pt;")
            column.addWidget(description)

            row_layout.addWidget(number)
            row_layout.addLayout(column, 1)
            steps_layout.addWidget(row)
            self._rows.append(row)
            self._numbers.append(number)
            self._buttons.append(button)
            self._descriptions.append(description)

        steps_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        navigation = QHBoxLayout()
        self._back_button = QPushButton()
        self._back_button.clicked.connect(self._go_back)
        navigation.addWidget(self._back_button)
        navigation.addStretch(1)
        self._next_button = QPushButton()
        self._next_button.setObjectName("Primary")
        self._next_button.clicked.connect(self._go_next)
        navigation.addWidget(self._next_button)
        layout.addLayout(navigation)

        if on_language_changed is not None:
            on_language_changed(self._relabel)
        self._relabel()
        self.set_current(0)

    def _go_back(self) -> None:
        """Ask the application to move one step back."""
        if self._current > 0:
            self._on_go(self._current - 1)

    def _go_next(self) -> None:
        """Ask the application to move one step forward."""
        if self._current < len(self._steps) - 1:
            self._on_go(self._current + 1)

    def _refresh_dynamic_text(self) -> None:
        """Relabel progress and the forward action."""
        total = len(self._steps)
        self._progress_label.setText(
            self._translate("Step {current} of {total}").format(
                current=self._current + 1, total=total
            )
        )
        if self._current < total - 1:
            next_name = self._steps[self._current + 1][0]
            self._next_button.setText(
                self._translate("Next: {step}").format(
                    step=self._translate(next_name)
                )
            )
        else:
            self._next_button.setText(
                self._translate("End of the guide")
            )

    def _relabel(self) -> None:
        """Apply the current language to every visible string."""
        self._eyebrow.setText(self._translate(self._eyebrow_key))
        self._title.setText(self._translate(self._title_key))
        self._subtitle.setText(self._translate(self._subtitle_key))
        self._back_button.setText(self._translate("Back"))
        self._collapse_button.setToolTip(self._translate("Hide guide"))
        for index, (name, hint) in enumerate(self._steps):
            self._buttons[index].setText(self._translate(name))
            self._buttons[index].setToolTip(self._translate(hint))
            self._descriptions[index].setText(self._translate(hint))
        for label, (_start, key) in zip(
            self._stage_labels, self._stages, strict=True
        ):
            label.setText(self._translate(key))
        self._refresh_dynamic_text()

    def set_current(self, index: int) -> None:
        """Mark one step as the current one and show its instruction."""
        if not 0 <= index < len(self._steps):
            return
        self._current = index
        for position, (button, row, number) in enumerate(
            zip(
                self._buttons,
                self._rows,
                self._numbers,
                strict=True,
            )
        ):
            current = position == index
            button.setStyleSheet(
                _BUTTON_CURRENT if current else _BUTTON
            )
            number.setStyleSheet(
                "color: palette(highlight); font-weight: 700;"
                if current
                else "color: palette(mid);"
            )
            row.setStyleSheet(
                "QFrame#StepRow { background: palette(alternate-base); "
                "border-left: 3px solid palette(highlight); "
                "border-radius: 6px; }"
                if current
                else ""
            )
        self._hint.setText(self._translate(self._steps[index][1]))
        self._progress.setValue(index + 1)
        self._back_button.setEnabled(index > 0)
        self._next_button.setEnabled(index < len(self._steps) - 1)
        self._refresh_dynamic_text()

    def current(self) -> int:
        """Return the step the panel is marking."""
        return self._current

    def step_names(self) -> list[str]:
        """Return the step titles, for the application's own checks."""
        return [name for name, _hint in self._steps]
