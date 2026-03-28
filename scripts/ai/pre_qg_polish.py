#!/usr/bin/env python3
"""AI script: polish ADF draft before QG check.

Usage:
    python3 scripts/ai/pre_qg_polish.py --file /path/to/draft.json --type story
    cat draft.json | python3 scripts/ai/pre_qg_polish.py --stdin --type story

Output (stdout): improved ADF JSON
Exit 0: success | Exit 1: unavailable
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import run_claude

_POLISH_PROMPT = """\
You are reviewing a Jira {issue_type} ADF JSON description before a quality gate check.

Quality gate checks for:
- At least 3 acceptance criteria in AC1:, AC2:, AC3: format
- Background section present and non-trivial (>20 words)
- Goals section with 2+ bullet points
- Out of Scope section present
- No placeholder text

The content below is the current ADF JSON draft.
<adf_draft>
{adf}
</adf_draft>

Improve the ADF to pass these checks. Keep existing good content.
Return ONLY the improved JSON object — no markdown fences, no preamble, no trailing text:
{{"version": 1, "type": "doc", "content": [...]}}"""


def build_polish_prompt(adf_json: str, issue_type: str) -> str:
    return _POLISH_PROMPT.format(adf=adf_json[:3000], issue_type=issue_type)


def parse_polished_adf(response: str) -> dict | None:
    """Parse bare JSON ADF object from response."""
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Polish ADF JSON before QG check")
    parser.add_argument("--file", help="Path to ADF JSON file")
    parser.add_argument("--stdin", action="store_true", help="Read ADF from stdin")
    parser.add_argument("--type", default="story", dest="issue_type",
                        choices=["story", "task", "epic", "bug", "subtask"])
    args = parser.parse_args()

    if args.stdin:
        raw = sys.stdin.read()
    elif args.file:
        raw = Path(args.file).read_text()
    else:
        parser.error("Provide --file or --stdin")
        return

    try:
        adf_data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    prompt = build_polish_prompt(json.dumps(adf_data, indent=2), args.issue_type)
    response = run_claude(prompt, timeout=30)
    if not response:
        sys.exit(1)

    polished = parse_polished_adf(response)
    if not polished:
        sys.exit(1)

    print(json.dumps(polished, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
