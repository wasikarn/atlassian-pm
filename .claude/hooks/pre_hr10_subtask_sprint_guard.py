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

CACHE_DB = Path.home() / ".cache" / "jira-generator" / "jira.db"
SPRINT_FIELD = "customfield_10020"

raw = sys.stdin.read()
data = json.loads(raw)
tool_input = data.get("tool_input", {})

# Extract issue key
issue_key = tool_input.get("issue_key", "")
if not issue_key:
    sys.exit(0)

# Check if sprint field is being set
additional = tool_input.get("additional_fields", {})
if isinstance(additional, str):
    try:
        additional = json.loads(additional)
    except (json.JSONDecodeError, TypeError):
        additional = {}

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
except Exception:
    pass

# --- Detection layer 3: Session state (HR5 known subtasks) ---
if not is_subtask:
    try:
        session_id = data.get("session_id", "")
        sys.path.insert(0, str(Path(__file__).parent))
        from hooks_state import hr5_is_known_subtask

        if hr5_is_known_subtask(session_id, issue_key):
            is_subtask = True
    except Exception:
        pass

if is_subtask:
    print(
        f"HR10 BLOCKED: Cannot set sprint on subtask {issue_key}.\n"
        f"Subtasks inherit sprint from their parent story.\n"
        f"Remove the {SPRINT_FIELD}/sprint field from the update.",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)
