"""The shared workflow guide: steps, navigation and translation."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from epy_export._core._runtime import pin_system_icu

pin_system_icu()

STEPS = (
    ("First", "Open the first step."),
    ("Second", "Do the second step."),
    ("Third", "Close the workflow."),
)
STAGES = ((0, "Start"), (2, "Finish"))


@pytest.fixture(scope="module")
def qt_app():
    """One offscreen QApplication for this module."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _guide(qt_app: object, on_go: Callable[[int], None] | None = None):
    from epy_export._ui.workflow_guide import WorkflowGuide

    return WorkflowGuide(
        STEPS,
        STAGES,
        on_go or (lambda _index: None),
    )


def test_the_guide_lists_every_step(qt_app: object) -> None:
    """The titles are the caller's, in order."""
    guide = _guide(qt_app)
    assert guide.step_names() == ["First", "Second", "Third"]
    assert [button.text() for button in guide._buttons] == [
        "First",
        "Second",
        "Third",
    ]


def test_clicking_a_step_opens_it(qt_app: object) -> None:
    """A step button reports its index to the application."""
    seen: list[int] = []
    guide = _guide(qt_app, seen.append)
    guide._buttons[1].click()
    assert seen == [1]


def test_next_and_back_move_one_step(qt_app: object) -> None:
    """The navigation buttons use the same callback as the steps."""
    seen: list[int] = []
    guide = _guide(qt_app, seen.append)
    guide.set_current(1)
    guide._next_button.click()
    guide._back_button.click()
    assert seen == [2, 0]


def test_the_last_step_ends_the_guide(qt_app: object) -> None:
    """There is no forward action at the end, but Back still works."""
    guide = _guide(qt_app)
    guide.set_current(2)
    assert not guide._next_button.isEnabled()
    assert guide._next_button.text() == "End of the guide"
    assert guide._back_button.isEnabled()


def test_an_out_of_range_step_is_ignored(qt_app: object) -> None:
    """A stale index cannot leave the guide without a current step."""
    guide = _guide(qt_app)
    guide.set_current(99)
    assert guide.current() == 0


def test_the_language_change_relabels_the_guide(qt_app: object) -> None:
    """The caller's translation is re-applied, not only applied once."""
    callbacks: list[Callable[[], None]] = []
    translated = {"en": False}

    def translate(text: str) -> str:
        return f"ES {text}" if translated["en"] else text

    from epy_export._ui.workflow_guide import WorkflowGuide

    guide = WorkflowGuide(
        STEPS,
        STAGES,
        lambda _index: None,
        translate=translate,
        on_language_changed=callbacks.append,
    )
    assert guide._buttons[0].text() == "First"
    translated["en"] = True
    callbacks[0]()
    assert guide._buttons[0].text() == "ES First"
    assert guide._stage_labels[0].text() == "ES Start"
    assert guide._progress_label.text() == "ES Step 1 of 3"


def test_the_current_step_shows_its_instruction(qt_app: object) -> None:
    """The hint follows the active step."""
    guide = _guide(qt_app)
    guide.set_current(1)
    assert "second" in guide._hint.text()
    assert guide._progress.value() == 2


def test_the_arrow_asks_the_host_to_collapse(qt_app: object) -> None:
    """The header arrow emits the collapse request for its dock."""
    seen: list[bool] = []
    guide = _guide(qt_app)
    guide.collapse_requested.connect(lambda: seen.append(True))
    assert guide._collapse_button.text() == "\u2192"
    guide._collapse_button.click()
    assert seen == [True]
