"""The contract module's own promises: the option bundle and the frozen types.

This file exists because the housekeeper's module-mirror rule found
``_contract/_engine.py`` with no test crediting it, and the gap was real
rather than bookkeeping. The vocabularies are pinned and drift-checked in
``test_vocabulary_drift.py`` and the alias is pinned through the facade in
``tests/_core/test_backends.py``, but :meth:`RenderOptions.named_fields`
had no test at all -- and it is the method the whole bundle exists for.
``_adapters/_adapter.py`` calls it to name the fields an engine does not
understand so the dispatcher can REFUSE them; the docstring says what the
alternative was, a caller asking ePy Reports for a journal profile and
getting a report with no signal.

The last test is the one with teeth: ``named_fields`` lists its seven
names by hand, so an eighth field added to the dataclass would be
invisible to it, the adapter would never see it, and the refusal that
justifies the bundle would silently stop covering it. That is a defect
that cannot be read off either piece alone.
"""

from __future__ import annotations

import dataclasses

import pytest

from epy_export.epy_suite_connect._contract import _engine

#: One non-default value per field, chosen to differ from the default the
#: dataclass declares. ``author`` is a Mapping defaulting to None, so any
#: mapping differs.
NON_DEFAULT: tuple[tuple[str, object], ...] = (
    ("appearance", "technical"),
    ("journal_id", "ieee"),
    ("author", {"name": "Ing. Angel Navarro-Mora M.Sc."}),
    ("language", "en"),
    ("project_type", "bridge"),
    ("source_kind", "quarto"),
    ("document_type", "paper"),
)


def test_named_fields_is_empty_when_the_caller_asked_for_nothing() -> None:
    """A bundle carrying only defaults names no field.

    The adapter's refusal reads this: if defaults were reported, every
    call would arrive carrying seven fields to justify.
    """
    assert _engine.RenderOptions().named_fields() == ()


@pytest.mark.parametrize(("field", "value"), NON_DEFAULT)
def test_named_fields_names_exactly_the_field_that_was_set(
    field: str, value: object
) -> None:
    """Setting one field names that one and no other."""
    options = _engine.RenderOptions(**{field: value})
    assert options.named_fields() == (field,)


def test_named_fields_names_every_field_that_was_set() -> None:
    """Several at once come back together, in the method's own order."""
    options = _engine.RenderOptions(
        journal_id="ieee", language="en", document_type="paper"
    )
    assert options.named_fields() == (
        "journal_id",
        "language",
        "document_type",
    )


def test_named_fields_can_report_every_field_the_dataclass_declares() -> None:
    """No field can be added to the bundle and stay invisible to it.

    ``named_fields`` walks a hand-written tuple of names. A field added
    to the dataclass and not to that tuple is a field the dispatcher can
    never refuse, which is the one thing the bundle is for. Compared by
    SET, because the method's order is its offer order and not this
    test's business.
    """
    declared = {f.name for f in dataclasses.fields(_engine.RenderOptions)}
    reportable = {
        field
        for field, value in NON_DEFAULT
        if _engine.RenderOptions(**{field: value}).named_fields() == (field,)
    }
    assert reportable == declared


ENGINE = _engine.Engine(
    engine_id="docs",
    label="ePy Docs",
    module="epy_docs",
    formats=("pdf",),
    themed=True,
    purpose="the generic writer",
)


@pytest.mark.parametrize(
    ("built", "field"),
    [(ENGINE, "label"), (_engine.RenderOptions(), "appearance")],
)
def test_the_contract_types_are_frozen(built: object, field: str) -> None:
    """Neither type can be mutated after it is built.

    The catalog hands the same :class:`Engine` instance to every caller,
    so a writable field would let one of them edit the entry the next one
    reads. The field set here is one the type really declares, so the
    refusal is the frozen dataclass and not a typo.
    """
    assert getattr(built, field) is not None
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(built, field, "other")
