"""Launch a sibling ePy application without importing it.

The suite applications are separate processes. A hand-off creates the
file the next stage owns and then starts that stage's executable; this
module resolves the executable in a checkout or in the installed
bundle, so an application never has to know where a sibling was put.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

__all__ = ["SiblingUnavailableError", "command", "launch"]


class SiblingUnavailableError(RuntimeError):
    """The sibling executable could not be found."""


def command(module: str) -> list[str]:
    """Return the command that starts one sibling application.

    In a frozen suite the executable sits beside the running one. In a
    checkout the console script is used when it is on PATH or in the
    interpreter's ``Scripts`` directory; otherwise the module is started
    with the running interpreter.
    """
    suffix = ".exe" if os.name == "nt" else ""
    if getattr(sys, "frozen", False):
        sibling = Path(sys.executable).with_name(module + suffix)
        if not sibling.is_file():
            raise SiblingUnavailableError(
                f"{module} is not beside {sys.executable}."
            )
        return [str(sibling)]
    found = shutil.which(module)
    if found:
        return [found]
    scripts = Path(sys.executable).parent / (
        "Scripts" if os.name == "nt" else "bin"
    )
    candidate = scripts / (module + suffix)
    if candidate.is_file():
        return [str(candidate)]
    return [sys.executable, "-m", module]


def launch(
    module: str, args: Sequence[str] = ()
) -> subprocess.Popen[bytes]:
    """Start one sibling application and return its process."""
    return subprocess.Popen([*command(module), *args])
