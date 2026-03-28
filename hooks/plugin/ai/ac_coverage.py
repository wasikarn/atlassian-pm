#!/usr/bin/env python3
"""PostToolUse async hook: semantic AC↔subtask coverage scoring.

Fires after jira_create_issue for subtasks. Scores how well subtask
objectives semantically cover the parent story ACs.
Exit code: 0 always.
"""

import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, inject_context, log_event, parse_stdin
from hooks_state import _load, _save, vs_get_coverage
from plugin.ai.claude_call import claude_call

_HOOK = "ai-ac-coverage"

_SCORE_PROMPT = """\
You are reviewing Jira subtask coverage of story acceptance criteria.

Story Acceptance Criteria:
{acs}

Subtask Objectives (created so far):
{subtasks}

Score (0-100): what percentage of the ACs are adequately addressed by the subtasks?
Consider semantic meaning, not just keyword matching.
Respond with only an integer 0-100."""


def check_coverage(acs: list[str], subtask_summaries: list[str]) -> Optional[int]:
    """Return coverage score 0-100, or None if unavailable."""
    if not acs or not subtask_summaries:
        return None

    acs_text = "\n".join(f"- {ac}" for ac in acs[:10])
    subtasks_text = "\n".join(f"- {s}" for s in subtask_summaries[:15])
    result = claude_call(_SCORE_PROMPT.format(acs=acs_text, subtasks=subtasks_text), timeout=12)

    if not result:
        return None
    try:
        return max(0, min(100, int(result.strip().split()[0])))
    except (ValueError, IndexError):
        return None


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    parent_key = None
    parent = tool_input.get("additional_fields", {})
    if isinstance(parent, str):
        try:
            parent = json.loads(parent)
        except json.JSONDecodeError:
            parent = {}
    if isinstance(parent, dict):
        p = parent.get("parent", {})
        parent_key = p.get("key") if isinstance(p, dict) else p

    if not parent_key:
        allow()
        return

    session_id = data.get("session_id", "")
    coverage = vs_get_coverage(session_id)
    acs = coverage["story_acs"].get(parent_key, [])

    resp = data.get("tool_response", {})
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except json.JSONDecodeError:
            resp = {}
    new_summary = resp.get("fields", {}).get("summary", "") if isinstance(resp, dict) else ""

    state = _load(session_id)
    subtask_summaries = state.get("ai_subtask_summaries", {}).get(parent_key, [])
    if new_summary:
        subtask_summaries = subtask_summaries + [new_summary]
        summaries_map = state.get("ai_subtask_summaries", {})
        summaries_map[parent_key] = subtask_summaries
        state["ai_subtask_summaries"] = summaries_map
        _save(session_id, state)

    score = check_coverage(acs, subtask_summaries)
    if score is None:
        allow()
        return

    log_event(_HOOK, "SCORED", {"parent": parent_key, "score": score, "ac_count": len(acs)})

    if score < 70:
        inject_context(
            f"AI COVERAGE WARNING: {parent_key} — subtasks cover ~{score}% of ACs semantically. "
            f"{len(acs)} ACs tracked, {len(subtask_summaries)} subtask(s) so far. "
            f"Consider adding subtasks for uncovered ACs before running /verify-issue."
        )


if __name__ == "__main__":
    main()
