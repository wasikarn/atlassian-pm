#!/usr/bin/env python3
"""Block Story creation/update when SP > story_size_threshold.

PreToolUse hook for jira_create_issue, jira_update_issue.
Reads threshold from project-config.json (jira.story_size_threshold, default: 13).

Exit codes: 0 = allow, 2 = deny
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config_loader import load_project_config
from hooks_lib import block, log_event, parse_stdin

_HOOK = "story-size-guard"
DEFAULT_THRESHOLD = 13
STORY_TYPES = {"story", "user story"}


def main() -> None:
    data = parse_stdin()
    if not data:
        sys.exit(0)

    inp = data.get("tool_input", {})

    # Detect issue type — jira_create_issue uses "issue_type"
    # jira_update_issue rarely includes issuetype; only block if explicitly present
    issue_type = (
        inp.get("issue_type", "")
        or inp.get("additional_fields", {}).get("issuetype", {}).get("name", "")
    ).lower()

    if issue_type not in STORY_TYPES:
        sys.exit(0)

    # Extract SP from additional_fields (create) or fields (update)
    sp_raw = (
        inp.get("additional_fields", {}).get("customfield_10016")
        or inp.get("fields", {}).get("customfield_10016")
    )
    if sp_raw is None:
        sys.exit(0)  # No SP in payload — pass, let QG handle

    try:
        sp = float(sp_raw)
    except (TypeError, ValueError):
        sys.exit(0)

    # Read threshold from project-config.json (fallback: DEFAULT_THRESHOLD)
    threshold = DEFAULT_THRESHOLD
    try:
        cfg = load_project_config()
        threshold = cfg.get("jira", {}).get("story_size_threshold", DEFAULT_THRESHOLD)
    except Exception:
        pass

    if sp <= threshold:
        sys.exit(0)

    log_event(_HOOK, "warn", {"sp": sp, "threshold": threshold, "issue_type": issue_type})
    block(
        f"Story SP ({int(sp)}) exceeds size threshold ({threshold}). "
        f"Split using SPIDR: by Scenario, Path, Interface, Data, or Rule. "
        f"Each slice should be independently deliverable."
    )  # block() calls sys.exit(2) — never returns


if __name__ == "__main__":
    main()
