---
name: create-testplan
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_create_issue, mcp__mcp-atlassian__jira_update_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Create Test Plan + [QA] Sub-task from User Story with a 6-phase QA workflow

  Phases: Discovery → Test Scope Analysis → Design Test Cases → Quality Gate → Create [QA] Sub-task → Summary

  Output: [QA] Sub-task in Jira (Test Plan embedded in description)

  Triggers: "create test plan", "QA", "test case", "testing", "สร้าง test plan", "add QA subtask"
  Use when: adding a QA sub-task and test plan to an existing Story
  Do NOT use for: initial story creation (use create-story); analyzing implementation (use analyze-story)
argument-hint: "[issue-key]"
effort: medium
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
> **Step 2:** `acli jira workitem edit --from-json {{artifacts_dir}}/tp-xxx-qa.json --yes`
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
/create-testplan {{PROJECT_KEY}}-101                # create [QA] sub-task for story {{PROJECT_KEY}}-101; agent reads all ACs first
/create-testplan {{PROJECT_KEY}}-101                # after bug fix: creates verification sub-task with regression cases
/create-testplan {{PROJECT_KEY}}-215                # story with 5 ACs → agent maps 100% coverage before designing test cases
```

### ❌ Bad

```text
/create-testplan                        # missing story key — skill cannot fetch ACs without it
/create-testplan {{PROJECT_KEY}}-112               # {{PROJECT_KEY}}-112 is a Sub-task, not a Story — test plan must target the parent story (1 Story = 1 [QA] Sub-task)
/create-testplan {{PROJECT_KEY}}-101               # run before ACs are finalized — test cases will be incomplete and need full rework
/create-testplan {{PROJECT_KEY}}-101               # calling a second time on a story that already has a [QA] sub-task — creates a duplicate; check first
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

## 🎓 Domain Expert Notes

### Why This Approach

Test plans derived directly from Acceptance Criteria (not from implementation) enforce black-box testing — the tester validates what the system _should_ do, not how it does it. The 100% AC coverage mandate prevents the most common QA gap: test cases written for the happy path while edge cases remain untested until production.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| IEEE 829 (Test Documentation Standard) | Phase 3 test case structure (ID, priority, Given/When/Then) | Industry-standard test case format ensures cases are reproducible and auditable |
| ISO/IEC 29119 (Risk-Based Testing) | Phase 2 AC coverage map + priority (🔴/🟠/🟡/🟢) | Priority assignment uses risk exposure (likelihood × impact) to focus test effort on critical paths first |
| ATDD (Acceptance Test-Driven Development) | Phase 2 mapping ACs → test scenarios before Phase 3 | Tests are defined from ACs before implementation detail is known — prevents testing the code instead of the requirement |
| Equivalence Partitioning (Myers) | Edge case (⚠️) and error (❌) test type classification | Input space is partitioned into valid/invalid/boundary classes; one test per class covers the full range |
| Given/When/Then (Gherkin, Cucumber) | Phase 3 test case format | Behavior-driven format makes test cases readable by non-technical stakeholders and linkable to ACs |

### Key Metrics

- **AC Coverage Ratio:** % of ACs with at least one mapped test scenario — must be 100% before Phase 3; < 100% = incomplete test plan
- **Test Case Density:** Number of test cases per AC — typical range is 2–5 cases per AC; < 2 suggests missing edge cases, > 8 suggests over-specification
- **Defect Detection Effectiveness (DDE):** % of bugs found by QA vs. total bugs — target > 90%; low DDE means test plan misses critical scenarios
- **Regression Coverage:** % of previously-failed ACs covered by regression cases — after any bug fix, the fixed AC must gain a regression test case

### Expert Decision Criteria

**Test type selection per AC:**

- AC describes the primary success path → ✅ Happy path test (mandatory for every AC)
- AC mentions limits, counts, or thresholds (e.g., "up to 5 items") → ⚠️ Edge case at boundary value
- AC references an error state or validation rule → ❌ Error/negative test
- AC involves UI interactions or visual feedback → 📱 UI test

**Priority assignment (risk-based):**

- 🔴 Critical: payment flows, authentication, data persistence — test failure = release blocker
- 🟠 High: core feature functionality visible to all users — test failure = release risk
- 🟡 Medium: secondary features, admin-only flows — test failure = known issue, ship with caveat
- 🟢 Low: cosmetic, edge case with workaround — test failure = backlog item

**When to add regression cases:**

- Any AC that was associated with a P1 or P2 bug fix must get a dedicated regression test case
- If a test case was added _after_ a bug was found in production, mark it `[Regression]` in the ID

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Test plan created before ACs are final | Phase 1 gate skipped or ACs still in draft | Enforce Phase 1 gate: check AC status before proceeding; re-run if ACs change |
| Generic TC-01/TC-02 cases with no business context | Phase 2 AC mapping skipped; test cases written from memory | Always complete AC coverage matrix (Phase 2) before writing any test cases |
| Same bug reported in production after QA pass | Edge and error test types missing; only happy path covered | Each AC must have at least one ⚠️ edge or ❌ error case alongside the ✅ happy path |
| Duplicate [QA] sub-tasks for the same story | Phase 1 discovery doesn't check for existing QA subtask | Search for `[QA]` subtask in Phase 1 before creating; if found, update instead of create |
| Test cases fail to catch regressions | No `[Regression]` tagging; P1/P2 fixes not linked back to test plan | After every P1/P2 bug fix, add a regression test case to the story's [QA] subtask |

### Authoritative References

- **IEEE 829-2008 (IEEE Standard for Software Test Documentation):** Defines test plan and test case structure — the ID/priority/Given-When-Then format in Phase 3 follows this standard
- **ISO/IEC 29119-2:2013 (Software Testing Processes):** Risk-based test strategy — the 🔴/🟠/🟡/🟢 priority model maps to ISO 29119's risk exposure classification
- **Glenford J. Myers — "The Art of Software Testing" (1979):** Equivalence partitioning and boundary value analysis — the theoretical basis for edge case (⚠️) test type selection
- **Kent Beck — "Test-Driven Development by Example":** ATDD principle — test cases written from requirements (ACs) before implementation details are known produces better coverage than testing the implementation
