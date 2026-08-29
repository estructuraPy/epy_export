"""Math delimiters, and why this lives here and not in one application.

Measured across the four engines on the same corpus: reports and slides
render it in three formats each with nothing to fix, while the two
LaTeX-based engines produced NO FILE -- "Missing $ inserted" -- until
204 and 238 delimiters were rewritten. The step that decides whether a
render survives was living in one application's two entry points.
"""

from __future__ import annotations

from epy_export._core._markdown import normalize_math


def test_inline_delimiters_become_dollars() -> None:
    got = normalize_math(r"El valor \(f_c\) es alto.")
    assert got.text == "El valor $f_c$ es alto."
    assert got.math_delimiters == 2


def test_display_delimiters_become_double_dollars() -> None:
    got = normalize_math(r"\[N_b = k_c\]")
    assert got.text == "$$N_b = k_c$$"
    assert got.math_delimiters == 2


def test_a_document_already_using_dollars_is_untouched() -> None:
    # The control. Rewriting a source an engine already reads is a
    # change nobody asked for, and the count is what says so.
    original = "El valor $f_c$ es alto."
    got = normalize_math(original)
    assert got.text == original
    assert got.math_delimiters == 0


def test_unbalanced_delimiters_are_left_for_a_person() -> None:
    # A document that opens with one syntax and closes with the other
    # would be silently corrupted by a blind substitution. No model has
    # produced one, which is exactly why nobody would notice.
    text = r"\(f_c$ y \(f_y\)"
    assert normalize_math(text).text == text
    assert normalize_math(text).math_delimiters == 0


def test_the_two_kinds_are_decided_separately() -> None:
    # Balanced inline, unbalanced display: the inline still converts.
    got = normalize_math(r"\(a\) y \[b")
    assert "$a$" in got.text
    assert r"\[b" in got.text
