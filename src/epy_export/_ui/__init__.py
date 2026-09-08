"""Widgets the family shares, for the one dialog all three editors need.

Kept out of ``epy_export``'s own imports on purpose: this subpackage
touches Qt, and the package is imported by callers that never draw
anything. Reach it the way the applications do, inside the function that
opens the window::

    from epy_export._ui.docs_export_dialog import DocsExportDialog

Why here at all. The dialog that configures an ePy Docs export is the
same window in ePy Reports, ePy Slides and ePy Papers: the same two
combos, the same directory picker, the same format checkboxes, the same
three remembered keys. Only three things differ, and each is passed in
-- which registry scope to remember under, and the two translation
callables the owning application already has.

Three copies of one window is the shape this suite has been paying for
elsewhere: a rule learned once, pasted into some of the places that
needed it, and absent from the rest.
"""

from __future__ import annotations

__all__: list[str] = []
