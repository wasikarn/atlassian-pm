"""Shared pytest fixtures for integration tests.

Provides mock infrastructure for:
- MCP server (jira_*, confluence_* tools)
- acli CLI (subprocess mocking)
- Hook execution context
- Cache invalidation tracking
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Path Setup ────────────────────────────────────────────────────────────────

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "mcp-servers" / "atlassian-cache"))


# ── Jira Issue Fixtures ────────────────────────────────────────────────────────


def make_jira_issue(
    key: str = "TP-100",
    summary: str = "Test Issue",
    status: str = "To Do",
    issue_type: str = "Task",
    priority: str = "Medium",
    assignee: str | None = "Test User",
    parent_key: str | None = None,
    description: dict | None = None,
    sprint_id: int | None = None,
    labels: list[str] | None = None,
    custom_fields: dict[str, Any] | None = None,
) -> dict:
    """Build a realistic Jira issue dict for testing.

    Matches the structure returned by jira_get_issue MCP tool.
    """
    fields = {
        "summary": summary,
        "status": {"name": status, "id": "1", "statusCategory": {"name": "To Do"}},
        "issuetype": {
            "name": issue_type,
            "id": "10001",
            "subtask": issue_type in ("Sub-task", "Subtask"),
        },
        "priority": {"name": priority, "id": "3"},
        "labels": labels or [],
        "description": description,
        "created": "2026-01-01T00:00:00.000+0000",
        "updated": "2026-01-01T00:00:00.000+0000",
    }

    if assignee:
        fields["assignee"] = {
            "displayName": assignee,
            "accountId": "abc123",
            "emailAddress": f"{assignee.lower().replace(' ', '.')}@test.com",
            "active": True,
        }
    else:
        fields["assignee"] = None

    if parent_key:
        fields["parent"] = {"key": parent_key}

    if sprint_id:
        fields["customfield_10020"] = [{"id": sprint_id, "name": f"Sprint {sprint_id}"}]

    if custom_fields:
        fields.update(custom_fields)

    return {
        "key": key,
        "id": "10001",
        "self": f"https://{{JIRA_SITE}}/rest/api/2/issue/{key}",
        "fields": fields,
    }


def make_adf_description(
    paragraphs: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
) -> dict:
    """Build an ADF description for testing.

    Args:
        paragraphs: List of paragraph texts
        acceptance_criteria: List of AC items (creates AC table)

    Returns:
        ADF document dict
    """
    content = []

    for text in paragraphs or []:
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": text}],
        })

    if acceptance_criteria:
        ac_rows = [
            {
                "type": "tableRow",
                "content": [
                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC"}]}]},
                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status"}]}]},
                ],
            },
        ]
        for ac in acceptance_criteria:
            ac_rows.append({
                "type": "tableRow",
                "content": [
                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": ac}]}]},
                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "TODO"}]}]},
                ],
            })
        content.append({"type": "table", "content": ac_rows})

    return {"version": 1, "type": "doc", "content": content}


# ── Confluence Page Fixtures ──────────────────────────────────────────────────


def make_confluence_page(
    page_id: str = "12345",
    title: str = "Test Page",
    space_key: str = "TEST",
    content: str = "## Overview\n\nTest content.",
    version: int = 1,
    labels: list[str] | None = None,
) -> dict:
    """Build a Confluence page dict for testing.

    Matches the structure returned by confluence_get_page MCP tool.
    """
    return {
        "id": page_id,
        "title": title,
        "space": {"key": space_key, "name": f"{space_key} Space"},
        "body": {
            "storage": {
                "value": content,
                "representation": "storage",
            },
        },
        "version": {"number": version, "when": "2026-01-01T00:00:00.000Z"},
        "metadata": {
            "labels": {
                "results": [{"name": label} for label in (labels or [])],
            },
        },
        "_links": {
            "webui": f"/wiki/spaces/{space_key}/pages/{page_id}",
        },
    }


# ── MCP Server Mock Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def mock_jira_mcp():
    """Mock Jira MCP server for integration tests.

    Tracks all calls and returns configurable responses.
    """
    calls: list[dict] = []
    issue_store: dict[str, dict] = {}  # Simulated Jira issue store

    def _make_response(tool_name: str, **kwargs):
        """Create a mock response for a Jira MCP tool."""
        call_record = {"tool": tool_name, "args": kwargs}
        calls.append(call_record)

        if tool_name == "jira_get_issue":
            key = kwargs.get("issue_key") or kwargs.get("issue_id")
            if key in issue_store:
                return {"issue": issue_store[key]}
            return {"error": f"Issue {key} not found"}

        if tool_name == "jira_create_issue":
            key = f"TP-{len(issue_store) + 100}"
            # Map MCP params to make_jira_issue params
            issue_params = {
                "summary": kwargs.get("summary", "New Issue"),
                "issue_type": kwargs.get("issue_type", "Task"),
                "status": kwargs.get("status", "To Do"),
                "priority": kwargs.get("priority", "Medium"),
                "description": kwargs.get("description"),
            }
            if kwargs.get("parent"):
                issue_params["parent_key"] = kwargs["parent"]["key"]
            issue = make_jira_issue(key=key, **issue_params)
            issue_store[key] = issue
            return {"issue": issue}

        if tool_name == "jira_update_issue":
            key = kwargs.get("issue_key")
            if key in issue_store:
                issue_store[key]["fields"].update(kwargs.get("fields", {}))
                return {"issue": issue_store[key]}
            return {"error": f"Issue {key} not found"}

        if tool_name == "jira_add_comment":
            key = kwargs.get("issue_key")
            return {"comment": {"id": "12345", "body": kwargs.get("comment", "")}}

        if tool_name == "jira_search":
            jql = kwargs.get("jql", "")
            issues = list(issue_store.values())
            return {"issues": issues, "total": len(issues)}

        if tool_name == "jira_get_agile_boards":
            return {"boards": [{"id": 108, "name": "TP Board", "type": "scrum"}]}

        if tool_name == "jira_get_sprints_from_board":
            return {"sprints": [{"id": 1000, "name": "Sprint 1", "state": "active"}]}

        return {}

    mock = MagicMock()
    mock.call = _make_response
    mock.calls = calls
    mock.issues = issue_store

    # Convenience methods
    mock.reset = lambda: (calls.clear(), issue_store.clear())
    mock.get_call_count = lambda tool: sum(1 for c in calls if c["tool"] == tool)

    return mock


@pytest.fixture
def mock_confluence_mcp():
    """Mock Confluence MCP server for integration tests.

    Tracks all calls and returns configurable responses.
    """
    calls: list[dict] = []
    page_store: dict[str, dict] = {}

    def _make_response(tool_name: str, **kwargs):
        """Create a mock response for a Confluence MCP tool."""
        call_record = {"tool": tool_name, "args": kwargs}
        calls.append(call_record)

        if tool_name == "confluence_get_page":
            page_id = kwargs.get("page_id")
            if page_id in page_store:
                return {"page": page_store[page_id]}
            return {"error": f"Page {page_id} not found"}

        if tool_name == "confluence_create_page":
            page_id = str(len(page_store) + 10000)
            page = make_confluence_page(
                page_id=page_id,
                title=kwargs.get("title", "New Page"),
                space_key=kwargs.get("space_key", "TEST"),
                content=kwargs.get("body", ""),
            )
            page_store[page_id] = page
            return {"page": page}

        if tool_name == "confluence_update_page":
            page_id = kwargs.get("page_id")
            if page_id in page_store:
                page_store[page_id].update(kwargs)
                return {"page": page_store[page_id]}
            return {"error": f"Page {page_id} not found"}

        if tool_name == "confluence_search":
            return {"results": list(page_store.values())}

        return {}

    mock = MagicMock()
    mock.call = _make_response
    mock.calls = calls
    mock.pages = page_store

    mock.reset = lambda: (calls.clear(), page_store.clear())
    mock.get_call_count = lambda tool: sum(1 for c in calls if c["tool"] == tool)

    return mock


# ── acli CLI Mock Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def mock_acli():
    """Mock acli CLI for integration tests.

    Intercepts subprocess calls and tracks acli commands.
    """
    calls: list[dict] = []

    def _run_acli(command: str, cwd: str | None = None) -> tuple[int, str, str]:
        """Simulate acli command execution.

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        call_record = {"command": command, "cwd": cwd}
        calls.append(call_record)

        # Parse command parts
        parts = command.split()
        if "workitem" in parts and "create" in parts:
            # Simulate successful issue creation
            return 0, json.dumps({"key": "TP-100", "id": "10001"}), ""
        if "workitem" in parts and "edit" in parts:
            return 0, json.dumps({"key": "TP-100", "updated": True}), ""
        if "workitem" in parts and "assign" in parts:
            return 0, "Issue assigned successfully", ""
        if "--version" in parts or "version" in parts:
            return 0, "acli 1.0.0", ""

        return 0, "", ""

    mock = MagicMock()
    mock.run = _run_acli
    mock.calls = calls

    # Subprocess mock for integration tests
    def mock_subprocess_run(cmd_args, **kwargs):
        """Mock subprocess.run for acli commands."""
        if "acli" in cmd_args[0] if isinstance(cmd_args, list) else "acli" in str(cmd_args):
            command = " ".join(cmd_args) if isinstance(cmd_args, list) else str(cmd_args)
            exit_code, stdout, stderr = _run_acli(command)
            result = MagicMock()
            result.returncode = exit_code
            result.stdout = stdout
            result.stderr = stderr
            return result
        # For non-acli commands, raise to indicate unexpected call
        raise RuntimeError(f"Unexpected subprocess call: {cmd_args}")

    mock.subprocess_run = mock_subprocess_run
    mock.reset = lambda: calls.clear()
    mock.get_call_count = lambda: len(calls)

    return mock


