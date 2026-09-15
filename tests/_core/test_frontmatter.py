"""The hand-rolled front-matter parser, ported unchanged from two copies.

Bug-compatible on purpose (see the module docstring): every title,
footer and watermark path in every document already written was parsed
by these exact rules, quoting quirks included. Nothing here had a test
before -- the whole module carried 17% coverage.
"""

from __future__ import annotations

from epy_export._core import _frontmatter

# --- strip_front_matter -----------------------------------------------------


def test_strip_removes_the_block_and_keeps_the_body() -> None:
    text = "---\ntitle: T\n---\n\nBody text.\n"
    assert _frontmatter.strip_front_matter(text) == "\n\nBody text.\n"


def test_strip_leaves_a_document_with_no_front_matter_alone() -> None:
    text = "# Just a heading\n\nBody.\n"
    assert _frontmatter.strip_front_matter(text) == text


def test_strip_leaves_an_unterminated_block_alone() -> None:
    # Opens with --- but never closes it -- not a front-matter block at
    # all, just a document that happens to start with a horizontal rule.
    text = "---\ntitle: T\n\nBody with no closing marker.\n"
    assert _frontmatter.strip_front_matter(text) == text


# --- parse_front_matter ------------------------------------------------------


def test_parse_reads_simple_scalar_fields() -> None:
    text = '---\ntitle: My Report\nauthor: "Ing. Angel"\n---\n\nBody\n'
    meta = _frontmatter.parse_front_matter(text)
    assert meta["title"] == "My Report"
    assert meta["author"] == "Ing. Angel"


def test_parse_skips_comments_indented_and_valueless_lines() -> None:
    text = (
        "---\n"
        "# a comment\n"
        "  nested: under something\n"
        "no colon here\n"
        "title: T\n"
        "---\n\nBody\n"
    )
    assert _frontmatter.parse_front_matter(text) == {"title": "T"}


def test_parse_returns_empty_for_a_document_with_no_front_matter() -> None:
    assert _frontmatter.parse_front_matter("Just a body.\n") == {}


def test_parse_returns_empty_for_an_unterminated_block() -> None:
    assert _frontmatter.parse_front_matter("---\ntitle: T\n\nBody\n") == {}


# --- parse_header_cells -------------------------------------------------


def test_header_cells_from_a_real_list() -> None:
    assert _frontmatter.parse_header_cells(["A", "B", 3]) == ["A", "B", "3"]


def test_header_cells_from_an_empty_value() -> None:
    assert _frontmatter.parse_header_cells(None) == []
    assert _frontmatter.parse_header_cells("") == []


def test_header_cells_from_a_flow_sequence_string() -> None:
    # parse_front_matter only ever returns scalars, so a YAML flow
    # sequence like ["A", "B"] arrives here as that literal string.
    assert _frontmatter.parse_header_cells('["A", "B"]') == ["A", "B"]


def test_header_cells_from_unparseable_bracketed_text_is_one_cell() -> None:
    assert _frontmatter.parse_header_cells("[not json") == ["[not json"]


def test_header_cells_from_a_plain_scalar_is_one_cell() -> None:
    assert _frontmatter.parse_header_cells("Just one column") == [
        "Just one column"
    ]


# --- set_metadata_field ---------------------------------------------------


def test_set_field_creates_a_block_when_there_is_none() -> None:
    result = _frontmatter.set_metadata_field("Body only.\n", "title", "T")
    assert result == "---\ntitle: T\n---\n\nBody only.\n"


def test_set_field_replaces_an_existing_value_in_place() -> None:
    text = "---\ntitle: Old\nauthor: A\n---\n\nBody\n"
    result = _frontmatter.set_metadata_field(text, "title", "New")
    assert "title: New" in result
    assert "title: Old" not in result
    assert "author: A" in result


def test_set_field_appends_a_new_field_to_an_existing_block() -> None:
    text = "---\ntitle: T\n---\n\nBody\n"
    result = _frontmatter.set_metadata_field(text, "author", "A")
    assert "title: T" in result
    assert "author: A" in result


def test_set_field_on_an_unterminated_block_prepends_a_fresh_one() -> None:
    # Opens with --- but never closes -- treated as no usable front
    # matter at all, so a fresh block is prepended rather than edited.
    text = "---\ntitle: T\n\nBody\n"
    result = _frontmatter.set_metadata_field(text, "author", "A")
    assert result.startswith("---\nauthor: A\n---\n\n")
    assert text in result


def test_set_field_quotes_a_value_that_needs_it() -> None:
    result = _frontmatter.set_metadata_field("Body\n", "title", "a: b")
    assert 'title: "a: b"' in result


def test_set_field_escapes_a_quote_inside_a_value_needing_quotes() -> None:
    result = _frontmatter.set_metadata_field(
        "Body\n", "title", 'a "quoted" word: yes'
    )
    assert r'\"quoted\"' in result


def test_set_field_leaves_a_plain_value_unquoted() -> None:
    result = _frontmatter.set_metadata_field("Body\n", "title", "Plain")
    assert "title: Plain\n" in result
    assert '"Plain"' not in result


def test_set_field_can_write_a_raw_yaml_value_unquoted() -> None:
    result = _frontmatter.set_metadata_field(
        "Body\n", "header", '["A", "B"]', raw=True
    )
    assert 'header: ["A", "B"]' in result


# --- is_truthy -------------------------------------------------------------


def test_is_truthy_recognises_every_affirmative_spelling() -> None:
    for word in ("true", "TRUE", "yes", "Yes", "1", "on", " on "):
        assert _frontmatter.is_truthy(word) is True


def test_is_truthy_is_false_for_none_and_anything_else() -> None:
    assert _frontmatter.is_truthy(None) is False
    assert _frontmatter.is_truthy("") is False
    assert _frontmatter.is_truthy("false") is False
    assert _frontmatter.is_truthy("nope") is False
