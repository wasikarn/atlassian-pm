#!/usr/bin/env python3
"""Record per-story outcomes to persistent JSONL history at sprint close.

Appends one record per story to ${CLAUDE_PLUGIN_DATA}/story-outcomes.jsonl.
Used by close-sprint skill in Phase 8 after sprint_health_record.py runs.

Usage:
    python scripts/story_outcome_record.py \\
        --sprint-id 45 \\
        --sprint-name "Sprint 12" \\
        --issues-json '[{"key":"{{PROJECT_KEY}}-1","summary":"...","sp":3,"assignee":"user@x.com","issuetype":"Story","labels":["be"],"status":"Done"}]'

Schema per record:
    ts            ISO timestamp at close time
    sprint_id     Jira sprint ID
    sprint_name   Sprint display name
    issue_key     Jira issue key ({{PROJECT_KEY}}-123)
    summary       Issue title (first 80 chars)
    issuetype     "Story" | "Task" | "Sub-task" | "Bug"
    estimated_sp  Story points at planning time (null if unestimated)
    assignee      Assignee display name or email (null if unassigned)
    service_tag   Extracted from labels: "BE" | "FE-Admin" | "FE-Web" | "Video" | "AI" | null
    outcome       "completed" | "carry_over"
    final_status  Jira status name at close time ("Done", "In Progress", etc.)
"""

import argparse
import json
import os
import re
import subprocess  # used in main() spawn block
import sys  # used in main() spawn block
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
)
STORY_OUTCOMES = DATA_DIR / "story-outcomes.jsonl"
MAX_RECORDS = 2000  # rolling window — prune oldest when exceeded

# Label patterns → service tag mapping (matches existing Jira label convention)
_SERVICE_PATTERNS = [
    (re.compile(r"\bfe[-_]?admin\b", re.I), "FE-Admin"),
    (re.compile(r"\bfe[-_]?web\b", re.I), "FE-Web"),
    (re.compile(r"\bvideo\b", re.I), "Video"),
    (re.compile(r"\bai[-_]?agent\b", re.I), "AI"),
    (re.compile(r"\bplayer\b", re.I), "Player"),
    (re.compile(r"\bbe\b", re.I), "BE"),
]

DONE_STATUSES = {"done", "closed", "resolved", "released"}


def extract_service_tag(labels: list[str]) -> str | None:
    for label in labels:
        for pattern, tag in _SERVICE_PATTERNS:
            if pattern.search(label):
                return tag
    return None


def is_completed(status: str) -> bool:
    return status.strip().lower() in DONE_STATUSES


def prune_if_needed(path: Path, max_records: int) -> None:
    """Keep only the most recent max_records lines (O(n) read, rewrite)."""
    if not path.exists():
        return
    lines = path.read_text().splitlines()
    if len(lines) > max_records:
        path.write_text("\n".join(lines[-max_records:]) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="Append per-story outcome records to story-outcomes.jsonl")
    p.add_argument("--sprint-id", required=True, help="Jira sprint ID")
    p.add_argument("--sprint-name", required=True, help="Sprint display name")
    p.add_argument(
        "--issues-json",
        required=True,
        help=(
            'JSON array of issue objects. Each object must have: '
            '"key" (str), "summary" (str), "status" (str). '
            'Optional: "sp" (int|null), "assignee" (str|null), '
            '"issuetype" (str), "labels" (list[str]).'
        ),
    )
    args = p.parse_args()

    try:
        issues = json.loads(args.issues_json)
    except json.JSONDecodeError as e:
        print(f"[story_outcome_record] ERROR: --issues-json is not valid JSON: {e}")
        raise SystemExit(1) from e

    if not isinstance(issues, list):
        print("[story_outcome_record] ERROR: --issues-json must be a JSON array")
        raise SystemExit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).isoformat()
    written = 0

    with open(STORY_OUTCOMES, "a") as f:
        for issue in issues:
            key = issue.get("key") or issue.get("issue_key")
            if not key:
                continue  # skip malformed entries silently
            status = str(issue.get("status") or "")
            labels = issue.get("labels") or []
            record = {
                "ts": ts,
                "sprint_id": args.sprint_id,
                "sprint_name": args.sprint_name,
                "issue_key": key,
                "summary": str(issue.get("summary") or "")[:80],
                "issuetype": str(issue.get("issuetype") or "Story"),
                "estimated_sp": issue.get("sp") or issue.get("estimated_sp"),
                "assignee": issue.get("assignee"),
                "service_tag": extract_service_tag(labels),
                "outcome": "completed" if is_completed(status) else "carry_over",
                "final_status": status,
            }
            f.write(json.dumps(record) + "\n")
            written += 1

    prune_if_needed(STORY_OUTCOMES, MAX_RECORDS)

    completed = sum(1 for i in issues if is_completed(str(i.get("status") or "")))
    carry_over = written - completed
    print(
        f"Story outcomes recorded: {written} issues — "
        f"{completed} completed, {carry_over} carry-over → story-outcomes.jsonl"
    )

    # Trigger calibration in background (non-blocking, fire-and-forget)
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if plugin_root:
        calibrate_path = Path(plugin_root) / "scripts" / "ai" / "calibrate.py"
        if calibrate_path.exists():
            log_path = DATA_DIR / "calibrate.log"
            try:
                with open(log_path, "a") as log_fd:
                    subprocess.Popen(
                        [sys.executable, str(calibrate_path)],
                        start_new_session=True,
                        stdout=subprocess.DEVNULL,
                        stderr=log_fd,
                    )
                # log_fd closed by context manager; child inherits the fd via dup2 before close
            except OSError:
                pass  # Spawn is fire-and-forget — never crash main()


if __name__ == "__main__":
    main()
