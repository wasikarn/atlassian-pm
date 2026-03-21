---
name: create-testplan
disable-model-invocation: true
x-compatibility: [jira-cache-server, mcp-atlassian, acli]
description: |
  Create Test Plan + [QA] Sub-task from User Story with a 5-phase QA workflow

  Phases: Discovery → Test Scope Analysis → Design Test Cases → Create [QA] Sub-task → Summary

  Output: [QA] Sub-task in Jira (Test Plan embedded in description)

  Triggers: "create test plan", "QA", "test case", "testing"
argument-hint: "[issue-key]"
---

# /create-testplan

**Role:** Senior QA Analyst
**Output:** [QA] Sub-task (with embedded Test Plan)

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Discovery | `story_data`, `subtask_inventory[]`, `test_scope` |
| 2. Test Scope | `ac_coverage_map[]`, `test_types[]` |
| 3. Design | `test_cases[]`, `coverage_matrix` |
| 4. QG | `qg_score`, `passed_qg` |
| 5. Create | `qa_subtask_key` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

> **Note:** Test Plan is embedded in [QA] Sub-task description instead of creating a separate Confluence page

## Phases

### 1. Discovery

- `MCP: jira_get_issue(issue_key: "{{PROJECT_KEY}}-XXX")`
- `MCP: jira_search(jql: "parent = {{PROJECT_KEY}}-XXX", fields: "summary,status,assignee,issuetype")` → Sub-tasks (**⚠️ NEVER add ORDER BY to parent queries**)
- Read: Narrative, ACs, Technical Note (if available)
- **⛔ GATE — DO NOT PROCEED** without user confirmation of test scope.

### 2. Test Scope Analysis

- Map ACs → Test scenarios
- 100% AC coverage required
- Test types: ✅ Happy / ⚠️ Edge / ❌ Error / 📱 UI

| AC | Description | Test Scenarios |
| --- | --- | --- |
| 1 | [AC1 desc] | TC1, TC2 |

**🟡 REVIEW** — Present AC coverage matrix to user. Proceed unless user objects.

### 3. Design Test Cases

- ID, AC coverage, Priority (🔴/🟠/🟡/🟢)
- Type: ✅ Happy / ⚠️ Edge / ❌ Error
- Given/When/Then format
- Test data requirements
- **🟡 REVIEW** — Present test cases to user. Proceed unless user objects.

### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT create QA subtask in Jira without QG ≥ 90%.

> [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | QA Quality X/5 | Overall X%`

### 5. Create [QA] Sub-task

> **🟢 AUTO** — Create → verify parent → edit description. All automated. Escalate only if parent verify fails.
> HR5: Two-Step + Verify Parent.

> **Principle:** 1 Story = 1 [QA] Sub-task (Test Plan embedded in description)
>
> ⚠️ Use **Two-Step Workflow** (see [Subtask Template](../../../references/templates-subtask.md)):
>
> **Step 1:** MCP `jira_create_issue` → summary: `[QA] - Test: [Feature Name]`, parent: `{{PROJECT_KEY}}-XXX`
> **Step 2:** `acli jira workitem edit --from-json {{artifacts_dir}}/bep-xxx-qa.json --yes`
>
> ⚠️ EDIT JSON uses `"issues": ["ABC-QQQ"]` (not `"parent"` or `"parentKey"`)

Panel colors: see [ADF Core Rules](../../../references/templates-core.md) — success=happy, warning=edge, error=error

> **🟢 AUTO** — HR6: `cache_invalidate(qa_subtask_key)` after create.
> **🟢 AUTO** — HR3: If assignee needed, use `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).

### 6. Summary

```text
## QA Complete: [Title] ({{PROJECT_KEY}}-XXX)

[QA] Sub-task: ABC-QQQ (N scenarios)
Coverage: X ACs → Y test scenarios (100%)

→ /verify-issue ABC-QQQ to verify
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
| --- | --- | --- |
| `json: unknown field "parent"` | Wrong field in JSON | Use MCP to create first, then acli edit |
| `json: unknown field "parentKey"` | Wrong field in JSON | Use MCP to create first, then acli edit |
| `Could not find issue by id or key` | Invalid parentIssueId | Use MCP to create first, then acli edit |

**Recommended Workflow:**

1. **Create** with MCP `jira_create_issue` (supports parent via additional_fields)
2. **Edit** with `acli --from-json` (add ADF description)

---

> See [references/examples.md](references/examples.md) for input/output examples.

## Examples

### ✅ Good

```text
/create-testplan BEP-101                # create [QA] sub-task for story BEP-101; agent reads all ACs first
/create-testplan BEP-101                # after bug fix: creates verification sub-task with regression cases
/create-testplan BEP-215                # story with 5 ACs → agent maps 100% coverage before designing test cases
```

### ❌ Bad

```text
/create-testplan                        # missing story key — skill cannot fetch ACs without it
/create-testplan BEP-112               # BEP-112 is a Sub-task, not a Story — test plan must target the parent story (1 Story = 1 [QA] Sub-task)
/create-testplan BEP-101               # run before ACs are finalized — test cases will be incomplete and need full rework
/create-testplan BEP-101               # calling a second time on a story that already has a [QA] sub-task — creates a duplicate; check first
```

### ❌ Bad (correct key, wrong approach)

```text
# Writing test cases from memory without reading story ACs first → results in generic TC-01/TC-02 cases
# Skipping Phase 2 AC coverage matrix → some ACs left uncovered (100% coverage is mandatory)
# Asking to assign the [QA] sub-task via MCP → HR3: use acli assign only
```

**Common mistakes:**

- Running before the story's ACs are finalized — any AC added or modified after test plan creation requires reworking all affected test cases
- Not achieving 100% AC coverage in Phase 2 — every AC must map to at least one test scenario before Phase 3 proceeds
- Creating a test plan against a Sub-task key instead of the parent Story key — 1 Story = 1 [QA] Sub-task is the enforced principle
- Calling the skill a second time on a story that already has a `[QA]` sub-task — search for existing QA subtask in Phase 1 discovery before creating a new one

## References

- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Subtask Template](../../../references/templates-subtask.md) - Subtask + QA ADF templates
- [Verification](../../../references/verification-checklist.md) - QA checklist
