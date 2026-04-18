#!/usr/bin/env python3
"""Estimate token costs for Jira/Confluence operations before execution.

Helps users understand token impact of planned operations:
- Compare full response vs fields param vs cache
- Estimate tokens for bulk operations
- Show savings percentage for optimization

Usage:
    # Estimate single issue fetch
    uv run scripts/api/estimate_tokens.py --operation get_issue --key TP-123

    # Compare with specific fields
    uv run scripts/api/estimate_tokens.py --operation get_issue --key TP-123 --fields "summary,status"

    # Estimate search operation
    uv run scripts/api/estimate_tokens.py --operation search --jql "project=TP" --limit 50

    # Estimate sprint issues
    uv run scripts/api/estimate_tokens.py --operation sprint --sprint-id 123

    # Compare cache vs MCP
    uv run scripts/api/estimate_tokens.py --compare

Exit codes:
    0 = success
    1 = API error
    2 = invalid arguments
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Token estimation constants
# GPT-4/Claude use ~4 chars per token on average
CHARS_PER_TOKEN = 4

# Typical response sizes (chars) based on empirical measurements
# Used when actual data not available
ESTIMATED_SIZES = {
    "issue_full": 8000,        # Full issue with all fields
    "issue_minimal": 500,     # Minimal fields (key, summary, status)
    "issue_standard": 2500,   # Standard fields (summary, status, assignee, etc.)
    "issue_with_description": 5000,  # Standard + description
    "search_result": 300,      # Single search result item
    "search_overhead": 200,    # Search response overhead
    "sprint_issue": 400,       # Sprint issue (minimal fields)
    "sprint_overhead": 300,    # Sprint response overhead
    "confluence_page_full": 15000,  # Full page with body.storage
    "confluence_page_metadata": 800,  # Page metadata only
    "cache_hit": 150,          # Cache lookup overhead
}

# Field presets for common operations
FIELD_PRESETS = {
    "minimal": "summary,status",
    "standard": "summary,status,assignee,issuetype,priority,labels",
    "full": "summary,status,assignee,issuetype,priority,labels,parent,description,created,updated,customfield_10015,customfield_10020",
}


def estimate_tokens(char_count: int) -> int:
    """Estimate tokens from character count."""
    return max(1, char_count // CHARS_PER_TOKEN)


def format_size(chars: int) -> str:
    """Format size in human-readable form."""
    tokens = estimate_tokens(chars)
    return f"~{chars:,} chars (~{tokens:,} tokens)"


def get_cached_size(issue_key: str) -> int | None:
    """Get cached issue size from SQLite cache if available.

    Returns None if cache doesn't exist or issue not cached.
    """
    cache_path = Path.home() / ".cache" / "atlassian-pm" / "atlassian.db"
    if not cache_path.exists():
        return None

    try:
        import sqlite3

        conn = sqlite3.connect(str(cache_path))
        cursor = conn.execute(
            "SELECT data FROM issues WHERE issue_key = ?",
            (issue_key,),
        )
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return len(row[0])
    except Exception:
        pass

    return None


def estimate_get_issue(
    api: JiraAPI,
    issue_key: str,
    fields: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Estimate token cost for jira_get_issue operation.

    Args:
        api: Jira API client
        issue_key: Issue key to fetch
        fields: Optional fields param to reduce response
        dry_run: If True, use estimates without API call

    Returns:
        Dict with estimation results
    """
    result = {
        "operation": "jira_get_issue",
        "issue_key": issue_key,
        "fields": fields,
        "full_response": None,
        "with_fields": None,
        "cache_hit": None,
        "savings": None,
    }

    if dry_run:
        # Use empirical estimates
        full_chars = ESTIMATED_SIZES["issue_full"]
        if fields:
            # Estimate based on number of fields
            field_count = len(fields.split(","))
            fields_chars = ESTIMATED_SIZES["issue_minimal"] + (field_count * 300)
        else:
            fields_chars = full_chars

        result["full_response"] = {
            "chars": full_chars,
            "tokens": estimate_tokens(full_chars),
            "source": "estimate",
        }
        result["with_fields"] = {
            "chars": fields_chars,
            "tokens": estimate_tokens(fields_chars),
            "source": "estimate",
        }
        result["cache_hit"] = {
            "chars": ESTIMATED_SIZES["cache_hit"],
            "tokens": estimate_tokens(ESTIMATED_SIZES["cache_hit"]),
            "source": "estimate",
        }
        result["savings"] = {
            "fields_vs_full": round((1 - fields_chars / full_chars) * 100, 1),
            "cache_vs_full": round((1 - ESTIMATED_SIZES["cache_hit"] / full_chars) * 100, 1),
        }
        return result

    # Fetch actual data
    try:
        # Full response (no fields param)
        full_data = api.get_issue(issue_key, fields="*all")
        full_chars = len(json.dumps(full_data))

        result["full_response"] = {
            "chars": full_chars,
            "tokens": estimate_tokens(full_chars),
            "source": "actual",
        }

        # With fields param
        if fields:
            fields_data = api.get_issue(issue_key, fields=fields)
            fields_chars = len(json.dumps(fields_data))
        else:
            fields_chars = full_chars

        result["with_fields"] = {
            "chars": fields_chars,
            "tokens": estimate_tokens(fields_chars),
            "source": "actual",
        }

        # Check cache
        cached_size = get_cached_size(issue_key)
        if cached_size:
            result["cache_hit"] = {
                "chars": cached_size,
                "tokens": estimate_tokens(cached_size),
                "source": "cache",
            }
        else:
            result["cache_hit"] = {
                "chars": ESTIMATED_SIZES["cache_hit"],
                "tokens": estimate_tokens(ESTIMATED_SIZES["cache_hit"]),
                "source": "estimate",
            }

        result["savings"] = {
            "fields_vs_full": round((1 - fields_chars / full_chars) * 100, 1),
            "cache_vs_full": round((1 - (cached_size or ESTIMATED_SIZES["cache_hit"]) / full_chars) * 100, 1),
        }

    except Exception as e:
        result["error"] = str(e)

    return result


