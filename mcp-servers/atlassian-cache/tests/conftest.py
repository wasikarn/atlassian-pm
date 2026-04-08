"""Shared test fixtures for atlassian-cache tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure atlassian_cache is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_issue(
    key: str = "TP-100",
    summary: str = "Test issue",
    status: str = "To Do",
    assignee: str = "Test User",
    issue_type: str = "Story",
    priority: str = "Medium",
    labels: list | None = None,
    parent_key: str | None = None,
    description: dict | None = None,
    sprint_id: int | None = None,
) -> dict:
    """Build a realistic Jira issue dict for testing."""
    fields = {
        "summary": summary,
        "status": {"name": status, "self": "https://jira/status/1", "statusCategory": {"name": "To Do"}},
        "assignee": {
            "displayName": assignee,
            "accountId": "abc123",
            "emailAddress": "test@test.com",
            "avatarUrls": {"48x48": "url"},
            "active": True,
            "timeZone": "UTC",
            "accountType": "atlassian",
        }
        if assignee
        else None,
        "issuetype": {
            "name": issue_type,
            "subtask": False,
            "hierarchyLevel": 0,
            "self": "https://jira/issuetype/1",
            "iconUrl": "url",
        },
        "priority": {"name": priority, "iconUrl": "url", "self": "https://jira/priority/1"},
        "labels": labels or [],
        "description": description,
    }
    if parent_key:
        fields["parent"] = {"key": parent_key, "self": f"https://jira/issue/{parent_key}"}
    if sprint_id:
        fields["customfield_10020"] = [{"id": sprint_id, "name": f"Sprint-{sprint_id}", "self": "url"}]

    return {
        "key": key,
        "id": "10001",
        "self": f"https://jira/issue/{key}",
        "expand": "operations,editmeta",
        "fields": fields,
    }


@pytest.fixture
def tmp_db(tmp_path):
    """Return a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def cache(tmp_db):
    """Create a AtlassianCache with a temporary database."""
    from atlassian_cache.cache import AtlassianCache

    c = AtlassianCache(db_path=tmp_db)
    yield c
    c.close()


@pytest.fixture
def sample_issue():
    """Return a sample Jira issue dict."""
    return make_issue()


@pytest.fixture
def sample_issue_with_noise():
    """Return an issue with many noise fields."""
    return make_issue(
        key="TEST-200",
        summary="Noisy issue",
        description={
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Description text here"}]}],
        },
    )


@pytest.fixture
def multiple_issues():
    """Return a list of issues for batch testing."""
    return [make_issue(key=f"TP-{i}", summary=f"Issue {i}", status="To Do") for i in range(1, 6)]


def make_page(
    page_id: str = "12345",
    title: str = "Test Page",
    space_key: str = "TEST",
    body_md: str = "## Overview\n\nPage content.",
    version_num: int = 1,
    labels: list | None = None,
    author: str = "Test Author",
) -> dict:
    """Build a minimal Confluence page dict for testing."""
    return {
        "id": page_id,
        "title": title,
        "space": {"key": space_key},
        "_body_md": body_md,   # pre-converted Markdown (would normally come from converter)
        "version": {"number": version_num, "when": "2026-01-01T00:00:00.000Z"},
        "metadata": {"labels": {"results": [{"name": l} for l in (labels or [])]}},
        "history": {"createdBy": {"displayName": author}},
        "_links": {"webui": f"/wiki/spaces/{space_key}/pages/{page_id}"},
    }


@pytest.fixture
def confluence_cache(cache):
    """Return a ConfluenceCache sharing the AtlassianCache connection."""
    from atlassian_cache.confluence_cache import ConfluenceCache
    return ConfluenceCache(cache.conn, cache._lock)


@pytest.fixture
def sample_page():
    return make_page()