# ── Hook Execution Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def hook_context():
    """Create hook execution context for testing PreToolUse hooks.

    Provides utilities to simulate hook input/output.
    """
    class HookContext:
        def __init__(self):
            self.last_output: dict | None = None
            self.last_exit_code: int = 0

        def make_input(
            self,
            tool_name: str,
            tool_input: dict,
            session_id: str = "test-session",
            cwd: str = "/tmp",
        ) -> dict:
            """Create hook input JSON."""
            return {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "session_id": session_id,
                "cwd": cwd,
            }

        def run_hook(self, hook_module, input_data: dict) -> dict | None:
            """Execute a hook with given input.

            Args:
                hook_module: The imported hook module (e.g., pre_hr1_quality_gate)
                input_data: Hook input dict

            Returns:
                {} on allow (exit 0), None on block (exit 1/2)
            """
            buf = io.StringIO()
            with (
                patch("sys.stdin.read", return_value=json.dumps(input_data)),
                redirect_stdout(buf),
            ):
                try:
                    hook_module.main()
                    raw = buf.getvalue().strip()
                    self.last_exit_code = 0
                    return json.loads(raw) if raw else {}
                except SystemExit as e:
                    self.last_exit_code = e.code
                    if e.code == 0:
                        return {}
                    return None  # blocked

    return HookContext()


