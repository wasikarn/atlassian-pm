#!/usr/bin/env python3
"""Auto-inject qmd search results before Glob/Grep on indexed projects.

PreToolUse hook — when Glob/Grep targets an indexed project:
1. Extract search query from the tool pattern
2. Run qmd CLI search automatically
3. Block with results → Claude gets qmd results first
4. Mark collection → subsequent Glob/Grep for same collection allowed

Exit 0 = allow, Exit 2 = block with qmd results
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hooks_state import (
    qmd_collection_for_path,
    qmd_is_collection_searched,
    qmd_mark_collection_searched,
)

QMD_BIN = "/Users/kobig/.bun/bin/qmd"

# Generic path segments that don't make good search queries
SKIP_SEGMENTS = {
    "**",
    "*",
    "src",
    "app",
    "modules",
    "components",
    "pages",
    "shared",
    "common",
    "utils",
    "lib",
    "types",
    "dtos",
    "services",
    "hooks",
    "contexts",
    "providers",
    "layouts",
    "features",
    "index",
    "config",
}


def split_identifier(s: str) -> str:
    """Split camelCase/PascalCase/snake_case/kebab-case into words."""
    # snake_case and kebab-case
    s = s.replace("_", " ").replace("-", " ")
    # camelCase and PascalCase: insert space before uppercase letters
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return s.lower()


raw = sys.stdin.read()
data = json.loads(raw)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "")

# Only intercept Glob and Grep
if tool_name not in ("Glob", "Grep"):
    sys.exit(0)

# Determine target path for collection detection
target_path = tool_input.get("path", "") or tool_input.get("pattern", "")
if not target_path:
    sys.exit(0)

# Check if path is in an indexed collection
collection = qmd_collection_for_path(target_path)
if not collection:
    sys.exit(0)

# Already auto-searched for this collection → allow
if qmd_is_collection_searched(session_id, collection):
    sys.exit(0)

# Extract search query based on tool type
query = ""
if tool_name == "Grep":
    # Grep pattern is the search string — use directly
    query = tool_input.get("pattern", "")
    # Clean regex-specific syntax for qmd search
    query = re.sub(r"[\\(){}[\]|^$.*+?]", " ", query)
    # Split camelCase/PascalCase/snake_case identifiers
    query = split_identifier(query)
    query = " ".join(query.split())
elif tool_name == "Glob":
    # Extract meaningful directory names from glob pattern
    pattern = tool_input.get("pattern", "")
    parts = pattern.replace("\\", "/").split("/")
    meaningful = []
    for p in parts:
        p = re.sub(r"\*+", "", p)  # Remove wildcards
        p = re.sub(r"\.\w+$", "", p)  # Remove file extensions
        p = re.sub(r"[{}]", " ", p)  # Remove braces
        p = p.strip()
        if p and p.lower() not in SKIP_SEGMENTS and len(p) > 2:
            meaningful.append(p)
    query = " ".join(meaningful)

# Can't extract meaningful query → allow Glob/Grep through
if not query or len(query.strip()) < 2:
    sys.exit(0)

# Run qmd search
try:
    result = subprocess.run(
        [QMD_BIN, "search", query, "-n", "8", "--files"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    qmd_output = result.stdout.strip()
except Exception:
    sys.exit(0)  # qmd failed → allow Glob/Grep

if not qmd_output:
    sys.exit(0)  # No results → allow Glob/Grep

# Parse --files output: #hash,score,qmd://collection/path
files = []
for line in qmd_output.split("\n"):
    parts = line.split(",", 2)
    if len(parts) >= 3:
        qmd_path = parts[2].strip()
        # Filter to only this collection
        prefix = f"qmd://{collection}/"
        if qmd_path.startswith(prefix):
            rel_path = qmd_path[len(prefix) :]
            files.append(rel_path)

if not files:
    sys.exit(0)  # No results for this collection → allow

# Mark this collection as auto-searched → subsequent calls allowed
qmd_mark_collection_searched(session_id, collection)

# Block with qmd results
file_list = "\n".join(f"  - {f}" for f in files)
print(
    json.dumps(
        {
            "error": (
                f'qmd auto-search [{collection}] query="{query}" ({len(files)} results):\n'
                f"{file_list}\n\n"
                f'Use mcp__qmd__get(path="{collection}/{files[0]}") to read a file.\n'
                f'Use mcp__qmd__search(query="...", collection="{collection}") for a different query.\n'
                f"Re-call {tool_name} if these results are insufficient (now unblocked for [{collection}])."
            )
        }
    )
)
sys.exit(2)
