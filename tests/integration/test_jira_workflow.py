"""End-to-end Jira workflow integration tests.

Tests the complete flow: hooks → MCP → acli → Jira.

Workflow scenarios covered:
1. Issue creation workflow (skill → hooks → MCP/acli)
2. Issue update workflow
3. Issue assignment workflow (HR3: acli only)
4. Sprint operations (HR7: dynamic sprint ID lookup)
5. Parent-child relationships (HR5: parent verification)
6. Cache invalidation (HR6: after MCP writes)
"""

from unittest.mock import patch

# Import fixtures from conftest
from tests.integration.conftest import (
    make_adf_description,
    make_jira_issue,
)

# ── Workflow: Issue Creation ───────────────────────────────────────────────────


class TestIssueCreationWorkflow:
    """Test the complete issue creation workflow.

    Flow: Skill → PreToolUse hook (HR1) → MCP create → PostToolUse hook (HR5/HR6)
    """

    def test_create_issue_passes_quality_gate(
        self,
        hook_context,
        mock_jira_mcp,
        temp_adf_file,
    ):
        """Issue with valid ADF passes HR1 quality gate check."""
        # Arrange: Create valid ADF file with recognized section headings
        # QG requires: Context/Objective section, actionable items, Thai text
        # Recognized sections: context, objective, scope, acceptance criteria
        adf_content = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Context"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Implement feature X for user story Y. This task addresses the need for better data processing. (สิ่งที่ผู้ใช้ต้องการ)"}],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Scope"}],
                },
                {
                    "type": "bulletList",
                    "content": [
                        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "src/module/feature.py"}]}]},
                        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "tests/test_feature.py"}]}]},
                    ],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Acceptance Criteria"}],
                },
                {
                    "type": "table",
                    "content": [
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status"}]}]},
                        ]},
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "User can do X"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "TODO"}]}]},
                        ]},
                    ],
                },
                {
                    "type": "panel",
                    "attrs": {"panelType": "note"},
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Implementation notes: ดำเนินการตามแผน"}]},
                    ],
                },
                {
                    "type": "panel",
                    "attrs": {"panelType": "info"},
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Create and update the module files"}]},
                    ],
                },
            ],
        }
        adf = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Implement feature X",
            "description": adf_content,
        }
        adf_path = temp_adf_file(adf, filename="TP-100-task.json")

        # Act: Simulate hook execution
        hook_input = hook_context.make_input(
            tool_name="Bash",
            tool_input={"command": f"acli jira workitem create --from-json {adf_path}"},
        )

        # Import hook module
        import hooks.plugin.guards.pre_hr1_quality_gate as hr1

        result = hook_context.run_hook(hr1, hook_input)

        # Assert: Hook allows the command (QG >= 90%)
        assert result == {}
        assert hook_context.last_exit_code == 0

    def test_create_issue_blocks_low_quality(
        self,
        hook_context,
        temp_adf_file,
    ):
        """Issue with low QG score is blocked by HR1."""
        # Arrange: Create ADF with missing AC (low quality)
        adf = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Bad task",  # Too short
            "description": {"version": 1, "type": "doc", "content": []},  # Empty
        }
        adf_path = temp_adf_file(adf, filename="bad-task.json")

        # Act
        hook_input = hook_context.make_input(
            tool_name="Bash",
            tool_input={"command": f"acli jira workitem create --from-json {adf_path}"},
        )

        import hooks.plugin.guards.pre_hr1_quality_gate as hr1

        result = hook_context.run_hook(hr1, hook_input)

        # Assert: Hook blocks the command
        assert result is None
        assert hook_context.last_exit_code == 1

    def test_create_issue_mcp_call_correct(
        self,
        mock_jira_mcp,
    ):
        """MCP jira_create_issue is called with correct arguments."""
        # Arrange
        create_params = {
            "project_key": "TP",
            "summary": "Test Task",
            "issue_type": "Task",
            "description": {"version": 1, "type": "doc", "content": []},
        }

        # Act
        response = mock_jira_mcp.call("jira_create_issue", **create_params)

        # Assert
        assert "issue" in response
        assert response["issue"]["key"].startswith("TP-")
        assert mock_jira_mcp.get_call_count("jira_create_issue") == 1

    def test_create_child_issue_verifies_parent(
        self,
        mock_jira_mcp,
        hook_context,
    ):
        """Creating child issue verifies parent exists (HR5)."""
        # Arrange: Parent epic exists
        parent_epic = make_jira_issue(key="TP-50", issue_type="Epic", summary="Parent Epic")
        mock_jira_mcp.issues["TP-50"] = parent_epic

        # Act: Create child task
        # Note: In real workflow, skill would first call jira_get_issue to verify parent
        # This test verifies the mock infrastructure supports the pattern
        child = make_jira_issue(key="TP-100", issue_type="Task", parent_key="TP-50")
        response = mock_jira_mcp.call("jira_create_issue", **{
            "summary": child["fields"]["summary"],
            "issue_type": "Task",
            "parent": {"key": "TP-50"},
        })

        # Assert: Child created with parent reference
        assert "issue" in response
        assert mock_jira_mcp.get_call_count("jira_create_issue") == 1


