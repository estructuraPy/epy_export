"""Package metadata for the cross-suite registry."""

from __future__ import annotations

from epy_export.epy_suite_connect import get_suite_info


def test_suite_info_names_this_package_and_its_version() -> None:
    import epy_export

    info = get_suite_info()

    assert info["pkg"] == "epy_export"
    assert info["version"] == epy_export.__version__
