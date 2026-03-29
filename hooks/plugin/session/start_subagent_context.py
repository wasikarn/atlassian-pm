"""SubagentStart hook: inject current session state into subagents.

When the main agent spawns a subagent (story-writer, alignment-checker,
quality-gate, sprint-planner, etc.), this hook injects the current
session state so subagents don't need to re-read CLAUDE.md or re-fetch
sprint IDs, and are aware of in-flight HR5/HR6 pending operations.

Injected context:
  - Core HR rule reminders (HR5, HR6, HR7, HR10) — write-capable agents only
  - Current sprint ID (if hr7 lookup was done) — write-capable agents only
  - HR6 pending cache invalidations — write-capable agents only
  - HR5 pending parent verifications — write-capable agents only
  - Domain events catalog — all agents
  - Search status — all agents

Read-only agents (no Jira write tools) skip HR rules to save ~500 tokens.

Exit 0 = always allow.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config_loader import load_project_config
from hooks_lib import build_hr_rules, inject_context, log_event, parse_stdin
from hooks_state import _load  # read-only access to session state

_cfg = load_project_config()
_BOARD_ID = _cfg.get("jira", {}).get("board_id", "<board_id>")

_HOOK = "subagent-context-inject"

# Agents that call Jira write tools and need full HR rule context.
# All others (read-only) skip HR rules to reduce token overhead.
_WRITE_CAPABLE_AGENTS = {
    "sprint-planner",           # jira_update_issue (sprint assignments)
    "alignment-checker",        # jira_update_issue, jira_add_comment, cache_invalidate
    "pr-review-jira-sync",      # jira_transition_issue, jira_add_comment
    "sprint-transition-agent",  # jira_update_issue
}

_HR_RULES = build_hr_rules(board_id=_BOARD_ID)


def main() -> None:
    data = parse_stdin()
    if not data:
        sys.exit(0)

    session_id = data.get("session_id", "")
    agent_type = data.get("agent_type", "unknown")
    is_write_capable = agent_type in _WRITE_CAPABLE_AGENTS

    state = _load(session_id)
    lines: list[str] = [f"=== SESSION CONTEXT (injected for subagent: {agent_type}) ==="]

    if is_write_capable:
        lines.append(_HR_RULES)
        lines.append("")

        # HR7 — sprint lookup status
        if state.get("hr7_lookup_done"):
            lines.append("HR7: Sprint lookup done this session — sprint IDs may be used.")
        else:
            lines.append(
                "HR7: Sprint lookup NOT done — must call "
                "jira_get_sprints_from_board() before setting sprint."
            )

        # HR6 — pending cache invalidations
        hr6 = state.get("hr6_pending", [])
        if hr6:
            lines.append(f"HR6 PENDING (must invalidate before reading): {', '.join(hr6)}")

        # HR5 — pending parent verifications
        hr5 = state.get("hr5_pending", [])
        if hr5:
            items = ", ".join(f"{p['child']}→{p['parent']}" for p in hr5)
            lines.append(f"HR5 PENDING (parent verify required): {items}")
    else:
        hr6 = state.get("hr6_pending", [])
        hr5 = state.get("hr5_pending", [])

    # Search status — useful for all agents
    if state.get("search_done"):
        lines.append("Search: dedup search already done this session.")

    # Domain events catalog — useful for all agents
    events = state.get("domain_events", {})
    if events:
        for epic, evts in events.items():
            if evts:
                lines.append(f"Domain events ({epic}): {', '.join(evts[:10])}")

    # Story ACs (VS integrity tracking) — useful for all agents
    vs_acs = state.get("vs_story_acs", {})
    if vs_acs:
        for story, acs in list(vs_acs.items())[:3]:
            lines.append(f"Story ACs ({story}): {len(acs)} ACs tracked")

    context = "\n".join(lines)
    log_event(_HOOK, "INJECTED", {
        "agent_type": agent_type,
        "is_write_capable": is_write_capable,
        "hr6_pending": hr6,
        "hr5_pending": len(hr5),
        "session_id": session_id,
    })
    inject_context(context, event_name="SubagentStart")


if __name__ == "__main__":
    main()
