"""Whether a sibling engine is here, and getting hold of it.

One owner for a question two bridges answered differently. epy_craft's
``docs_bridge`` asked with ``importlib.import_module`` inside a
try/except; epy_reports' asked with ``importlib.util.find_spec``. They
disagree on a real case -- a package that is installed but whose own
imports fail -- and disagreeing about "is it here" is how one
application greys out a menu the other offers.

**Both mechanisms are kept, for their two different jobs.**

:func:`backend_present` answers "should I OFFER this?", and must import
nothing: the answer is needed while a menu is being built, and importing
``epy_reports`` to find out whether it exists pulls in plotly and
matplotlib to draw a menu item.

:func:`load_backend` answers "give it to me", at the moment of use, and
raises named when it cannot. That is where a present-but-broken package
must surface -- loudly, with the module named -- rather than being
smoothed into "not installed".

So a backend that is present but broken is offered and then fails by
name, which is the honest pair. Answering only with ``find_spec`` hides
the breakage until a render dies in a worker thread; answering only with
``import_module`` makes opening a menu cost the whole scientific stack.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

__all__ = [
    "ENV_DOCS_PYTHON",
    "BackendUnavailableError",
    "RenderFailedError",
    "Route",
    "backend_present",
    "backend_route",
    "load_backend",
]

ENV_DOCS_PYTHON = "EPY_DOCS_PYTHON"
"""Where an interpreter carrying ePy Docs was found, for a child process.

Published by ePy Studio when it launches an application, read here. The
name lives in this package because both ends depend on it and neither
depends on the other: Studio imports it, the applications import it, and
a rename therefore cannot leave one side listening for a variable the
other stopped setting.
"""

_HINTED = {"epy_docs": ENV_DOCS_PYTHON}
"""Engines that can be reached in another interpreter, and the variable
naming it. Only ePy Docs: the other three engines are the applications
this bundle already carries.
"""


@dataclass(frozen=True)
class Route:
    """How this process can reach an engine, if at all.

    Attributes:
        mode: ``"in_process"``, ``"subprocess"`` or ``"none"``.
        python: The interpreter to run it in, for ``"subprocess"``.
    """

    mode: str
    python: str = ""

    @property
    def reachable(self) -> bool:
        """Whether the engine can be reached at all."""
        return self.mode != "none"


def backend_route(module: str) -> Route:
    """Return how this process can reach ``module``.

    Asking only whether the module imports HERE is the question that has
    a permanently wrong answer inside a frozen bundle: PyInstaller closes
    ``sys.path`` to the bundle, so a package installed in the user's own
    Python is invisible no matter what the spec says. Every application
    asked it that way, so every "export through ePy Docs" entry has been
    greyed out in every shipped executable since the first release --
    including ePy Draft's DEFAULT engine.

    So the question is about the MACHINE. Import here when we can, and
    otherwise use the interpreter ePy Studio found and named in the
    environment.

    Args:
        module: Importable package name, e.g. ``"epy_docs"``.

    Returns:
        The route. ``"none"`` is a normal answer, not an error: the
        applications work without the optional engine.
    """
    if backend_present(module):
        return Route("in_process")
    variable = _HINTED.get(module)
    if variable:
        named = os.environ.get(variable, "")
        if named and Path(named).is_file():
            return Route("subprocess", named)
    return Route("none")


class BackendUnavailableError(RuntimeError):
    """The engine is not installed, or cannot be imported."""


class RenderFailedError(RuntimeError):
    """The engine was reached, ran, and did not produce a sound document.

    Separate from :class:`BackendUnavailableError` on purpose. The two
    were conflated: the check that refuses a truncated PDF -- written
    after a three-of-ten-page file passed a file-exists test -- raised
    the *unavailable* error, so a partial document was reported to the
    reader as "the engine is not installed". One of those is fixed by
    installing something and the other never is.
    """


def backend_present(module: str) -> bool:
    """Report whether ``module`` could be imported, without importing it.

    Args:
        module: Importable package name, e.g. ``"epy_docs"``.

    Returns:
        Whether an importable module of that name is on the path. A
        package that is present but whose own imports fail still answers
        True here; :func:`load_backend` is what surfaces that, by name.
        Offering an entry that then fails clearly beats hiding it.
    """
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        # ValueError: a module already in sys.modules with __spec__ None.
        return False
    # A namespace package -- any bare directory of that name on the path,
    # PEP 420 -- has no loader. It satisfies find_spec and imports to an
    # empty module, so the caller would reach for an attribute that was
    # never there. That is not a backend.
    return spec is not None and spec.loader is not None


def load_backend(module: str, *, why: str) -> ModuleType:
    """Import ``module`` and return it, or raise saying what is missing.

    Args:
        module: Importable package name.
        why: What the caller wanted it for, in a few words, so the
            message says which capability the reader has lost rather
            than only which package is absent.

    Returns:
        The imported module.

    Raises:
        BackendUnavailableError: Naming the module and ``why``. The
            original ImportError is chained, so a package that is
            installed but broken shows its real cause instead of being
            reported as absent.
    """
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise BackendUnavailableError(
            f"{why} needs {module}, which is not installed here "
            f"(or failed to import: {exc})."
        ) from exc