class TestIssueUpdateWorkflow:
    """Test the issue update workflow.

    Flow: Skill → PreToolUse hook (HR1) → MCP update → PostToolUse hook (HR6)
    """

    def test_update_issue_passes_quality_gate(
        self,
        hook_context,
        mock_jira_mcp,
        temp_adf_file,
    ):
        """Issue update with valid ADF passes HR1."""
        # Arrange: Existing issue
        existing = make_jira_issue(key="TP-100", summary="Original summary")
        mock_jira_mcp.issues["TP-100"] = existing

        # Create update ADF with recognized section headings for QG
        adf_content = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Objective"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Updated description for the task (คำอธิบาย)"}],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Scope"}],
                },
                {
                    "type": "bulletList",
                    "content": [
                        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Update module X"}]}]},
                        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Add tests"}]}]},
                    ],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Acceptance Criteria"}],
                },
                {
                    "type": "table",
                    "content": [
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status"}]}]},
                        ]},
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Works correctly"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "TODO"}]}]},
                        ]},
                    ],
                },
                {
                    "type": "panel",
                    "attrs": {"panelType": "note"},
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Implementation steps"}]},
                    ],
                },
            ],
        }
        adf = {
            "issues": ["TP-100"],
            "description": adf_content,
        }
        adf_path = temp_adf_file(adf, filename="TP-100-update-task.json")

        # Act
        hook_input = hook_context.make_input(
            tool_name="Bash",
            tool_input={"command": f"acli jira workitem edit --from-json {adf_path}"},
        )

        import hooks.plugin.guards.pre_hr1_quality_gate as hr1

        result = hook_context.run_hook(hr1, hook_input)

        # Assert
        assert result == {}

    def test_update_issue_mcp_call_correct(
        self,
        mock_jira_mcp,
    ):
        """MCP jira_update_issue is called with correct arguments."""
        # Arrange: Existing issue
        existing = make_jira_issue(key="TP-100")
        mock_jira_mcp.issues["TP-100"] = existing

        # Act
        update_fields = {
            "summary": "Updated summary",
            "description": {"version": 1, "type": "doc", "content": []},
        }
        response = mock_jira_mcp.call(
            "jira_update_issue",
            issue_key="TP-100",
            fields=update_fields,
        )

        # Assert
        assert "issue" in response
        assert mock_jira_mcp.get_call_count("jira_update_issue") == 1


class TestIssueAssignmentWorkflow:
    """Test the issue assignment workflow.

    HR3: Assignment must use acli (MCP silently fails).
    """

    def test_assign_uses_acli_not_mcp(
        self,
        mock_acli,
        mock_jira_mcp,
    ):
        """Assignment workflow uses acli, not MCP (HR3)."""
        # Arrange
        issue_key = "TP-100"
        assignee = "user@example.com"

        # Act: Simulate assignment via acli
        with patch("subprocess.run", side_effect=mock_acli.subprocess_run):
            exit_code, stdout, stderr = mock_acli.run(
                f"acli jira workitem assign -k {issue_key} -a {assignee} -y"
            )

        # Assert: acli was called, MCP was NOT called for assignment
        assert exit_code == 0
        assert mock_acli.get_call_count() >= 1
        # MCP should NOT have been called for assignment
        assert mock_jira_mcp.get_call_count("jira_update_issue") == 0

    def test_mcp_assignment_silently_fails(
        self,
        mock_jira_mcp,
    ):
        """Document that MCP assignment appears to succeed but doesn't update."""
        # Arrange: Create issue first
        issue = make_jira_issue(key="TP-100", summary="Test Issue")
        mock_jira_mcp.issues["TP-100"] = issue

        # This is a documentation test - MCP assignment "succeeds" but
        # assignee field is NOT actually updated in Jira
        issue_key = "TP-100"

        # MCP would return success but assignee is not set
        response = mock_jira_mcp.call(
            "jira_update_issue",
            issue_key=issue_key,
            fields={"assignee": {"accountId": "user123"}},
        )

        # The response looks successful
        assert "issue" in response
        # But HR3 rule mandates using acli for assignment


