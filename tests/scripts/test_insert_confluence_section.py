"""Tests for insert_after_section() in scripts/api/update_confluence_page.py."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from api.update_confluence_page import insert_after_section

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _page_xml(*headings_and_paras: str) -> str:
    """Build a minimal Confluence storage XML body from alternating H2 + p blocks."""
    return "".join(headings_and_paras)


# ---------------------------------------------------------------------------
# Section found — insertion placed correctly
# ---------------------------------------------------------------------------

class TestInsertAfterSectionFound:
    def test_inserts_paragraph_after_first_block_following_heading(self) -> None:
        xml = (
            "<h2>Overview</h2>"
            "<p>Existing paragraph.</p>"
            "<h2>Details</h2>"
            "<p>Detail paragraph.</p>"
        )
        result = insert_after_section(xml, "Overview", "New content here")

        # The new <p> should appear after the first block under Overview
        overview_end = result.index("Existing paragraph.")
        details_start = result.index("<h2>Details</h2>")
        new_content_pos = result.index("New content here")

        assert overview_end < new_content_pos < details_start, (
            "New content should be between the first Overview paragraph and the Details heading"
        )

    def test_case_insensitive_fallback(self) -> None:
        xml = "<h2>Technical Notes</h2><p>Some note.</p>"
        result = insert_after_section(xml, "technical notes", "Added via case-insensitive match")
        assert "Added via case-insensitive match" in result

    def test_exact_match_preferred_over_case_insensitive(self) -> None:
        xml = (
            "<h2>Notes</h2><p>First section.</p>"
            "<h2>notes</h2><p>Second section.</p>"
        )
        result = insert_after_section(xml, "Notes", "Exact match content")
        # Should insert after "First section." not "Second section."
        first_para_pos = result.index("First section.")
        second_para_pos = result.index("Second section.")
        new_pos = result.index("Exact match content")
        assert first_para_pos < new_pos < second_para_pos

    def test_inserts_raw_content_without_p_wrap(self) -> None:
        xml = "<h2>Section A</h2><p>Para.</p>"
        result = insert_after_section(xml, "Section A", "<ul><li>item</li></ul>", raw=True)
        assert "<ul>" in result
        assert "<li>item</li>" in result
        # raw content should NOT be double-wrapped
        assert "<p><ul>" not in result

    def test_insertion_at_end_when_last_section(self) -> None:
        xml = "<h2>Last Section</h2><p>Only paragraph.</p>"
        result = insert_after_section(xml, "Last Section", "Appended content")
        assert "Appended content" in result
        # New content comes after existing paragraph
        assert result.index("Only paragraph.") < result.index("Appended content")

    def test_heading_with_no_following_block(self) -> None:
        """Heading at end of doc with no body — insert right after it."""
        xml = "<h2>Empty Section</h2>"
        result = insert_after_section(xml, "Empty Section", "First paragraph")
        assert "First paragraph" in result
        assert result.index("<h2>Empty Section</h2>") < result.index("First paragraph")


# ---------------------------------------------------------------------------
# Section not found — error + suggestions
# ---------------------------------------------------------------------------

class TestInsertAfterSectionNotFound:
    def test_raises_value_error_when_section_missing(self) -> None:
        xml = "<h2>Overview</h2><p>Content.</p>"
        with pytest.raises(ValueError, match="not found"):
            insert_after_section(xml, "Nonexistent Section", "content")

    def test_error_includes_available_headings(self) -> None:
        xml = "<h2>Overview</h2><p>A.</p><h3>Details</h3><p>B.</p>"
        with pytest.raises(ValueError) as exc_info:
            insert_after_section(xml, "Missing Section", "content")
        msg = str(exc_info.value)
        assert "Overview" in msg
        assert "Details" in msg

    def test_error_includes_fuzzy_suggestions(self) -> None:
        xml = "<h2>Technical Notes</h2><p>A.</p>"
        with pytest.raises(ValueError) as exc_info:
            insert_after_section(xml, "Technical Summary", "content")
        msg = str(exc_info.value)
        # "Technical" is a shared word — should suggest "Technical Notes"
        assert "Technical Notes" in msg

    def test_no_suggestions_when_no_overlap(self) -> None:
        xml = "<h2>Overview</h2><p>A.</p>"
        with pytest.raises(ValueError) as exc_info:
            insert_after_section(xml, "ZZZ XYZ ABC", "content")
        # Should still mention available headings even without fuzzy match
        assert "Overview" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Dry-run mode — prints but doesn't call API
# ---------------------------------------------------------------------------

class TestInsertAfterSectionDryRun:
    def test_dry_run_returns_true_without_api_call(self) -> None:
        """process_insert_after_section with dry_run=True should not call update_page."""
        from api.update_confluence_page import process_insert_after_section

        mock_api = MagicMock()
        mock_api.get_page.return_value = {
            "title": "Test Page",
            "version": {"number": 3},
            "body": {"storage": {"value": "<h2>Overview</h2><p>Existing.</p>"}},
        }

        result = process_insert_after_section(
            mock_api,
            "111",
            "Overview",
            "Dry run content",
            dry_run=True,
        )

        assert result is True
        mock_api.update_page.assert_not_called()

    def test_dry_run_prints_preview(self, capsys) -> None:
        from api.update_confluence_page import process_insert_after_section

        mock_api = MagicMock()
        mock_api.get_page.return_value = {
            "title": "Test Page",
            "version": {"number": 1},
            "body": {"storage": {"value": "<h2>My Section</h2><p>Body text.</p>"}},
        }

        process_insert_after_section(
            mock_api,
            "222",
            "My Section",
            "Preview text here",
            dry_run=True,
        )

        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_live_mode_calls_update_page(self) -> None:
        from api.update_confluence_page import process_insert_after_section

        mock_api = MagicMock()
        mock_api.get_page.return_value = {
            "title": "Test Page",
            "version": {"number": 2},
            "body": {"storage": {"value": "<h2>Section</h2><p>Body.</p>"}},
        }
        mock_api.update_page.return_value = {"version": {"number": 3}}

        result = process_insert_after_section(
            mock_api,
            "333",
            "Section",
            "New content",
            dry_run=False,
        )

        assert result is True
        mock_api.update_page.assert_called_once()
