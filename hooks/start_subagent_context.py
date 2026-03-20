"""SubagentStart hook: inject current session state into subagents.

When the main agent spawns a subagent (story-writer, alignment-checker,
quality-gate, sprint-planner, etc.), this hook injects the current
session state so subagents don't need to re-read CLAUDE.md or re-fetch
sprint IDs, and are aware of in-flight HR5/HR6 pending operations.

Injected context:
  - Current sprint ID (if hr7 lookup was done)
  - HR6 pending invalidations
  - HR5 pending parent verifications
  - Domain events catalog
  - Core HR rule reminders (HR5, HR6, HR7, HR10)

Exit 0 = always allow.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import load_project_config
from hooks_lib import inject_context, log_event
from hooks_state import _load  # read-only access to session state

_cfg = load_project_config()
_BOARD_ID = _cfg.get("jira", {}).get("board_id", "<board_id>")

_HOOK = "subagent-context-inject"

_HR_RULES = """\
HARD RULES (violating = data corruption / silent failure):
- HR5: After MCP subtask create → verify parent with jira_get_issue(fields='parent')
- HR6: After ANY Jira write → cache_invalidate(issue_key, auto_refresh=true) immediately
- HR7: Sprint ID NEVER hardcoded — always jira_get_sprints_from_board(board_id={_BOARD_ID}, state='active')
- HR10: NEVER set sprint field (customfield_10020) on subtasks — inherited from parent
- Tool: jira_get_issue / jira_search ALWAYS require fields + limit params\
"""


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    session_id = data.get("session_id", "")
    agent_type = data.get("agent_type", "unknown")

    state = _load(session_id)
    lines: list[str] = [f"=== SESSION CONTEXT (injected for subagent: {agent_type}) ==="]
    lines.append(_HR_RULES)
    lines.append("")

    # HR7 — sprint lookup status
    if state.get("hr7_lookup_done"):
        lines.append("HR7: Sprint lookup done this session — sprint IDs may be used.")
    else:
        lines.append("HR7: Sprint lookup NOT done — must call jira_get_sprints_from_board() before setting sprint.")

    # HR6 — pending cache invalidations
    hr6 = state.get("hr6_pending", [])
    if hr6:
        lines.append(f"HR6 PENDING (must invalidate before reading): {', '.join(hr6)}")

    # HR5 — pending parent verifications
    hr5 = state.get("hr5_pending", [])
    if hr5:
        items = ", ".join(f"{p['child']}→{p['parent']}" for p in hr5)
        lines.append(f"HR5 PENDING (parent verify required): {items}")

    # Search status
    if state.get("search_done"):
        lines.append("Search: dedup search already done this session.")

    # Domain events catalog
    events = state.get("domain_events", {})
    if events:
        for epic, evts in events.items():
            if evts:
                lines.append(f"Domain events ({epic}): {', '.join(evts[:10])}")

    # Story ACs (VS integrity tracking)
    vs_acs = state.get("vs_story_acs", {})
    if vs_acs:
        for story, acs in list(vs_acs.items())[:3]:
            lines.append(f"Story ACs ({story}): {len(acs)} ACs tracked")

    context = "\n".join(lines)
    log_event(_HOOK, "INJECTED", {
        "agent_type": agent_type,
        "hr6_pending": hr6,
        "hr5_pending": len(hr5),
        "session_id": session_id,
    })
    inject_context(context, event_name="SubagentStart")


if __name__ == "__main__":
    main()
