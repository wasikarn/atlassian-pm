#!/usr/bin/env python3
"""AI script: enrich rough description → structured ADF JSON.

Usage:
    python3 scripts/ai/enrich_description.py --text "rough description" --type story

Output (stdout): ADF JSON string
Exit 0: success | Exit 1: claude unavailable or parse failure
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import run_claude

_ENRICH_PROMPT = """\
You are writing a Jira {issue_type} description in Atlassian Document Format (ADF).

The content below is the user's rough description of the issue.
<user_description>
{text}
</user_description>

Write a complete ADF JSON document with these sections as headings:
1. Background — why this is needed
2. Goals — what success looks like (2-4 bullet points)
3. Acceptance Criteria — numbered list, each starting "AC{{n}}:"
4. Out of Scope — what this does NOT cover

Return ONLY a valid JSON code block in this format:
```json
{{"version": 1, "type": "doc", "content": [...]}}
```

Use ADF paragraph, heading (level 3), bulletList, orderedList nodes.
Do not add any text outside the JSON block."""


def build_enrich_prompt(text: str, issue_type: str) -> str:
    return _ENRICH_PROMPT.format(text=text[:1000], issue_type=issue_type)


def parse_adf_from_response(response: str) -> dict | None:
    """Extract JSON from a ```json ... ``` block or bare JSON."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r'(\{"version".*\})', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
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
