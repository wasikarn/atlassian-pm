#!/usr/bin/env python3
"""HR10: Block sprint field updates on subtasks.

PreToolUse hook for mcp__mcp-atlassian__jira_update_issue.
Jira rejects sprint on subtasks (they inherit from parent).
Prevents wasted API calls and parallel-call cascade failures.

Detection layers:
  1. Cache DB: issue_type or parent_key columns
  2. Cache DB: raw JSON data (fields.issuetype, fields.parent)
  3. Session state: HR5 known subtasks (created this session)

Exit codes: 0 = allow, 2 = block
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import get_additional_fields, log_event, parse_stdin

CACHE_DB = Path.home() / ".cache" / "atlassian-pm" / "atlassian.db"
SPRINT_FIELD = "customfield_10020"

data = parse_stdin()
if not data:
    sys.exit(0)
tool_input = data.get("tool_input", {})

# Extract issue key
issue_key = tool_input.get("issue_key", "")
if not issue_key:
    sys.exit(0)

# Check if sprint field is being set
additional = get_additional_fields(tool_input)
has_sprint = SPRINT_FIELD in additional or "sprint" in additional
if not has_sprint:
    sys.exit(0)

# --- Detection layer 1+2: Cache DB ---
is_subtask = False
try:
    conn = sqlite3.connect(str(CACHE_DB))
    row = conn.execute(
        "SELECT issue_type, parent_key, data FROM issues WHERE issue_key = ?",
        (issue_key,),
    ).fetchone()
    conn.close()

    if row:
        issue_type, parent_key, raw_data = row
        # Layer 1: structured columns
        if (issue_type and "subtask" in issue_type.lower()) or parent_key:
            is_subtask = True
        # Layer 2: raw JSON data
        elif raw_data:
            try:
                jdata = json.loads(raw_data)
                fields = jdata.get("fields", {})
                itype = fields.get("issuetype", {})
                if (
                    (isinstance(itype, dict) and "subtask" in itype.get("name", "").lower())
                    or itype.get("subtask") is True
                    or fields.get("parent")
                ):
                    is_subtask = True
            except (json.JSONDecodeError, TypeError):
                pass
except Exception as e:
    log_event("hr10-sprint-guard", "ERROR", {"phase": "cache_db", "issue_key": issue_key, "error": str(e)})

# --- Detection layer 3: Session state (HR5 known subtasks) ---
if not is_subtask:
    try:
        session_id = data.get("session_id", "")
        from hooks_state import hr5_is_known_subtask

        if hr5_is_known_subtask(session_id, issue_key):
            is_subtask = True
    except Exception as e:
        log_event("hr10-sprint-guard", "ERROR", {"phase": "session_state", "issue_key": issue_key, "error": str(e)})

if is_subtask:
    print(
        f"HR10 BLOCKED: Cannot set sprint on subtask {issue_key}.\n"
        f"Subtasks inherit sprint from their parent story.\n"
        f"Remove the {SPRINT_FIELD}/sprint field from the update.",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)
