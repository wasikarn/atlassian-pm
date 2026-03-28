#!/usr/bin/env python3
"""UserPromptSubmit async hook: LLM-based intent detection for issue creation.

Fires async alongside pre_prompt_skill_redirect.py (which uses regex).
Catches Thai/English variants the regex misses.
Exit code: 0 always.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, inject_context, log_event, parse_stdin
from hooks_state import _load, _save
from plugin.ai.claude_call import claude_call
from plugin.ai.json_utils import CLASSIFY_SCHEMA, parse_json
from plugin.ai.prompts import CLASSIFY_PROMPT

_HOOK = "ai-intent-detect"

_SKILL_MAP = {
    "bug":     ("atlassian-pm:bug-triage",   "bug/defect triage → severity → duplicate check → ADF → QG ≥ 90%"),
    "story":   ("atlassian-pm:create-story", "discovery → INVEST → QG ≥ 90% → subtask design"),
    "epic":    ("atlassian-pm:create-epic",  "scope definition → ADF → QG ≥ 90%"),
    "subtask": ("atlassian-pm:create-story", "Part B of create-story handles subtask design"),
    "task":    ("atlassian-pm:create-task",  "scoping → ADF → QG ≥ 90%"),
}

def classify_intent(prompt: str) -> str | None:
    """Return issue type string or None if no creation intent detected."""
    result = claude_call(CLASSIFY_PROMPT.format(prompt=prompt[:500]), timeout=10)
    if not result:
        return None
    data = parse_json(result, CLASSIFY_SCHEMA)
    if data is None:
        return None
    classification = data["intent"]  # already lowercased + validated by schema
    return classification if classification in _SKILL_MAP else None


def main() -> None:
    try:
        data = parse_stdin()
        if not data:
            sys.exit(0)

        prompt = data.get("prompt", "")
        if not prompt:
            sys.exit(0)

        # Skip AI call if the regex hook already detected and redirected this prompt
        session_id = data.get("session_id", "")
        if session_id:
            state = _load(session_id)
            if state.get("prompt_skill_redirected"):
                state.pop("prompt_skill_redirected", None)
                _save(session_id, state)
                log_event(_HOOK, "SKIP", {"reason": "regex_hook_already_redirected"})
                allow()
                return

        issue_type = classify_intent(prompt)
        if not issue_type:
            log_event(_HOOK, "SKIP", {"reason": "no_intent_or_unavailable"})
            allow()
            return

        skill_name, hint = _SKILL_MAP[issue_type]
        log_event(_HOOK, "DETECTED", {"type": issue_type, "skill": skill_name})

        inject_context(
            f"<important-reminder>AI INTENT CONFIRMED — {issue_type.upper()} CREATION DETECTED\n"
            f"You MUST invoke `/{skill_name}` via the Skill tool BEFORE any Jira write.\n"
            f"Workflow: {hint}\n"
            f"DO NOT call jira_create_issue or acli directly.</important-reminder>",
            event_name="UserPromptSubmit",
        )
    except Exception:
        allow()


if __name__ == "__main__":
    main()
