#!/usr/bin/env python3
"""
Configure project files from project-config.json

Replaces hardcoded values (project key, Jira site, company, custom fields) in
skill files, scripts, and docs with values from .claude/project-config.json

Usage:
    python scripts/configure-project.py                  # Dry run: show what --apply would do
    python scripts/configure-project.py --apply          # Apply: placeholders → real values
    python scripts/configure-project.py --revert         # Dry run: show what revert would do
    python scripts/configure-project.py --revert --apply # Revert: real values → placeholders
"""

import json
import re
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_DIR / ".claude" / "project-config.json"
SKILLS_DIR = PROJECT_DIR / ".claude" / "skills"

# Placeholder format: {{KEY}}
# Default values are used as fallback when config doesn't have the key
PLACEHOLDERS = {
    "PROJECT_KEY": "BEP",
    "JIRA_SITE": "100-stars.atlassian.net",
    "CONFLUENCE_SITE": "100-stars.atlassian.net",
    "SPACE_KEY": "BEP",
    "START_DATE_FIELD": "{{START_DATE_FIELD}}",
    "SPRINT_FIELD": "{{SPRINT_FIELD}}",
    "BOARD_ID": 2,
    "COMPANY": "Tathep",
    "COMPANY_LOWER": "tathep",
}


def load_config() -> dict:
    """Load project-config.json and extract values."""
    if not CONFIG_PATH.exists():
        print(f"Error: {CONFIG_PATH} not found")
        print("  Copy template: cp .claude/project-config.json.template .claude/project-config.json")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    return {
        "PROJECT_KEY": config["jira"]["project_key"],
        "JIRA_SITE": config["jira"]["site"],
        "CONFLUENCE_SITE": config["confluence"]["site"],
        "SPACE_KEY": config["confluence"]["space_key"],
        "START_DATE_FIELD": config["jira"]["custom_fields"]["start_date"],
        "SPRINT_FIELD": config["jira"]["custom_fields"]["sprint"],
        "BOARD_ID": config["jira"]["board_id"],
        "COMPANY": config.get("company", PLACEHOLDERS["COMPANY"]),
        "COMPANY_LOWER": config.get("company_lower", PLACEHOLDERS["COMPANY_LOWER"]),
    }


def get_replacement_patterns(values: dict, revert: bool = False) -> list[tuple[str, str]]:
    """Generate regex patterns for replacement."""
    patterns = []

    for key, placeholder_default in PLACEHOLDERS.items():
        actual_value = values.get(key, placeholder_default)
        placeholder = f"{{{{{key}}}}}"  # {{KEY}}

        if revert:
            # Replace actual values with placeholders
            if key == "PROJECT_KEY":
                patterns.extend(
                    [
                        (rf'"projectKey":\s*"{re.escape(actual_value)}"', f'"projectKey": "{placeholder}"'),
                        (rf'project_key:\s*"{re.escape(actual_value)}"', f'project_key: "{placeholder}"'),
                        (rf'project_key="{re.escape(actual_value)}"', f'project_key="{placeholder}"'),
                        (rf'space_key:\s*"{re.escape(actual_value)}"', f'space_key: "{placeholder}"'),
                        (rf'space_key="{re.escape(actual_value)}"', f'space_key="{placeholder}"'),
                        # Issue key pattern {{PROJECT_KEY}}-XXX (but not in URLs or smart links)
                        (rf"(?<!/browse/){re.escape(actual_value)}-XXX", f"{placeholder}-XXX"),
                    ]
                )
            elif key == "JIRA_SITE":
                patterns.append((rf"https://{re.escape(actual_value)}", f"https://{placeholder}"))
            elif key == "CONFLUENCE_SITE":
                # Only add if different from JIRA_SITE
                if actual_value != values.get("JIRA_SITE"):
                    patterns.append((rf"https://{re.escape(actual_value)}", f"https://{placeholder}"))
            elif key in ("START_DATE_FIELD", "SPRINT_FIELD"):
                patterns.append((rf"{re.escape(actual_value)}", placeholder))
            elif key == "BOARD_ID":
                patterns.append((rf"board_id={re.escape(str(actual_value))}", f"board_id={placeholder}"))
            elif key == "COMPANY":
                # Company name in various contexts
                patterns.extend(
                    [
                        (rf"{re.escape(actual_value)} Platform", f"{placeholder} Platform"),
                        (rf"for \*\*{re.escape(actual_value)} Platform\*\*", f"for **{placeholder} Platform**"),
                        (
                            rf"Agile Documentation System for \*\*{re.escape(actual_value)}",
                            f"Agile Documentation System for **{placeholder}",
                        ),
                    ]
                )
            elif key == "COMPANY_LOWER":
                # Lowercase company in paths, domains, identifiers
                patterns.extend(
                    [
                        (rf"~/Codes/Works/{re.escape(actual_value)}/", f"~/Projects/{placeholder}/"),
                    ]
                )
        else:
            # Replace placeholders with actual values
            if key == "PROJECT_KEY":
                patterns.extend(
                    [
                        (r'"projectKey":\s*"\{\{PROJECT_KEY\}\}"', f'"projectKey": "{actual_value}"'),
                        (r'project_key:\s*"\{\{PROJECT_KEY\}\}"', f'project_key: "{actual_value}"'),
                        (r'project_key="\{\{PROJECT_KEY\}\}"', f'project_key="{actual_value}"'),
                        (r'space_key:\s*"\{\{SPACE_KEY\}\}"', f'space_key: "{actual_value}"'),
                        (r'space_key="\{\{SPACE_KEY\}\}"', f'space_key="{actual_value}"'),
                        (r"\{\{PROJECT_KEY\}\}-XXX", f"{actual_value}-XXX"),
                    ]
                )
            elif key == "JIRA_SITE":
                patterns.append((r"https://\{\{JIRA_SITE\}\}", f"https://{actual_value}"))
            elif key == "CONFLUENCE_SITE":
                patterns.append((r"https://\{\{CONFLUENCE_SITE\}\}", f"https://{actual_value}"))
            elif key in ("START_DATE_FIELD", "SPRINT_FIELD"):
                patterns.append((rf"\{{\{{{key}\}}\}}", actual_value))
            elif key == "BOARD_ID":
                patterns.append((r"board_id=\{\{BOARD_ID\}\}", f"board_id={actual_value}"))
            elif key == "COMPANY":
                patterns.extend(
                    [
                        (r"\{\{COMPANY\}\} Platform", f"{actual_value} Platform"),
                        (r"for \*\*\{\{COMPANY\}\} Platform\*\*", f"for **{actual_value} Platform**"),
                        (
                            r"Agile Documentation System for \*\*\{\{COMPANY\}\}",
                            f"Agile Documentation System for **{actual_value}",
                        ),
                    ]
                )
            elif key == "COMPANY_LOWER":
                patterns.extend(
                    [
                        (r"~/Projects/\{\{COMPANY_LOWER\}\}/", f"~/Codes/Works/{actual_value}/"),
                    ]
                )

    return patterns


