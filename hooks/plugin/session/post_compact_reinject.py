"""PostCompact hook: persist compact_summary to session state for debugging.

PostCompact fires after context compaction completes and receives compact_summary
(the summary Claude wrote of the compacted context). This hook saves it to the
session state file so it can be referenced in post-mortem debugging.

Note: PostCompact does NOT support additionalContext injection — it is logging
only. Context reinjection is handled by start_compact_reinject.py (SessionStart
with compact matcher) which fires when the session resumes post-compaction.

Exit 0 = always (no output control for PostCompact).
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import log_event, parse_stdin

_HOOK = "compact-reinject"

STATE_DIR = Path("/tmp/claude-hooks-state")


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        return

    session_id     = data.get("session_id", "default")
    trigger        = data.get("trigger", "unknown")   # "manual" | "auto"
    compact_summary = data.get("compact_summary", "")

    if not compact_summary:
        log_event(_HOOK, "SKIP", {"reason": "no_compact_summary", "session_id": session_id})
        return

    state_file   = STATE_DIR / f"{session_id}.json"
    compact_file = STATE_DIR / f"{session_id}.compact-summary.txt"

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Save compact summary for human inspection / future tooling
    compact_file.write_text(compact_summary)

    # Annotate main state file with compaction metadata
    try:
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
    except Exception:
        state = {}

    state["last_compact"] = {
        "ts":      time.time(),
        "trigger": trigger,
        "summary_len": len(compact_summary),
        "summary_path": str(compact_file),
    }
    state_file.write_text(json.dumps(state))

    log_event(_HOOK, "TRACKED", {"trigger": trigger, "summary_len": len(compact_summary), "session_id": session_id})
    print(
        f"PostCompact: saved compact_summary ({len(compact_summary)} chars, trigger={trigger}) "
        f"→ {compact_file}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