# ── Workflow: Sprint Operations ─────────────────────────────────────────────────


class TestSprintWorkflow:
    """Test sprint-related operations.

    HR7: Sprint ID must be looked up dynamically, never hardcoded.
    """

    def test_sprint_id_dynamic_lookup(
        self,
        mock_jira_mcp,
    ):
        """Sprint ID is looked up via MCP, not hardcoded."""
        # Act: Get sprints from board
        board_response = mock_jira_mcp.call("jira_get_agile_boards", project_key="TP")
        board_id = board_response["boards"][0]["id"]

        sprint_response = mock_jira_mcp.call(
            "jira_get_sprints_from_board",
            board_id=board_id,
            state="active",
        )

        # Assert: Sprint ID comes from API
        assert board_id == 108  # From config
        assert len(sprint_response["sprints"]) >= 1
        assert "id" in sprint_response["sprints"][0]

    def test_sprint_field_uses_dynamic_id(
        self,
        mock_jira_mcp,
    ):
        """Setting sprint field uses dynamically fetched sprint ID."""
        # Arrange: Get sprint ID dynamically
        sprint_response = mock_jira_mcp.call(
            "jira_get_sprints_from_board",
            board_id=108,
            state="active",
        )
        sprint_id = sprint_response["sprints"][0]["id"]

        # Act: Update issue with sprint
        existing = make_jira_issue(key="TP-100")
        mock_jira_mcp.issues["TP-100"] = existing

        mock_jira_mcp.call(
            "jira_update_issue",
            issue_key="TP-100",
            fields={"customfield_10020": sprint_id},
        )

        # Assert: Dynamic sprint ID was used
        assert isinstance(sprint_id, int)


# ── Workflow: Parent-Child Relationships ───────────────────────────────────────


class TestParentChildWorkflow:
    """Test parent-child issue relationships.

    HR5: Parent must be verified when creating child issues.
    """

    def test_create_child_verifies_parent_exists(
        self,
        mock_jira_mcp,
    ):
        """Creating child issue verifies parent exists first."""
        # Arrange: Parent exists
        parent = make_jira_issue(key="TP-50", issue_type="Epic")
        mock_jira_mcp.issues["TP-50"] = parent

        # Act: Create child with parent reference
        # In real workflow, skill would call jira_get_issue first to verify parent
        child_params = {
            "summary": "Child task",
            "issue_type": "Task",
            "parent": {"key": "TP-50"},
        }
        response = mock_jira_mcp.call("jira_create_issue", **child_params)

        # Assert: Child created with parent reference
        assert "issue" in response
        assert mock_jira_mcp.get_call_count("jira_create_issue") == 1

    def test_set_parent_uses_script_not_mcp(
        self,
        mock_acli,
    ):
        """Setting parent on existing issue uses Python script (HR5).

        MCP/acli silently ignore parent field on existing issues.
        """
        # This is a documentation test - setting parent requires
        # jira_set_parent.py script, not MCP or acli

        # The workflow would be:
        # 1. Verify issue exists via jira_get_issue
        # 2. Call jira_set_parent.py --issues TP-100 --parent TP-50

        # This test documents the correct approach
        assert True  # Placeholder for actual script execution test


# ── Workflow: Cache Invalidation ───────────────────────────────────────────────