def estimate_search(
    api: JiraAPI,
    jql: str,
    limit: int = 50,
    fields: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Estimate token cost for jira_search operation.

    Args:
        api: Jira API client
        jql: JQL query
        limit: Max results
        fields: Optional fields param
        dry_run: If True, use estimates

    Returns:
        Dict with estimation results
    """
    result = {
        "operation": "jira_search",
        "jql": jql,
        "limit": limit,
        "fields": fields,
        "full_response": None,
        "with_fields": None,
        "savings": None,
    }

    if dry_run:
        # Estimate based on limit
        full_chars = ESTIMATED_SIZES["search_overhead"] + (ESTIMATED_SIZES["search_result"] * limit * 3)
        if fields:
            field_count = len(fields.split(","))
            fields_chars = int(ESTIMATED_SIZES["search_overhead"] + (ESTIMATED_SIZES["search_result"] * limit * field_count * 0.5))
        else:
            fields_chars = full_chars

        result["full_response"] = {
            "chars": full_chars,
            "tokens": estimate_tokens(int(full_chars)),
            "source": "estimate",
        }
        result["with_fields"] = {
            "chars": fields_chars,
            "tokens": estimate_tokens(int(fields_chars)),
            "source": "estimate",
        }
        result["savings"] = {
            "fields_vs_full": round((1 - fields_chars / full_chars) * 100, 1) if fields else 0,
        }
        return result

    try:
        # Full response
        full_data = api.search_issues(jql, fields="*all", max_results=min(limit, 50))
        full_chars = len(json.dumps(full_data))

        result["full_response"] = {
            "chars": full_chars,
            "tokens": estimate_tokens(full_chars),
            "source": "actual",
        }

        # With fields
        if fields:
            fields_data = api.search_issues(jql, fields=fields, max_results=min(limit, 50))
            fields_chars = len(json.dumps(fields_data))
        else:
            fields_chars = full_chars

        result["with_fields"] = {
            "chars": fields_chars,
            "tokens": estimate_tokens(fields_chars),
            "source": "actual",
        }

        result["savings"] = {
            "fields_vs_full": round((1 - fields_chars / full_chars) * 100, 1) if fields else 0,
        }

    except Exception as e:
        result["error"] = str(e)

    return result


def estimate_sprint_issues(
    api: JiraAPI,
    sprint_id: int,
    fields: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Estimate token cost for jira_get_sprint_issues operation.

    Args:
        api: Jira API client
        sprint_id: Sprint ID
        fields: Optional fields param
        dry_run: If True, use estimates

    Returns:
        Dict with estimation results
    """
    result = {
        "operation": "jira_get_sprint_issues",
        "sprint_id": sprint_id,
        "fields": fields,
        "full_response": None,
        "with_fields": None,
        "cache_hit": None,
        "savings": None,
    }

    if dry_run:
        # Assume ~15 issues per sprint on average
        issue_count = 15
        full_chars = ESTIMATED_SIZES["sprint_overhead"] + (ESTIMATED_SIZES["sprint_issue"] * issue_count * 4)
        if fields:
            field_count = len(fields.split(","))
            fields_chars = int(ESTIMATED_SIZES["sprint_overhead"] + (ESTIMATED_SIZES["sprint_issue"] * issue_count * field_count * 0.3))
        else:
            fields_chars = full_chars

        result["full_response"] = {
            "chars": full_chars,
            "tokens": estimate_tokens(int(full_chars)),
            "source": "estimate",
        }
        result["with_fields"] = {
            "chars": fields_chars,
            "tokens": estimate_tokens(int(fields_chars)),
            "source": "estimate",
        }
        result["cache_hit"] = {
            "chars": ESTIMATED_SIZES["cache_hit"],
            "tokens": estimate_tokens(ESTIMATED_SIZES["cache_hit"]),
            "source": "estimate",
        }
        result["savings"] = {
            "fields_vs_full": round((1 - fields_chars / full_chars) * 100, 1) if fields else 0,
            "cache_vs_full": round((1 - ESTIMATED_SIZES["cache_hit"] / full_chars) * 100, 1),
        }
        return result

    try:
        # Full response
        full_data = api.get_sprint_issues(sprint_id, fields="*all")
        full_chars = len(json.dumps(full_data))
        issue_count = len(full_data.get("issues", []))

        result["full_response"] = {
            "chars": full_chars,
            "tokens": estimate_tokens(full_chars),
            "issue_count": issue_count,
            "source": "actual",
        }

        # With fields
        if fields:
            fields_data = api.get_sprint_issues(sprint_id, fields=fields)
            fields_chars = len(json.dumps(fields_data))
        else:
            fields_chars = full_chars

        result["with_fields"] = {
            "chars": fields_chars,
            "tokens": estimate_tokens(fields_chars),
            "source": "actual",
        }

        # Cache savings (per issue)
        result["cache_hit"] = {
            "chars": ESTIMATED_SIZES["cache_hit"] * issue_count,
            "tokens": estimate_tokens(ESTIMATED_SIZES["cache_hit"] * issue_count),
            "source": "estimate",
        }

        result["savings"] = {
            "fields_vs_full": round((1 - fields_chars / full_chars) * 100, 1) if fields else 0,
            "cache_vs_full": round((1 - (ESTIMATED_SIZES["cache_hit"] * issue_count) / full_chars) * 100, 1),
        }

    except Exception as e:
        result["error"] = str(e)

    return result


def estimate_confluence_page(
    api: JiraAPI,
    page_id: str,
    with_content: bool = True,
    dry_run: bool = False,
) -> dict:
    """Estimate token cost for confluence_get_page operation.

    Args:
        api: Jira API client (has Confluence methods)
        page_id: Confluence page ID
        with_content: Include body.storage
        dry_run: If True, use estimates

    Returns:
        Dict with estimation results
    """
    result = {
        "operation": "confluence_get_page",
        "page_id": page_id,
        "with_content": with_content,
        "full_response": None,
        "metadata_only": None,
        "savings": None,
    }

    if dry_run:
        full_chars = ESTIMATED_SIZES["confluence_page_full"] if with_content else ESTIMATED_SIZES["confluence_page_metadata"]
        meta_chars = ESTIMATED_SIZES["confluence_page_metadata"]

        result["full_response"] = {
            "chars": full_chars,
            "tokens": estimate_tokens(full_chars),
            "source": "estimate",
        }
        result["metadata_only"] = {
            "chars": meta_chars,
            "tokens": estimate_tokens(meta_chars),
            "source": "estimate",
        }
        result["savings"] = {
            "metadata_vs_full": round((1 - meta_chars / full_chars) * 100, 1),
        }
        return result

    try:
        # Full response with content
        if with_content:
            full_data = api.get_confluence_page(page_id)
            full_chars = len(json.dumps(full_data))
        else:
            full_chars = ESTIMATED_SIZES["confluence_page_full"]

        result["full_response"] = {
            "chars": full_chars,
            "tokens": estimate_tokens(full_chars),
            "source": "actual",
        }

        # Metadata only
        meta_data = api.get_confluence_page(page_id, expand="version,space")
        meta_chars = len(json.dumps(meta_data))

        result["metadata_only"] = {
            "chars": meta_chars,
            "tokens": estimate_tokens(meta_chars),
            "source": "actual",
        }

        result["savings"] = {
            "metadata_vs_full": round((1 - meta_chars / full_chars) * 100, 1),
        }

    except Exception as e:
        result["error"] = str(e)

    return result


def print_comparison(result: dict) -> None:
    """Print human-readable comparison table."""
    print(f"\n{'=' * 70}")
    print(f"Operation: {result['operation']}")
    if "issue_key" in result:
        print(f"Issue: {result['issue_key']}")
    if "jql" in result:
        print(f"JQL: {result['jql'][:50]}{'...' if len(result.get('jql', '')) > 50 else ''}")
        print(f"Limit: {result.get('limit', 50)}")
    if "sprint_id" in result:
        print(f"Sprint ID: {result['sprint_id']}")
    if "page_id" in result:
        print(f"Page ID: {result['page_id']}")
    print(f"{'=' * 70}")

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return

    # Full response
    if result.get("full_response"):
        fr = result["full_response"]
        extra = f" ({fr.get('issue_count', '')} issues)" if "issue_count" in fr else ""
        print(f"  Full response:    {format_size(fr['chars'])}{extra}")

    # With fields
    if result.get("with_fields") and result.get("fields"):
        wf = result["with_fields"]
        print(f"  With fields param: {format_size(wf['chars'])} (fields: {result['fields']})")

    # Metadata only (for Confluence)
    if result.get("metadata_only"):
        mo = result["metadata_only"]
        print(f"  Metadata only:     {format_size(mo['chars'])}")

    # Cache hit
    if result.get("cache_hit"):
        ch = result["cache_hit"]
        print(f"  Cache hit:         {format_size(ch['chars'])} (source: {ch['source']})")

    # Savings
    if result.get("savings"):
        print("\n  Savings:")
        if "fields_vs_full" in result["savings"]:
            pct = result["savings"]["fields_vs_full"]
            print(f"    fields param:    {pct}% reduction")
        if "cache_vs_full" in result["savings"]:
            pct = result["savings"]["cache_vs_full"]
            print(f"    cache vs full:   {pct}% reduction")
        if "metadata_vs_full" in result["savings"]:
            pct = result["savings"]["metadata_vs_full"]
            print(f"    metadata only:   {pct}% reduction")

    print(f"{'=' * 70}\n")


def print_compare_table() -> None:
    """Print comparison table of all operations."""
    print(f"\n{'=' * 80}")
    print("Token Cost Comparison: MCP vs Fields vs Cache")
    print(f"{'=' * 80}")
    print(f"\n{'Operation':<30} {'Full MCP':<15} {'With Fields':<15} {'Cache Hit':<15} {'Savings':<10}")
    print(f"{'-' * 80}")

    # Issue fetch
    print(f"{'jira_get_issue':<30} ", end="")
    print(f"{format_size(ESTIMATED_SIZES['issue_full']):<15} ", end="")
    print(f"{format_size(ESTIMATED_SIZES['issue_standard']):<15} ", end="")
    print(f"{format_size(ESTIMATED_SIZES['cache_hit']):<15} ", end="")
    full = ESTIMATED_SIZES['issue_full']
    fields = ESTIMATED_SIZES['issue_standard']
    cache = ESTIMATED_SIZES['cache_hit']
    print(f"~{round((1 - fields/full)*100)}% / ~{round((1-cache/full)*100)}%")

    # Search (10 results)
    search_full = ESTIMATED_SIZES['search_overhead'] + 10 * ESTIMATED_SIZES['search_result'] * 3
    search_fields = ESTIMATED_SIZES['search_overhead'] + 10 * ESTIMATED_SIZES['search_result']
    print(f"{'jira_search (n=10)':<30} ", end="")
    print(f"{format_size(search_full):<15} ", end="")
    print(f"{format_size(search_fields):<15} ", end="")
    print(f"{'N/A':<15} ", end="")
    print(f"~{round((1 - search_fields/search_full)*100)}%")

    # Sprint issues (15 issues)
    sprint_full = ESTIMATED_SIZES['sprint_overhead'] + 15 * ESTIMATED_SIZES['sprint_issue'] * 4
    sprint_fields = ESTIMATED_SIZES['sprint_overhead'] + 15 * ESTIMATED_SIZES['sprint_issue']
    sprint_cache = 15 * ESTIMATED_SIZES['cache_hit']
    print(f"{'jira_get_sprint_issues (n=15)':<30} ", end="")
    print(f"{format_size(sprint_full):<15} ", end="")
    print(f"{format_size(sprint_fields):<15} ", end="")
    print(f"{format_size(sprint_cache):<15} ", end="")
    print(f"~{round((1 - sprint_fields/sprint_full)*100)}% / ~{round((1-sprint_cache/sprint_full)*100)}%")

    # Confluence page
    print(f"{'confluence_get_page':<30} ", end="")
    print(f"{format_size(ESTIMATED_SIZES['confluence_page_full']):<15} ", end="")
    print(f"{format_size(ESTIMATED_SIZES['confluence_page_metadata']):<15} ", end="")
    print(f"{'N/A':<15} ", end="")
    print(f"~{round((1 - ESTIMATED_SIZES['confluence_page_metadata']/ESTIMATED_SIZES['confluence_page_full'])*100)}%")

    print(f"{'=' * 80}")

    print("\nField Presets:")
    for name, fields in FIELD_PRESETS.items():
        print(f"  --fields {name:<10} → {fields}")

    print("\nRecommendations:")
    print("  1. Always use fields param to reduce token usage by 60-90%")
    print("  2. Use cache_get_issue for repeated reads (95%+ savings)")
    print("  3. For sprint planning: cache_sprint_issues > jira_get_sprint_issues")
    print("  4. For Confluence: omit body.storage unless you need content")
    print(f"{'=' * 80}\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Estimate token costs for Jira/Confluence operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Estimate issue fetch
  uv run scripts/api/estimate_tokens.py --operation get_issue --key TP-123

  # With fields comparison
  uv run scripts/api/estimate_tokens.py --operation get_issue --key TP-123 --fields standard

  # Search estimation
  uv run scripts/api/estimate_tokens.py --operation search --jql "project=TP" --limit 20

  # Sprint issues
  uv run scripts/api/estimate_tokens.py --operation sprint --sprint-id 123

  # Compare all operations (estimated)
  uv run scripts/api/estimate_tokens.py --compare

Operations: get_issue, search, sprint, confluence
Field presets: minimal, standard, full
        """,
    )

    parser.add_argument(
        "--operation", "-o",
        choices=["get_issue", "search", "sprint", "confluence"],
        help="Operation to estimate",
    )
    parser.add_argument(
        "--key", "-k",
        help="Issue key (for get_issue)",
    )
    parser.add_argument(
        "--jql", "-j",
        help="JQL query (for search)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="Max results (for search/sprint)",
    )
    parser.add_argument(
        "--sprint-id", "-s",
        type=int,
        help="Sprint ID (for sprint)",
    )
    parser.add_argument(
        "--page-id", "-p",
        help="Confluence page ID (for confluence)",
    )
    parser.add_argument(
        "--fields", "-f",
        help="Fields to fetch (comma-separated or preset: minimal/standard/full)",
    )
    parser.add_argument(
        "--compare", "-c",
        action="store_true",
        help="Show comparison table of all operations",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Use estimated sizes without API calls",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable",
    )

    args = parser.parse_args()

    # Show comparison table
    if args.compare:
        print_compare_table()
        return 0

    # Validate arguments
    if not args.operation:
        parser.error("Operation required (or use --compare)")

    # Resolve field preset
    fields = args.fields
    if fields and fields in FIELD_PRESETS:
        fields = FIELD_PRESETS[fields]

    # Load credentials and create API client
    try:
        creds = load_credentials()
        api = JiraAPI(
            base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
            auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
            ssl_context=create_ssl_context(),
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize API client: {e}")
        return 1

    # Execute estimation
    result = None

    if args.operation == "get_issue":
        if not args.key:
            parser.error("--key required for get_issue operation")
        result = estimate_get_issue(api, args.key, fields, args.dry_run)

    elif args.operation == "search":
        if not args.jql:
            parser.error("--jql required for search operation")
        result = estimate_search(api, args.jql, args.limit, fields, args.dry_run)

    elif args.operation == "sprint":
        if not args.sprint_id:
            parser.error("--sprint-id required for sprint operation")
        result = estimate_sprint_issues(api, args.sprint_id, fields, args.dry_run)

    elif args.operation == "confluence":
        if not args.page_id:
            parser.error("--page-id required for confluence operation")
        result = estimate_confluence_page(api, args.page_id, with_content=True, dry_run=args.dry_run)

    # Ensure result is valid
    if result is None:
        print("ERROR: No result from estimation")
        return 1

    # Output
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_comparison(result)

    return 0 if "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
