---
name: update-story
disable-model-invocation: true
x-compatibility: [jira-cache-server, mcp-atlassian, acli]
description: |
  Update an existing User Story with a 6-phase update workflow

  Phases: Fetch Current → Impact Analysis → Preserve Intent → Generate Update → Quality Gate → Apply Update

  Supports: add AC, modify AC, adjust scope, format migration

  Triggers: "update story", "edit story", "add AC"
argument-hint: "[issue-key] [changes]"
---

# /update-story

**Role:** Senior Product Owner
**Output:** Updated User Story

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Fetch | `story_data`, `subtask_inventory[]` |
| 2. Impact | `change_type`, `impact_on_subtasks` |
| 3. Preserve | `preservation_rules` |
| 4. Generate | `update_adf_json` |
| 5. QG | `qg_score`, `passed_qg` |
| 6. Apply | `applied` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

### 1. Fetch Current State

- `MCP: jira_get_issue(issue_key: "{{PROJECT_KEY}}-XXX")`
- `MCP: jira_search(jql: "parent = {{PROJECT_KEY}}-XXX", fields: "summary,status,assignee,issuetype")` → Sub-tasks (**⚠️ NEVER add ORDER BY to parent queries**)
- Read: Narrative, ACs, Scope, Status
- **🟡 REVIEW** — Present current state to user. Proceed unless user objects.

### 2. Impact Analysis

| Change Type | Impact on Sub-tasks | Impact on QA |
| --- | --- | --- |
| Add AC | Need to create sub-task? | Need to add test? |
| Remove AC | Need to delete sub-task? | Need to delete test? |
| Modify AC | Need to update sub-task? | Need to update test? |
| Format only | ❌ No impact | ❌ No impact |

**⛔ GATE — DO NOT PROCEED** without user confirmation of changes.

### 3. Preserve Intent

- ✅ Adding ACs is allowed
- ✅ Adjusting wording is allowed
- ⚠️ Be careful changing scope (requires re-analysis)
- ❌ Do not change core value proposition without informing

### 4. Generate Update

- Generate ADF JSON → `{{artifacts_dir}}/bep-xxx-update.json`
- Show comparison:
  - Narrative: [No change / Changed]
  - ACs: ✅ Kept / ✏️ Modified / ➕ New
- **⛔ GATE — DO NOT APPLY** without user approval of all generated changes.

### 5. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send updates to Atlassian without QG ≥ 90%.

> [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`

### 6. Apply Update

> **🟢 AUTO** — If QG passed → apply automatically. No user interaction needed.

```bash
acli jira workitem edit --from-json {{artifacts_dir}}/bep-xxx-update.json --yes
```

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after apply.

**If start_date or due_date changed — HR8 subtask alignment:**

```text
# Fetch subtasks with dates
MCP: jira_search(jql: "parent = {{PROJECT_KEY}}-XXX", fields: "summary,status,{{START_DATE_FIELD}},duedate,timetracking")
# ⚠️ NEVER add ORDER BY to parent queries (HR2)

# For each active subtask: validate dates within new parent range
# - subtask start < new parent start → clamp to parent start
# - subtask due > new parent due → extend parent due OR flag
# - missing dates → distribute evenly within parent range
# - missing OE → estimate from summary keywords (2h-4h)

# Or run batch fix:
Bash: python3 scripts/sprint/sprint_subtask_alignment.py --sprint <id>
```

> **🟢 AUTO** — HR6: `cache_invalidate(subtask_key)` after each subtask date fix.

**Output:**

```text
## Story Updated: [Title] ({{PROJECT_KEY}}-XXX)
Changes: [list]
Subtask alignment: [X subtasks checked, Y adjusted]
→ May need: /update-subtask ABC-YYY
→ May need: /sync-alignment {{PROJECT_KEY}}-XXX (for auto cascade)
```

---

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.

## References

- [Update Workflow Patterns](../../../references/update-workflow.md) — common Phase 5 QG, Phase 6 apply, gate phrases, preserve intent structure
- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Story Template](../../../references/templates-story.md) - Story ADF template + best practices
- [Verification Checklist](../../../references/verification-checklist.md) - INVEST, AC quality
