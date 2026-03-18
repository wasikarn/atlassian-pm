---
name: update-subtask
disable-model-invocation: true
x-compatibility: [jira-cache-server, mcp-atlassian, acli]
description: |
  Update an existing Sub-task with a 6-phase update workflow

  Phases: Fetch Current → Identify Changes → Preserve Intent → Generate Update → Quality Gate → Apply Update

  Supports: format migration, add details, language fix, add AC

  Triggers: "update subtask", "edit subtask", "adjust subtask"
argument-hint: "[issue-key] [changes]"
---

# /update-subtask

**Role:** Senior Technical Analyst
**Output:** Updated Sub-task

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Fetch | `subtask_data`, `parent_story` |
| 2. Identify | `change_type`, `change_scope` |
| 3. Preserve | `preservation_rules` |
| 4. Generate | `update_adf_json` |
| 5. QG | `qg_score`, `passed_qg` |
| 6. Apply | `applied` |

> **Workflow Patterns:** See [workflow-patterns.md](../shared-references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed` as you work.

### 1. Fetch Current State

- `MCP: jira_get_issue(issue_key: "{{PROJECT_KEY}}-XXX", fields: "summary,status,description,parent,{{START_DATE_FIELD}},duedate,timetracking")`
- Fetch parent story: `MCP: jira_get_issue(issue_key: "<parent_key>", fields: "summary,status,{{START_DATE_FIELD}},duedate")`
- Read: Description, Summary, Status
- **HR8 baseline:** Record parent start/due dates for Phase 6 validation
- **🟡 REVIEW** — Present current state to user. Proceed unless user objects.

### 2. Identify Changes

| Type | Description | Example |
| --- | --- | --- |
| **Format** | Adjust format | wiki → ADF |
| **Content** | Add/edit content | add AC |
| **Language** | Fix language | EN → Thai + transliteration |
| **Codebase** | Update paths | generic → actual |

**⛔ GATE — DO NOT PROCEED** without user confirmation of changes.

### 3. Preserve Intent

- ✅ Adjusting format is allowed
- ✅ Adding details is allowed
- ✅ Translating language is allowed
- ❌ Do not change the objective
- ❌ Do not remove existing ACs

### 4. Generate Update

- If file paths need updating → `Task(Explore)`
- Generate ADF JSON → `tasks/bep-xxx-update.json`
- Show Before/After comparison
- **⛔ GATE — DO NOT APPLY** without user approval of all generated changes.

### 5. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send updates to Atlassian without QG ≥ 90%.

> [QG Scoring Rules](../shared-references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`

### 6. Apply Update

> **🟢 AUTO** — If QG passed → apply automatically. No user interaction needed.

```bash
acli jira workitem edit --from-json tasks/bep-xxx-update.json --yes
```

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after apply.

**HR8 — Validate dates against parent (if dates changed or set):**

```text
# After apply, verify subtask dates within parent range:
# - subtask start_date ≥ parent start_date
# - subtask due_date ≤ parent due_date
# - If OE was set/changed, validate it matches estimation panel
# If violation detected → warn user + suggest fix
# ⚠️ HR10: NEVER set sprint on subtasks — inherits from parent
```

---

## Common Scenarios

| Scenario | Command |
| --- | --- |
| Format migrate | `/update-subtask {{PROJECT_KEY}}-XXX "migrate ADF"` |
| Add file paths | `/update-subtask {{PROJECT_KEY}}-XXX "add file paths"` |
| Fix language | `/update-subtask {{PROJECT_KEY}}-XXX "fix to Thai"` |
| Add AC | `/update-subtask {{PROJECT_KEY}}-XXX "add AC error handling"` |

---

## References

- [ADF Core Rules](../shared-references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Subtask Template](../shared-references/templates-subtask.md) - Subtask ADF template + best practices
- [Tool Selection](../shared-references/tools.md) - Tool selection
