---
name: update-subtask
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
description: |
  Update an existing Sub-task with a 6-phase update workflow

  Phases: Fetch Current → Identify Changes → Preserve Intent → Generate Update → Quality Gate → Apply Update

  Supports: format migration, add details, language fix, add AC

  Triggers: "update subtask", "edit subtask", "adjust subtask"
argument-hint: "[issue-key] [changes]"
effort: medium
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

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

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
- Generate ADF JSON → `{{artifacts_dir}}/bep-xxx-update.json`
- Show Before/After comparison
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

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.

## Examples

### ✅ Good

```text
/update-subtask {{PROJECT_KEY}}-112                        # agent reads current state + parent dates, then asks what to change
/update-subtask {{PROJECT_KEY}}-112 migrate                # convert Wiki markup → ADF format
/update-subtask {{PROJECT_KEY}}-112 "add file paths"       # agent runs Task(Explore) to discover actual paths, then updates
/update-subtask {{PROJECT_KEY}}-112 "fix language Thai"    # translate description to Thai with English transliteration
```

### ❌ Bad

```text
/update-subtask                                # missing issue key — cannot fetch current state
/update-subtask {{PROJECT_KEY}}-101                        # {{PROJECT_KEY}}-101 is a User Story — use /update-story instead
/update-subtask {{PROJECT_KEY}}-112 "set start 2025-01-01 due 2025-03-01"  # dates outside parent range → HR8 violation
/update-subtask {{PROJECT_KEY}}-112 "add to sprint 42"    # HR10: subtask sprint is inherited from parent — never set directly
```

**Common mistakes:**

- Passing a Story key — the skill updates it without the story-specific AC impact analysis that `/update-story` provides
- Setting subtask dates that fall outside the parent story's `start_date`/`due_date` range — this violates HR8 and corrupts sprint burndown
- Attempting to set `{{SPRINT_FIELD}}` (sprint) on a subtask — HR10 explicitly forbids this; sprint is always inherited from the parent
- Removing existing ACs during an update — Phase 3 preservation rules block this, but explicitly asking to "remove AC" bypasses the intent check

## References

- [Update Workflow Patterns](../../../references/update-workflow.md) — common Phase 5 QG, Phase 6 apply, gate phrases, preserve intent structure
- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Subtask Template](../../../references/templates-subtask.md) - Subtask ADF template + best practices
- [Tool Selection](../../../references/tools.md) - Tool selection

## 🎓 Domain Expert Notes

### Why This Approach

In-sprint subtask updates are high-risk changes: a subtask that shifts scope mid-sprint can invalidate the parent story's burndown, break date alignment with siblings, and silently corrupt sprint velocity metrics. The preserve-intent phase is the formal safeguard that separates _enriching_ a subtask (allowed) from _re-scoping_ it (requires story-level re-planning).

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Scrum Sprint Scope Protection | Phase 3 Preserve Intent rules | Sprint commitment is inviolable; updating format/language is safe, but changing objective requires PO/TL sign-off |
| Earned Value Management (EVM) | HR8 date validation in Phase 6 | Subtask dates must stay within parent range to preserve schedule baseline integrity; violations distort EV calculations |
| WIP Limit Discipline (Kanban) | Phase 2 change type identification | In-sprint scope expansion increases WIP; each change type is evaluated for WIP impact before applying |
| Impediment Management (Scrum) | Content updates that add "blocked by" or remove ACs | Removals and dependency additions must be flagged to the Scrum Master, not silently applied |

### Key Metrics

- **In-sprint Update Frequency:** Number of subtask updates after sprint start — > 2 updates per subtask signals poor initial decomposition; review story-to-subtask breakdown
- **Scope Drift Rate:** % of subtasks where objective changed mid-sprint — target 0%; any objective change should trigger a sprint re-planning discussion
- **Date Alignment Violations (HR8):** Count of subtasks with dates outside parent range — must be 0; violations corrupt sprint burndown charts
- **Description Completeness Score:** QG score before and after update — update should not decrease QG score; if it does, the update introduced ambiguity

### Expert Decision Criteria

**When an update is safe (no re-planning needed):**

- Format migration (Wiki → ADF): zero content change, always safe
- Language translation (EN → Thai + transliteration): preserves meaning, always safe
- Adding file paths discovered via `Task(Explore)`: adds specificity, does not change scope
- Fixing typos or broken links: always safe

**When an update requires TL/PO approval first:**

- Adding new ACs to a subtask already In Progress — expands scope, may delay completion
- Removing existing ACs from a subtask — signals scope reduction; must check if the removed AC is covered elsewhere
- Changing estimated hours (OE field) mid-sprint — affects sprint capacity model and velocity reporting
- Changing the subtask objective (what it delivers) — this is a new subtask, not an update

**Date update rules (HR8 enforcement):**

- Subtask `start_date` must be ≥ parent story `start_date`
- Subtask `due_date` must be ≤ parent story `due_date`
- If new dates violate the parent range, update the parent story's dates first, then apply subtask dates

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Sprint burndown shows subtask "done" but story still open | Subtask scope expanded without updating parent story ACs | Phase 3: check if added ACs are covered in parent story; if not, update story first |
| Subtask dates drift outside parent range after update | HR8 validation skipped or parent dates not fetched in Phase 1 | Always fetch parent dates in Phase 1; validate after every date field change in Phase 6 |
| Subtask sprint field set directly (API error) | HR10 not enforced; user explicitly requests sprint assignment | Refuse: sprint is always inherited from parent; direct setting causes API error and cascade failure |
| ACs silently removed during format migration | Phase 3 preservation not applied to checklist items | Count ACs before and after generation; if count differs, flag to user before applying |
| Updated subtask fails QG after apply | Content was modified beyond stated change type in Phase 2 | Re-run QG; if < 90%, auto-fix then re-score before accepting the update as complete |

### Authoritative References

- **Scrum Guide (Schwaber & Sutherland):** Sprint goal and scope protection — the preserve-intent rules directly implement the Scrum principle that sprint scope is agreed at planning and only changed by mutual consent
- **Project Management Institute (PMI) — PMBOK:** Integrated Change Control — any scope change (even at subtask level) requires a change request; Phase 3 gate is the lightweight equivalent
- **Earned Value Management (ANSI/EIA-748):** Schedule baseline integrity — date validation (HR8) prevents "rubber baseline" syndrome where dates shift continuously, making EV metrics meaningless
- **Anderson, David J. — "Kanban" (2010):** WIP limits and change cost — mid-sprint scope changes add invisible WIP; the identify-changes phase makes the WIP cost visible before committing
