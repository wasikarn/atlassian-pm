---
name: story-cascade
disable-model-invocation: true
context: fork
description: |
  Update Story + cascade changes to related Sub-tasks with a 9-phase workflow

  Phases: Fetch → Understand Changes → Impact Analysis → Explore (if needed) → Generate Story Update → Generate Sub-task Updates → Quality Gate → Apply All → Summary

  Composite: Automatic impact analysis, update everything in a single transaction

  Triggers: "story cascade", "update all", "cascade changes"
argument-hint: "[issue-key] [changes]"
---

# /story-cascade

**Role:** PO + TA Combined
**Output:** Updated Story + Updated/New Sub-tasks

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Fetch | `story_data`, `subtask_inventory[]`, `current_state` |
| 2. Understand | `change_type`, `impact_level` |
| 3. Impact | `impact_map[]`, `cascade_plan` |
| 4. Explore | `file_paths[]`, `patterns[]` (conditional) |
| 5. Story Update | `story_adf_json` |
| 6. Subtask Updates | `subtask_adf_jsons[]` |
| 7. QG | `qg_score`, `passed_qg` |
| 8. Apply | `applied_keys[]` |

> **Workflow Patterns:** See [workflow-patterns.md](../shared-references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed` as you work.

### 1. Fetch Current State

- `MCP: jira_get_issue(issue_key: "{{PROJECT_KEY}}-XXX")`
- `MCP: jira_search(jql: "parent = {{PROJECT_KEY}}-XXX", fields: "summary,status,assignee,issuetype")` (**⚠️ NEVER add ORDER BY to parent queries**)
- Build inventory: Story + all Sub-tasks
- **🟡 REVIEW** — Present inventory summary to user. Proceed unless user objects.

### 2. Understand Changes

| Change Type | Impact Level |
| --- | --- |
| Format only | 🟢 Low |
| Clarify AC | 🟢 Low |
| Add AC | 🟡 Medium |
| Modify AC | 🟡 Medium |
| Remove AC | 🔴 High |
| Change Scope | 🔴 High |

**⛔ GATE — DO NOT PROCEED** without user confirmation of change type + impact level.

### 3. Impact Analysis

| AC | Related Sub-tasks | Impact |
| --- | --- | --- |
| AC1 | BEP-YYY | ❌ No change |
| AC2 | BEP-YYY, BEP-ZZZ | ✏️ Must update |
| AC3 (new) | - | ➕ Need new |

**🟡 REVIEW** — Present impact table + cascade plan to user. Proceed unless user objects.

### 4. Codebase Exploration (if needed)

> **🟢 AUTO** — Run only if scope changed or new sub-task needed. Skip if format-only. Validate paths with Glob.

- Run only if: New sub-task needed OR scope changed
- [Parallel Explore](../shared-references/workflow-patterns.md#parallel-explore): Launch 2-3 agents (Backend/Frontend/Shared) IN PARALLEL.
- Validate paths with Glob. Generic paths REJECTED. Skip if format-only.

### 5. Generate Story Update

> **🟢 AUTO** — Generate automatically from change analysis. No user interaction needed.

- Apply changes: narrative, ACs, scope
- Generate ADF JSON → `tasks/bep-xxx-update.json`
- Show comparison table

### 6. Generate Sub-task Updates

- Preserve original intent
- Update ACs to align
- New sub-tasks: follow template
- Generate JSON files
- **🔄 ITERATE** — Present all generated changes as plan cards (story update + per-subtask changes). Ask: Approve all / Annotate (specify item #) / Major rework.
  - Annotate → user specifies which updates to change → revise ONLY those → re-present (max 3 rounds)
  - Approve → proceed to Quality Gate
  - Major rework → back to Impact Analysis
  - See [Annotation Cycle](../shared-references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 7. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send updates to Atlassian without QG ≥ 90%.

> [QG Scoring Rules](../shared-references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`

### 8. Apply All Updates

> **🟢 AUTO** — If QG passed → apply all automatically. Escalate only if parent verify fails.
> HR5: New subtasks must use Two-Step + Verify Parent.

```bash
# Story first
acli jira workitem edit --from-json tasks/bep-xxx-update.json --yes
# Then sub-tasks
acli jira workitem edit --from-json tasks/bep-yyy-update.json --yes
# New sub-tasks: Two-Step (MCP create shell → verify parent → acli edit)
```

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after EVERY Atlassian write.
> **🟢 AUTO** — HR3: If assignee needed, use `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).

**HR8 — Cascade date alignment (if story dates changed):**

```text
# For each subtask (existing + new): ensure dates within parent range
# New subtasks: set dates + OE during Two-Step creation
MCP: jira_update_issue(issue_key="BEP-YYY", additional_fields={
  "timetracking": {"originalEstimate": "<N>h"},
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",  # ≥ parent start
  "duedate": "YYYY-MM-DD"             # ≤ parent due
})
# Existing subtasks: validate + fix if dates now outside new parent range
# - subtask start < new parent start → clamp to parent start
# - subtask due > new parent due → extend parent due OR flag
# ⚠️ HR10: NEVER set sprint on subtasks
```

> **🟢 AUTO** — HR6: `cache_invalidate(subtask_key)` after each subtask date fix.

### 9. Cleanup & Summary

```bash
rm tasks/bep-*-update.json tasks/new-*.json
```

```text
## Cascade Complete
Story: {{PROJECT_KEY}}-XXX (AC2 modified, AC3 added)
Updated: BEP-YYY, BEP-ZZZ
Created: BEP-NEW
→ Review QA sub-task if needed
```

---

## Cascade vs Separate

| Approach | Commands | Issues |
| --- | --- | --- |
| Separate | `/update-story` + N × `/update-subtask` | Lost context |
| Cascade | `/story-cascade {{PROJECT_KEY}}-XXX` | Auto impact |

---

## Example

**Input:** `/story-cascade BEP-2468 "เพิ่ม AC สำหรับ pagination บน coupon list"`

**Output:**

```
Impact Analysis: 2 sub-tasks affected
Updated:
  ✅ BEP-2468 Story: +AC4 (Pagination)
  ✅ BEP-2469 [BE]: +scope item — paginate API response
  ✅ BEP-2470 [FE-Admin]: +scope item — pagination component
  ⏭️ BEP-2471 [QA]: no change needed (test plan covers pagination)
```

---

## References

- [ADF Core Rules](../shared-references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Story Template](../shared-references/templates-story.md) - Story ADF template + best practices
- [Subtask Template](../shared-references/templates-subtask.md) - Subtask ADF template + QA
- [Tool Selection](../shared-references/tools.md) - Tool selection
