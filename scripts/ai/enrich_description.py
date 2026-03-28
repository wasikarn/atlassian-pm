#!/usr/bin/env python3
"""AI script: enrich rough description → structured ADF JSON.

Usage:
    python3 scripts/ai/enrich_description.py --text "rough description" --type story

Output (stdout): ADF JSON string
Exit 0: success | Exit 1: claude unavailable or parse failure
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import run_claude
from prompts import ENRICH_PROMPT


def build_enrich_prompt(text: str, issue_type: str) -> str:
    return ENRICH_PROMPT.format(text=text[:1000], issue_type=issue_type)


def parse_adf_from_response(response: str) -> dict | None:
    """Parse bare JSON ADF object from response."""
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich rough description to ADF JSON")
    parser.add_argument("--text", required=True, help="Rough description text")
    parser.add_argument("--type", default="story", dest="issue_type",
                        choices=["story", "task", "epic", "bug"])
    args = parser.parse_args()

    prompt = build_enrich_prompt(args.text, args.issue_type)
    response = run_claude(prompt, timeout=25)
    if not response:
        sys.exit(1)

    adf = parse_adf_from_response(response)
    if not adf:
        sys.exit(1)

    print(json.dumps(adf, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
