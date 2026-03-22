#!/usr/bin/env python3
"""P8: Skill Usage Measurement — log every Skill tool invocation.

PreToolUse hook for the Skill tool.
Appends a JSONL record to ${CLAUDE_PLUGIN_DATA}/skill-usage.jsonl for
monthly analysis: find undertriggering skills, most-used skills, candidates
for removal or command wrapping.

Exit codes: 0 (always — never blocks skill invocation)
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, log_event, parse_stdin

_HOOK = "p8-skill-usage-log"


def build_record(tool_input: dict, session_id: str, project: str) -> dict:
    """Build a JSONL log record for a Skill invocation."""
    skill_name = str(tool_input.get("skill", ""))
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "skill_name": skill_name,
        "session_id": session_id,
        "project": project,
    }


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "")
    project = os.environ.get("CLAUDE_PROJECT_NAME", "unknown")

    record = build_record(tool_input, session_id, project)

    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", str(Path.home() / ".claude"))
    log_path = Path(plugin_data) / "skill-usage.jsonl"
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # non-fatal — logging must never block skill invocation

    log_event(_HOOK, "TRACKED", {"skill": record["skill_name"], "session_id": session_id})
    allow()


if __name__ == "__main__":
    main()
