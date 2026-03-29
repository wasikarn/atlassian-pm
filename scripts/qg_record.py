#!/usr/bin/env python3
"""Record QG score to persistent JSONL history.

Appends one record per call to ${CLAUDE_PLUGIN_DATA}/qg-history.jsonl.
Used by create-story and analyze-story skills after each Quality Gate run.

Usage:
    python scripts/qg_record.py \\
        --issue-key {{PROJECT_KEY}}-123 \\
        --type Story \\
        --score 87 \\
        --status PASS \\
        --service "[BE]" \\
        --checks-failed "ST3,T2"
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
QG_HISTORY = DATA_DIR / "qg-history.jsonl"


def main() -> None:
    p = argparse.ArgumentParser(description="Append a QG score record to qg-history.jsonl")
    p.add_argument("--issue-key", required=True, help="Jira issue key (e.g. {{PROJECT_KEY}}-123)")
    p.add_argument("--type", required=True, dest="issue_type", help="Story | Subtask | Epic")
    p.add_argument("--score", required=True, type=int, help="QG score 0-100")
    p.add_argument("--status", required=True, choices=["PASS", "FAIL"])
    p.add_argument("--service", default="", help="Service tag e.g. [BE], [FE-Admin], [FE-Web]")
    p.add_argument(
        "--checks-failed",
        default="",
        help="Comma-separated failed check IDs e.g. ST3,T2",
    )
    args = p.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    checks = [c.strip() for c in args.checks_failed.split(",") if c.strip()]
    record = {
        "ts": datetime.now(UTC).isoformat(),
        "issue_key": args.issue_key.upper(),
        "type": args.issue_type,
        "score": args.score,
        "status": args.status,
        "service": args.service,
        "checks_failed": checks,
    }

    with open(QG_HISTORY, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"QG recorded: {args.issue_key} {args.status} {args.score}%")


if __name__ == "__main__":
    main()
