#!/usr/bin/env python3
"""Record sprint health metrics to persistent JSONL history.

Appends one record per sprint close to ${CLAUDE_PLUGIN_DATA}/sprint-health.jsonl.
Used by close-sprint skill in Phase 8 (Summary) after velocity-tracker runs.

Usage:
    python scripts/sprint_health_record.py \\
        --sprint-id 45 \\
        --sprint-name "Sprint 12" \\
        --planned-sp 42 \\
        --completed-sp 38 \\
        --carry-over-count 3 \\
        --carry-over-sp 8 \\
        --total-issues 25 \\
        --done-issues 21
"""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
)
SPRINT_HEALTH = DATA_DIR / "sprint-health.jsonl"


def main() -> None:
    p = argparse.ArgumentParser(description="Append sprint health record to sprint-health.jsonl")
    p.add_argument("--sprint-id", required=True, help="Jira sprint ID")
    p.add_argument("--sprint-name", required=True, help="Sprint display name")
    p.add_argument("--planned-sp", type=int, default=0, help="Total planned story points")
    p.add_argument("--completed-sp", type=int, default=0, help="Completed story points")
    p.add_argument("--carry-over-count", type=int, default=0, help="Number of incomplete issues")
    p.add_argument("--carry-over-sp", type=int, default=0, help="SP of incomplete issues")
    p.add_argument("--total-issues", type=int, default=0, help="Total issues in sprint")
    p.add_argument("--done-issues", type=int, default=0, help="Issues with Done status")
    args = p.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    completion_ratio = (
        round(args.completed_sp / args.planned_sp, 3) if args.planned_sp > 0 else 0
    )
    carry_over_rate = (
        round(args.carry_over_count / args.total_issues, 3) if args.total_issues > 0 else 0
    )

    record = {
        "ts": datetime.now(UTC).isoformat(),
        "sprint_id": args.sprint_id,
        "sprint_name": args.sprint_name,
        "planned_sp": args.planned_sp,
        "completed_sp": args.completed_sp,
        "carry_over_count": args.carry_over_count,
        "carry_over_sp": args.carry_over_sp,
        "total_issues": args.total_issues,
        "done_issues": args.done_issues,
        "completion_ratio": completion_ratio,
        "carry_over_rate": carry_over_rate,
    }

    with open(SPRINT_HEALTH, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(
        f"Sprint health recorded: {args.sprint_name} — "
        f"{completion_ratio * 100:.0f}% completion, "
        f"{carry_over_rate * 100:.0f}% carry-over"
    )


if __name__ == "__main__":
    main()
