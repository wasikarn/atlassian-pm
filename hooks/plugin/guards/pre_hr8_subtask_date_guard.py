#!/usr/bin/env python3
"""HR8: Block subtask date updates that fall outside parent story's date range.

PreToolUse hook for mcp__mcp-atlassian__jira_update_issue.
Checks customfield_10015 (start date) and duedate against parent dates.

Detection: cache DB issue_type/parent_key → fetch parent dates → compare.
Falls back silently if parent dates are unknown (no cache entry).

Exit codes: 0 = allow, 2 = block (date out of range)
"""

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import get_additional_fields, log_event, parse_stdin
from hooks_state import hr5_is_known_subtask

CACHE_DB = Path.home() / ".cache" / "atlassian-pm" / "atlassian.db"
START_FIELD = "customfield_10015"
DUE_FIELD = "duedate"


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def _get_parent_key_from_cache(issue_key: str) -> str | None:
    """Return parent_key for issue_key from cache DB, or None."""
    try:
        conn = sqlite3.connect(str(CACHE_DB))
        row = conn.execute(
            "SELECT issue_type, parent_key, data FROM issues WHERE issue_key = ?",
            (issue_key,),
        ).fetchone()
        conn.close()
        if not row:
            return None
        issue_type, parent_key, raw_data = row
        # Layer 1: structured columns
        if parent_key:
            return parent_key
        # Layer 2: raw JSON
        if raw_data:
            try:
                jdata = json.loads(raw_data)
                parent = jdata.get("fields", {}).get("parent", {})
                if isinstance(parent, dict) and parent.get("key"):
                    return parent["key"]
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception as e:
        log_event("hr8-date-guard", "ERROR", {"phase": "get_parent_key", "issue_key": issue_key, "error": str(e)})
    return None


def _get_story_dates(story_key: str) -> tuple[date | None, date | None]:
    """Return (start_date, due_date) for story_key from cache DB."""
    try:
        conn = sqlite3.connect(str(CACHE_DB))
        row = conn.execute(
            "SELECT data FROM issues WHERE issue_key = ?",
            (story_key,),
        ).fetchone()
        conn.close()
        if not row or not row[0]:
            return None, None
        jdata = json.loads(row[0])
        fields = jdata.get("fields", {})
        start = _parse_date(fields.get(START_FIELD) or fields.get("customfield_10015"))
        due = _parse_date(fields.get("duedate"))
        return start, due
    except Exception as e:
        log_event("hr8-date-guard", "ERROR", {"phase": "get_story_dates", "story_key": story_key, "error": str(e)})
        return None, None


data = parse_stdin()
if not data:
    sys.exit(0)

tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "")

issue_key = tool_input.get("issue_key", "")
if not issue_key:
    sys.exit(0)

# Only check date fields
additional = get_additional_fields(tool_input)
new_start = _parse_date(additional.get(START_FIELD))
new_due = _parse_date(additional.get(DUE_FIELD))

if not new_start and not new_due:
    sys.exit(0)  # no date fields being set — nothing to check

# Determine if this is a subtask
parent_key = _get_parent_key_from_cache(issue_key)
if not parent_key:
    # Fallback: check HR5 session state
    try:
        if not hr5_is_known_subtask(session_id, issue_key):
            sys.exit(0)
        # It's a known subtask but parent_key unknown — skip (can't validate without parent dates)
        sys.exit(0)
    except Exception:
        sys.exit(0)

# Fetch parent date range
parent_start, parent_due = _get_story_dates(parent_key)

violations = []

if new_start and parent_start and new_start < parent_start:
    violations.append(
        f"  Start date {new_start} is before parent {parent_key} start {parent_start}"
    )

if new_due and parent_due and new_due > parent_due:
    violations.append(
        f"  Due date {new_due} is after parent {parent_key} due {parent_due}"
    )

if new_start and new_due and new_start > new_due:
    violations.append(
        f"  Start date {new_start} is after due date {new_due} (invalid range)"
    )

if violations:
    log_event("hr8-date-guard", "BLOCKED", {
        "issue_key": issue_key,
        "parent_key": parent_key,
        "new_start": str(new_start),
        "new_due": str(new_due),
        "parent_start": str(parent_start),
        "parent_due": str(parent_due),
    })
    print(
        f"HR8 BLOCKED: Subtask date alignment violation for {issue_key}.\n"
        + "\n".join(violations)
        + f"\nFix: keep subtask dates within {parent_key} range "
        + f"({parent_start} → {parent_due}).",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)
