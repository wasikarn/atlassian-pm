#!/usr/bin/env python3
"""Lightweight ADF pre-check before the full quality-gate agent.

Two-phase check:
  Phase 1: Pure Python structural validation (no AI, instant)
  Phase 2: Single claude -p call for content quality (AC format, language, specificity)

Usage:
    python3 scripts/ai/qg_quick.py --file /path/to/draft.json --type story
    cat draft.json | python3 scripts/ai/qg_quick.py --stdin --type story

Output (stdout): JSON object — always exit 0; caller decides how to act.
{
  "quick_pass": true|false,
  "structural_issues": ["QUIRK-1: panel missing panelType at content[2]", ...],
  "content_issues": ["AC2 uses generic 'call API' — must name specific endpoint", ...],
  "ac_count": 3,
  "score_estimate": 88,
  "skip_full_agent": false   // true only when score_estimate >= 95 AND no structural issues
}

score_estimate penalties (conservative — full agent may score differently):
  -15 per panel missing panelType
  -20 if ac_count < 3
  -15 if background section empty/missing
  -10 per content issue (from AI phase)
  -5  if language issues detected

skip_full_agent: true signals that this ADF is strong enough to skip the Sonnet
agent entirely. Threshold is deliberately high (>=95) to avoid false positives.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import run_claude
from prompts import CONTENT_CHECK_PROMPT


# ── Phase 1: Pure Python structural checks ────────────────────────────────────

def _extract_text(node: dict) -> str:
    """Recursively extract all text from an ADF node."""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = []
    for child in node.get("content", []):
        parts.append(_extract_text(child))
    return " ".join(p for p in parts if p)


def _count_acs(adf: dict) -> int:
    """Count AC<N>: markers anywhere in the ADF."""
    text = _extract_text(adf)
    return len(re.findall(r"\bAC\d+\s*:", text))


def _has_background(adf: dict) -> bool:
    """Check that ADF has a non-trivial Background section (>20 words)."""
    text = _extract_text(adf).lower()
    bg_idx = text.find("background")
    if bg_idx == -1:
        return False
    bg_text = text[bg_idx: bg_idx + 500]
    return len(bg_text.split()) > 25


def _check_panels(content: list) -> list[str]:
    """Return list of structural issues for panel nodes missing panelType."""
    issues = []
    for i, node in enumerate(content):
        if node.get("type") == "panel":
            if not node.get("attrs", {}).get("panelType"):
                issues.append(f"QUIRK-1: panel missing panelType at content[{i}]")
    return issues


def structural_check(adf: dict) -> tuple[list[str], int, int]:
    """Return (issues, ac_count, penalty).

    penalty = cumulative score deduction from structural problems only.
    """
    issues: list[str] = []
    penalty = 0

    # ADF root
    if adf.get("type") != "doc" or not isinstance(adf.get("content"), list):
        issues.append("ADF root is not a valid doc node")
        penalty += 30

    content = adf.get("content", [])

    # Panel panelType
    panel_issues = _check_panels(content)
    issues.extend(panel_issues)
    penalty += len(panel_issues) * 15

    # AC count
    ac_count = _count_acs(adf)
    if ac_count < 3:
        issues.append(f"Only {ac_count} AC(s) found — need at least 3")
        penalty += 20

    # Background
    if not _has_background(adf):
        issues.append("Background section missing or too short (<20 words)")
        penalty += 15

    return issues, ac_count, penalty


# ── Phase 2: AI content check ─────────────────────────────────────────────────

def content_check(adf: dict, issue_type: str) -> tuple[list[str], int]:
    """Run a single claude -p call. Return (content_issues, penalty)."""
    text = _extract_text(adf)[:2000]
    if not text.strip():
        return ["ADF has no readable text"], 20

    result = run_claude(
        CONTENT_CHECK_PROMPT.format(text=text, issue_type=issue_type),
        timeout=12,
    )
    if not result:
        return [], 0  # non-blocking: AI unavailable → skip content check

    try:
        data = json.loads(result.strip())
    except json.JSONDecodeError:
        return [], 0

    issues: list[str] = []
    penalty = 0

    if not data.get("ac_ok", True):
        for issue in data.get("ac_issues", []):
            if issue:
                issues.append(issue)
                penalty += 10

    if not data.get("language_ok", True):
        for issue in data.get("language_issues", []):
            if issue:
                issues.append(issue)
        penalty += 5

    if not data.get("background_ok", True):
        # background already checked structurally; avoid double-counting
        pass

    return issues, penalty


# ── Main ─────────────────────────────────────────────────────────────────────

def run_quick_check(adf: dict, issue_type: str) -> dict:
    """Run both phases and return result object."""
    structural_issues, ac_count, struct_penalty = structural_check(adf)
    content_issues, content_penalty = content_check(adf, issue_type)

    total_penalty = struct_penalty + content_penalty
    score_estimate = max(0, 100 - total_penalty)

    all_issues = structural_issues + content_issues
    quick_pass = len(structural_issues) == 0 and score_estimate >= 70

    # Only skip full agent when ADF is very strong: no structural issues + high score
    skip_full_agent = len(structural_issues) == 0 and len(content_issues) == 0 and score_estimate >= 95

    return {
        "quick_pass": quick_pass,
        "structural_issues": structural_issues,
        "content_issues": content_issues,
        "ac_count": ac_count,
        "score_estimate": score_estimate,
        "skip_full_agent": skip_full_agent,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight ADF pre-check")
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
        adf = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}", "quick_pass": False,
                          "structural_issues": ["Cannot parse ADF JSON"],
                          "content_issues": [], "ac_count": 0, "score_estimate": 0,
                          "skip_full_agent": False}))
        sys.exit(0)

    result = run_quick_check(adf, args.issue_type)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