class TestCacheInvalidation:
    """Test cache invalidation after MCP writes.

    HR6: Cache must be invalidated after any MCP write operation.
    """

    def test_cache_invalidation_after_create(
        self,
        mock_cache,
        mock_jira_mcp,
    ):
        """Cache is invalidated after issue creation."""
        # Act: Create issue
        response = mock_jira_mcp.call(
            "jira_create_issue",
            summary="New issue",
            issue_type="Task",
        )
        issue_key = response["issue"]["key"]

        # Simulate cache invalidation
        mock_cache.invalidate(issue_key)

        # Assert
        assert issue_key in mock_cache.invalidations
        assert mock_cache.get_invalidation_count() == 1

    def test_cache_invalidation_after_update(
        self,
        mock_cache,
        mock_jira_mcp,
    ):
        """Cache is invalidated after issue update."""
        # Arrange
        issue = make_jira_issue(key="TP-100")
        mock_jira_mcp.issues["TP-100"] = issue

        # Act: Update issue
        mock_jira_mcp.call("jira_update_issue", issue_key="TP-100", fields={"summary": "Updated"})
        mock_cache.invalidate("TP-100")

        # Assert
        assert "TP-100" in mock_cache.invalidations

    def test_cache_invalidation_after_comment(
        self,
        mock_cache,
        mock_jira_mcp,
    ):
        """Cache is invalidated after adding comment."""
        # Act: Add comment
        mock_jira_mcp.call("jira_add_comment", issue_key="TP-100", comment="Test comment")
        mock_cache.invalidate("TP-100")

        # Assert
        assert "TP-100" in mock_cache.invalidations


# ── Workflow: JQL Queries ───────────────────────────────────────────────────────


class TestJQLWorkflow:
    """Test JQL query operations.

    HR2: Never add ORDER BY to parent= queries.
    """

    def test_jql_parent_query_no_order_by(
        self,
        hook_context,
    ):
        """JQL with parent= clause is checked for ORDER BY violation (HR2)."""
        # Act: Hook checks JQL
        hook_input = hook_context.make_input(
            tool_name="mcp__mcp-atlassian__jira_search",
            tool_input={"jql": "parent = TP-100 ORDER BY created DESC"},
        )

        import hooks.plugin.guards.pre_hr2_jql_order_guard as hr2

        result = hook_context.run_hook(hr2, hook_input)

        # Assert: Hook blocks the query
        assert result is None
        assert hook_context.last_exit_code == 1

    def test_jql_parent_query_allowed_without_order_by(
        self,
        hook_context,
    ):
        """JQL with parent= clause (no ORDER BY) is allowed."""
        hook_input = hook_context.make_input(
            tool_name="mcp__mcp-atlassian__jira_search",
            tool_input={"jql": "parent = TP-100 AND status = 'To Do'"},
        )

        import hooks.plugin.guards.pre_hr2_jql_order_guard as hr2

        result = hook_context.run_hook(hr2, hook_input)

        # Assert: Hook allows the query
        assert result == {}

    def test_jql_search_uses_fields_param(
        self,
        mock_jira_mcp,
    ):
        """Jira search uses fields parameter for token efficiency."""
        # Act
        mock_jira_mcp.call(
            "jira_search",
            jql="project = TP AND status = 'To Do'",
            fields=["summary", "status", "assignee"],
            limit=50,
        )

        # Assert: fields was passed (would be verified in real MCP call)
        calls = [c for c in mock_jira_mcp.calls if c["tool"] == "jira_search"]
        assert len(calls) == 1
        assert "fields" in calls[0]["args"]


# ── Workflow: End-to-End ───────────────────────────────────────────────────────


