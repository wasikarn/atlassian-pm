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
→ May need: /sync-artifacts {{PROJECT_KEY}}-XXX (for auto cascade)
```

---

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.

## Examples

### ✅ Good

```text
/update-story {{PROJECT_KEY}}-101                          # agent reads current story + subtasks, then asks what to change
/update-story {{PROJECT_KEY}}-101 "add AC for error state" # adds missing AC; agent runs subtask impact analysis automatically
/update-story {{PROJECT_KEY}}-101 "remove AC-3 (descoped)" # removes AC; agent flags any subtask that only covers AC-3
/update-story {{PROJECT_KEY}}-101 migrate                  # migrate Wiki narrative → ADF format only (no AC changes)
```

### ❌ Bad

```text
/update-story                                  # missing issue key — cannot fetch current state
/update-story {{PROJECT_KEY}}-105                          # {{PROJECT_KEY}}-105 is a Sub-task — use /update-subtask instead
/update-story {{PROJECT_KEY}}-101 "rewrite all ACs"        # full redesign with cascading subtask changes → use /sync-artifacts {{PROJECT_KEY}}-101 instead
/update-story {{PROJECT_KEY}}-101 "change dates"           # changing parent dates requires checking all subtask date ranges (HR8); confirm alignment is reviewed
```

**Common mistakes:**

- Passing a Sub-task key — the skill reads it as a story and skips the AC impact analysis that `/update-subtask` performs; always verify the issue type before calling
- Making scope changes (add/remove ACs) without reviewing the subtask impact shown in Phase 2 — can leave subtasks covering descoped ACs or missing new ACs entirely
- Using this skill when the story needs a full structural redesign — use `/sync-artifacts {{PROJECT_KEY}}-XXX` to cascade changes to all subtasks automatically
- Changing parent `start_date` or `due_date` without checking that existing subtask dates still fall within the new range (HR8 violation)

## References

- [Update Workflow Patterns](../../../references/update-workflow.md) — common Phase 5 QG, Phase 6 apply, gate phrases, preserve intent structure
- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Story Template](../../../references/templates-story.md) - Story ADF template + best practices
- [Verification Checklist](../../../references/verification-checklist.md) - INVEST, AC quality
