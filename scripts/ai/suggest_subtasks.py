#!/usr/bin/env python3
"""AI script: suggest subtask breakdown from story ACs.

Usage:
    python3 scripts/ai/suggest_subtasks.py --story TP-123 --acs "AC1: ...\nAC2: ..."

Output (stdout): JSON array of suggested subtask summaries
Exit 0: success | Exit 1: unavailable
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import run_claude
from prompts import SUBTASK_PROMPT


def build_subtask_prompt(story_key: str, acs: list[str]) -> str:
    acs_text = "\n".join(acs[:15])
    return SUBTASK_PROMPT.format(story_key=story_key, acs=acs_text)


def parse_subtasks_from_response(response: str) -> list[str]:
    """Extract numbered list items from response."""
    if not response.strip():
        return []
    subtasks = []
    for line in response.strip().split("\n"):
        match = re.match(r"^\d+\.\s+(.+)$", line.strip())
        if match:
            subtasks.append(match.group(1).strip())
    return subtasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Suggest subtask breakdown from story ACs")
    parser.add_argument("--story", required=True, help="Story key e.g. TP-123")
    parser.add_argument("--acs", required=True, help="ACs, newline-separated")
    args = parser.parse_args()

    acs = [ac.strip() for ac in args.acs.strip().split("\n") if ac.strip()]
    if not acs:
        print("[]")
        sys.exit(0)

    prompt = build_subtask_prompt(args.story, acs)
    response = run_claude(prompt, timeout=25)
    if not response:
        sys.exit(1)

    subtasks = parse_subtasks_from_response(response)
    if not subtasks:
        sys.exit(1)

    print(json.dumps(subtasks, ensure_ascii=False))


if __name__ == "__main__":
    main()
