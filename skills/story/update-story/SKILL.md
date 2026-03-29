---
name: update-story
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Update an existing User Story with a 6-phase update workflow

  Phases: Fetch Current → Impact Analysis → Preserve Intent → Generate Update → Quality Gate → Apply Update

  Supports: add AC, modify AC, adjust scope, format migration

  Triggers: "update story", "edit story", "add AC", "แก้ไข story", "modify acceptance criteria", "adjust story scope"
  Use when: modifying ACs, scope, or description of an existing User Story
  Do NOT use for: creating new stories (use create-story); Sub-task updates (use update-subtask)
argument-hint: "[issue-key] [changes]"
effort: medium
---

# /update-story

**Role:** Senior Product Owner
**Output:** Updated User Story

## Context Object (accumulated across phases)

| Phase | Adds to Context |
| ----- | --------------- |
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

> **⚠️ MANDATORY:** Read `references/templates-story.md` before generating any ADF. Use `panel` nodes — NEVER use `heading` nodes in issue descriptions.

- Generate ADF JSON → `{{artifacts_dir}}/tp-xxx-update.json`
- Show comparison:
  - Narrative: [No change / Changed]
  - ACs: ✅ Kept / ✏️ Modified / ➕ New
- **⛔ GATE — DO NOT APPLY** without user approval of all generated changes.

### 5. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send updates to Atlassian without QG ≥ 90%.
>
> [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`

### 6. Apply Update

> **🟢 AUTO** — If QG passed → apply automatically. No user interaction needed.

```bash
acli jira workitem edit --from-json {{artifacts_dir}}/tp-xxx-update.json --yes
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

## 🎓 Domain Expert Notes

### Why This Approach

Story updates during a sprint are the single largest source of mid-sprint scope creep in agile teams (Atlassian State of Agile 2024). The Preserve Intent phase exists because story changes are rarely neutral: adding an AC almost always implies new subtask work, and removing an AC almost always implies a subtask that is now doing work the team agreed to descope. Making the impact explicit before generating the update prevents silent misalignment between the story and its child artifacts.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Definition of Ready re-validation (DoR) | Phase 5 Quality Gate | Any change that affects scope, ACs, or value proposition resets the DoR clock; the 90% QG threshold is the automated DoR re-check |
| Change Impact Matrix | Phase 2 Impact Analysis table | Maps change type → subtask/QA impact; industry-standard practice from ITIL change management adapted to story-level granularity |
| Preserve Intent principle (Ron Jeffries) | Phase 3 Preserve Intent rules | The story's core value proposition (the "So that" clause) must remain stable across updates; changes to value proposition require a new story or epic-level re-scoping discussion |
| HR8 Date Alignment | Phase 6 subtask date fix | Parent date changes cascade to children; failing to propagate date changes creates HR8 violations that corrupt sprint burndown and capacity reports |
| Scope creep taxonomy | Phase 2 change type classification | Distinguishes between legitimate refinement (add AC that was always implied) and scope creep (add AC that expands the original commitment); only the former should be processed without escalation |

### Key Metrics

- **Change frequency threshold:** If a story requires more than 2 update cycles in a single sprint, it is a signal that the story was not sufficiently refined before sprint start (DoR failure upstream)
- **AC delta limit:** Adding or removing more than 2 ACs in a single update is a HIGH-impact change that should trigger `/sync-artifacts` rather than `/update-story`; the impact graph is too wide for single-story update
- **Subtask alignment rate:** After any AC change, 100% of active (not Done) subtasks must be re-checked for relevance; Done subtasks are flagged only, never modified
- **QG re-pass rate:** If QG fails after 2 auto-fix attempts on an update, the update is structurally inconsistent — return to Phase 2 and re-classify the change type

### Expert Decision Criteria

- If the change removes an AC that a subtask exclusively covers → do NOT delete the subtask silently; flag it for the assignee and surface a "descope decision" to the user before applying the update
- If the story is `In Progress` (sprint active) and the change type is HIGH (Remove AC, Change scope) → escalate to the user with an explicit sprint impact warning before proceeding; mid-sprint scope reduction affects team velocity metrics
- If `start_date` or `due_date` changes → always run HR8 subtask alignment; never skip even if the user says "just update the story dates"; date misalignment silently corrupts sprint burndown
- If change type is "Format only" → skip Phases 2-3 entirely; go directly to Phase 4 Generate Update with a format-migration template; QG must still pass
- If the story narrative's persona changes → this is a HIGH-impact change equivalent to "Business value change"; the story may no longer fit its parent epic scope — run A4 alignment check from `/verify-issue` before applying

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Subtask still covers descoped AC after story update | Phase 2 subtask impact analysis skipped or dismissed | Fetch all subtasks post-update via `jira_search(jql="parent={{PROJECT_KEY}}-XXX")`; compare each subtask objective against current story ACs; flag orphaned subtasks |
| Story QG fails after adding a well-written AC | New AC uses implementation language ("Implement X") instead of outcome language ("User sees X") | Rewrite AC using Given-When-Then outcome format; implementation ACs consistently fail the Testable criterion |
| Date update causes HR8 violation | Subtask dates not adjusted after parent date shift | Run `sprint_subtask_alignment.py --sprint <id>` immediately after any parent date change; verify with `jira_get_issue(fields="{{START_DATE_FIELD}},duedate")` per subtask |
| Update applied but cache returns stale data | HR6 `cache_invalidate` not called after `acli` write | Call `cache_invalidate(issue_key)` immediately after every write; verify with `cache_get_issue` that the summary/description reflects the change |
| "Preserve Intent" rule prevents a legitimate redesign | Story has fundamentally changed in scope but `/update-story` is being used instead of creating a new story | If the "So that" benefit clause changes, close the current story and create a new one via `/create-story`; don't patch a misaligned story |

### Authoritative References

- **Atlassian, "Definition of Ready" (2024):** "Review your DoR regularly — if you notice the team is regularly not completing all their work in a sprint, it likely means your DoR needs to be reviewed"; story updates that bypass the QG re-check are the most common DoR evasion
- **Mike Cohn, "Agile Estimating and Planning" (2005):** Scope changes during a sprint should be logged as new backlog items and traded against existing items of equal size; silent in-sprint AC additions are the most common cause of sprint overcommitment
- **Ron Jeffries (XP):** "A story's value proposition is the contract with the customer — changing it mid-sprint without discussion is a contract breach"; the Preserve Intent phase formalises this boundary
- **DEEP Backlog criteria (Mike Cohn):** Detailed Appropriately, Estimated, Emergent, Prioritised — the "Emergent" criterion explicitly allows story evolution; the key is that evolution is conscious and impact-assessed, not accidental

---

## References

- [Update Workflow Patterns](../../../references/update-workflow.md) — common Phase 5 QG, Phase 6 apply, gate phrases, preserve intent structure
- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Story Template](../../../references/templates-story.md) - Story ADF template + best practices
- [Verification Checklist](../../../references/verification-checklist.md) - INVEST, AC quality
