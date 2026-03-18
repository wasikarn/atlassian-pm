#!/usr/bin/env python3
"""Track qmd tool usage in session state.

PostToolUse hook — marks qmd as used so L3 block hook unblocks Glob/Grep.

Exit 0 = always allow
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hooks_state import qmd_mark_used

raw = sys.stdin.read()
data = json.loads(raw)
tool_name = data.get("tool_name", "")
session_id = data.get("session_id", "")

# Track any qmd MCP tool usage
if tool_name.startswith("mcp__qmd__"):
    qmd_mark_used(session_id)

sys.exit(0)
