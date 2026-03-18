#!/usr/bin/env python3
"""W: Suggest fallback when Explore agent returns generic paths.

PostToolUse hook for Task tool.
Detects when Task(subagent_type=Explore) returns generic/placeholder
file paths and suggests switching to hybrid mode.

Exit 0 = always allow
"""

import json
import re
import sys

raw = sys.stdin.read()
data = json.loads(raw)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
tool_output = str(data.get("tool_output", ""))

# Only trigger on Task tool with Explore subagent
if tool_name != "Task":
    sys.exit(0)
if tool_input.get("subagent_type") != "Explore":
    sys.exit(0)

# Check for generic path indicators
GENERIC_INDICATORS = [
    r"src/\w+/",  # bare "src/something/" without full path
    r"lib/\w+\.ts",  # generic lib paths
    r"\[file path\]",  # placeholder text
    r"path/to/",  # obvious placeholder
    r"example\.ts",  # example files
    r"could not find",  # search failure
    r"no results found",  # empty results
    r"generic",  # self-describing
]

# Count generic indicators
generic_count = sum(1 for pattern in GENERIC_INDICATORS if re.search(pattern, tool_output, re.I))

# Also check for very short output (explore returned almost nothing)
is_too_short = len(tool_output.strip()) < 100

if generic_count >= 2 or is_too_short:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "⚠️ Explore agent returned generic/incomplete paths. "
                "Consider: (1) Re-run with more specific search terms, "
                "(2) Use Glob/Grep directly for targeted file search, "
                "(3) Ask user for specific file paths or module names. "
                "Generic paths in subtasks violate HR1 quality gate."
            ),
        }
    }
    print(json.dumps(output))

sys.exit(0)
