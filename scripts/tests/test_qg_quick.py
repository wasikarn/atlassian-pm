#!/usr/bin/env python3
"""Tests for scripts/ai/qg_quick.py"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.qg_quick import _count_acs, run_quick_check, structural_check

_VALID_ADF = {
    "version": 1,
    "type": "doc",
    "content": [
        {
            "type": "panel",
            "attrs": {"panelType": "info"},
            "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "Background: this feature is needed because users cannot reset their password when "
                 "using third-party OAuth providers and it causes significant support overhead."}
            ]}]
        },
        {
            "type": "panel",
            "attrs": {"panelType": "success"},
            "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "AC1: Given user clicks reset, When POST /v2/auth/reset called, Then 200 returned. "
                 "AC2: Given invalid token, When POST /v2/auth/reset called, Then 401 returned. "
                 "AC3: Given expired token, When POST /v2/auth/reset called, Then 422 returned."}
            ]}]
        },
    ]
}

_ADF_MISSING_PANEL_TYPE = {
    "version": 1,
    "type": "doc",
    "content": [
        {"type": "panel", "attrs": {}, "content": []},  # missing panelType
    ]
}


class TestStructuralCheck(unittest.TestCase):

    def test_valid_adf_no_issues(self):
        issues, ac_count, penalty = structural_check(_VALID_ADF)
        self.assertEqual(issues, [])
        self.assertEqual(ac_count, 3)
        self.assertEqual(penalty, 0)

    def test_missing_panel_type(self):
        issues, _, penalty = structural_check(_ADF_MISSING_PANEL_TYPE)
        self.assertTrue(any("panelType" in i for i in issues))
        # panelType missing (+15) + no ACs (+20) + no background (+15) = 50
        self.assertEqual(penalty, 50)

    def test_low_ac_count(self):
        adf = {"version": 1, "type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "AC1: something"}]}
        ]}
        issues, ac_count, penalty = structural_check(adf)
        self.assertEqual(ac_count, 1)
        self.assertGreater(penalty, 0)
        self.assertTrue(any("AC" in i for i in issues))

    def test_missing_background(self):
        adf = {"version": 1, "type": "doc", "content": [
            {"type": "paragraph", "content": [
                {"type": "text", "text": "AC1: test AC2: test AC3: test"}
            ]}
        ]}
        issues, _, penalty = structural_check(adf)
        self.assertTrue(any("Background" in i for i in issues))
        self.assertGreater(penalty, 0)


class TestCountAcs(unittest.TestCase):

    def test_counts_ac_markers(self):
        adf = {"type": "doc", "content": [{"type": "text", "text": "AC1: do this. AC2: do that. AC3: do more."}]}
        self.assertEqual(_count_acs(adf), 3)

    def test_zero_when_none(self):
        adf = {"type": "doc", "content": [{"type": "text", "text": "no acceptance criteria here"}]}
        self.assertEqual(_count_acs(adf), 0)


class TestRunQuickCheck(unittest.TestCase):

    def test_strong_adf_may_skip_full_agent(self):
        # With claude unavailable (returns None), score based on structure only
        with patch("ai.qg_quick.run_claude_json", return_value=None):
            result = run_quick_check(_VALID_ADF, "story")
        self.assertTrue(result["quick_pass"])
        self.assertEqual(result["structural_issues"], [])
        self.assertGreaterEqual(result["score_estimate"], 70)

    def test_missing_panel_type_fails_quick(self):
        with patch("ai.qg_quick.run_claude_json", return_value=None):
            result = run_quick_check(_ADF_MISSING_PANEL_TYPE, "story")
        self.assertFalse(result["quick_pass"])
        self.assertGreater(len(result["structural_issues"]), 0)

    def test_content_check_reduces_score(self):
        ai_response = {
            "ac_ok": False,
            "language_ok": True,
            "background_ok": True,
            "ac_issues": ["AC2 uses generic 'call API' — must name specific endpoint"],
            "language_issues": []
        }
        with patch("ai.qg_quick.run_claude_json", return_value=ai_response):
            result = run_quick_check(_VALID_ADF, "story")
        self.assertGreater(len(result["content_issues"]), 0)
        self.assertLess(result["score_estimate"], 100)

    def test_skip_full_agent_only_when_perfect(self):
        ai_response = {
            "ac_ok": True, "language_ok": True, "background_ok": True,
            "ac_issues": [], "language_issues": []
        }
        with patch("ai.qg_quick.run_claude_json", return_value=ai_response):
            result = run_quick_check(_VALID_ADF, "story")
        self.assertTrue(result["skip_full_agent"])
        self.assertEqual(result["score_estimate"], 100)

    def test_ai_unavailable_is_non_blocking(self):
        """If claude unavailable, structural check still works."""
        with patch("ai.qg_quick.run_claude_json", return_value=None):
            result = run_quick_check(_VALID_ADF, "story")
        self.assertIsNotNone(result)
        self.assertIn("score_estimate", result)


if __name__ == "__main__":
    unittest.main()
