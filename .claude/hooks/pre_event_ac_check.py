#!/usr/bin/env python3
"""R: Check event-based AC names against Domain Model catalog.

PreToolUse hook for Bash (acli --from-json).
When writing Story ADF, checks if event-based AC names (PascalCase pattern)
reference events from the tracked Domain Model catalog.

Warns (does not block) if event names are unrecognized.

Exit codes: 0 = always allow (warning only)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import ACLI_FROM_JSON_RE as ACLI_RE
from hooks_state import event_get_all_events

# Event-based AC: PascalCase multi-word = domain event (e.g. CouponCollected)
# vs verb-based: single word (Display, Validate, Handle)
EVENT_AC_RE = re.compile(r"AC\d+:\s*([A-Z][a-z]+(?:[A-Z][a-z]+)+)")

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(0)

if data.get("tool_name") != "Bash":
    sys.exit(0)

cmd = data.get("tool_input", {}).get("command", "")
match = ACLI_RE.search(cmd)
if not match:
    sys.exit(0)

session_id = data.get("session_id", "")
known_events = event_get_all_events(session_id)
if not known_events:
    sys.exit(0)

json_path = Path(match.group(1))
if not json_path.is_absolute():
    json_path = Path(data.get("cwd", ".")) / json_path

if not json_path.exists():
    sys.exit(0)

try:
    content = json_path.read_text()
except OSError:
    sys.exit(0)

ac_events = EVENT_AC_RE.findall(content)
if not ac_events:
    sys.exit(0)

unknown = [e for e in ac_events if e not in known_events]
if unknown:
    print(
        f"⚠️ Event-AC consistency: {', '.join(unknown)} not in Domain Model catalog.\n"
        f"Known events: {', '.join(sorted(known_events))}\n"
        f"If new events, update parent Epic's Domain Model section."
    )

sys.exit(0)
