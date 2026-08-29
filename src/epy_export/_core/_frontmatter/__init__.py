"""Read and write the YAML-ish header at the top of a source document.

The front-matter half of what used to be ``_core/snippets`` in both
epy_reports and epy_slides -- byte for byte identical in the two, so a
fix to one reached the other only if someone remembered.

Only this half moved. The other half is the editor's snippet palette
(figure, table, equation and link templates, label finding), which has
two consumers and both of them are user interfaces. A library whose
whole point is that it needs no UI should not own the insert menu of a
text editor.

**The parser stays hand-rolled and is ported unchanged.** Not moving to
PyYAML is a deliberate refusal on two grounds. The stated one is weight:
this keeps a YAML dependency out of four frozen bundles. The one that
actually binds is behaviour -- every title, footer and watermark path in
every document already written was parsed by these exact rules, quoting
quirks included, and a "proper" parser disagrees with them in cases
nobody has enumerated. Correctness here means bug-compatible.
"""

from __future__ import annotations

import json
import re

__all__ = [
    "parse_front_matter",
    "parse_header_cells",
    "set_metadata_field",
    "strip_front_matter",
]


def strip_front_matter(text: str) -> str:
    """Return the document body with the YAML front-matter block removed."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end < 0:
        return text
    return text[end + 4:]


def parse_front_matter(text: str) -> dict[str, str]:
    """Extract top-level ``key: value`` pairs from a YAML block.

    Nested mappings, lists and multi-line scalars are skipped. The
    result is good enough for fields like ``title``, ``author``,
    ``date``, ``bibliography`` and ``csl`` — which is all the editor
    needs at runtime.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end]
    meta: dict[str, str] = {}
    for raw in block.splitlines():
        if not raw or raw.startswith("#") or raw.startswith(" "):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        meta[key.strip()] = value.strip().strip("\"'")
    return meta


def parse_header_cells(value: object) -> list[str]:
    """Normalize a ``header`` front-matter value into a list of cells.

    ``parse_front_matter`` returns scalars as strings, so a YAML flow
    sequence like ``["A", "B"]`` arrives here as that literal string. This
    accepts either a real list or that JSON-ish string and returns the cell
    strings; anything else becomes a single-cell list.
    """
    if isinstance(value, list):
        return [str(x) for x in value]
    text = str(value or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            items = json.loads(text)
        except (ValueError, TypeError):
            items = None
        if isinstance(items, list):
            return [str(x) for x in items]
    return [text]


def _format_yaml_value(value: str) -> str:
    """Quote ``value`` if it would be ambiguous as a YAML scalar."""
    needs_quotes = (
        value == ""
        or value[0] in "!&*?|>%@`"
        or value.strip() != value
        or any(ch in value for ch in ":#")
    )
    if needs_quotes:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def set_metadata_field(
    text: str, field: str, value: str, *, raw: bool = False
) -> str:
    """Insert or replace a top-level YAML ``field`` in ``text``.

    Creates a front-matter block at the top of the buffer when none
    exists. When the field is already present, its value is replaced
    in place; otherwise the field is appended to the existing block.

    Args:
        text: The full document text.
        field: The YAML key to set.
        value: The value to write.
        raw: When ``True`` the value is written verbatim (no scalar
            quoting). Use it for values that are already valid YAML, such
            as a flow sequence ``["a", "b"]`` for the ``header`` field.
    """
    formatted = value if raw else _format_yaml_value(value)
    line = f"{field}: {formatted}"

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            head = text[:3]  # opening '---'
            block = text[3:end]
            tail = text[end:]
            pattern = re.compile(
                rf"^{re.escape(field)}\s*:.*$", re.MULTILINE
            )
            if pattern.search(block):
                block = pattern.sub(line, block, count=1)
            else:
                if not block.endswith("\n"):
                    block += "\n"
                block += line + "\n"
            return head + block + tail

    # No usable front matter — prepend a fresh block.
    return f"---\n{line}\n---\n\n{text}"
