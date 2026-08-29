r"""Math delimiters a typesetter will read, whoever is asking.

This lived inside one application, called by two of its own entry
points, and was measured being the difference between a document and no
document. Rendering the same source through all four engines:

    reports   3 of 3 formats, 0 delimiters to fix
    slides    3 of 3,          0 to fix
    docs      0 of 3           -> 3 of 3 after 204 were fixed
    papers    1 of 2           -> 2 of 2 after 238

The two engines that go through LaTeX abort on ``\(`` and ``\[``: the
Markdown reader does not recognise them, escapes them into literal
text, and LaTeX then dies on the commands left stranded outside math
mode. "Missing $ inserted", and no file.

So it belongs where every engine can be reached from, not in one
application that happens to remember. A shared engine layer whose whole
purpose is that four applications reach an engine the SAME way, while
the step that decides whether the render survives lives in two callers,
is a layer that has not finished the job.

The three conditions the original module set for itself hold here and
are why this is a move rather than a rewrite:

**Lossless.** ``\(x\)`` and ``$x$`` mean the same thing to every reader
of Markdown; only the syntax differs.

**Applied to a COPY.** Nothing here writes over the source. The caller
gets new text and decides what to do with it.

**Reported.** The count comes back, so a caller can say how many
repairs a document needed rather than quietly improving it.

What is NOT repaired is as deliberate. A primed symbol with an exponent
-- ``f'_c^{n}`` -- also aborts the render, and guessing at an author's
grouping is a change of meaning rather than of syntax. That stays a
review point for a person.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Repair", "normalize_math"]

INLINE_OPEN = re.compile(r"\\\(")
INLINE_CLOSE = re.compile(r"\\\)")
DISPLAY_OPEN = re.compile(r"\\\[")
DISPLAY_CLOSE = re.compile(r"\\\]")


@dataclass(frozen=True)
class Repair:
    """What was changed on the way to the typesetter.

    Attributes:
        text: The repaired document.
        math_delimiters: How many delimiters were rewritten. Zero means
            the document already used the syntax the engine reads.
    """

    text: str
    math_delimiters: int


def normalize_math(text: str) -> Repair:
    r"""Rewrite LaTeX math delimiters into the Markdown ones.

    ``\(x\)`` becomes ``$x$`` and ``\[x\]`` becomes ``$$x$$``. Both
    pairs are converted together or not at all per kind, so a document
    that opens with one and closes with the other -- which no model has
    produced, but which would silently corrupt the maths -- is left
    alone for a human to look at.

    Args:
        text: The document as it was written.

    Returns:
        The repair, carrying the new text and how many delimiters moved.
    """
    inline_open = len(INLINE_OPEN.findall(text))
    inline_close = len(INLINE_CLOSE.findall(text))
    display_open = len(DISPLAY_OPEN.findall(text))
    display_close = len(DISPLAY_CLOSE.findall(text))

    changed = 0
    if inline_open and inline_open == inline_close:
        text = INLINE_OPEN.sub("$", text)
        text = INLINE_CLOSE.sub("$", text)
        changed += inline_open + inline_close
    if display_open and display_open == display_close:
        text = DISPLAY_OPEN.sub("$$", text)
        text = DISPLAY_CLOSE.sub("$$", text)
        changed += display_open + display_close
    return Repair(text=text, math_delimiters=changed)
