"""The facade must load with nothing else installed.

Two invariants, and both are load-bearing rather than tidy.

**No heavy import at module level.** A caller who only wants to read a
document's front matter must not pay for Qt, pypdf, reportlab or Pillow.
The extras exist precisely so they can be absent.

**No sibling import at module level.** epy_reports imports epy_export,
and epy_export's adapters name epy_reports -- that is a cycle unless
every adapter reaches its backend inside a function body. This test is
what keeps that true; without it the cycle appears the first time
somebody hoists an import to the top "for clarity", and the failure
lands in whichever application happens to import second.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BLOCKED = (
    "PySide6",
    "pypdf",
    "reportlab",
    "PIL",
    "epy_reports",
    "epy_slides",
    "epy_papers",
    "epy_docs",
    "yaml",
)

_BLOCKED_PROBE = """
import builtins
BLOCKED = {blocked!r}
_real = builtins.__import__


def _guard(name, *args, **kwargs):
    if name.split(".")[0] in BLOCKED:
        raise ImportError("blocked by the isolation probe: " + name)
    return _real(name, *args, **kwargs)


builtins.__import__ = _guard
import epy_export

# Usable, not merely importable.
assert epy_export.engine("slides").formats == ("pdf", "pptx", "html")
header = epy_export.parse_front_matter("---\\ntitle: x\\n---\\n")
assert header == {{"title": "x"}}
assert "docs" in epy_export.engine_ids()
print("OK")
"""

_RESIDENT_PROBE = """
import sys
import epy_export
BLOCKED = {blocked!r}
resident = sorted(n for n in BLOCKED if n in sys.modules)
print("RESIDENT:" + ",".join(resident))
"""


_PRESENCE_PROBE = """
import sys
import epy_export
epy_export.installed()
BLOCKED = {blocked!r}
print("RESIDENT:" + ",".join(sorted(n for n in BLOCKED if n in sys.modules)))
"""


def _run(probe: str) -> subprocess.CompletedProcess[str]:
    """Run ``probe`` in a subprocess that can see the source tree.

    pytest's own pythonpath does not reach a subprocess, so the source
    tree is handed over explicitly. Everything else in the environment
    is inherited on purpose: the point is to prove the facade loads
    without the heavy names, not that it loads inside a stripped shell.
    """
    src = Path(__file__).resolve().parents[1] / "src"
    env = dict(os.environ, PYTHONPATH=str(src))
    return subprocess.run(
        [sys.executable, "-c", probe.format(blocked=BLOCKED)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_the_facade_imports_with_every_heavy_name_blocked() -> None:
    result = _run(_BLOCKED_PROBE)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_importing_the_facade_pulls_in_no_heavy_module() -> None:
    # The stronger statement, and it runs on a machine where all of them
    # ARE installed -- which is what makes it a real test here. The
    # blocked probe above proves the facade survives their absence; this
    # one proves it does not reach for them when they are present.
    result = _run(_RESIDENT_PROBE)
    assert result.returncode == 0, result.stderr
    line = next(
        item
        for item in result.stdout.splitlines()
        if item.startswith("RESIDENT:")
    )
    resident = [name for name in line[len("RESIDENT:") :].split(",") if name]
    assert resident == [], f"imported at module level: {resident}"


def test_asking_whether_an_engine_is_present_imports_nothing() -> None:
    # backend_present uses find_spec, which deliberately does NOT go
    # through builtins.__import__ -- discovered by this very probe
    # failing when it asserted otherwise. That is the property being
    # relied on: a menu can ask about four engines without paying for
    # any of them.
    result = _run(_PRESENCE_PROBE)
    assert result.returncode == 0, result.stderr
    assert "RESIDENT:\n" in result.stdout or result.stdout.strip().endswith(
        "RESIDENT:"
    ), result.stdout
