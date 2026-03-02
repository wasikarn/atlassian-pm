#!/usr/bin/env python3
"""Shared utilities for Claude hooks (I/O, logging, data extraction).

Separate from hooks_state.py (session state) — this module provides:
  - Centralized logging    → log_event(hook_name, level, data)
  - I/O helpers            → parse_stdin, allow, block, inject_context
  - Data extraction        → get_issue_key, get_additional_fields, get_parent_key
  - Constants              → ACLI_FROM_JSON_RE, LOG_DIR
  - Type detection         → detect_issue_type(data, file_path)

Import pattern in hooks:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hooks_lib import log_event, allow, block, ...
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────

LOG_DIR = Path.home() / ".claude" / "hooks-logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass  # non-fatal: logging must never break a hook

# Matches: acli jira workitem create|edit --from-json <path>
ACLI_FROM_JSON_RE = re.compile(
    r"acli\s+jira\s+workitem\s+(?:create|edit)\s+"
    r"(?:.*\s)?--from-json\s+[\"']?([^\s\"']+)[\"']?"
)

# Issue type patterns — order matters (story before subtask, epic before task)
_TYPE_PATTERNS = [
    ("story",   re.compile(r"story", re.I)),
    ("subtask", re.compile(r"subtask|sub[-_]", re.I)),
    ("epic",    re.compile(r"epic", re.I)),
    ("qa",      re.compile(r"qa|testplan|test[-_]plan", re.I)),
    ("task",    re.compile(r"task|migration|spike|chore|tech[-_]debt", re.I)),
]


# ── Logging ────────────────────────────────────────────────────────────────

def log_event(hook_name: str, level: str, data: dict) -> None:
    """Append a JSON log entry to the daily hooks log file.

    Args:
        hook_name: Hook identifier (e.g. "hr1-qg-before-write")
        level:     Log level (ALLOWED, BLOCKED, REMIND, TRACKED, WARN, ERROR, SKIP...)
        data:      Additional key-value pairs to include in the log entry
    """
    try:
        now = datetime.now(UTC)
        log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"
        entry = {"ts": now.isoformat(), "hook": hook_name, "level": level, **data}
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # logging must never break a hook


# ── I/O helpers ────────────────────────────────────────────────────────────

def parse_stdin() -> dict | None:
    """Read and parse JSON from stdin.

    Returns:
        Parsed dict, or None if stdin is empty / invalid JSON.
    """
    try:
        return json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        return None


def allow() -> None:
    """Output empty JSON object — signals 'allow' to Claude hooks runtime."""
    print("{}")


def block(reason: str) -> None:
    """Block the tool call: print reason to stderr and exit with code 2.

    Note: Does not return — always raises SystemExit(2).
    """
    print(reason, file=sys.stderr)
    sys.exit(2)


def inject_context(text: str) -> None:
    """Inject additionalContext into Claude's context (PostToolUse hooks only).

    Outputs the hookSpecificOutput wrapper required by the hooks runtime.
    """
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


# ── Data extraction ────────────────────────────────────────────────────────

def get_issue_key(tool_input: dict) -> str | None:
    """Extract issue key from tool_input, trying common field names in priority order.

    Priority: issue_key → issue_key_or_id → key
    Returns uppercase key (e.g. "BEP-123") or None if not found.
    """
    for field in ("issue_key", "issue_key_or_id", "key"):
        if field in tool_input:
            return str(tool_input[field]).upper()
    return None


def get_additional_fields(tool_input: dict) -> dict:
    """Extract additional_fields from tool_input, safely parsing JSON strings.

    Returns empty dict if field missing, not a dict, or invalid JSON.
    """
    additional = tool_input.get("additional_fields", {})
    if isinstance(additional, str):
        try:
            additional = json.loads(additional)
        except (json.JSONDecodeError, TypeError):
            additional = {}
    return additional if isinstance(additional, dict) else {}


def get_parent_key(tool_input: dict) -> str | None:
    """Extract parent issue key from tool_input.additional_fields.

    Handles both formats:
      - Dict:   {"parent": {"key": "BEP-X"}}
      - String: {"parent": "BEP-X"}

    Returns the parent key string, or None if not present.
    """
    additional = get_additional_fields(tool_input)
    parent = additional.get("parent")
    if not parent:
        return None
    if isinstance(parent, dict):
        return parent.get("key") or parent.get("id")
    if isinstance(parent, str):
        return parent
    return None


# ── Type detection ─────────────────────────────────────────────────────────

def detect_issue_type(data: dict, file_path: "Path | str | None" = None) -> str:
    """Detect issue type from ADF data or filename.

    Detection priority:
      1. Explicit 'type' field in data  (e.g. "Story", "Sub-task")
      2. Filename stem                  (e.g. "bep-123-subtask.json")
      3. Default: 'subtask'

    Args:
        data:      ADF JSON dict (may contain 'type' key)
        file_path: Optional path to the JSON file for filename inference

    Returns:
        One of: "story", "subtask", "epic", "qa", "task"
    """
    type_val = str(data.get("type", "")).lower()
    for issue_type, pattern in _TYPE_PATTERNS:
        if pattern.search(type_val):
            return issue_type

    if file_path is not None:
        name = Path(file_path).stem.lower()
        for issue_type, pattern in _TYPE_PATTERNS:
            if pattern.search(name):
                return issue_type

    return "subtask"
