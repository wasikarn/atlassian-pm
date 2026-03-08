#!/usr/bin/env python3
"""R: Track Domain Model events from Epic descriptions.

PostToolUse hook for mcp__mcp-atlassian__jira_get_issue.
When an Epic is read, extracts Domain Events from the Domain Model
section and saves to session state for event-AC consistency checking.

Exit 0 = always allow
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hooks_state import event_set_domain_events

raw = sys.stdin.read()
data = json.loads(raw)
tool_output = str(data.get("tool_output", ""))
session_id = data.get("session_id", "")

# Quick check: is this an Epic?
if "Epic" not in tool_output:
    sys.exit(0)

# Extract issue key
key_match = re.search(r'"key"\s*:\s*"([A-Z]+-\d+)"', tool_output)
if not key_match:
    sys.exit(0)
issue_key = key_match.group(1)

# Look for Domain Events in the output text
# Handles ADF text nodes: "Domain Events: " followed by event list
events_match = re.search(
    r"Domain Events?:?\s*[\"']?\s*([A-Z][A-Za-z,\s]+?)(?:\s*[—\-]|[\"']|\n|$)",
    tool_output,
)
if not events_match:
    sys.exit(0)

events_text = events_match.group(1).strip()
events_text = re.sub(r"[\[\]]", "", events_text)
events = [e.strip() for e in events_text.split(",") if e.strip()]

# Filter out placeholder/template text
events = [e for e in events if not e.startswith("[") and e not in ("Event1", "Event2") and len(e) > 2]

if events:
    event_set_domain_events(session_id, issue_key, events)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"📋 Domain Model tracked ({issue_key}): {', '.join(events)}. "
                f"Event-based AC names will be checked against this catalog."
            ),
        }
    }
    print(json.dumps(output))

sys.exit(0)
