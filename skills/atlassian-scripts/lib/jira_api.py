"""Jira REST API v3 client for ADF description manipulation.

This module provides a class-based API client for Jira operations:
- Get issue with ADF description
- Search issues via JQL
- Get board sprints (Agile API)
- Update issue description (preserving ADF formatting)
- Walk and replace text in ADF tree

Uses REST API v3 which returns/accepts ADF (Atlassian Document Format),
preserving all formatting (panels, tables, marks, etc.)

Usage:
    from lib.jira_api import JiraAPI, derive_jira_url
    from lib.auth import create_ssl_context, load_credentials, get_auth_header

    creds = load_credentials()
    api = JiraAPI(
        base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context()
    )

    issue = api.get_issue("BEP-2819")
    description = issue["fields"]["description"]
    # ... modify ADF ...
    api.update_description("BEP-2819", modified_description)
"""

import json
import logging
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from typing import Any

from .exceptions import APIError, IssueNotFoundError

logger = logging.getLogger(__name__)

# Validate Jira issue key format (e.g., BEP-123, PROJ-1)
_ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{0,9}-\d{1,6}$")


def _validate_issue_key(issue_key: str) -> str:
    """Validate issue key format to prevent URL path injection.

    Args:
        issue_key: Key to validate (e.g., 'BEP-123')

    Returns:
        The validated issue key.

    Raises:
        ValueError: If key format is invalid.
    """
    if not isinstance(issue_key, str) or not _ISSUE_KEY_RE.match(issue_key):
        raise ValueError(f"Invalid issue key format: {issue_key!r}")
    return issue_key


def derive_jira_url(confluence_url: str) -> str:
    """Derive Jira base URL from Confluence URL.

    Strips '/wiki' suffix from Confluence URL to get the Atlassian site URL.

    Args:
        confluence_url: Confluence wiki URL (e.g., https://example.atlassian.net/wiki)

    Returns:
        Jira base URL (e.g., https://example.atlassian.net)
    """
    return confluence_url.rstrip("/").removesuffix("/wiki")


def walk_and_replace(node: Any, replacements: list[tuple[str, str]]) -> int:
    """Walk ADF tree and replace text in text nodes.

    Recursively traverses the ADF JSON structure, finding text nodes
    and applying find/replace operations.

    Args:
        node: ADF node (dict or list)
        replacements: List of (find, replace) tuples

    Returns:
        Number of text replacements made.
    """
    changes = 0
    if isinstance(node, dict):
        if node.get("type") == "text" and "text" in node:
            for old, new in replacements:
                if old in node["text"]:
                    node["text"] = node["text"].replace(old, new)
                    changes += 1
        for key in ("content", "attrs"):
            if key in node and isinstance(node[key], (list, dict)):
                changes += walk_and_replace(node[key], replacements)
    elif isinstance(node, list):
        for item in node:
            changes += walk_and_replace(item, replacements)
    return changes


