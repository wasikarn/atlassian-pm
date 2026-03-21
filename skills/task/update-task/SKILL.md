---
name: update-task
disable-model-invocation: true
x-compatibility: [jira-cache, mcp-atlassian, acli]
description: |
  Update an existing Jira Task with a 6-phase update workflow

  Phases: Fetch Current → Identify Changes → Preserve Intent → Generate Update → Quality Gate → Apply Update

  Supports: format migration, add details, change type template

  Triggers: "update task", "edit task", "adjust task"
argument-hint: "{{PROJECT_KEY}}-XXX [changes]"
---

# /update-task

**Role:** Developer / Tech Lead
**Output:** Updated Jira Task

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Fetch | `task_data`, `current_format`, `task_type` |
| 2. Identify | `change_type`, `change_scope` |
| 3. Preserve | `preservation_rules` |
| 4. Generate | `update_adf_json` |
| 5. QG | `qg_score`, `passed_qg` |
| 6. Apply | `applied` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

### 1. Fetch Current State

- `MCP: jira_get_issue(issue_key: "{{PROJECT_KEY}}-XXX")`
- Read: Summary, Description, Status, Priority, Labels
- Identify current format: Wiki markup or ADF
- Identify current type (if applicable): tech-debt, bug, chore, spike

**🟡 REVIEW** — Present current state to user. Proceed unless user objects.

---

### 2. Identify Changes

Ask the user what they want to update:

| Change Type | Description |
| --- | --- |
| `migrate` | Convert Wiki → ADF format |
| `add-details` | Add more details (issues, ACs, etc.) |
| `change-type` | Change template type |
| `update-content` | Edit existing content |

**Common scenarios:**

```text
1. Migrate format (Wiki → ADF)
2. Add issues/ACs
3. Change priority
4. Add reference links
5. Other (specify)
```

**⛔ GATE — DO NOT PROCEED** without user confirmation of changes.

---

### 3. Preserve Intent

| Change Type | Preserve | Allow Change |
| --- | --- | --- |
| Format migrate | ✅ All content | Format only |
| Add details | ✅ Existing content | ➕ New sections |
| Change type | ⚠️ Core info | Template structure |
| Update content | ✅ Other sections | Specified sections |

**Rules:**

- ✅ Adding content is allowed
- ✅ Adjusting format/wording is allowed
- ⚠️ Be careful changing scope
- ❌ Do not delete content without informing

**🟢 AUTO** — Apply preservation rules programmatically. No user interaction needed.

---

### 4. Generate Update

Generate ADF JSON → `{{artifacts_dir}}/bep-xxx-update.json`

**EDIT format (do not include projectKey, type, summary):**

```json
{
  "issues": ["{{PROJECT_KEY}}-XXX"],
  "description": {
    "type": "doc",
    "version": 1,
    "content": [...]
  }
}
```

**Show comparison:**

```text
## Changes Preview

| Section | Before | After |
|---------|--------|-------|
| Format | Wiki | ADF |
| Context | ✅ Kept | ✅ Kept |
| Issues | 3 items | 5 items (➕2) |
| ACs | ❌ None | ➕ 5 items |

Would you like to apply these changes?
```

**⛔ GATE — DO NOT APPLY** without user approval of all generated changes.

---

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

**Output:**

```text
## ✅ Task Updated: [Title] ({{PROJECT_KEY}}-XXX)

**Changes:**
- [list of changes applied]

🔗 [View in Jira](https://{{JIRA_SITE}}/browse/ABC-XXX)

→ Use /verify-issue {{PROJECT_KEY}}-XXX to check quality
```

---

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.
> See [references/task-type-detection.md](references/task-type-detection.md) for auto-detection patterns by content.

## Examples

### ✅ Good

```text
/update-task {{PROJECT_KEY}}-88                       # agent reads current state, then asks what to change
/update-task {{PROJECT_KEY}}-88 migrate               # migrate Wiki markup → ADF format
/update-task {{PROJECT_KEY}}-88 add-details           # add missing ACs or reference links to existing task
/update-task {{PROJECT_KEY}}-88 change-type chore     # switch template from tech-debt → chore
```

### ❌ Bad

```text
/update-task                              # missing issue key — agent cannot fetch current state
/update-task {{PROJECT_KEY}}-55                       # {{PROJECT_KEY}}-55 is a User Story — use /update-story instead
/update-task {{PROJECT_KEY}}-88 "change to story"     # cannot change issue type Task→Story via this skill — use Jira UI directly
/update-task {{PROJECT_KEY}}-88 "rewrite everything"  # scope too vague; agent must infer change type — be explicit
```

**Common mistakes:**

- Passing a Story key ({{PROJECT_KEY}}-XXX where type=Story) — the skill will update it as if it's a Task, bypassing story-specific AC impact analysis; use `/update-story` instead
- Not specifying what to update when calling the skill — forces agent to guess the change type in Phase 2, risking wrong template selection
- Expecting the skill to change the Jira issue type (Task → Story) — issue type changes must be done in Jira UI directly
- Forgetting to run `/verify-issue {{PROJECT_KEY}}-XXX` after update to confirm QG score is still valid

## References

- [Update Workflow Patterns](../../../references/update-workflow.md) — common Phase 5 QG, Phase 6 apply, gate phrases, preserve intent structure
- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Task Template](../../../references/templates-task.md) - Task ADF templates (tech-debt, bug, chore, spike)
- After: `/verify-issue {{PROJECT_KEY}}-XXX` to check quality
