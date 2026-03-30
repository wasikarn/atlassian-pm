#!/usr/bin/env python3
"""R: Check event-based AC names against Domain Model catalog.

PreToolUse hook for Bash (acli --from-json).
When writing Story ADF, checks if event-based AC names (PascalCase pattern)
reference events from the tracked Domain Model catalog.

Warns (does not block) if event names are unrecognized.

Exit codes: 0 = always allow (warning only)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import ACLI_FROM_JSON_RE as ACLI_RE, inject_context, log_event, parse_stdin
from hooks_state import event_get_all_events

_HOOK = "event-ac-check"

# Event-based AC: PascalCase multi-word = domain event (e.g. CouponCollected)
# vs verb-based: single word (Display, Validate, Handle)
EVENT_AC_RE = re.compile(r"AC\d+:\s*([A-Z][a-z]+(?:[A-Z][a-z]+)+)")


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        sys.exit(0)

    session_id = data.get("session_id", "")

    if data.get("tool_name") != "Bash":
        log_event(_HOOK, "SKIP", {"reason": "wrong_tool", "session_id": session_id})
        sys.exit(0)

    cmd = data.get("tool_input", {}).get("command", "")
    match = ACLI_RE.search(cmd)
    if not match:
        log_event(_HOOK, "SKIP", {"reason": "no_acli_match", "session_id": session_id})
        sys.exit(0)

    known_events = event_get_all_events(session_id)
    if not known_events:
        log_event(_HOOK, "SKIP", {"reason": "no_known_events", "session_id": session_id})
        sys.exit(0)

    json_path = Path(match.group(1))
    if not json_path.is_absolute():
        json_path = Path(data.get("cwd", ".")) / json_path

    if not json_path.exists():
        log_event(_HOOK, "SKIP", {"reason": "file_not_found", "session_id": session_id})
        sys.exit(0)

    try:
        content = json_path.read_text()
    except OSError:
        log_event(_HOOK, "SKIP", {"reason": "file_read_error", "session_id": session_id})
        sys.exit(0)

    ac_events = EVENT_AC_RE.findall(content)
    if not ac_events:
        log_event(_HOOK, "SKIP", {"reason": "no_ac_events", "session_id": session_id})
        sys.exit(0)

    unknown = [e for e in ac_events if e not in known_events]
    if unknown:
        log_event(_HOOK, "WARN", {"unknown_events": unknown, "session_id": session_id})
        inject_context(
            f"⚠️ Event-AC consistency: {', '.join(unknown)} not in Domain Model catalog.\n"
            f"Known events: {', '.join(sorted(known_events))}\n"
            f"If new events, update parent Epic's Domain Model section.",
            event_name="PreToolUse",
        )
    else:
        log_event(_HOOK, "ALLOWED", {"ac_events": ac_events, "session_id": session_id})

    sys.exit(0)


if __name__ == "__main__":
    main()
