#!/usr/bin/env python3
"""Pre-flight ADF quality gate check.

Usage: python3 scripts/validate_adf.py tasks/abc-XXXX-task-update.json

Runs the same AdfValidator + detect_issue_type that the HR1 hook uses,
but shows per-check breakdown so you can fix issues BEFORE attempting
acli write (avoiding hook block → debug → retry round-trips).

Tip: Include issue type in filename (e.g. -task-, -story-, -subtask-)
     to ensure correct type detection. Default is 'subtask'.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "atlassian-scripts"))
sys.path.insert(0, str(ROOT / "hooks"))

from lib.adf_validator import AdfValidator, detect_format  # noqa: E402
from hooks_lib import detect_issue_type  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <adf-json-file>")
        sys.exit(1)

    fp = Path(sys.argv[1])
    if not fp.exists():
        print(f"File not found: {fp}")
        sys.exit(1)

    with open(fp) as f:
        data = json.load(f)

    fmt, adf = detect_format(data)
    issue_type = detect_issue_type(data, fp)
    wrapper = data if fmt in ("create", "edit") else None

    validator = AdfValidator()
    report = validator.validate(adf, issue_type, wrapper)

    # Output
    status = "PASS" if report.passed else "FAIL"
    print(f"[{status}] {fp.name} — Type: {issue_type}, Score: {report.score:.1f}%")
    print()
    for c in report.checks:
        icon = {"pass": "✓", "warn": "⚠", "fail": "✗"}.get(c.status.value, "?")
        print(f"  {icon} {c.check_id}: {c.message}")

    if not report.passed:
        print(f"\nScore {report.score:.1f}% < 90% — fix issues above before writing to Jira.")
        sys.exit(2)


if __name__ == "__main__":
    main()
