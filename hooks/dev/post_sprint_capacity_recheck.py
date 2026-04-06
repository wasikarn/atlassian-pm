#!/usr/bin/env python3
"""PostToolUse: warn when sprint field is updated — remind to check capacity.

Triggers after: jira_update_issue (when customfield_10020/sprint changes).
Injects additionalContext suggestion to verify sprint capacity.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config_loader import load_project_config
from hooks_lib import inject_context, parse_stdin

data = parse_stdin()
if not data:
    sys.exit(0)

tool_input = data.get("tool_input", {})

# Detect sprint field update in additional_fields
additional_fields = tool_input.get("additional_fields", {})
if "customfield_10020" not in additional_fields:
    sys.exit(0)

sprint_value = additional_fields.get("customfield_10020")
sprint_id = None
if isinstance(sprint_value, dict):
    sprint_id = sprint_value.get("id") or sprint_value.get("name")
elif isinstance(sprint_value, (int, str)):
    sprint_id = sprint_value

# Read team throughput from project-config.json
avg_throughput = 39  # default
try:
    cfg = load_project_config()
    avg_throughput = cfg.get("team", {}).get("avg_throughput_per_sprint", avg_throughput)
except Exception:
    pass

sprint_ref = f"sprint {sprint_id}" if sprint_id else "sprint"
inject_context(
    f"Sprint assignment updated ({sprint_ref}). "
    f"Verify sprint capacity has not exceeded team throughput ({avg_throughput} SP). "
    f"Run `/atlassian-pm:apm-plan-sprint --check-capacity` or manually sum SP of all issues in this sprint."
)

sys.exit(0)
