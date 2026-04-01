#!/usr/bin/env python3
"""Q: ADF Template Structure Validator.

PreToolUse hook for Bash. Validates ADF JSON structure matches
template requirements before acli writes to Jira.

Checks required headings by issue type, panel presence, non-empty content.
Complements HR1 QG scoring with fast structural pre-check.

Exit codes: 0 = allow, 2 = block (structure invalid)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import ACLI_FROM_JSON_RE, detect_issue_type, inject_context, log_event, parse_stdin

_HOOK = "adf-structure-validate"

# Required headings by issue type (normalized lowercase, emoji-stripped)
REQUIRED_HEADINGS = {
    "epic": ["epic overview"],
    "task": ["สิ่งที่ผู้ใช้ต้องการ", "เงื่อนไขที่ต้องผ่าน"],
    "qa": ["test objective", "test cases"],
}


def extract_headings(content: list) -> list[str]:
    headings = []
    for node in content:
        if node.get("type") == "heading":
            texts = []
            for child in node.get("content", []):
                if child.get("type") == "text":
                    texts.append(child.get("text", ""))
            headings.append("".join(texts))
    return headings


def normalize(h: str) -> str:
    return re.sub(r"^[^\w]*", "", h).strip().lower()


def has_panel(content: list) -> bool:
    return any(node.get("type") == "panel" for node in content)


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        sys.exit(0)

    session_id = data.get("session_id", "")

    if data.get("tool_name") != "Bash":
        log_event(_HOOK, "SKIP", {"reason": "wrong_tool", "session_id": session_id})
        sys.exit(0)

    cmd = data.get("tool_input", {}).get("command", "")
    match = ACLI_FROM_JSON_RE.search(cmd)
    if not match:
        log_event(_HOOK, "SKIP", {"reason": "no_acli_match", "session_id": session_id})
        sys.exit(0)

    json_path = Path(match.group(1))
    if not json_path.is_absolute():
        json_path = Path(data.get("cwd", ".")) / json_path

    if not json_path.exists():
        log_event(_HOOK, "SKIP", {"reason": "file_not_found", "file": str(json_path), "session_id": session_id})
        sys.exit(0)

    try:
        adf_data = json.loads(json_path.read_text())
    except (json.JSONDecodeError, OSError):
        log_event(_HOOK, "SKIP", {"reason": "file_parse_error", "session_id": session_id})
        sys.exit(0)

    desc = adf_data.get("description", {})
    if not isinstance(desc, dict) or desc.get("type") != "doc":
        log_event(_HOOK, "BLOCKED", {"reason": "invalid_desc_type", "session_id": session_id})
        print(
            'ADF STRUCTURE ERROR: description must be {"type": "doc", "version": 1, "content": [...]}',
            file=sys.stderr,
        )
        sys.exit(2)

    content = desc.get("content", [])
    if not content:
        log_event(_HOOK, "BLOCKED", {"reason": "empty_content", "session_id": session_id})
        print("ADF STRUCTURE ERROR: description.content is empty", file=sys.stderr)
        sys.exit(2)

    issue_type = detect_issue_type(adf_data, json_path)
    headings = extract_headings(content)
    heading_normalized = [normalize(h) for h in headings]

    required = REQUIRED_HEADINGS.get(issue_type, [])
    missing = [r for r in required if not any(r in h for h in heading_normalized)]

    if missing:
        log_event(_HOOK, "BLOCKED", {"issue_type": issue_type, "missing": missing, "session_id": session_id})
        print(
            f"ADF STRUCTURE ERROR ({issue_type}): Missing required headings: {', '.join(missing)}\n"
            f"Found: {headings}\n"
            f"Fix the ADF JSON template structure before writing.",
            file=sys.stderr,
        )
        sys.exit(2)

    if has_panel(content):
        # Warning only — panels are forbidden in v3.0.0 (Epic→Task hierarchy)
        log_event(_HOOK, "WARN", {"issue_type": issue_type, "reason": "panel_present", "session_id": session_id})
        inject_context(
            f"⚠️ ADF structure ({issue_type}): Panel found but panels are forbidden in v3.0.0. Remove panels from the ADF template.",
            event_name="PreToolUse",
        )
    else:
        log_event(_HOOK, "ALLOWED", {"issue_type": issue_type, "session_id": session_id})

    sys.exit(0)


if __name__ == "__main__":
    main()
