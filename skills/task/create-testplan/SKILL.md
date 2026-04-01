---
name: create-testplan
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_create_issue, mcp__mcp-atlassian__jira_update_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Create Test Plan + [QA] Task from parent Epic or feature Task with a 6-phase QA workflow

  Phases: Discovery → Test Scope Analysis → Design Test Cases → Quality Gate → Create [QA] Task → Summary

  Output: [QA] Task in Jira (Test Plan embedded in description)

  Triggers: "create test plan", "QA", "test case", "testing", "สร้าง test plan", "add QA task"
  Use when: adding a QA task and test plan to an existing Epic or feature Task
  Do NOT use for: initial task creation (use create-task); analyzing implementation (use analyze-story or create-task)
argument-hint: "[issue-key]"
effort: medium
---

# /create-testplan

**Role:** Senior QA Analyst
**Output:** [QA] Task (with embedded Test Plan)

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Discovery | `parent_data`, `task_inventory[]`, `test_scope` |
| 2. Test Scope | `ac_coverage_map[]`, `test_types[]` |
| 3. Design | `test_cases[]`, `coverage_matrix` |
| 4. QG | `qg_score`, `passed_qg` |
| 5. Create | `qa_task_key` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

> **Note:** Test Plan is embedded in [QA] Task description instead of creating a separate Confluence page

## Phases

### 1. Discovery

- `MCP: jira_get_issue(issue_key: "{{PROJECT_KEY}}-XXX")`
- `MCP: jira_search(jql: "parent = {{PROJECT_KEY}}-XXX", fields: "summary,status,assignee,issuetype")` → child Tasks (**⚠️ NEVER add ORDER BY to parent queries**)
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

> **ADF is minimal-first** — AC Coverage matrix (Phase 2) is internal planning only. Do NOT embed it in the Jira ADF description.
> Jira ADF = `วัตถุประสงค์ทดสอบ` heading + `ชุดทดสอบ` heading + optional `อ้างอิง`. No panels.

- Max 8 test cases; split into a second [QA] Task if > 8
- Each TC: ID, Given/When/Then, AC ref, Priority (🔴/🟠/🟡/🟢)
- Type: ✅ Happy path / ⚠️ Edge case / ❌ Error case
- **🟡 REVIEW** — Present test cases to user. Proceed unless user objects.

### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT create QA Task in Jira without QG ≥ 90%.
>
> [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | QA Quality X/5 | Overall X%`
>
> **🟢 AUTO (validate_adf.py):**
>
> ```bash
> uv run scripts/api/validate_adf.py {{artifacts_dir}}/tp-xxx-qa.json --type qa --json
> ```
>
> Score ≥ 90 = PASS. If FAIL → check `issues[].fix_hint` → run `--fix` → re-score. Max 1 fix cycle.

### 5. Create [QA] Task

> **🟢 AUTO** — Create → verify parent → edit description. All automated. Escalate only if parent verify fails.
> HR5: Two-Step + Verify Parent.

> **Principle:** 1 Epic/Feature Task = 1 [QA] Task (Test Plan embedded in description)
>
> ⚠️ Use **Two-Step Workflow** (see [Task Template](../../../references/templates-task.md)):
>
> **Step 1:** MCP `jira_create_issue` → summary: `[QA] - Test: [Feature Name]`, type: `Task`, parent: `{{PROJECT_KEY}}-XXX`
> **Step 2:** `acli jira workitem edit --from-json {{artifacts_dir}}/tp-xxx-qa.json --yes`
>
> ⚠️ EDIT JSON uses `"issues": ["ABC-QQQ"]` (not `"parent"` or `"parentKey"`)

> **⚠️ MANDATORY:** Read `references/templates-task.md` § "Mode: qa" before generating any ADF. Required headings: `วัตถุประสงค์ทดสอบ` + `ชุดทดสอบ`. Optional: `อ้างอิง` only when real links exist. No panel nodes.

> **🟢 AUTO** — HR6: `cache_invalidate(qa_task_key)` after create.
> **🟢 AUTO** — HR3: If assignee needed, use `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).

### 6. Summary

```text
## QA Complete: [Title] ({{PROJECT_KEY}}-XXX)

[QA] Task: ABC-QQQ (N scenarios)
Coverage: X ACs → Y test scenarios (100%)

→ /verify-issue ABC-QQQ to verify
```

## Common Errors & Fixes

| Error | Cause | Fix |
| --- | --- | --- |
| `json: unknown field "parent"` | Wrong field in JSON | Use MCP to create first, then acli edit |
| `json: unknown field "parentKey"` | Wrong field in JSON | Use MCP to create first, then acli edit |
| `Could not find issue by id or key` | Invalid parentIssueId | Use MCP to create first, then acli edit |

**Recommended Workflow:**

1. **Create** with MCP `jira_create_issue` (supports parent via additional_fields)
2. **Edit** with `acli --from-json` (add ADF description)

> See [references/examples.md](references/examples.md) for input/output examples.

## Examples

### ✅ Good

```text
/create-testplan {{PROJECT_KEY}}-101                # create [QA] Task for Epic/Task {{PROJECT_KEY}}-101; agent reads all ACs first
/create-testplan {{PROJECT_KEY}}-101                # after bug fix: creates verification task with regression cases
/create-testplan {{PROJECT_KEY}}-215                # task with 5 ACs → agent maps 100% coverage before designing test cases
```

### ❌ Bad

```text
/create-testplan                        # missing issue key — skill cannot fetch ACs without it
/create-testplan {{PROJECT_KEY}}-101               # run before ACs are finalized — test cases will be incomplete and need full rework
/create-testplan {{PROJECT_KEY}}-101               # calling a second time on an issue that already has a [QA] Task — creates a duplicate; check first
```

### ❌ Bad (correct key, wrong approach)

```text
# Writing test cases from memory without reading ACs first → results in generic TC-01/TC-02 cases
# Skipping Phase 2 AC coverage matrix → some ACs left uncovered (100% coverage is mandatory)
# Asking to assign the [QA] Task via MCP → HR3: use acli assign only
```

**Common mistakes:**

- Running before the ACs are finalized — any AC added or modified after test plan creation requires reworking all affected test cases
- Not achieving 100% AC coverage in Phase 2 — every AC must map to at least one test scenario before Phase 3 proceeds
- Calling the skill a second time on an issue that already has a `[QA]` Task — search for existing QA task in Phase 1 discovery before creating a new one

## References

[ADF Core Rules](../../../references/templates-core.md) · [Task Template](../../../references/templates-task.md) · [Verification](../../../references/verification-checklist.md)

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)
