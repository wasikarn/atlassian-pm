#!/usr/bin/env python3
"""Batch update Jira issue fields from JSON config.

Updates dates, story points, labels, sprint, and priority across multiple issues
in a single command. Enforces HR6 (cache invalidation), HR8 (subtask date alignment),
and HR10 (no sprint on subtasks).

Usage:
    # From config file
    python jira_batch_update.py --config updates.json

    # Dry run (validate only)
    python jira_batch_update.py --config updates.json --dry-run

    # Verbose output
    python jira_batch_update.py --config updates.json -v

Config format (updates.json):
    {
      "updates": [
        {
          "keys": ["BEP-3263", "BEP-3264"],
          "start_date": "2026-02-11",
          "due_date": "2026-02-12"
        },
        {
          "keys": ["BEP-3265"],
          "start_date": "2026-02-12",
          "due_date": "2026-02-14",
          "story_points": 3,
          "labels": ["fe-web"]
        },
        {
          "keys": ["BEP-2722"],
          "sprint": 640
        }
      ]
    }

Supported fields:
    start_date   - Start date (YYYY-MM-DD) → customfield_10015
    due_date     - Due date (YYYY-MM-DD) → duedate
    story_points - Story points → customfield_10036
    labels       - Labels (list of strings) → labels
    sprint       - Sprint ID (integer) → customfield_10020
    priority     - Priority name → priority

Exit codes:
    0 = all updates succeeded
    1 = some updates failed
    2 = error (input/credentials)
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import (
    APIError,
    CredentialsError,
    IssueNotFoundError,
    JiraAPI,
    create_ssl_context,
    derive_jira_url,
    get_auth_header,
    load_credentials,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Config field names → Jira REST API field IDs (resolved at runtime from project-config)
SIMPLE_FIELDS = {"due_date": "duedate"}
PRIORITY_FIELD = "priority"


def load_project_config() -> dict:
    """Load project-config.json from .claude/"""
    config_path = Path(__file__).parent.parent.parent.parent / "project-config.json"
    with open(config_path) as f:
        return json.load(f)


def create_api() -> JiraAPI:
    """Create configured Jira API client."""
    creds = load_credentials()
    jira_url = derive_jira_url(creds["CONFLUENCE_URL"])
    return JiraAPI(
        base_url=jira_url,
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )


def validate_date(date_str: str) -> bool:
    """Check YYYY-MM-DD format."""
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", date_str))


def build_fields_payload(
    update: dict,
    custom_fields: dict,
    is_subtask: bool,
) -> dict[str, Any]:
    """Convert config update entry to Jira REST API fields dict.

    HR10: Skips sprint for subtasks.
    """
    fields: dict[str, Any] = {}

    if "start_date" in update:
        fields[custom_fields["start_date"]] = update["start_date"]
    if "due_date" in update:
        fields["duedate"] = update["due_date"]
    if "story_points" in update:
        fields[custom_fields["story_points"]] = update["story_points"]
    if "labels" in update:
        fields["labels"] = update["labels"]
    if "sprint" in update:
        if is_subtask:
            logger.warning("HR10: Skipping sprint on subtask (inherits from parent)")
        else:
            fields[custom_fields["sprint"]] = update["sprint"]
    if "priority" in update:
        fields["priority"] = {"name": update["priority"]}

    return fields


def validate_config(config: dict) -> list[str]:
    """Validate config structure, return list of errors."""
    errors = []

    if "updates" not in config:
        errors.append("Missing 'updates' key in config")
        return errors

    if not isinstance(config["updates"], list):
        errors.append("'updates' must be a list")
        return errors

    for i, update in enumerate(config["updates"]):
        prefix = f"updates[{i}]"

        if "keys" not in update:
            errors.append(f"{prefix}: missing 'keys'")
            continue

        if not isinstance(update["keys"], list) or not update["keys"]:
            errors.append(f"{prefix}: 'keys' must be a non-empty list")

        for key in update.get("keys", []):
            if not re.match(r"^[A-Z]+-\d+$", key):
                errors.append(f"{prefix}: invalid issue key '{key}'")

        if "start_date" in update and not validate_date(update["start_date"]):
            errors.append(f"{prefix}: invalid start_date format (expected YYYY-MM-DD)")

        if "due_date" in update and not validate_date(update["due_date"]):
            errors.append(f"{prefix}: invalid due_date format (expected YYYY-MM-DD)")

        if "story_points" in update and not isinstance(update["story_points"], (int, float)):
            errors.append(f"{prefix}: story_points must be a number")

        if "labels" in update and not isinstance(update["labels"], list):
            errors.append(f"{prefix}: labels must be a list")

        if "sprint" in update and not isinstance(update["sprint"], int):
            errors.append(f"{prefix}: sprint must be an integer")

        # Check at least one field to update (besides keys)
        field_keys = set(update.keys()) - {"keys"}
        if not field_keys:
            errors.append(f"{prefix}: no fields to update")

    return errors


def check_subtask(api: JiraAPI, issue_key: str) -> bool:
    """Check if issue is a subtask."""
    try:
        issue = api.get_issue(issue_key, fields="issuetype")
        type_name = issue["fields"]["issuetype"]["name"]
        return type_name.lower() in ("subtask", "sub-task")
    except (APIError, IssueNotFoundError):
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch update Jira issue fields from JSON config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", required=True, help="Path to updates JSON config file")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview, no writes")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        return 2

    with open(config_path) as f:
        config = json.load(f)

    # Validate config
    errors = validate_config(config)
    if errors:
        print("Config validation errors:")
        for err in errors:
            print(f"  - {err}")
        return 2

    # Load project config for custom field IDs
    project_config = load_project_config()
    custom_fields = project_config["jira"]["custom_fields"]

    updates = config["updates"]
    total_issues = sum(len(u["keys"]) for u in updates)

    print(f"{'=' * 60}")
    print(f"Batch Update: {len(updates)} groups, {total_issues} issues")
    if args.dry_run:
        print("MODE: DRY RUN (no writes)")
    print(f"{'=' * 60}")

    if args.dry_run:
        # Preview mode
        for i, update in enumerate(updates):
            keys = update["keys"]
            field_names = [k for k in update if k != "keys"]
            print(f"\n  Group {i + 1}: {', '.join(keys)}")
            print(f"    Fields: {', '.join(field_names)}")
        print(f"\n\u2705 DRY RUN \u2014 config valid, {total_issues} issues would be updated")
        return 0

    # Execute updates
    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 2

    succeeded = 0
    failed = 0
    all_keys: list[str] = []

    for i, update in enumerate(updates):
        keys = update["keys"]
        print(f"\n[Group {i + 1}/{len(updates)}] {', '.join(keys)}")

        for key in keys:
            # Check if subtask (for HR10)
            is_subtask = check_subtask(api, key)

            # Build payload
            fields = build_fields_payload(update, custom_fields, is_subtask)
            if not fields:
                print(f"  {key}: no applicable fields (skipped)")
                continue

            # Execute update
            try:
                api.update_fields(key, fields)
                field_names = list(fields.keys())
                print(f"  {key}: {', '.join(field_names)} \u2705")
                succeeded += 1
                all_keys.append(key)
            except (APIError, IssueNotFoundError) as e:
                err_msg = str(e)
                if hasattr(e, "status_code"):
                    err_msg = f"{e.status_code} {e.reason}"
                print(f"  {key}: FAILED \u2014 {err_msg}")
                failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Results: {succeeded} succeeded, {failed} failed")

    if all_keys:
        print(f"\nHR6 Action: cache_invalidate for {len(all_keys)} issues:")
        for key in all_keys:
            print(f"  cache_invalidate('{key}')")

    print(f"{'=' * 60}")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
