"""Tests for atlassian_cache.sections — 100% coverage."""
from atlassian_cache.sections import split_sections, diff_sections, SectionData


def test_split_single_section():
    md = "## Overview\n\nThis is the overview text.\n"
    sections = split_sections("P1", md)
    assert len(sections) == 1
    assert sections[0].heading == "Overview"
    assert sections[0].section_id == "P1::overview"
    assert "overview text" in sections[0].body_md


def test_split_multiple_sections():
    md = "## Intro\n\nIntro text.\n\n## Details\n\nDetail text.\n"
    sections = split_sections("P2", md)
    assert len(sections) == 2
    assert sections[0].heading == "Intro"
    assert sections[1].heading == "Details"


def test_split_no_h2():
    """Pages with no H2 headings return a single synthetic section."""
    md = "Just some plain text without headings."
    sections = split_sections("P3", md)
    assert len(sections) == 1
    assert sections[0].heading == "_body"
    assert sections[0].section_id == "P3::_body"  # sentinel must not be slugified


def test_split_section_id_slugification():
    md = "## My Complex Heading!\n\nContent.\n"
    sections = split_sections("P4", md)
    assert sections[0].section_id == "P4::my-complex-heading"


def test_split_empty_page():
    sections = split_sections("P5", "")
    assert sections == []


def test_content_hash_is_sha256():
    import hashlib
    md = "## Section\n\nBody text.\n"
    sections = split_sections("P6", md)
    expected = hashlib.sha256(sections[0].body_md.encode()).hexdigest()
    assert sections[0].content_hash == expected


def test_diff_detects_new_sections():
    new = split_sections("P7", "## A\n\nNew content.\n\n## B\n\nContent B.\n")
    old = split_sections("P7", "## A\n\nOld content.\n")
    changed, removed = diff_sections(new, {s.section_id: s for s in old})
    assert any(s.heading == "A" for s in changed)  # A changed
    assert any(s.heading == "B" for s in changed)  # B is new


def test_diff_detects_removed_sections():
    new = split_sections("P8", "## A\n\nSame content.\n")
    old = split_sections("P8", "## A\n\nSame content.\n\n## B\n\nContent B.\n")
    changed, removed = diff_sections(new, {s.section_id: s for s in old})
    assert len(changed) == 0  # A is unchanged
    assert "P8::b" in removed


def test_diff_unchanged_not_in_changed():
    content = "## A\n\nIdentical content.\n"
    sections = split_sections("P9", content)
    old_map = {s.section_id: s for s in sections}
    changed, removed = diff_sections(sections, old_map)
    assert len(changed) == 0  # nothing changed
    assert len(removed) == 0
