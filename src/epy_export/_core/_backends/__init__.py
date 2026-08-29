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
from types import ModuleType

__all__ = [
    "BackendUnavailableError",
    "RenderFailedError",
    "backend_present",
    "load_backend",
]


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