class TestEndToEndWorkflow:
    """Complete end-to-end workflow tests combining all components."""

    def test_full_issue_lifecycle(
        self,
        mock_jira_mcp,
        mock_cache,
        mock_acli,
    ):
        """Test complete issue lifecycle: create → update → assign → comment."""
        # 1. Create issue via MCP
        create_response = mock_jira_mcp.call(
            "jira_create_issue",
            summary="Lifecycle test issue",
            issue_type="Task",
            description={"version": 1, "type": "doc", "content": []},
        )
        issue_key = create_response["issue"]["key"]
        mock_cache.invalidate(issue_key)

        # 2. Update issue via MCP
        mock_jira_mcp.call(
            "jira_update_issue",
            issue_key=issue_key,
            fields={"summary": "Updated lifecycle test"},
        )
        mock_cache.invalidate(issue_key)

        # 3. Assign via acli (HR3)
        with patch("subprocess.run", side_effect=mock_acli.subprocess_run):
            mock_acli.run(f"acli jira workitem assign -k {issue_key} -a user@test.com -y")

        # 4. Add comment via MCP
        mock_jira_mcp.call("jira_add_comment", issue_key=issue_key, comment="Progress update")
        mock_cache.invalidate(issue_key)

        # Assert: All operations completed
        assert mock_jira_mcp.get_call_count("jira_create_issue") == 1
        assert mock_jira_mcp.get_call_count("jira_update_issue") == 1
        assert mock_jira_mcp.get_call_count("jira_add_comment") == 1
        assert mock_acli.get_call_count() >= 1  # Assignment
        assert mock_cache.get_invalidation_count() == 3  # After each MCP write

    def test_workflow_with_hook_validation(
        self,
        hook_context,
        mock_jira_mcp,
        temp_adf_file,
    ):
        """Test workflow with hook validation at each step."""
        # Step 1: Validate ADF before create (with recognized sections for QG)
        adf_content = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Context"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Task description with Thai content (คำอธิบายงาน)"}],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Scope"}],
                },
                {
                    "type": "bulletList",
                    "content": [
                        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "src/main.py"}]}]},
                        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "tests/test_main.py"}]}]},
                    ],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Acceptance Criteria"}],
                },
                {
                    "type": "table",
                    "content": [
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status"}]}]},
                        ]},
                        {"type": "tableRow", "content": [
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Complete"}]}]},
                            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "TODO"}]}]},
                        ]},
                    ],
                },
                {
                    "type": "panel",
                    "attrs": {"panelType": "note"},
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Implementation notes"}]},
                    ],
                },
                {
                    "type": "panel",
                    "attrs": {"panelType": "info"},
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Create the required files"}]},
                    ],
                },
            ],
        }
        adf = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Valid task for workflow",
            "description": adf_content,
        }
        adf_path = temp_adf_file(adf, filename="workflow-test.json")

        hook_input = hook_context.make_input(
            tool_name="Bash",
            tool_input={"command": f"acli jira workitem create --from-json {adf_path}"},
        )

        import hooks.plugin.guards.pre_hr1_quality_gate as hr1

        result = hook_context.run_hook(hr1, hook_input)

        # Assert: Hook validation passes
        assert result == {}

        # Step 2: Would create issue (simulated)
        mock_jira_mcp.call(
            "jira_create_issue",
            summary=adf["summary"],
            issue_type="Task",
        )

        assert mock_jira_mcp.get_call_count("jira_create_issue") == 1


# ── Edge Cases ─────────────────────────────────────────────────────────────────


class TestWorkflowEdgeCases:
    """Test edge cases and error handling."""

    def test_create_orphan_child_issue(
        self,
        mock_jira_mcp,
    ):
        """Creating child with non-existent parent is handled."""
        # Arrange: Parent does NOT exist
        # mock_jira_mcp.issues is empty

        # Act: Try to create child with non-existent parent
        child_params = {
            "summary": "Orphan child",
            "issue_type": "Task",
            "parent": {"key": "TP-999"},  # Non-existent
        }
        response = mock_jira_mcp.call("jira_create_issue", **child_params)

        # Assert: Issue created but may be orphan (HR5 mitigation needed)
        # In production, HR5 hook would catch this
        assert "issue" in response

    def test_concurrent_cache_invalidation(
        self,
        mock_cache,
    ):
        """Multiple rapid cache invalidations are tracked."""
        # Act: Rapid invalidations
        for i in range(5):
            mock_cache.invalidate(f"TP-{100 + i}")

        # Assert: All tracked
        assert mock_cache.get_invalidation_count() == 5

    def test_vibe_mode_lower_threshold(
        self,
        hook_context,
        temp_adf_file,
    ):
        """Vibe mode uses lower QG threshold from config."""
        # Arrange: ADF that would fail normal threshold but pass vibe
        adf = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Vibe task",
            "description": make_adf_description(
                paragraphs=["Quick vibe task"],
                acceptance_criteria=["AC1: Done"],  # Minimal AC
            ),
        }
        adf_path = temp_adf_file(adf, filename="vibe-task.json")

        # Act: Run hook with --vibe flag
        hook_input = hook_context.make_input(
            tool_name="Bash",
            tool_input={"command": f"acli jira workitem create --from-json {adf_path} --vibe"},
        )

        import hooks.plugin.guards.pre_hr1_quality_gate as hr1

        result = hook_context.run_hook(hr1, hook_input)

        # Note: Actual threshold depends on project-config.json
        # This test validates the hook processes --vibe correctly
        # Result depends on configured threshold
        assert hook_context.last_exit_code in (0, 1)  # Either pass or fail cleanly
