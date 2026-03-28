#!/usr/bin/env python3
"""PostToolUse async hook: rate Explore agent path quality.

Fires after Task tool completes. Rates path specificity via claude -p.
Exit code: 0 always.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, inject_context, log_event, parse_stdin
from plugin.ai.claude_call import claude_call
from plugin.ai.prompts import RATE_PROMPT

_HOOK = "ai-path-quality"
_PATH_RE = re.compile(r"[`'\"]([a-zA-Z0-9_/.-]+\.[a-zA-Z]{1,5})[`'\"]")


def extract_paths(text: str) -> list[str]:
    """Extract quoted file paths from text."""
    return list(dict.fromkeys(_PATH_RE.findall(text)))[:20]


def rate_paths(paths: list[str]) -> str | None:
    """Return 'good', 'fair', 'poor', or None if unavailable."""
    if not paths:
        return None
    paths_text = "\n".join(f"- {p}" for p in paths[:15])
    result = claude_call(RATE_PROMPT.format(paths=paths_text), timeout=10)
    if not result:
        return None
    try:
        data = json.loads(result.strip())
        rating = data.get("rating", "").lower()
    except (json.JSONDecodeError, AttributeError):
        return None
    return rating if rating in ("good", "fair", "poor") else None


def main() -> None:
    try:
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
    except Exception:
        allow()


if __name__ == "__main__":
    main()
