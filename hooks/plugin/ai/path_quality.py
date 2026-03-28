#!/usr/bin/env python3
"""PostToolUse async hook: rate Explore agent path quality.

Fires after Task tool completes. Rates path specificity via claude -p.
Exit code: 0 always.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, inject_context, log_event, parse_stdin
from plugin.ai.claude_call import claude_call

_HOOK = "ai-path-quality"
_PATH_RE = re.compile(r"[`'\"]([a-zA-Z0-9_/.-]+\.[a-zA-Z]{1,5})[`'\"]")

_RATE_PROMPT = """\
Rate the specificity of these file paths for a software implementation task.
Good paths name specific files. Poor paths are just directories like src/ or lib/.

Paths:
{paths}

Respond with one word: good, fair, or poor."""


def extract_paths(text: str) -> list[str]:
    """Extract quoted file paths from text."""
    return list(dict.fromkeys(_PATH_RE.findall(text)))[:20]


def rate_paths(paths: list[str]) -> Optional[str]:
    """Return 'good', 'fair', 'poor', or None if unavailable."""
    if not paths:
        return None
    paths_text = "\n".join(f"- {p}" for p in paths[:15])
    result = claude_call(_RATE_PROMPT.format(paths=paths_text), timeout=10)
    if not result:
        return None
    rating = result.strip().lower().split()[0]
    return rating if rating in ("good", "fair", "poor") else None


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    if data.get("tool_name") != "Task":
        allow()
        return

    response = data.get("tool_response", "")
    if isinstance(response, dict):
        response = json.dumps(response)

    paths = extract_paths(str(response))
    if not paths:
        allow()
        return

    rating = rate_paths(paths)
    if rating is None:
        allow()
        return

    log_event(_HOOK, "RATED", {"rating": rating, "path_count": len(paths)})

    if rating == "poor":
        inject_context(
            f"AI PATH QUALITY: Explore returned {len(paths)} paths rated '{rating}'. "
            f"Paths like {paths[:3]} are too generic. Consider re-running Explore with "
            f"more specific queries (e.g. grep for class/function names, not just directories)."
        )


if __name__ == "__main__":
    main()
