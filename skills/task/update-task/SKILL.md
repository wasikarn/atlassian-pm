---
name: update-task
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Update an existing Jira Task with a 6-phase update workflow

  Phases: Fetch Current → Identify Changes → Preserve Intent → Generate Update → Quality Gate → Apply Update

  Supports: format migration, add details, change type template

  Triggers: "update task", "edit task", "adjust task", "แก้ไข task", "fix task description"
  Use when: editing a standalone Task's format, details, or type template
  Do NOT use for: story updates (use update-story); subtask updates (use update-subtask)
argument-hint: "{{PROJECT_KEY}}-XXX [changes]"
effort: medium
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

## 🎓 Domain Expert Notes

### Why This Approach

Task updates happen at two distinct moments with different risk profiles: pre-sprint (safe, no velocity impact) and in-sprint (risky, may invalidate sprint commitment). The preserve-intent phase makes scope change explicit and forces a conscious decision rather than a silent edit that corrupts sprint reporting.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Kanban Change Management (Anderson, 2010) | Phase 2 change type classification (migrate/add-details/change-type/update-content) | Anderson's explicit policies principle: classify changes by WIP impact before executing. `migrate` = standard change (zero WIP impact, pre-approved); `add-details` = low impact (additive, no scope shift); `change-type`/`update-content` = normal change (requires approval, WIP risk) |
| ITIL 4 Change Enablement | Phase 4 gate before applying changes | ITIL 4 defines 4 change types: **standard** (pre-approved, low risk) = migrate/add-details; **normal** (approval required, risk assessed) = update-content with scope shift; **emergency** (expedited, documented post-hoc) = blocked escalation path; **undoable** (irreversible) = type-change operations. The Phase 4 gate classifies every update against this taxonomy before applying |
| Agile Impediment Escalation (Scrum Guide) | Blocked task protocol in update-content changes | A task update that adds "blocked by" context triggers an impediment — must be visible to the Scrum Master within the same sprint day; description update alone is invisible on sprint board status filters |
| Docs as Code (Anne Gentle, "Docs Like Code", 2017) | Format migration (Wiki → ADF) change type | Treating task descriptions as versioned, structured documents reviewed with the same rigour as source code. ADF enforces structure; QG scoring provides the equivalent of a code review gate — ensures docs remain machine-readable and diffable |

### Key Metrics

- **Update-to-Creation Ratio:** Number of task updates vs. tasks created in a sprint — ratio > 0.5 signals tasks are being created before enough information is known
- **Format Debt:** Count of tasks still in Wiki markup (non-ADF) — migrate tasks reduce this debt; should trend to 0 over 2 sprints
- **Post-update QG Score:** QG score after each update — must not drop below the pre-update score; a drop signals content was degraded
- **Blocked Task Age:** Time a task spends in "blocked" state before being escalated — target < 1 business day; > 2 days signals impediment management gap

### Expert Decision Criteria

**Change type selection:**

- Task description uses Wiki markup (e.g., `*bold*`, `{code}`) → `migrate`; all other change types require ADF-format task first
- User wants to add more issues, ACs, or reference links to existing content → `add-details`; original content is never modified
- Task was created as `tech-debt` but the work is actually mechanical maintenance → `change-type` to `chore`; review ACs and checklist for consistency
- Specific sections have outdated information (stale PR link, changed file path) → `update-content`; only named sections change

**Blocked task escalation protocol:**

- If updating a task to add "blocked" status: record the blocker in the description AND transition the issue to "Blocked" in Jira
- Escalation path: developer → Tech Lead (same day) → Sprint Planning (next sprint if unresolved)
- A task that has been blocked for > 3 days without resolution should be removed from the sprint and re-planned

**Task handoff best practices:**

- When updating a task to change assignee (mid-sprint handoff): add a "Progress Note" section to the description with what was completed, what remains, and any gotchas discovered
- Handoff without a progress note = knowledge loss; the next developer will repeat investigation already done

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Task type changed but template structure not updated | `change-type` applied without regenerating the ADF template | Always regenerate full ADF template for the new type; do not patch old template sections |
| QG score drops after update | Sections removed or content degraded during "update-content" change | Run before/after QG comparison; if score drops, restore removed sections and re-score |
| Format migration breaks existing ADF panels | Wiki → ADF migration applied to an already-ADF task | Check current format in Phase 1 (`Identify current format`); never apply migration to ADF-format task |
| Blocked task not visible to Scrum Master | Task description updated but Jira status not transitioned | Pair description update with status transition to "Blocked"; description alone is invisible in sprint board filters |
| `/update-task` run on a Story key | No type-check in Phase 1; story updated as if it were a task | Check `issuetype` in Phase 1; if Story, redirect to `/update-story` immediately |

### Authoritative References

- **Mike Cohn — "Agile Estimating and Planning":** Task granularity and sprint commitment — tasks updated mid-sprint must be reviewed for capacity impact; the Phase 4 gate implements this discipline
- **David Anderson — "Kanban" (2010):** Explicit policies and change management — classifying changes before applying them is a core Kanban practice that prevents invisible scope creep
- **Jeff Sutherland — "Scrum: The Art of Doing Twice the Work in Half the Time":** Impediment removal is the Scrum Master's primary job — surfacing blocked tasks via status transition (not just description update) ensures impediments are visible
- **ITIL 4 Service Management:** Change enablement — the four change types (standard/normal/emergency/undoable) map directly to the four update-task change types in terms of risk profile and approval requirements