def process_file(filepath: Path, patterns: list[tuple[str, str]], dry_run: bool = True) -> list[str]:
    """Process a single file and return list of changes made."""
    changes = []

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return [f"  Error reading: {e}"]

    new_content = content
    for pattern, replacement in patterns:
        matches = re.findall(pattern, new_content)
        if matches:
            new_content = re.sub(pattern, replacement, new_content)
            changes.append(f"  {pattern[:50]}... → {replacement[:50]}... ({len(matches)} matches)")

    if changes and not dry_run:
        filepath.write_text(new_content, encoding="utf-8")

    return changes


def collect_files() -> list[Path]:
    """Collect all files to process.

    Only documentation and shell files — NOT Python source code
    (Python uses custom field IDs at runtime, replacing would break code).
    """
    files = []
    self_path = Path(__file__).resolve()

    # Skills .md files
    files.extend(SKILLS_DIR.rglob("*.md"))

    # Scripts (.sh only — Python scripts use runtime values)
    scripts_dir = PROJECT_DIR / "scripts"
    files.extend(scripts_dir.glob("*.sh"))
    # Executable scripts without extension (like sync-skills)
    for f in scripts_dir.iterdir():
        if f.is_file() and not f.suffix and f.name != "__pycache__":
            files.append(f)

    # Root files
    for name in ("CLAUDE.md", "README.md"):
        p = PROJECT_DIR / name
        if p.exists():
            files.append(p)

    # Exclude self
    return sorted(f for f in set(files) if f.resolve() != self_path)


def main():
    # Parse args
    apply_changes = "--apply" in sys.argv
    revert_mode = "--revert" in sys.argv

    # --revert --apply = revert AND write to files
    # --revert         = revert dry run (show what would change)
    # --apply          = apply (placeholders → real values) AND write

    # Load config
    config_values = load_config()

    print("=" * 60)
    if revert_mode:
        print("REVERT MODE: Converting actual values -> placeholders")
    else:
        print("CONFIGURE MODE: Converting placeholders -> actual values")
    if not apply_changes:
        print("(DRY RUN — add --apply to write changes)")
    print("=" * 60)
    print(f"\nConfig: {CONFIG_PATH}")
    print("Values:")
    for k, v in config_values.items():
        print(f"  {k}: {v}")
    print()

    # Get patterns
    patterns = get_replacement_patterns(config_values, revert=revert_mode)

    # Collect files
    files = collect_files()

    print(f"Scanning {len(files)} files...\n")

    total_changes = 0
    files_changed = 0

    for filepath in files:
        rel_path = filepath.relative_to(PROJECT_DIR)
        changes = process_file(filepath, patterns, dry_run=not apply_changes)

        if changes:
            files_changed += 1
            total_changes += len(changes)
            print(f"  {rel_path}")
            for change in changes:
                print(change)
            print()

    # Summary
    print("=" * 60)
    if apply_changes:
        print(f"Applied {total_changes} changes in {files_changed} files")
    else:
        print(f"Found {total_changes} potential changes in {files_changed} files")
        print("\nRun with --apply to write changes:")
        if revert_mode:
            print(f"  python {Path(__file__).name} --revert --apply")
        else:
            print(f"  python {Path(__file__).name} --apply")
            print("\nOr revert to placeholders:")
            print(f"  python {Path(__file__).name} --revert --apply")


if __name__ == "__main__":
    main()
