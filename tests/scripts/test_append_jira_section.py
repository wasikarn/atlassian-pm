"""Tests for append_after_section() in scripts/api/update_jira_description.py."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from api.update_jira_description import append_after_section, process_append_section
from lib.exceptions import APIError, IssueNotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(*nodes) -> dict:
    return {"type": "doc", "version": 1, "content": list(nodes)}


def _heading(level: int, text: str) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def _paragraph(text: str) -> dict:
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": text}],
    }


# ---------------------------------------------------------------------------
# Section found — insertion placed correctly
# ---------------------------------------------------------------------------

class TestAppendAfterSectionFound:
    def test_appends_after_last_block_in_section(self) -> None:
        doc = _make_doc(
            _heading(2, "Overview"),
            _paragraph("First para."),
            _paragraph("Second para."),
            _heading(2, "Details"),
            _paragraph("Detail para."),
        )
        result = append_after_section(doc, "Overview", "Appended text")
        content = result["content"]

        # Find positions
        overview_idx = next(i for i, n in enumerate(content) if n.get("type") == "heading" and "Overview" in str(n))
        details_idx = next(i for i, n in enumerate(content) if n.get("type") == "heading" and "Details" in str(n))
        appended_idx = next(
            i for i, n in enumerate(content)
            if n.get("type") == "paragraph" and "Appended text" in str(n.get("content", ""))
        )

        assert overview_idx < appended_idx < details_idx, (
            "Appended paragraph should be inside the Overview section, before Details"
        )

    def test_appends_at_end_when_last_section(self) -> None:
        doc = _make_doc(
            _heading(2, "Final Section"),
            _paragraph("Only content."),
        )
        result = append_after_section(doc, "Final Section", "End content")
        content = result["content"]
        texts = [
            n["content"][0]["text"]
            for n in content
            if n.get("type") == "paragraph"
        ]
        assert texts[-1] == "End content"

    def test_case_insensitive_fallback(self) -> None:
        doc = _make_doc(
            _heading(2, "Technical Notes"),
            _paragraph("Some notes."),
        )
        result = append_after_section(doc, "technical notes", "Case insensitive content")
        paragraphs = [n for n in result["content"] if n.get("type") == "paragraph"]
        texts = [p["content"][0]["text"] for p in paragraphs]
        assert "Case insensitive content" in texts

    def test_exact_match_preferred_over_case_insensitive(self) -> None:
        doc = _make_doc(
            _heading(2, "Notes"),
            _paragraph("First section body."),
            _heading(2, "notes"),
            _paragraph("Second section body."),
        )
        result = append_after_section(doc, "Notes", "Exact match")
        content = result["content"]
        # Find paragraph index for exact match
        first_notes_idx = next(
            i for i, n in enumerate(content)
            if n.get("type") == "heading"
            and n.get("content", [{}])[0].get("text") == "Notes"
        )
        second_notes_idx = next(
            i for i, n in enumerate(content)
            if n.get("type") == "heading"
            and n.get("content", [{}])[0].get("text") == "notes"
        )
        appended_idx = next(
            i for i, n in enumerate(content)
            if n.get("type") == "paragraph"
            and n.get("content", [{}])[0].get("text") == "Exact match"
        )
        assert first_notes_idx < appended_idx < second_notes_idx

    def test_does_not_mutate_original_doc(self) -> None:
        import copy
        doc = _make_doc(
            _heading(2, "Section"),
            _paragraph("Original."),
        )
        original_len = len(doc["content"])
        original_copy = copy.deepcopy(doc)

        append_after_section(doc, "Section", "New content")

        assert len(doc["content"]) == original_len, "Original doc should not be mutated"
        assert doc == original_copy

    def test_stops_before_same_level_heading(self) -> None:
        """Content is inserted before the next heading at the same level."""
        doc = _make_doc(
            _heading(2, "Section A"),
            _paragraph("A body."),
            _heading(2, "Section B"),
            _paragraph("B body."),
        )
        result = append_after_section(doc, "Section A", "A appended")
        content = result["content"]
        b_idx = next(i for i, n in enumerate(content) if n.get("type") == "heading" and "Section B" in str(n))
        appended_idx = next(
            i for i, n in enumerate(content)
            if n.get("type") == "paragraph" and "A appended" in str(n.get("content", ""))
        )
        assert appended_idx < b_idx

    def test_subsection_headings_included_in_section_scope(self) -> None:
        """h3 under an h2 section is part of that section; insertion after h3 body."""
        doc = _make_doc(
            _heading(2, "Parent Section"),
            _paragraph("Parent body."),
            _heading(3, "Child Section"),
            _paragraph("Child body."),
            _heading(2, "Next Section"),
        )
        result = append_after_section(doc, "Parent Section", "Parent appended")
        content = result["content"]
        next_section_idx = next(
            i for i, n in enumerate(content)
            if n.get("type") == "heading" and "Next Section" in str(n)
        )
        appended_idx = next(
            i for i, n in enumerate(content)
            if n.get("type") == "paragraph" and "Parent appended" in str(n.get("content", ""))
        )
        assert appended_idx < next_section_idx


# ---------------------------------------------------------------------------
# Section not found — error + suggestions
# ---------------------------------------------------------------------------

class TestAppendAfterSectionNotFound:
    def test_raises_value_error(self) -> None:
        doc = _make_doc(_heading(2, "Overview"), _paragraph("Body."))
        with pytest.raises(ValueError, match="not found"):
            append_after_section(doc, "Nonexistent Section", "content")

    def test_error_includes_available_headings(self) -> None:
        doc = _make_doc(
            _heading(2, "Overview"),
            _heading(3, "Details"),
        )
        with pytest.raises(ValueError) as exc_info:
            append_after_section(doc, "Missing", "content")
        msg = str(exc_info.value)
        assert "Overview" in msg
        assert "Details" in msg

    def test_error_includes_fuzzy_suggestions(self) -> None:
        doc = _make_doc(_heading(2, "Technical Notes"), _paragraph("Body."))
        with pytest.raises(ValueError) as exc_info:
            append_after_section(doc, "Technical Summary", "content")
        assert "Technical Notes" in str(exc_info.value)


# ---------------------------------------------------------------------------
# process_append_section — found/not-found/dry-run via mock API
# ---------------------------------------------------------------------------

class TestProcessAppendSection:
    def _mock_api(self, description=None) -> MagicMock:
        api = MagicMock()
        api.get_issue.return_value = {
            "fields": {
                "summary": "Test issue",
                "description": description or _make_doc(
                    _heading(2, "Overview"),
                    _paragraph("Body text."),
                ),
            }
        }
        api.update_description.return_value = 204
        return api

    def test_dry_run_returns_success_without_update(self) -> None:
        api = self._mock_api()
        status = process_append_section(api, "TP-1", "Overview", "New text", dry_run=True)
        assert status == "success"
        api.update_description.assert_not_called()

    def test_live_mode_calls_update_description(self) -> None:
        api = self._mock_api()
        status = process_append_section(api, "TP-1", "Overview", "New text", dry_run=False)
        assert status == "success"
        api.update_description.assert_called_once()
        # Verify that the ADF passed to update_description contains the new paragraph
        call_args = api.update_description.call_args
        new_adf = call_args[0][1]
        all_texts = [
            n["content"][0]["text"]
            for n in new_adf.get("content", [])
            if n.get("type") == "paragraph" and n.get("content")
        ]
        assert "New text" in all_texts

    def test_section_not_found_returns_failed(self) -> None:
        api = self._mock_api()
        status = process_append_section(api, "TP-1", "Nonexistent", "text", dry_run=False)
        assert status == "failed"
        api.update_description.assert_not_called()

    def test_issue_not_found_returns_failed(self) -> None:
        api = MagicMock()
        api.get_issue.side_effect = IssueNotFoundError("TP-999")
        status = process_append_section(api, "TP-999", "Section", "text", dry_run=False)
        assert status == "failed"

    def test_api_error_returns_failed(self) -> None:
        api = MagicMock()
        api.get_issue.side_effect = APIError(500, "Server Error", "boom")
        status = process_append_section(api, "TP-1", "Section", "text", dry_run=False)
        assert status == "failed"

    def test_missing_description_returns_skipped(self) -> None:
        api = MagicMock()
        api.get_issue.return_value = {
            "fields": {"summary": "Issue with no description", "description": None}
        }
        status = process_append_section(api, "TP-2", "Section", "text", dry_run=False)
        assert status == "skipped"
