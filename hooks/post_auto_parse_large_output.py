#!/usr/bin/env python3
"""Auto-parse MCP tool outputs that exceed Claude's token limit.

PostToolUse hook — when tool_response contains "exceeds maximum allowed tokens",
extracts the saved file path and runs parse-mcp-output.py to return a formatted
summary table as additionalContext.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context, log_event

_HOOK = "auto-parse-large-output"
PARSER_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "parse-mcp-output.py"

# Max lines to inject back into context (avoid flooding)
MAX_OUTPUT_LINES = 60


def extract_saved_file_path(response_text: str) -> str | None:
    """Extract file path from overflow error message."""
    # Pattern: "Output has been saved to /path/to/file.txt"
    # Also handles: "output has been saved to /path/to/file.txt"
    match = re.search(
        r"[Oo]utput has been saved to\s+(\S+\.txt)",
        response_text,
    )
    if match:
        return match.group(1)
    return None


def run_parser(file_path: str) -> str | None:
    """Run parse-mcp-output.py and return formatted output."""
    if not PARSER_SCRIPT.exists():
        return None

    try:
        result = subprocess.run(
            [sys.executable, str(PARSER_SCRIPT), file_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Combine stdout (table) and stderr (count)
            lines = result.stdout.strip().split("\n")
            count_line = result.stderr.strip()

            if len(lines) > MAX_OUTPUT_LINES:
                truncated = lines[:MAX_OUTPUT_LINES]
                truncated.append(f"... ({len(lines) - MAX_OUTPUT_LINES} more rows)")
                truncated.append(f'Full output: python3 scripts/parse-mcp-output.py "{file_path}"')
                return "\n".join(truncated) + f"\n{count_line}"

            return result.stdout.strip() + f"\n{count_line}"
    except (subprocess.TimeoutExpired, OSError) as e:
        log_event(_HOOK, "ERROR", {"error": str(e), "file": file_path})
        return None

    return None


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    # Get tool_response as string
    response = data.get("tool_response", "")
    if isinstance(response, dict):
        response = json.dumps(response)
    if not isinstance(response, str):
        response = str(response)

    # Check for overflow pattern
    if "exceeds maximum allowed tokens" not in response:
        print("{}")
        return

    # Extract file path
    file_path = extract_saved_file_path(response)
    if not file_path or not Path(file_path).exists():
        log_event(_HOOK, "WARN", {"reason": "file_path not found", "response": response[:200]})
        print("{}")
        return

    # Run parser
    tool_name = data.get("tool_name", "unknown")
    parsed = run_parser(file_path)

    if not parsed:
        log_event(_HOOK, "WARN", {"reason": "parser failed", "file": file_path})
        print("{}")
        return

    log_event(_HOOK, "PARSED", {"tool": tool_name, "file": file_path, "lines": parsed.count("\n") + 1})
    inject_context(
        f"AUTO-PARSED large output from {tool_name}:\n\n"
        f"{parsed}\n\n"
        f"Raw file: {file_path}\n"
        f'Filter: python3 scripts/parse-mcp-output.py "{file_path}" --status "In Progress" --assignee joakim'
    )


if __name__ == "__main__":
    main()
