#!/usr/bin/env python3
"""HR8 (SP part): Warn when task SP sum exceeds parent epic's SP by >50%.

PostToolUse hook for mcp__mcp-atlassian__jira_update_issue.
Fires when Story Points (customfield_10016) is set on a known subtask.
Compares sum of all cached sibling subtask SPs against parent SP.

Cannot block (PostToolUse) — injects additionalContext warning instead.
Debounced per parent per session to avoid repetitive messages.

Exit codes: 0 (always)
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import get_additional_fields, inject_context, log_event, parse_stdin
from hooks_state import _load, _save, hr5_is_known_subtask

CACHE_DB = Path.home() / ".cache" / "atlassian-pm" / "atlassian.db"
SP_FIELD = "customfield_10016"
SP_RATIO_THRESHOLD = 1.5  # warn if subtask sum > parent_sp * 1.5


def _get_parent_key(issue_key: str) -> str | None:
    try:
        conn = sqlite3.connect(str(CACHE_DB))
        row = conn.execute(
            "SELECT parent_key, data FROM issues WHERE issue_key = ?",
            (issue_key,),
        ).fetchone()
        conn.close()
        if not row:
            return None
        parent_key, raw_data = row
        if parent_key:
            return parent_key
        if raw_data:
            try:
                jdata = json.loads(raw_data)
                p = jdata.get("fields", {}).get("parent", {})
                if isinstance(p, dict):
                    return p.get("key")
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception as e:
        log_event("hr8-sp-sum", "ERROR", {"phase": "get_parent_key", "error": str(e)})
    return None


def _get_sp(issue_key: str) -> int | None:
    try:
        conn = sqlite3.connect(str(CACHE_DB))
        row = conn.execute(
            "SELECT data FROM issues WHERE issue_key = ?", (issue_key,)
        ).fetchone()
        conn.close()
        if not row or not row[0]:
            return None
        fields = json.loads(row[0]).get("fields", {})
        val = fields.get(SP_FIELD)
        return int(val) if val is not None else None
    except Exception:
        return None


def _get_subtask_keys(parent_key: str) -> list[str]:
    """Return all subtask keys for parent from cache DB."""
    try:
        conn = sqlite3.connect(str(CACHE_DB))
        rows = conn.execute(
            "SELECT issue_key FROM issues WHERE parent_key = ?", (parent_key,)
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def _hr8_sp_is_suggested(session_id: str, parent_key: str) -> bool:
    return parent_key in _load(session_id).get("hr8_sp_suggested", [])


def _hr8_sp_mark_suggested(session_id: str, parent_key: str) -> None:
    state = _load(session_id)
    suggested = list(state.get("hr8_sp_suggested", []))
    if parent_key not in suggested:
        suggested.append(parent_key)
    state["hr8_sp_suggested"] = suggested
    _save(session_id, state)


data = parse_stdin()
if not data:
    sys.exit(0)

tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "")
issue_key = tool_input.get("issue_key", "")
if not issue_key:
    sys.exit(0)

# Only check when SP is being set
additional = get_additional_fields(tool_input)
if SP_FIELD not in additional:
    sys.exit(0)

# Determine if this is a subtask
parent_key = _get_parent_key(issue_key)
if not parent_key:
    try:
        if not hr5_is_known_subtask(session_id, issue_key):
            sys.exit(0)
    except Exception:
        sys.exit(0)
    sys.exit(0)  # known subtask but no parent key — skip

if _hr8_sp_is_suggested(session_id, parent_key):
    sys.exit(0)

# Fetch parent SP
parent_sp = _get_sp(parent_key)
if not parent_sp:
    sys.exit(0)  # no parent SP to compare against

# Sum all sibling subtask SPs from cache
sibling_keys = _get_subtask_keys(parent_key)
sibling_total = 0
for key in sibling_keys:
    sp = _get_sp(key)
    if sp:
        sibling_total += sp

# Add the new SP being set (may replace existing — approximate)
try:
    new_sp = int(additional[SP_FIELD])
except (ValueError, TypeError):
    sys.exit(0)

# Subtract this issue's existing SP to avoid double-count
existing_sp = _get_sp(issue_key) or 0
total_after = sibling_total - existing_sp + new_sp

if total_after > parent_sp * SP_RATIO_THRESHOLD:
    _hr8_sp_mark_suggested(session_id, parent_key)
    log_event("hr8-sp-sum", "WARN", {
        "issue_key": issue_key,
        "parent_key": parent_key,
        "parent_sp": parent_sp,
        "subtask_total_after": total_after,
    })
    inject_context(
        f"HR8 WARNING: Task SP sum for {parent_key} will be ~{total_after} "
        f"but parent Epic SP is {parent_sp} (>{int(SP_RATIO_THRESHOLD * 100)}% over). "
        f"Check estimation: either parent Epic SP needs updating or tasks are over-scoped. "
        f"Run /verify-issue {parent_key} --with-subtasks (A3-A4 checks) to confirm."
    )

sys.exit(0)
