#!/usr/bin/env python3
"""HR1: Quality Gate >= threshold before Atlassian writes.

PreToolUse hook for Bash tool. Intercepts acli commands that write
ADF JSON to Jira and validates the JSON file against quality gate.

Only matches:
  acli jira workitem create --from-json <path>
  acli jira workitem edit --from-json <path>

Threshold: reads vibe.qg_threshold from .claude/project-config.json
when --vibe flag is present in the triggering command. Defaults to 90%.

Exit codes:
    0 = success/pass (QG >= threshold or not an acli command)
    1 = fail/validation error (QG < threshold)
    2 = runtime error/exception (script failure)
"""

import json
import os
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────
# Use CLAUDE_PLUGIN_ROOT env var if available, fallback to relative path resolution
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
PROJECT_CONFIG_PATH = PLUGIN_ROOT / ".claude" / "project-config.json"

sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from hooks_lib import ACLI_FROM_JSON_RE, allow, block, detect_issue_type, log_event, parse_stdin

_HOOK = "hr1-qg-before-write"
_DEFAULT_THRESHOLD = 90.0


def _log(level: str, data: dict) -> None:
    log_event(_HOOK, level, data)


def _load_vibe_threshold() -> float:
    """Read vibe.qg_threshold from project-config.json. Returns default if not found."""
    try:
        with open(PROJECT_CONFIG_PATH) as f:
            config = json.load(f)
        threshold = config.get("vibe", {}).get("qg_threshold")
        if isinstance(threshold, (int, float)) and 0 <= threshold <= 100:
            return float(threshold)
    except (OSError, json.JSONDecodeError):
        pass
    return _DEFAULT_THRESHOLD


def _is_vibe_mode(cmd: str) -> bool:
    """Detect vibe mode: --vibe flag anywhere in the command."""
    return "--vibe" in cmd.split()


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    # Only process Bash tool
    if data.get("tool_name") != "Bash":
        allow()
        return

    cmd = data.get("tool_input", {}).get("command", "")

    # Check if this is an acli write command with --from-json
    match = ACLI_FROM_JSON_RE.search(cmd)
    if not match:
        allow()
        return

    json_path = Path(match.group(1))
    # Resolve relative paths against cwd
    if not json_path.is_absolute():
        json_path = Path(data.get("cwd", ".")) / json_path

    if not json_path.exists():
        # File not found — let acli handle the error
        _log("SKIP", {"reason": "file_not_found", "file": str(json_path)})
        allow()
        return

    # Load the ADF JSON file
    try:
        with open(json_path) as f:
            adf_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        _log("ERROR", {"reason": str(e), "file": str(json_path)})
        allow()
        return

    # Import validator (lazy — only when we actually need it)
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from lib.adf_validator import AdfValidator, detect_format
    except ImportError as e:
        _log("ERROR", {"reason": f"import_failed: {e}"})
        allow()
        return

    # Detect format and extract ADF
    fmt, adf = detect_format(adf_data)
    if not adf or not isinstance(adf, dict):
        _log("SKIP", {"reason": "no_adf", "format": fmt, "file": str(json_path)})
        allow()
        return

    wrapper = adf_data if fmt in ("create", "edit") else None
    issue_type = detect_issue_type(adf_data, json_path)

    # Determine threshold — vibe mode uses lower threshold from config
    vibe = _is_vibe_mode(cmd)
    threshold = _load_vibe_threshold() if vibe else _DEFAULT_THRESHOLD

    # Validate
    validator = AdfValidator(threshold=threshold)
    report = validator.validate(adf, issue_type, wrapper)

    log_data = {
        "file": json_path.name,
        "type": issue_type,
        "format": fmt,
        "score": round(report.score, 1),
        "threshold": threshold,
        "vibe_mode": vibe,
        "passed": report.passed,
        "session_id": data.get("session_id", ""),
    }

    if report.passed:
        _log("ALLOWED", log_data)
        allow()
    else:
        # Build failure details
        issues = [f"  {c.check_id}: {c.message}" for c in report.checks if c.status.value == "fail"]
        issues_text = "\n".join(issues[:5])  # Top 5 failures
        reason = (
            f"HR1 BLOCKED: Quality Gate {report.score:.1f}% < {threshold:.0f}% "
            f"(type: {issue_type}, file: {json_path.name})"
            + (" [vibe mode]" if vibe else "") + "\n"
            f"Top issues:\n{issues_text}\n"
            f"Fix the ADF JSON and re-validate before writing to Jira."
        )
        _log("BLOCKED", log_data)
        block(reason)


if __name__ == "__main__":
    main()
