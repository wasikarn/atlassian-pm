#!/usr/bin/env python3
"""Re-inject critical context after compaction.

SessionStart hook (matcher: compact) — outputs HR reminders + pending state
so Claude doesn't lose track of rules and in-progress operations.

stdout → injected into Claude's post-compaction context.
"""

import json
import sys
from pathlib import Path

try:
    data = json.loads(sys.stdin.read())
except Exception:
    data = {}

session_id = data.get("session_id", "default")
state_file = Path(f"/tmp/claude-hooks-state/{session_id}.json")

# ── HR Reminders (always output) ──────────────────────
reminders = """
=== POST-COMPACTION CRITICAL REMINDERS ===

HARD RULES (violating = data corruption):
- HR5: Subtask = Two-Step + Verify parent (MCP create → jira_get_issue verify → acli edit)
- HR6: cache_invalidate(issue_key) after EVERY Jira write
- HR7: Sprint ID = ALWAYS lookup via jira_get_sprints_from_board(), NEVER hardcode
- HR10: NEVER set sprint (customfield_10020) on subtasks — inherits from parent

TOOL RULES:
- jira_get_issue / jira_search: ALWAYS use fields + limit params
- Subtask creation: ALWAYS sequential (never parallel)
- Cache: cache_get_issue first → fallback jira_get_issue if miss
- Assignee: ONLY via acli (MCP silently fails)
- Confluence macros: ONLY via update_page_storage.py (MCP corrupts XML)
- JQL with parent: NEVER add ORDER BY (parser error)
""".strip()

print(reminders)

# ── Pending operations from hooks_state ───────────────
if not state_file.exists():
    sys.exit(0)

try:
    state = json.loads(state_file.read_text())
except Exception:
    sys.exit(0)

pending = []

# HR5: pending parent verifications
hr5 = state.get("hr5_pending", [])
if hr5:
    items = ", ".join(f"{p['child']}->parent:{p['parent']}" for p in hr5)
    pending.append(f"HR5 PENDING PARENT VERIFY: {items}")

# HR6: pending cache invalidations
hr6 = state.get("hr6_pending", [])
if hr6:
    pending.append(f"HR6 PENDING CACHE INVALIDATE: {', '.join(hr6)}")

# HR7: sprint lookup status
if state.get("hr7_lookup_done"):
    pending.append("HR7: Sprint lookup done this session (OK to use sprint IDs)")
else:
    pending.append("HR7: Sprint lookup NOT done yet — must lookup before setting sprint")

# Search status
if state.get("search_done"):
    pending.append("Search: Already searched this session")

# Domain events catalog
events = state.get("domain_events", {})
if events:
    for epic, evts in events.items():
        pending.append(f"Domain events ({epic}): {', '.join(evts[:10])}")

# VS integrity tracking
vs_acs = state.get("vs_story_acs", {})
if vs_acs:
    for story, acs in vs_acs.items():
        pending.append(f"Story ACs ({story}): {', '.join(acs[:8])}")

if pending:
    print("\n\n=== SESSION STATE (from hooks) ===")
    for item in pending:
        print(f"- {item}")
