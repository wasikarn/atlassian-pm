"""Shared test fixtures for jira-cache-server tests."""

import sys
from pathlib import Path

import pytest

# Ensure jira_cache is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_issue(
    key: str = "BEP-100",
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
    """Create a JiraCache with a temporary database."""
    from jira_cache.cache import JiraCache

    c = JiraCache(db_path=tmp_db)
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
        key="BEP-200",
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
    return [make_issue(key=f"BEP-{i}", summary=f"Issue {i}", status="To Do") for i in range(1, 6)]
