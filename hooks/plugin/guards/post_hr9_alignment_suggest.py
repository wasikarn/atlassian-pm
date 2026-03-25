#!/usr/bin/env python3
"""HR9: Suggest alignment verification after subtask batch creation.

PostToolUse hook for mcp__mcp-atlassian__jira_create_issue.
After creating a subtask, checks if story ACs are adequately covered.
Fires once per parent story per session to avoid suggestion spam.

Logic:
  1. Track subtask count per parent in session state.
  2. On first subtask for a parent: no suggestion (too early — batch may continue).
  3. On 2nd subtask (or when AC data shows under-coverage): inject verification reminder.
  4. Debounced per parent: suggest once per parent per session.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, get_parent_key, inject_context, log_event, parse_stdin
from hooks_state import _load, _save, vs_get_coverage

_HOOK = "hr9-alignment-suggest"


def extract_issue_key(data: dict) -> str | None:
    resp = data.get("tool_response", {})
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except (json.JSONDecodeError, TypeError):
            resp = {}
    if isinstance(resp, dict):
        return resp.get("key")
    return None


def hr9_get_subtask_count(session_id: str, parent_key: str) -> int:
    return _load(session_id).get("hr9_subtask_counts", {}).get(parent_key, 0)


def hr9_increment_subtask_count(session_id: str, parent_key: str) -> int:
    state = _load(session_id)
    counts = state.get("hr9_subtask_counts", {})
    counts[parent_key] = counts.get(parent_key, 0) + 1
    state["hr9_subtask_counts"] = counts
    _save(session_id, state)
    return counts[parent_key]


def hr9_is_suggested(session_id: str, parent_key: str) -> bool:
    return parent_key in _load(session_id).get("hr9_suggested", [])


def hr9_mark_suggested(session_id: str, parent_key: str) -> None:
    state = _load(session_id)
    suggested = list(state.get("hr9_suggested", []))
    if parent_key not in suggested:
        suggested.append(parent_key)
    state["hr9_suggested"] = suggested
    _save(session_id, state)


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    parent_key = get_parent_key(tool_input)

    # Only fire for subtask creation
    if not parent_key:
        allow()
        return

    issue_key = extract_issue_key(data)
    if not issue_key:
        allow()
        return

    session_id = data.get("session_id", "")

    # Track subtask count for this parent
    count = hr9_increment_subtask_count(session_id, parent_key)

    # Only suggest once per parent per session
    if hr9_is_suggested(session_id, parent_key):
        allow()
        return

    # Check AC coverage ratio from VS state (populated by create-story Phase 2)
    coverage = vs_get_coverage(session_id)
    story_acs = coverage["story_acs"].get(parent_key, [])
    ac_count = len(story_acs)

    # Trigger: suggest when ≥ 2 subtasks created, or AC:subtask ratio > 2.5:1
    under_covered = ac_count > 0 and ac_count / count > 2.5
    enough_subtasks = count >= 2

    if not (under_covered or enough_subtasks):
        allow()
        return

    hr9_mark_suggested(session_id, parent_key)

    # Build context-aware message
    if ac_count > 0:
        msg = (
            f"HR9 REMINDER: {parent_key} has {ac_count} ACs but only {count} subtask(s) created so far. "
            f"Run /verify-issue {parent_key} --with-subtasks (A1-A6 checks) after all subtasks are created "
            f"to confirm every AC is traceable to a subtask objective."
        )
    else:
        msg = (
            f"HR9 REMINDER: {count} subtask(s) created for {parent_key}. "
            f"Run /verify-issue {parent_key} --with-subtasks after the batch is complete "
            f"to verify AC alignment (A1-A6 checks). Untraced ACs = QA gaps."
        )

    log_event(_HOOK, "SUGGEST", {
        "parent_key": parent_key,
        "subtask_count": count,
        "ac_count": ac_count,
        "session_id": session_id,
    })
    inject_context(msg)


if __name__ == "__main__":
    main()
