#!/usr/bin/env python3
"""Validate ADF JSON against quality gate criteria.

Enforces HR1: Quality Gate >= 90% before Atlassian writes.
Supports: Story, Subtask, Epic, QA issue types.

Usage:
    # Validate a story
    python validate_adf.py tasks/story.json --type story

    # Validate with auto-fix
    python validate_adf.py tasks/story.json --type story --fix

    # Summary only (for piping)
    python validate_adf.py tasks/story.json --type story --json

    # Validate subtask (EDIT format)
    python validate_adf.py tasks/subtask.json --type subtask

Exit codes:
    0 = pass (>= 90%)
    1 = fail (< 90%)
    2 = error (invalid input)
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.adf_validator import (
    AdfValidator,
    CheckStatus,
    ValidationReport,
    detect_format,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def print_report(report: ValidationReport, verbose: bool = False) -> None:
    """Print human-readable validation report."""
    score = report.score
    status_icon = "\u2705" if score >= 90 else "\u26a0\ufe0f" if score >= 70 else "\u274c"

    print(f"\n{'=' * 60}")
    print(f"ADF Validation: {report.issue_type.upper()}")
    print(f"{'=' * 60}")
    print(f"Score: {score:.1f}% {status_icon}")
    print(f"Checks: {len(report.checks)} total")

    # Count by status
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for c in report.checks:
        counts[c.status.value] += 1
    print(f"  \u2705 Pass: {counts['pass']}  \u26a0\ufe0f Warn: {counts['warn']}  \u274c Fail: {counts['fail']}")

    # Show issues
    issues = [c for c in report.checks if c.status != CheckStatus.PASS]
    if issues:
        print(f"\nIssues ({len(issues)}):")
        for c in issues:
            icon = "\u26a0\ufe0f" if c.status == CheckStatus.WARN else "\u274c"
            fix = " [auto-fixable]" if c.auto_fixable else ""
            print(f"  {icon} {c.check_id}: {c.message}{fix}")
            if c.fix_hint and verbose:
                print(f"     \u2192 {c.fix_hint}")

    if verbose:
        print("\nAll checks:")
        for c in report.checks:
            icon = (
                "\u2705"
                if c.status == CheckStatus.PASS
                else "\u26a0\ufe0f"
                if c.status == CheckStatus.WARN
                else "\u274c"
            )
            print(f"  {icon} {c.check_id}: {c.message}")

    print(f"{'=' * 60}")
    if report.passed:
        print("RESULT: PASS \u2014 Quality gate met (>= 90%)")
    else:
        fixable = sum(1 for c in issues if c.auto_fixable)
        if fixable:
            print(f"RESULT: FAIL \u2014 {fixable} issue(s) auto-fixable, run with --fix")
        else:
            print("RESULT: FAIL \u2014 Manual fixes required")
    print(f"{'=' * 60}\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate ADF JSON against quality gate criteria (HR1 enforcement)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_adf.py tasks/story.json --type story
  python validate_adf.py tasks/story.json --type story --fix
  python validate_adf.py tasks/story.json --type story --json
  python validate_adf.py tasks/subtask.json --type subtask --verbose

Issue types: story, subtask, epic, qa
Exit codes: 0=pass, 1=fail, 2=error
        """,
    )

    parser.add_argument("file", help="Path to ADF JSON file")
    parser.add_argument(
        "--type",
        "-t",
        required=True,
        choices=["story", "subtask", "epic", "qa"],
        help="Issue type for quality checks",
    )
    parser.add_argument("--fix", action="store_true", help="Auto-fix and write to -fixed.json")
    parser.add_argument("--json", action="store_true", help="Output JSON report only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all checks")

    args = parser.parse_args()

    # Load JSON file
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        return 2

    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON: %s", e)
        return 2

    # Detect format and extract ADF
    fmt, adf = detect_format(data)
    if not adf or not isinstance(adf, dict):
        logger.error("Could not extract ADF document from %s (format: %s)", file_path, fmt)
        return 2

    wrapper = data if fmt in ("create", "edit") else None

    # Validate
    validator = AdfValidator()
    report = validator.validate(adf, args.type, wrapper)

    # JSON output mode
    if args.json:
        result = report.to_dict()
        result["file"] = str(file_path)
        result["format"] = fmt
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if report.passed else 1

    # Human-readable output
    print_report(report, verbose=args.verbose)

    # Auto-fix mode
    if args.fix and not report.passed:
        fixable = [c for c in report.checks if c.auto_fixable and c.status != CheckStatus.PASS]
        if not fixable:
            print("No auto-fixable issues found. Manual fixes required.")
            return 1

        print(f"Applying {len(fixable)} auto-fix(es)...")
        fixed_adf, new_report = validator.auto_fix(adf, report)

        # Write fixed file
        if fmt == "create" or fmt == "edit":
            data["description"] = fixed_adf
        else:
            data = fixed_adf

        fixed_path = file_path.with_stem(file_path.stem + "-fixed")
        with open(fixed_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nFixed file: {fixed_path}")
        print_report(new_report, verbose=args.verbose)
        return 0 if new_report.passed else 1

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