@pytest.fixture
def temp_adf_file(tmp_path):
    """Create a temporary ADF JSON file for testing.

    Returns a factory that creates files.
    """
    def create_adf_file(
        adf_data: dict,
        filename: str = "issue.json",
        issue_type: str = "Task",
    ) -> Path:
        """Create an ADF file and return its path."""
        file_path = tmp_path / filename
        with open(file_path, "w") as f:
            json.dump(adf_data, f)
        return file_path

    return create_adf_file


# ── Cache Mock Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def mock_cache():
    """Mock AtlassianCache for integration tests.

    Tracks cache invalidation calls.
    """
    invalidations: list[str] = []

    mock = MagicMock()
    mock.invalidate = lambda key: invalidations.append(key)
    mock.invalidations = invalidations
    mock.reset = lambda: invalidations.clear()
    mock.get_invalidation_count = lambda: len(invalidations)

    return mock


# ── Session State Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def session_state(tmp_path):
    """Mock session state for testing hooks that use state persistence.

    Provides a temporary directory for state files.
    """
    state_dir = tmp_path / "session_state"
    state_dir.mkdir(parents=True, exist_ok=True)

    class SessionState:
        def __init__(self, directory: Path):
            self.directory = directory
            self.state_files: dict[str, dict] = {}

        def get_state_file(self, name: str) -> Path:
            return self.directory / f"{name}.json"

        def set_state(self, name: str, data: dict):
            self.state_files[name] = data
            path = self.get_state_file(name)
            with open(path, "w") as f:
                json.dump(data, f)

        def get_state(self, name: str) -> dict | None:
            path = self.get_state_file(name)
            if path.exists():
                with open(path) as f:
                    return json.load(f)
            return self.state_files.get(name)

    return SessionState(state_dir)


# ── Project Config Fixture ─────────────────────────────────────────────────────


@pytest.fixture
def mock_project_config(tmp_path):
    """Create a mock project-config.json for testing.

    Returns default config and allows customization.
    """
    config_path = tmp_path / "project-config.json"

    def create_config(overrides: dict | None = None) -> Path:
        default_config = {
            "project": {
                "key": "TP",
                "board_id": 108,
                "sprint_field": "customfield_10020",
                "start_date_field": "customfield_10015",
            },
            "team": {
                "default_assignee": "team@company.com",
            },
            "vibe": {
                "qg_threshold": 90,
            },
            "services": {
                "jira": "{{JIRA_SITE}}",
                "confluence": "{{JIRA_SITE}}/wiki",
            },
        }
        if overrides:
            self._deep_merge(default_config, overrides)

        with open(config_path, "w") as f:
            json.dump(default_config, f)
        return config_path

    return create_config


# ── Utility Functions ──────────────────────────────────────────────────────────


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Deep merge overrides into base dict."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
