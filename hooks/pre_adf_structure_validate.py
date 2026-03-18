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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import ACLI_FROM_JSON_RE, detect_issue_type

# Required headings by issue type (normalized lowercase, emoji-stripped)
REQUIRED_HEADINGS = {
    "epic": ["epic overview"],
    "story": ["user story", "acceptance criteria"],
    "subtask": ["objective"],
    "qa": ["test objective", "test cases"],
    "task": [],
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


raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(0)

if data.get("tool_name") != "Bash":
    sys.exit(0)

cmd = data.get("tool_input", {}).get("command", "")
match = ACLI_FROM_JSON_RE.search(cmd)
if not match:
    sys.exit(0)

json_path = Path(match.group(1))
if not json_path.is_absolute():
    json_path = Path(data.get("cwd", ".")) / json_path

if not json_path.exists():
    sys.exit(0)

try:
    adf_data = json.loads(json_path.read_text())
except (json.JSONDecodeError, OSError):
    sys.exit(0)

desc = adf_data.get("description", {})
if not isinstance(desc, dict) or desc.get("type") != "doc":
    print(
        'ADF STRUCTURE ERROR: description must be {"type": "doc", "version": 1, "content": [...]}',
        file=sys.stderr,
    )
    sys.exit(2)

content = desc.get("content", [])
if not content:
    print("ADF STRUCTURE ERROR: description.content is empty", file=sys.stderr)
    sys.exit(2)

issue_type = detect_issue_type(adf_data, json_path)
headings = extract_headings(content)
heading_normalized = [normalize(h) for h in headings]

required = REQUIRED_HEADINGS.get(issue_type, [])
missing = [r for r in required if not any(r in h for h in heading_normalized)]

if missing:
    print(
        f"ADF STRUCTURE ERROR ({issue_type}): Missing required headings: {', '.join(missing)}\n"
        f"Found: {headings}\n"
        f"Fix the ADF JSON template structure before writing.",
        file=sys.stderr,
    )
    sys.exit(2)

if issue_type != "task" and not has_panel(content):
    # Warning only — print to stdout, exit 0
    print(f"⚠️ ADF structure ({issue_type}): No panel found. Templates require panels (info/success/warning/error).")

sys.exit(0)
