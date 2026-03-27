#!/usr/bin/env python3
"""UserPromptSubmit: Detect issue creation intent and redirect to the correct skill.

Injects an important-reminder into Claude's context before it responds,
directing it to invoke the appropriate atlassian-pm skill instead of
calling Jira write tools directly.

Patterns detected (Thai + English):
  bug / บัก / defect / ข้อผิดพลาด  → /atlassian-pm:bug-triage
  story                              → /atlassian-pm:create-story
  task / ticket / งาน               → /atlassian-pm:create-task
  epic                               → /atlassian-pm:create-epic
  subtask                            → /atlassian-pm:create-story (Part B)

Exit codes: 0 (always — never blocks user prompts)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import inject_context, log_event, parse_stdin

_HOOK = "pre-prompt-skill-redirect"

# (compiled pattern, issue_type, skill_name, workflow_hint)
_RULES: list[tuple[re.Pattern, str, str, str]] = [
    # Bug / defect — checked first (most specific)
    (
        re.compile(
            r"(?i)(?:"
            r"(?:create|สร้าง|report|triage|add|new|file|open|found|พบ)\s+(?:a\s+|an?\s+)?(?:new\s+)?(?:bug|บัก|defect|ข้อผิดพลาด)"
            r"|(?:bug|บัก|defect|ข้อผิดพลาด)\s+(?:report|triage|found|พบ|สร้าง|ใหม่)"
            r"|(?:มีบัก|มี bug|bug นี้|bug เจอ)"
            r")"
        ),
        "bug",
        "atlassian-pm:bug-triage",
        "intake → severity → duplicate check → ADF → QG ≥ 90% → Jira create",
    ),
    # Story
    (
        re.compile(
            r"(?i)(?:"
            r"(?:create|สร้าง|add|new|write|เพิ่ม)\s+(?:a\s+)?(?:user\s+)?story"
            r"|(?:user\s+)?story\s+(?:for|about|เพื่อ|สำหรับ)"
            r"|สร้าง\s*(?:user\s+)?story"
            r")"
        ),
        "story",
        "atlassian-pm:create-story",
        "discovery → INVEST → QG ≥ 90% → subtask design → Jira create",
    ),
    # Epic
    (
        re.compile(
            r"(?i)(?:create|สร้าง|add|new|เพิ่ม)\s+(?:an?\s+)?epic"
        ),
        "epic",
        "atlassian-pm:create-epic",
        "scope definition → ADF → QG ≥ 90% → Jira create",
    ),
    # Subtask — checked before task (more specific)
    (
        re.compile(
            r"(?i)(?:create|สร้าง|add|เพิ่ม)\s+(?:a\s+)?subtask"
        ),
        "subtask",
        "atlassian-pm:create-story",
        "Part B of /create-story handles subtask design and creation",
    ),
    # Task / ticket — broadest, checked last
    (
        re.compile(
            r"(?i)(?:"
            r"(?:create|สร้าง|add|new|เพิ่ม)\s+(?:a\s+|an?\s+)?(?:new\s+)?(?:task|งาน|ticket|jira\s+ticket)"
            r"|สร้าง\s*(?:jira\s*)?(?:task|ticket|งาน)"
            r")"
        ),
        "task",
        "atlassian-pm:create-task",
        "scoping → ADF → QG ≥ 90% → Jira create",
    ),
]


def detect_intent(prompt: str) -> tuple[str, str, str] | None:
    """Return (issue_type, skill_name, hint) if issue creation intent detected, else None."""
    for pattern, issue_type, skill_name, hint in _RULES:
        if pattern.search(prompt):
            return issue_type, skill_name, hint
    return None


def main() -> None:
    data = parse_stdin()
    if not data:
        sys.exit(0)

    prompt = data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    result = detect_intent(prompt)
    if not result:
        sys.exit(0)

    issue_type, skill_name, hint = result
    log_event(_HOOK, "REDIRECT", {"issue_type": issue_type, "skill": skill_name})

    inject_context(
        f"<important-reminder>SKILL REQUIRED — {issue_type.upper()} CREATION DETECTED\n"
        f"You MUST invoke `/{skill_name}` skill via the Skill tool BEFORE using any Jira write tool.\n"
        f"Skill workflow: {hint}\n"
        f"DO NOT call jira_create_issue, jira_batch_create_issues, or acli create directly.\n"
        f"The skill handles QG ≥ 90%, proper ADF template, duplicate check, and all Jira writes.</important-reminder>",
        event_name="UserPromptSubmit",
    )


if __name__ == "__main__":
    main()
