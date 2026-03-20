#!/usr/bin/env python3
"""Post-write verifier for Jira issues.

Enforces HR3 (assignee), HR5 (parent link), HR6 (cache invalidate).
Verifies that Jira writes actually took effect by reading back from API.

Usage:
    # Verify parent link
    python verify_write.py BEP-1234 --check parent --expected-parent BEP-1200

    # Verify assignee
    python verify_write.py BEP-1234 --check assignee

    # Verify multiple issues
    python verify_write.py BEP-1234 BEP-1235 --check parent,assignee

    # JSON output
    python verify_write.py BEP-1234 --check parent --json

Exit codes:
    0 = all checks passed
    1 = one or more checks failed
    2 = error (API/credentials)
"""

import argparse
import json
import logging
import sys
from pathlib import Path

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


def create_api() -> JiraAPI:
    """Create configured Jira API client."""
    creds = load_credentials()
    jira_url = derive_jira_url(creds["CONFLUENCE_URL"])
    return JiraAPI(
        base_url=jira_url,
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )


def verify_issue(
    api: JiraAPI,
    issue_key: str,
    checks: list[str],
    expected_parent: str | None = None,
) -> dict:
    """Verify a single issue against checks.

    Returns:
        Dict with check results and actions_needed.
    """
    fields = "summary,status,assignee,parent,issuetype"
    issue = api.get_issue(issue_key, fields=fields)

    result = {
        "key": issue_key,
        "summary": issue["fields"].get("summary", ""),
        "checks": {},
        "actions_needed": [],
    }

    issue_fields = issue["fields"]

    if "parent" in checks:
        parent = issue_fields.get("parent")
        parent_key = parent.get("key") if parent else None
        if expected_parent:
            if parent_key == expected_parent:
                result["checks"]["parent"] = {
                    "status": "pass",
                    "message": f"Parent = {parent_key}",
                }
            else:
                result["checks"]["parent"] = {
                    "status": "fail",
                    "message": f"Parent = {parent_key}, expected {expected_parent}",
                }
        else:
            if parent_key:
                result["checks"]["parent"] = {
                    "status": "pass",
                    "message": f"Parent = {parent_key}",
                }
            else:
                result["checks"]["parent"] = {
                    "status": "fail",
                    "message": "No parent link set (HR5 violation)",
                }

    if "assignee" in checks:
        assignee = issue_fields.get("assignee")
        if assignee:
            display = assignee.get("displayName", assignee.get("emailAddress", "set"))
            result["checks"]["assignee"] = {
                "status": "pass",
                "message": f"Assignee = {display}",
            }
        else:
            result["checks"]["assignee"] = {
                "status": "fail",
                "message": "No assignee set (HR3 — use acli to assign)",
            }

    if "description" in checks:
        desc = issue_fields.get("description")
        if desc and isinstance(desc, dict) and desc.get("type") == "doc":
            content = desc.get("content", [])
            result["checks"]["description"] = {
                "status": "pass",
                "message": f"ADF description with {len(content)} nodes",
            }
        elif desc:
            result["checks"]["description"] = {
                "status": "warn",
                "message": "Description exists but not in ADF format",
            }
        else:
            result["checks"]["description"] = {
                "status": "fail",
                "message": "No description set",
            }

    # HR6: Always recommend cache invalidation after verification
    result["actions_needed"].append(f"cache_invalidate('{issue_key}')")

    return result


def print_result(result: dict, verbose: bool = False) -> bool:
    """Print verification result. Returns True if all checks passed."""
    all_pass = True
    print(f"\n  {result['key']}: {result['summary'][:50]}")

    for check_name, check in result["checks"].items():
        icon = "\u2705" if check["status"] == "pass" else "\u26a0\ufe0f" if check["status"] == "warn" else "\u274c"
        print(f"    {icon} {check_name}: {check['message']}")
        if check["status"] == "fail":
            all_pass = False

    if verbose and result["actions_needed"]:
        print(f"    \u2192 Actions: {', '.join(result['actions_needed'])}")

    return all_pass


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Post-write verifier for Jira issues (HR3/HR5/HR6 enforcement)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_write.py BEP-1234 --check parent --expected-parent BEP-1200
  python verify_write.py BEP-1234 BEP-1235 --check parent,assignee
  python verify_write.py BEP-1234 --check parent,assignee,description --json

Available checks: parent, assignee, description
Exit codes: 0=pass, 1=fail, 2=error
        """,
    )

    parser.add_argument("issues", nargs="+", help="Issue key(s) to verify")
    parser.add_argument(
        "--check",
        "-c",
        required=True,
        help="Comma-separated checks: parent, assignee, description",
    )
    parser.add_argument("--expected-parent", help="Expected parent key (for parent check)")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show actions needed")

    args = parser.parse_args()
    checks = [c.strip() for c in args.check.split(",")]

    valid_checks = {"parent", "assignee", "description"}
    invalid = set(checks) - valid_checks
    if invalid:
        parser.error(f"Invalid checks: {invalid}. Valid: {valid_checks}")

    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 2

    results = []
    all_pass = True

    if not args.json:
        print(f"{'=' * 60}")
        print(f"Post-Write Verification ({len(args.issues)} issue(s))")
        print(f"Checks: {', '.join(checks)}")
        print(f"{'=' * 60}")

    for issue_key in args.issues:
        try:
            result = verify_issue(api, issue_key, checks, args.expected_parent)
            results.append(result)

            if not args.json:
                passed = print_result(result, verbose=args.verbose)
                if not passed:
                    all_pass = False
            else:
                for check in result["checks"].values():
                    if check["status"] == "fail":
                        all_pass = False

        except IssueNotFoundError:
            results.append({"key": issue_key, "error": "Issue not found"})
            all_pass = False
            if not args.json:
                print(f"\n  \u274c {issue_key}: Issue not found")
        except APIError as e:
            results.append({"key": issue_key, "error": f"API error: {e.status_code}"})
            all_pass = False
            if not args.json:
                print(f"\n  \u274c {issue_key}: API error {e.status_code}")

    if args.json:
        print(json.dumps({"results": results, "all_pass": all_pass}, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'=' * 60}")
        status = "\u2705 ALL PASSED" if all_pass else "\u274c SOME FAILED"
        print(f"Result: {status}")
        if results:
            all_actions = []
            for r in results:
                all_actions.extend(r.get("actions_needed", []))
            if all_actions:
                print(f"HR6 Actions: {', '.join(all_actions)}")
        print(f"{'=' * 60}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