class JiraAPI:
    """Jira REST API v3 client.

    Uses API v3 which works with ADF (Atlassian Document Format) for
    rich text fields like description. This preserves all formatting
    including panels, tables, marks, code blocks, etc.

    Attributes:
        base_url: Jira site URL (e.g., https://example.atlassian.net)
        auth_header: Authorization header value (Basic auth)
        ssl_context: SSL context for HTTPS requests
    """

    def __init__(
        self,
        base_url: str,
        auth_header: str,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_header = auth_header
        self.ssl_context = ssl_context
        logger.debug("JiraAPI initialized for %s", self.base_url)

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the Jira API.

        Args:
            method: HTTP method (GET, PUT, POST)
            endpoint: API endpoint path
            data: Request body data (will be JSON encoded)

        Returns:
            Parsed JSON response, or {"_status": code} for empty responses.

        Raises:
            IssueNotFoundError: If issue not found (404)
            APIError: If API request fails
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("%s %s", method, url)

        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", self.auth_header)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        if data is not None:
            req.data = json.dumps(data).encode("utf-8")

        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                if body:
                    return json.loads(body)
                return {"_status": resp.status}

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.debug("API error body: %s", error_body[:200])

            if e.code == 404:
                raise IssueNotFoundError("unknown", f"Resource not found: {endpoint}") from e

            raise APIError(e.code, e.reason, error_body) from e

        except urllib.error.URLError as e:
            logger.error("URL error: %s", e.reason)
            raise APIError(0, str(e.reason), "") from e

    def get_issue(
        self,
        issue_key: str,
        fields: str = "description,summary",
    ) -> dict[str, Any]:
        """Get Jira issue with ADF description via REST API v3.

        Args:
            issue_key: Jira issue key (e.g., 'BEP-2819')
            fields: Comma-separated field names to return

        Returns:
            Issue data including fields with ADF description.

        Raises:
            IssueNotFoundError: If issue key doesn't exist
            APIError: If API request fails
        """
        _validate_issue_key(issue_key)
        logger.info("Getting issue %s", issue_key)
        safe_fields = urllib.parse.quote(fields, safe=",")

        try:
            return self._request("GET", f"/rest/api/3/issue/{issue_key}?fields={safe_fields}")
        except IssueNotFoundError:
            raise IssueNotFoundError(issue_key) from None

    def search_issues(
        self,
        jql: str,
        fields: str = "summary,status",
        max_results: int = 50,
        start_at: int = 0,
    ) -> dict[str, Any]:
        """Search Jira issues via JQL.

        Args:
            jql: JQL query string (e.g., 'sprint = 123 AND status != Done')
            fields: Comma-separated field names to return
            max_results: Maximum results per page (max 50)
            start_at: Pagination offset

        Returns:
            Search results with issues list, total count, and pagination info.

        Raises:
            APIError: If search fails (e.g., invalid JQL)
        """
        logger.info("Searching issues: %s", jql[:80])

        params = urllib.parse.urlencode(
            {
                "jql": jql,
                "fields": fields,
                "maxResults": min(max_results, 50),
                "startAt": start_at,
            }
        )
        return self._request("GET", f"/rest/api/3/search/jql?{params}")

    def get_board_sprints(
        self,
        board_id: int,
        state: str = "active,future",
    ) -> dict[str, Any]:
        """Get sprints for a board via Agile REST API.

        Args:
            board_id: Jira board ID
            state: Sprint state filter (active, future, closed)

        Returns:
            Sprint list with id, name, state, dates, goal.

        Raises:
            APIError: If board not found or API fails
        """
        logger.info("Getting sprints for board %d (state=%s)", board_id, state)

        params = urllib.parse.urlencode({"state": state})
        return self._request("GET", f"/rest/agile/1.0/board/{board_id}/sprint?{params}")

    def get_sprint_issues(
        self,
        sprint_id: int,
        fields: str = "summary,status,assignee",
        max_results: int = 50,
        start_at: int = 0,
    ) -> dict[str, Any]:
        """Get issues in a sprint via Agile REST API.

        Args:
            sprint_id: Jira sprint ID (e.g., 123)
            fields: Comma-separated field names
            max_results: Maximum results per page (max 50)
            start_at: Pagination offset

        Returns:
            Sprint issues with pagination info.

        Raises:
            APIError: If sprint not found or API fails
        """
        logger.info("Getting issues for sprint %d", sprint_id)

        params = urllib.parse.urlencode(
            {
                "fields": fields,
                "maxResults": min(max_results, 50),
                "startAt": start_at,
            }
        )
        return self._request("GET", f"/rest/agile/1.0/sprint/{sprint_id}/issue?{params}")

    def update_description(
        self,
        issue_key: str,
        description_adf: dict[str, Any],
    ) -> int:
        """Update issue description with ADF via REST API v3.

        Args:
            issue_key: Jira issue key (e.g., 'BEP-2819')
            description_adf: ADF document for the new description

        Returns:
            HTTP status code (204 = success).

        Raises:
            IssueNotFoundError: If issue key doesn't exist
            APIError: If API request fails
        """
        _validate_issue_key(issue_key)
        logger.info("Updating description for %s", issue_key)

        result = self._request(
            "PUT",
            f"/rest/api/3/issue/{issue_key}",
            {"fields": {"description": description_adf}},
        )
        status = result.get("_status", 200)
        logger.info("Updated %s (HTTP %d)", issue_key, status)
        return status

    def create_issue(
        self,
        project_key: str,
        issue_type: str,
        summary: str,
        parent_key: str | None = None,
        additional_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new Jira issue via REST API v3.

        Args:
            project_key: Project key (e.g., 'BEP')
            issue_type: Issue type name (e.g., 'Story', 'Task', 'Subtask', 'Epic')
            summary: Issue summary/title
            parent_key: Parent issue key for subtasks (e.g., 'BEP-1200')
            additional_fields: Extra fields to set on creation

        Returns:
            Created issue data with 'key', 'id', 'self' fields.

        Raises:
            APIError: If creation fails
        """
        logger.info("Creating %s in %s: %s", issue_type, project_key, summary[:60])

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary,
        }
        if parent_key:
            fields["parent"] = {"key": parent_key}
        if additional_fields:
            fields.update(additional_fields)

        return self._request("POST", "/rest/api/3/issue", {"fields": fields})

    def update_fields(
        self,
        issue_key: str,
        fields: dict[str, Any],
    ) -> int:
        """Update arbitrary fields on a Jira issue via REST API v3.

        Args:
            issue_key: Jira issue key (e.g., 'BEP-2819')
            fields: Dictionary of field IDs to values

        Returns:
            HTTP status code (204 = success).

        Raises:
            IssueNotFoundError: If issue key doesn't exist
            APIError: If API request fails
        """
        _validate_issue_key(issue_key)
        logger.info("Updating fields for %s: %s", issue_key, list(fields.keys()))

        result = self._request(
            "PUT",
            f"/rest/api/3/issue/{issue_key}",
            {"fields": fields},
        )
        status = result.get("_status", 200)
        logger.info("Updated %s (HTTP %d)", issue_key, status)
        return status

    def rank_issues(
        self,
        issue_keys: list[str],
        rank_after_key: str | None = None,
        rank_before_key: str | None = None,
    ) -> int:
        """Rank issues in the backlog via Agile REST API.

        Args:
            issue_keys: List of issue keys to rank (in order)
            rank_after_key: Rank these issues after this key
            rank_before_key: Rank these issues before this key

        Returns:
            HTTP status code (204 = success).

        Raises:
            APIError: If ranking fails
        """
        logger.info("Ranking %d issues", len(issue_keys))

        body: dict[str, Any] = {"issues": issue_keys}
        if rank_after_key:
            body["rankAfterIssue"] = rank_after_key
        elif rank_before_key:
            body["rankBeforeIssue"] = rank_before_key

        result = self._request("PUT", "/rest/agile/1.0/issue/rank", body)
        status = result.get("_status", 200)
        logger.info("Ranked %d issues (HTTP %d)", len(issue_keys), status)
        return status

    def fix_description(
        self,
        issue_key: str,
        replacements: list[tuple[str, str]],
        dry_run: bool = False,
    ) -> tuple[bool, int]:
        """Fix issue description by replacing text in ADF nodes.

        High-level convenience method that:
        1. Gets the issue's ADF description
        2. Deep copies and applies text replacements
        3. Updates the issue (unless dry_run)

        Args:
            issue_key: Jira issue key
            replacements: List of (find, replace) tuples
            dry_run: If True, only check for matches without updating

        Returns:
            Tuple of (had_changes, change_count)
        """
        issue = self.get_issue(issue_key)
        summary = issue["fields"]["summary"]
        description = issue["fields"].get("description")

        logger.info("Processing %s: %s", issue_key, summary)

        if not description:
            logger.warning("%s has no description", issue_key)
            return False, 0

        modified = deepcopy(description)
        change_count = walk_and_replace(modified, replacements)

        if change_count == 0:
            logger.info("%s: no matches found", issue_key)
            return False, 0

        logger.info("%s: found %d replacement(s)", issue_key, change_count)

        if dry_run:
            logger.info("%s: DRY RUN - no changes applied", issue_key)
            return True, change_count

        status = self.update_description(issue_key, modified)
        if status in (200, 204):
            logger.info("%s: updated successfully", issue_key)
            return True, change_count

        logger.error("%s: update failed (HTTP %d)", issue_key, status)
        return False, change_count
