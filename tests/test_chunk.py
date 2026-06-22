from __future__ import annotations

from atlas.chunk import (
    _hard_split,
    _is_code_chunk,
    _split_on_h2,
    chunk_markdown,
    parse_frontmatter,
)


def test_no_frontmatter_passthrough() -> None:
    meta, body = parse_frontmatter("hello")
    assert meta == {}
    assert body == "hello"


def test_valid_frontmatter() -> None:
    md = "---\ntitle: Foo\n---\n\nbody text"
    meta, body = parse_frontmatter(md)
    assert meta == {"title": "Foo"}
    assert body == "body text"


def test_malformed_yaml_still_returns_body() -> None:
    md = "---\n: bad\n---\n\nbody"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body == "body"


def test_split_on_h2_single_returns_overview() -> None:
    sections = _split_on_h2("just prose")
    assert sections == [("Overview", "just prose")]


def test_split_on_h2_respects_boundaries() -> None:
    sections = _split_on_h2("intro\n## H2A\nbody a\n## H2B\nbody b")
    assert len(sections) == 3
    assert sections[0] == ("Overview", "intro")
    assert sections[1][0] == "H2A"
    assert sections[2][0] == "H2B"
    assert "body a" in sections[1][1]
    assert "body b" in sections[2][1]


def test_is_code_chunk_true_for_fenced_block() -> None:
    assert _is_code_chunk("```python\nx=1\n```") is True


def test_is_code_chunk_false_no_fence() -> None:
    assert _is_code_chunk("just text") is False


def test_hard_split_under_limit_is_noop() -> None:
    assert _hard_split("short", 100) == ["short"]


def test_hard_split_paragraph_boundary() -> None:
    text = "a" * 100 + "\n\n" + "b" * 100
    parts = _hard_split(text, 120)
    assert len(parts) == 2
    assert all(len(p) <= 120 for p in parts)


def test_chunk_markdown_produces_records() -> None:
    md = "---\ntitle: Test\n---\n\nintro\n\n## Section A\ncode body\n```\nx=1\n```"
    chunks = chunk_markdown(md, publication="test", file="a.md")
    assert len(chunks) >= 2
    assert chunks[0]["heading"] == "Overview"
    assert chunks[0]["publication"] == "test"
    assert chunks[0]["file"] == "a.md"
    assert chunks[1]["heading"] == "Section A"
    assert chunks[1]["is_code"] is True
