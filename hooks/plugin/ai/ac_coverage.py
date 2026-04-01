#!/usr/bin/env python3
"""PostToolUse async hook: semantic AC↔task coverage scoring.

Fires after jira_create_issue for tasks. Scores how well task
objectives semantically cover the parent epic/parent ACs.
Exit code: 0 always.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config_loader import load_project_config
from hooks_lib import allow, inject_context, log_event, parse_stdin
from hooks_state import _load, _save, vs_get_coverage
from plugin.ai.claude_call import claude_call_json
from plugin.ai.json_utils import SCORE_JSON_SCHEMA
from plugin.ai.prompts import SCORE_PROMPT

_HOOK = "ai-ac-coverage"


def _extract_text(node) -> str:
    """Recursively extract plain text from an ADF node."""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return " ".join(_extract_text(n) for n in node)
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        parts = []
        for child in node.get("content", []):
            parts.append(_extract_text(child))
        return " ".join(p for p in parts if p)
    return ""


def _strip_adf(text: str) -> str:
    """Extract plain text from ADF JSON or return text as-is."""
    text = text.strip()
    if not text.startswith("{") and not text.startswith("["):
        return text
    try:
        data = json.loads(text)
        return _extract_text(data)
    except (json.JSONDecodeError, TypeError):
        return text


def check_coverage(acs: list[str], subtask_summaries: list[str]) -> int | None:
    """Return coverage score 0-100, or None if unavailable."""
    if not acs or not subtask_summaries:
        return None

    clean_acs = [_strip_adf(ac) for ac in acs[:10]]
    clean_subtasks = [_strip_adf(s) for s in subtask_summaries[:15]]

    acs_text = "\n".join(f"- {ac}" for ac in clean_acs)
    subtasks_text = "\n".join(f"- {s}" for s in clean_subtasks)
    data = claude_call_json(
        SCORE_PROMPT.format(acs=acs_text, subtasks=subtasks_text),
        json_schema=SCORE_JSON_SCHEMA,
        timeout=12,
    )
    if data is None:
        return None
    score = data.get("score")
    if not isinstance(score, int):
        return None
    return max(0, min(100, score))  # clamp 0-100


def main() -> None:
    try:
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
            subtask_summaries = [*subtask_summaries, new_summary]
            summaries_map = state.get("ai_subtask_summaries", {})
            summaries_map[parent_key] = subtask_summaries
            state["ai_subtask_summaries"] = summaries_map
            _save(session_id, state)

        score = check_coverage(acs, subtask_summaries)
        if score is None:
            allow()
            return

        log_event(_HOOK, "SCORED", {"parent": parent_key, "score": score, "ac_count": len(acs)})

        config = load_project_config()
        threshold = config.get("quality", {}).get("ac_coverage_threshold", 70)

        if score < threshold:
            inject_context(
                f"AI COVERAGE WARNING: {parent_key} — tasks cover ~{score}% of epic/parent ACs semantically. "
                f"{len(acs)} ACs tracked, {len(subtask_summaries)} task(s) so far. "
                f"Consider adding tasks for uncovered ACs before running /verify-issue."
            )
    except Exception:
        allow()


if __name__ == "__main__":
    main()
