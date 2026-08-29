"""Make the process safe for Qt to load, before Qt loads.

One owner for a workaround that lived three times -- in epy_reports,
epy_slides and epy_papers -- each with its own copy of the same
docstring, two of which said "Mirrors epy_reports._pin_system_icu".
Self-documented triplication is still triplication.

Public, not private, because it now crosses a package boundary: each
application calls it explicitly at its own import, so the ordering stays
visible where it matters. This module deliberately does NOT call it on
import -- a side effect that fires from an unrelated import is how the
ordering stops being reviewable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

__all__ = ["pin_system_icu"]


def pin_system_icu() -> None:
    r"""Bind Qt's ICU imports to the Windows system ICU before Qt loads.

    PySide6 >= 6.9 links ``Qt6Core.dll`` against the unversioned Windows ICU
    (``System32\icuuc.dll``, shipped since Windows 10 1703). Conda
    environments register ``Library\bin`` as a DLL directory, and the conda
    ``icu`` package exposes its own unversioned ``icuuc.dll`` there with
    version-suffixed exports — the loader binds that copy first and every
    ``PySide6.Qt*`` import dies with ``WinError 127`` (procedure not found).
    Preloading the System32 copy by full path pins the module name so Qt
    resolves against the right ICU. No-op off Windows, when the system DLL
    is absent, or when ICU is already loaded.
    """
    if sys.platform != "win32":
        return
    import ctypes  # noqa: PLC0415

    system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    system_icu = Path(system_root) / "System32" / "icuuc.dll"
    if not system_icu.is_file():
        return
    try:
        ctypes.WinDLL(str(system_icu))
    except OSError:
        return
