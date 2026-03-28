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
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import log_event, parse_stdin
from hooks_state import (
    qmd_collection_for_path,
    qmd_is_collection_searched,
    qmd_mark_collection_searched,
)

QMD_BIN = shutil.which("qmd")
if not QMD_BIN:
    sys.exit(0)  # qmd not installed → allow Glob/Grep through

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
    # Framework/infra directories — structural, not semantic
    "routes",
    "validators",
    "middlewares",
    "middleware",
    "scripts",
    "helpers",
    "handlers",
    "contracts",
    "database",
    "migrations",
    "seeders",
}

# File extensions QMD does NOT index — Glob/Grep targeting these is pure navigation
_UNINDEXED_EXTENSIONS = {
    ".py", ".sh", ".bash", ".zsh",
    ".json", ".jsonc", ".lock",
    ".yaml", ".yml", ".toml", ".env",
    ".sql", ".csv", ".txt", ".log",
    ".go", ".rb", ".php", ".java", ".c", ".cpp", ".h",
}

# Pre-compiled regexes — avoids recompilation on every hook invocation
_RE_CAMEL_LOWER_UPPER = re.compile(r"([a-z])([A-Z])")
_RE_ACRONYM = re.compile(r"([A-Z]+)([A-Z][a-z])")
_RE_REGEX_SYNTAX = re.compile(r"[\\(){}[\]|^$.*+?]")
_RE_FILE_EXT = re.compile(r"\.(\w+)$")
_RE_WILDCARDS = re.compile(r"\*+")
_RE_EXTENSIONS = re.compile(r"\.\w+$")
_RE_BRACES = re.compile(r"[{}]")


def split_identifier(s: str) -> str:
    """Split camelCase/PascalCase/snake_case/kebab-case into words."""
    s = s.replace("_", " ").replace("-", " ")
    s = _RE_CAMEL_LOWER_UPPER.sub(r"\1 \2", s)
    s = _RE_ACRONYM.sub(r"\1 \2", s)
    return s.lower()


def main() -> None:
    data = parse_stdin()
    if not data:
        sys.exit(0)

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
        # Skip if file glob filter targets non-indexed extension
        file_glob = tool_input.get("glob", "") or tool_input.get("type", "")
        if file_glob:
            _, ext = os.path.splitext(file_glob)
            if ext in _UNINDEXED_EXTENSIONS:
                sys.exit(0)

        # Grep pattern is the search string — use directly
        query = tool_input.get("pattern", "")
        # Skip structural patterns with no real word content (<3 alpha chars)
        alpha_count = sum(1 for c in query if c.isalpha())
        if alpha_count < 3:
            sys.exit(0)
        # Clean regex-specific syntax for qmd search
        query = _RE_REGEX_SYNTAX.sub(" ", query)
        # Split camelCase/PascalCase/snake_case identifiers
        query = split_identifier(query)
        query = " ".join(query.split())
    elif tool_name == "Glob":
        # Extract meaningful directory names from glob pattern
        pattern = tool_input.get("pattern", "")

        # Skip if pattern targets non-indexed file extension
        ext_match = _RE_FILE_EXT.search(pattern.rstrip("/"))
        if ext_match:
            ext = "." + ext_match.group(1)
            if ext in _UNINDEXED_EXTENSIONS:
                sys.exit(0)

        parts = pattern.replace("\\", "/").split("/")
        meaningful = []
        for p in parts:
            p = _RE_WILDCARDS.sub("", p)   # Remove wildcards
            p = _RE_EXTENSIONS.sub("", p)  # Remove file extensions
            p = _RE_BRACES.sub(" ", p)     # Remove braces
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
    except Exception as e:
        log_event("qmd-auto-search", "ERROR", {"phase": "subprocess", "query": query, "error": str(e)})
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
                rel_path = qmd_path[len(prefix):]
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


if __name__ == "__main__":
    main()
