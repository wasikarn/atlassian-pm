#!/usr/bin/env python3
"""Tests for pre_prompt_skill_redirect.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugin.session.pre_prompt_skill_redirect import detect_intent

# ── Bug detection ──────────────────────────────────────────────────────────

def test_detects_english_create_bug():
    result = detect_intent("create a bug for login issue")
    assert result is not None
    assert result[0] == "bug"
    assert result[1] == "atlassian-pm:bug-triage"


def test_detects_thai_create_bug():
    result = detect_intent("สร้าง bug เรื่อง player หยุดทำงาน")
    assert result is not None
    assert result[0] == "bug"


def test_detects_report_bug():
    result = detect_intent("I want to report a bug in the payment flow")
    assert result is not None
    assert result[0] == "bug"


def test_detects_thai_bug_found():
    result = detect_intent("พบ bug ใน API ช่วยสร้าง ticket")
    assert result is not None
    assert result[0] == "bug"


def test_detects_defect():
    result = detect_intent("found a defect in schedule calculation")
    assert result is not None
    assert result[0] == "bug"


# ── Story detection ────────────────────────────────────────────────────────

def test_detects_create_story():
    result = detect_intent("create a user story for payment integration")
    assert result is not None
    assert result[0] == "task"
    assert result[1] == "atlassian-pm:create-task"


def test_detects_thai_create_story():
    result = detect_intent("สร้าง story สำหรับ ad schedule")
    assert result is not None
    assert result[0] == "task"


def test_detects_new_story():
    result = detect_intent("new story about notification system")
    assert result is not None
    assert result[0] == "task"


# ── Task detection ─────────────────────────────────────────────────────────

def test_detects_create_task():
    result = detect_intent("create a task to update the README")
    assert result is not None
    assert result[0] == "task"
    assert result[1] == "atlassian-pm:create-task"


def test_detects_thai_create_task():
    result = detect_intent("สร้าง task สำหรับ refactor API")
    assert result is not None
    assert result[0] == "task"


def test_detects_create_ticket():
    result = detect_intent("create a jira ticket for deployment issue")
    assert result is not None
    assert result[0] == "task"


# ── Epic detection ─────────────────────────────────────────────────────────

def test_detects_create_epic():
    result = detect_intent("create an epic for the new billing module")
    assert result is not None
    assert result[0] == "epic"
    assert result[1] == "atlassian-pm:create-epic"


def test_detects_thai_create_epic():
    result = detect_intent("สร้าง epic สำหรับ player V2")
    assert result is not None
    assert result[0] == "epic"


# ── Subtask detection ──────────────────────────────────────────────────────

def test_detects_create_subtask():
    result = detect_intent("create a subtask for the BE work")
    assert result is not None
    assert result[0] == "task"
    assert result[1] == "atlassian-pm:create-task"


# ── Non-creation prompts should NOT match ─────────────────────────────────

def test_no_match_on_read_issue():
    result = detect_intent("show me TP-123 details")
    assert result is None


def test_no_match_on_update():
    result = detect_intent("update the story description for TP-456")
    assert result is None


def test_no_match_on_search():
    result = detect_intent("search for bugs related to payment")
    assert result is None


def test_no_match_on_empty():
    result = detect_intent("")
    assert result is None


def test_no_match_on_unrelated():
    result = detect_intent("what is the sprint velocity this week?")
    assert result is None


# ── Bug takes priority over task ───────────────────────────────────────────

def test_bug_not_confused_with_task():
    """'bug' keyword should not be classified as 'task'."""
    result = detect_intent("create bug ticket for ad_display_count issue")
    assert result is not None
    assert result[0] == "bug"
