#!/usr/bin/env python3
"""HR1: Quality Gate >= 90% before Atlassian writes.

PreToolUse hook for Bash tool. Intercepts acli commands that write
ADF JSON to Jira and validates the JSON file against quality gate.

Only matches:
  acli jira workitem create --from-json <path>
  acli jira workitem edit --from-json <path>

Exit codes: 0 = allow (or not an acli command), 2 = deny (QG < 90%)
"""

import json
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "atlassian-scripts"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import ACLI_FROM_JSON_RE, detect_issue_type, log_event

_HOOK = "hr1-qg-before-write"


def _log(level: str, data: dict) -> None:
    log_event(_HOOK, level, data)


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    # Only process Bash tool
    if data.get("tool_name") != "Bash":
        print("{}")
        return

    cmd = data.get("tool_input", {}).get("command", "")

    # Check if this is an acli write command with --from-json
    match = ACLI_FROM_JSON_RE.search(cmd)
    if not match:
        print("{}")
        return

    json_path = Path(match.group(1))
    # Resolve relative paths against cwd
    if not json_path.is_absolute():
        json_path = Path(data.get("cwd", ".")) / json_path

    if not json_path.exists():
        # File not found — let acli handle the error
        _log("SKIP", {"reason": "file_not_found", "file": str(json_path)})
        print("{}")
        return

    # Load the ADF JSON file
    try:
        with open(json_path) as f:
            adf_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        _log("ERROR", {"reason": str(e), "file": str(json_path)})
        print("{}")
        return

    # Import validator (lazy — only when we actually need it)
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from lib.adf_validator import AdfValidator, detect_format
    except ImportError as e:
        _log("ERROR", {"reason": f"import_failed: {e}"})
        print("{}")
        return

    # Detect format and extract ADF
    fmt, adf = detect_format(adf_data)
    if not adf or not isinstance(adf, dict):
        _log("SKIP", {"reason": "no_adf", "format": fmt, "file": str(json_path)})
        print("{}")
        return

    wrapper = adf_data if fmt in ("create", "edit") else None
    issue_type = detect_issue_type(adf_data, json_path)

    # Validate
    validator = AdfValidator()
    report = validator.validate(adf, issue_type, wrapper)

    log_data = {
        "file": json_path.name,
        "type": issue_type,
        "format": fmt,
        "score": round(report.score, 1),
        "passed": report.passed,
        "session_id": data.get("session_id", ""),
    }

    if report.passed:
        _log("ALLOWED", log_data)
        print("{}")
    else:
        # Build failure details
        issues = [f"  {c.check_id}: {c.message}" for c in report.checks if c.status.value == "fail"]
        issues_text = "\n".join(issues[:5])  # Top 5 failures
        reason = (
            f"HR1 BLOCKED: Quality Gate {report.score:.1f}% < 90% "
            f"(type: {issue_type}, file: {json_path.name})\n"
            f"Top issues:\n{issues_text}\n"
            f"Fix the ADF JSON and re-validate before writing to Jira."
        )
        _log("BLOCKED", log_data)
        print(reason, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
