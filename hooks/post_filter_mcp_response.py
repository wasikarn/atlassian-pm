"""PostToolUse hook: filter Jira MCP response noise before Claude processes it.

Uses updatedMCPToolOutput to replace what Claude sees with a stripped-down
version that removes avatarUrls, iconUrls, self-links, and other structural
noise that consumes tokens without adding value.

Typical savings: 30-60% token reduction per Jira issue read.

Applies to: jira_get_issue, jira_search
Does NOT apply to: cache_get_issue (cache server already returns condensed data)

Exit 0 = always allow.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import log_event, parse_stdin, update_mcp_output

_HOOK = "mcp-response-filter"

# ── Noise field sets ────────────────────────────────────────────────────────

# Top-level keys to remove from issue dicts
_TOP_NOISE = {"expand", "self", "transitions", "changelog",
              "renderedFields", "names", "schema", "editmeta", "operations",
              "versionedRepresentations"}

# issue.fields keys to remove
_FIELD_NOISE = {"watches", "votes", "worklog", "editmeta",
                "operations", "versionedRepresentations", "timetracking",
                "aggregatetimespent", "timespent", "aggregatetimeoriginalestimate",
                "aggregatetimeestimate", "progress", "aggregateprogress"}

# Sub-keys to strip from person objects (assignee, reporter, creator)
_PERSON_KEEP = {"accountId", "displayName", "emailAddress"}

# Sub-keys to strip from statusCategory
_STATUS_CAT_KEEP = {"name", "key"}

# Sub-keys to strip from issuetype
_ISSUETYPE_NOISE = {"self", "iconUrl", "avatarId", "entityId",
                    "subTaskIssueTypes", "hierarchyLevel"}

# Sub-keys to strip from priority
_PRIORITY_KEEP = {"name", "id"}

# Sub-keys to strip from project
_PROJECT_NOISE = {"self", "avatarUrls", "projectTypeKey", "simplified",
                  "style", "isPrivate", "properties", "entityId",
                  "uuid", "projectCategory"}


# ── Cleaners ────────────────────────────────────────────────────────────────

def _clean_person(obj: object) -> object:
    if not isinstance(obj, dict):
        return obj
    return {k: v for k, v in obj.items() if k in _PERSON_KEEP}


def _clean_status(obj: object) -> object:
    if not isinstance(obj, dict):
        return obj
    result = {k: v for k, v in obj.items() if k not in {"self", "iconUrl"}}
    if isinstance(result.get("statusCategory"), dict):
        result["statusCategory"] = {
            k: v for k, v in result["statusCategory"].items()
            if k in _STATUS_CAT_KEEP
        }
    return result


def _clean_issuetype(obj: object) -> object:
    if not isinstance(obj, dict):
        return obj
    return {k: v for k, v in obj.items() if k not in _ISSUETYPE_NOISE}


def _clean_priority(obj: object) -> object:
    if not isinstance(obj, dict):
        return obj
    return {k: v for k, v in obj.items() if k in _PRIORITY_KEEP}


def _clean_project(obj: object) -> object:
    if not isinstance(obj, dict):
        return obj
    return {k: v for k, v in obj.items() if k not in _PROJECT_NOISE}


def _clean_fields(fields: dict) -> dict:
    result = {k: v for k, v in fields.items() if k not in _FIELD_NOISE}
    for person_field in ("assignee", "reporter", "creator"):
        if person_field in result:
            result[person_field] = _clean_person(result[person_field])
    if "status" in result:
        result["status"] = _clean_status(result["status"])
    if "issuetype" in result:
        result["issuetype"] = _clean_issuetype(result["issuetype"])
    if "priority" in result:
        result["priority"] = _clean_priority(result["priority"])
    if "project" in result:
        result["project"] = _clean_project(result["project"])
    return result


def _clean_issue(issue: object) -> object:
    if not isinstance(issue, dict):
        return issue
    result = {k: v for k, v in issue.items() if k not in _TOP_NOISE}
    if isinstance(result.get("fields"), dict):
        result["fields"] = _clean_fields(result["fields"])
    return result


def _size(obj: object) -> int:
    """Approximate byte size of serialised object."""
    return len(json.dumps(obj, separators=(",", ":")))


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    data = parse_stdin()
    if not data:
        print("{}")
        return

    tool_name  = data.get("tool_name", "")
    session_id = data.get("session_id", "")

    is_get    = tool_name.endswith("jira_get_issue")
    is_search = tool_name.endswith("jira_search")

    if not (is_get or is_search):
        print("{}")
        return

    raw_response = data.get("tool_response")
    if not raw_response:
        print("{}")
        return

    # Parse if string
    if isinstance(raw_response, str):
        try:
            response = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError):
            print("{}")
            return
    else:
        response = raw_response

    before = _size(response)

    if is_get and isinstance(response, dict):
        filtered = _clean_issue(response)
    elif is_search and isinstance(response, dict) and "issues" in response:
        filtered = {
            k: ([_clean_issue(i) for i in v] if k == "issues" else v)
            for k, v in response.items()
            if k not in {"expand", "warningMessages"}
        }
    else:
        print("{}")
        return

    after = _size(filtered)
    saved = before - after
    pct   = round(saved / before * 100) if before else 0

    if saved <= 0:
        print("{}")
        return

    log_event(_HOOK, "FILTERED", {
        "tool": tool_name,
        "before_bytes": before,
        "after_bytes": after,
        "saved_pct": pct,
        "session_id": session_id,
    })
    update_mcp_output(filtered, context=f"MCP response filtered: {pct}% noise removed ({saved:,} bytes saved).")


if __name__ == "__main__":
    main()
