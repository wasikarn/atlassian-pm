---
name: story-full
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache-server, mcp-atlassian, mcp-confluence, acli]
description: |
  Create User Story + Sub-tasks in one complete workflow (PO + TA combined) with a 10-phase workflow

  Phases: Discovery → Write Story → INVEST → Create Story → Impact → Explore Codebase → Design → Alignment → Create Sub-tasks → Summary

  Composite: No need to copy-paste issue keys, context preserved throughout workflow

  Triggers: "story full", "create story + subtasks", "full workflow", "create story with subtasks", "story and subtasks"
argument-hint: "[story-description]"
---

# /story-full

**Role:** PO + TA Combined
**Output:** User Story + Sub-tasks (complete workflow)

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 0. Blueprint (optional) | `blueprint_page_id`, `selected_story_index`, `blueprint_acs_hints[]` |
| 1. Discovery | `epic_data`, `vs_assignment`, `user_requirements`, `user_context` |
| 2. Write Story | `story_narrative`, `acs[]`, `scope`, `dod` |
| 3. INVEST | `invest_score`, `vs_validated` |
| 3b. QG Story | `story_adf_json`, `story_qg_score` |
| 4. Create Story | `story_key` (ABC-XXX) |
| 5. Impact | `services_impacted[]`, `vs_verified` |
| 6. Explore | `file_paths[]`, `patterns[]`, `dependencies[]` |
| 7. Design | `subtask_designs[]` |
| 8. Alignment | `alignment_checklist` |
| 9. QG Subtasks | `qg_score`, `passed_qg` |
| 10. Create | `subtask_keys[]` |

> **Workflow Patterns:** See [workflow-patterns.md](../shared-references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Blueprint Handoff Check

> **Check first:** ดู conversation history ว่ามี `/feature-blueprint` output หรือไม่

**If `blueprint_backlog_map` is present in history:**

**Step 1 — แสดง story list:**
แสดง stories จาก blueprint เป็น numbered list (1-based) ให้ user เลือก:

```text
Blueprint stories:
1. [stories[0].title] — [stories[0].vs_label] ([stories[0].sp_estimate])
2. [stories[1].title] — [stories[1].vs_label] ([stories[1].sp_estimate])
...
```

Ask: "ต้องการสร้าง story ข้อไหน? (ระบุหมายเลข)"

- ถ้า index ไม่มีใน list → แสดง list ใหม่ให้ user เลือกอีกครั้ง

**Step 2 — Extract selected story (stories[N-1] where N = user's 1-based choice):**

- `stories[N-1].title` → ใช้เป็น story summary draft
- `stories[N-1].narrative_hint` → เริ่ม narrative จาก hint นี้
- `stories[N-1].acs_hint[]` → ใช้เป็น starting points สำหรับ ACs
- `stories[N-1].vs_label` → pre-assign VS label
- `stories[N-1].sp_estimate` → suggest SP (S/M/L)
- `blueprint_page_id` (ถ้ามี) → link ใน story description "References"
- ถ้า field ใด missing → ข้ามการ populate field นั้น

**Step 3 — Confirm before proceeding:**
แสดง summary:
> "Story: [title] | VS: [vs_label] | SP: [sp_estimate]\nใช้ข้อมูลจาก blueprint สำหรับ story นี้ confirm?"

**⛔ GATE** — รอ user confirm ก่อนดำเนินต่อ

**In Phase 1 (Discovery):**

- ✅ ยังคง fetch epic via `jira_get_issue` ถ้า epic key ใน blueprint → ได้ `epic_data`
- ❌ ข้าม interview questions (Who/What/Why/Constraints) — มีข้อมูลจาก blueprint แล้ว
- ❌ ข้าม VS assignment question — ใช้ `vs_label` จาก blueprint แทน

ดำเนินต่อ Phase 2 Write User Story โดยใช้ blueprint context เป็น draft

**If no blueprint in history:** ดำเนิน Phase 1 Discovery ปกติ (ถาม Who/What/Why/Constraints)

---

## Part A: Create Story (Phases 1-4)

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed` as you work.

### 1. Discovery

- Ask: Who? What? Why? Constraints?
  - **Story Context:** What is the user currently doing? What's difficult? (for 📍 context line)
- If Epic exists → `MCP: jira_get_issue(issue_key: "ABC-XXX")` + read VS plan + Problem narrative
- **VS Assignment:** Which vertical slice? (`vs1-skeleton`, `vs2-*`, `vs-enabler`)
- **⛔ GATE — DO NOT PROCEED** without user confirmation of requirements + VS assignment.

### 2. Write User Story

```text
📍 [User's current situation — what they're doing, what's difficult]  ⚡ optional
As a [persona],
I want to [action],
So that [benefit].
```

- ⚡ **Context line:** Include when persona is new or workflow is complex — not needed for every story
- Define ACs, Scope, DoD
- **AC Naming:** Use `AC{N}: [Verb] — [Scenario Name]` (not just "AC1: Title")
- **VS Check:** Story delivers e2e value? All layers touched? (not shell-only)
- **🔄 ITERATE** — Present story draft as plan card (narrative, ACs, scope, DoD). Ask: Approve / Annotate / Major rework.
  - Annotate → user specifies items to change → revise ONLY those items → re-present (max 3 rounds)
  - Approve → proceed to INVEST validation
  - Major rework → back to Discovery
  - See [Annotation Cycle](../shared-references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 3. INVEST + VS Validation

- [ ] **I**ndependent - Not dependent on other stories
- [ ] **N**egotiable - Room for discussion
- [ ] **V**aluable - Clear business value
- [ ] **E**stimable - Can estimate effort
- [ ] **S**mall + **Vertical** - Completable in 1 sprint? **End-to-end slice?**
- [ ] **T**estable - All ACs verifiable in isolation

**VS Anti-pattern Check:**

- ❌ Shell-only (UI has no logic) → Add minimal happy path
- ❌ Layer-split (BE separated from FE) → Combine into single story

**🟢 AUTO** — Validate all criteria. If any fail or VS anti-pattern detected → auto-fix and re-validate. Escalate to user only if unfixable.

### 3b. Quality Gate — Story (HR1)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate to user only if still < 90% after 2 attempts.
> HR1: DO NOT send Story to Atlassian without QG ≥ 90%.

1. Generate ADF JSON → `tasks/story.json`
2. Score against `shared-references/verification-checklist.md` (Technical + Story Quality)
3. If < 90% → auto-fix → re-score (max 2 attempts)
4. If ≥ 90% → proceed to Phase 4 automatically
5. If still < 90% after 2 fixes → escalate to user

### 4. Create Story in Jira

> **🟢 AUTO** — If Phase 3b QG passed → create automatically. No user interaction needed.

```bash
acli jira workitem create --from-json tasks/story.json
```

**Labels (MANDATORY):** Feature label + VS label (e.g., `coupon-web`, `vs2-collect-e2e`)

**Capture story key → ABC-XXX**

> **🟢 AUTO** — HR6: `cache_invalidate(story_key)` after create.

**Set story estimation fields:**

```text
MCP: jira_update_issue(issue_key="ABC-XXX", additional_fields={
  "customfield_10016": <SP>,                  # Story Points (XS=1,S=2,M=3,L=5,XL=8)
  "customfield_10107": {"value": "<SIZE>"},   # Size
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",          # Start Date
  "duedate": "YYYY-MM-DD"                     # Due Date
})
```

> **🟢 AUTO** — HR6: `cache_invalidate(story_key)` after field update.

## Part B: Create Sub-tasks (Phases 5-10)

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed` as you work.

### 5. Impact Analysis

| Service | Impact | Reason |
| --- | --- | --- |
| Backend | ✅/❌ | [why] |
| Admin | ✅/❌ | [why] |
| Website | ✅/❌ | [why] |

**VS Verification:** Story touches all layers for e2e slice? (not layer-only)

**🟡 REVIEW** — Present impact table + VS verification to user. Proceed unless user objects.

### 6. Codebase Exploration ⚠️ MANDATORY

> [Parallel Explore](../shared-references/workflow-patterns.md#parallel-explore): Launch 2-3 agents (Backend/Frontend/Shared) IN PARALLEL.
> Validate paths with Glob. Generic paths REJECTED. Re-explore max 2 attempts.

**What each agent MUST discover:**

| Agent | Must Find |
|-------|-----------|
| Backend | Models/Migrations path, Controllers pattern, Routes file, Config enums (any enum to extend?), Auth middleware on similar routes, Existing similar implementation as REF |
| Frontend | Page dir structure, Service base pattern (`ApiBaseService`?), OAuth/auth lib, Shared UI components (dialogs, icons, layouts) with exact filenames |
| Shared/Config | `.env` variables consumed by feature, Types/interfaces, Error handling patterns |

**Critical validation:**

- Validate every filename with Glob — don't assume (typos exist in real codebases)
- Config enums that need new values → include as MODIFY in scope
- Auth middleware: which routes require `auth:publicApi`? Which are public?
- Find at least 1 REF pattern per subtask to guide developer

### 7. Design Sub-tasks

**Tech Lead Decomposition — dependency ordering:** See [analyze-story/SKILL.md](../analyze-story/SKILL.md) for TL decomposition ordering.

**Scope table format per subtask** (single Action | File table):

- `CREATE` — new file to create from scratch
- `MODIFY` — existing file to add/change code
- `REF` — existing file developer reads as pattern guide (no changes — just follow the pattern)
- **Minimum 1 REF row per subtask** — never leave developer without a pattern reference

**AC specificity requirements (Tech Lead level):**

- Reference actual method names from Phase 6: e.g., `LineAuthStrategy.handleCallback()`
- Specify exact HTTP endpoints + status codes: `POST /v2/notification/line-accounts → 201 or 409`
- Specify data contracts: `{ line_uid, display_name, avatar_url, access_token }`
- Specify error UI: toast color + exact error message text
- Specify env vars if consumed by new code

**Config/enum awareness:**

- New feature type → check if config enum needs a new value (add as MODIFY to scope)
- New unique constraint → specify explicitly in migration AC
- Middleware → document which middleware applies to each new route in AC

- 1 sub-task per service boundary (split only if complexity warrants)
- **VS Integrity:** Each subtask contributes to VS completion (not horizontal layer)
- Summary: `[TAG] - Description`
- ACs: Thai narrative + English technical terms

- **🔄 ITERATE** — Present subtask design as plan cards (tag, scope files, ACs, OE per subtask). Ask: Approve all / Annotate (specify subtask #) / Major rework.
  - Annotate → user specifies subtask + notes → revise ONLY annotated subtasks → re-present (max 3 rounds)
  - Approve → proceed to Alignment Check
  - Major rework → back to Codebase Exploration
  - See [Annotation Cycle](../shared-references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 8. Alignment Check

> **🟢 AUTO** — Verify programmatically. Auto-fix misalignment. Escalate only if unfixable.

- [ ] Sum of sub-tasks = Complete Story?
- [ ] No gaps? No scope creep?
- [ ] File paths exist? (validate with Glob)
- [ ] **VS integrity maintained?** (subtasks complete the slice, not horizontal)

If any check fails → auto-adjust subtask scope/design → re-check. Escalate to user only if gap cannot be resolved automatically.

### 9. Quality Gate — Subtasks (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT create subtasks in Jira without QG ≥ 90%.

> [QG Scoring Rules](../shared-references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Subtask Quality X/5 | Overall X%`

### 10. Create Sub-tasks

> **🟢 AUTO** — Create → verify parent → edit descriptions. All automated. Escalate only if parent verify fails after retry.
> HR5: Two-Step + Verify Parent. acli does not support the parent field. MCP may silently ignore parent.

> [Two-Step Subtask](../shared-references/workflow-patterns.md#two-step-subtask-creation): MCP create shell → verify parent → acli edit. Batch ≥3: create all → verify all → edit all.

```text
# Step 1: Create shells (parallel)
MCP: jira_create_issue({project_key: "{{PROJECT_KEY}}", summary:"[BE] - ...", issue_type:"Subtask", additional_fields:{parent:{key:"ABC-XXX"}, timetracking:{originalEstimate:"4h"}}})
MCP: jira_create_issue({project_key: "{{PROJECT_KEY}}", summary:"[FE-Web] - ...", issue_type:"Subtask", additional_fields:{parent:{key:"ABC-XXX"}, timetracking:{originalEstimate:"4h"}}})

# Step 2: Verify parent (HR5) — DO NOT SKIP
MCP: jira_get_issue(issue_key: "ABC-YYY", fields: "parent") → confirm parent.key = "ABC-XXX"
MCP: jira_get_issue(issue_key: "ABC-ZZZ", fields: "parent") → confirm parent.key = "ABC-XXX"
# If parent missing → fix via REST API before continuing

# Step 2b: Set subtask dates + OE (HR8 alignment — dates must be within parent range)
MCP: jira_update_issue(issue_key="ABC-YYY", additional_fields={
  "timetracking": {"originalEstimate": "<N>h"},
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",  # Start Date (≥ parent start)
  "duedate": "YYYY-MM-DD"             # Due Date (≤ parent due)
})
# ⚠️ HR10: NEVER set sprint on subtasks — inherits from parent
# ⚠️ HR8: Distribute subtask dates evenly within parent date range

# Step 3: Update descriptions
acli jira workitem edit --from-json tasks/subtask-be.json --yes
acli jira workitem edit --from-json tasks/subtask-fe.json --yes
```

> **🟢 AUTO** — HR6: `cache_invalidate(subtask_key)` after EVERY Atlassian write.
> **🟢 AUTO** — HR3: If assignee needed, use `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).

### 11. Summary

```text
## Story Full Complete
Story: ABC-XXX
Sub-tasks: ABC-YYY [BE], ABC-ZZZ [FE-Admin]
→ /create-testplan ABC-XXX for QA
→ /verify-issue ABC-XXX --with-subtasks
```

## Benefits vs Separate Workflow

| Approach | When | Context |
| --- | --- | --- |
| `/story-full` | New story from scratch (default) | Preserved across all phases |
| `/analyze-story` | Story already exists, need subtasks only | Starts from Phase 5 |

## Example

**Input:** "สร้าง story + subtasks สำหรับ admin ดู ad report แบบ monthly"

**Output:**

- Story `ABC-3100`: [FE-Admin] - ดู Ad Report แบบรายเดือน (Monthly Ad Report)
  - AC1: Display — แสดง report table with impression, click, revenue per billboard
  - AC2: Filter — เลือกเดือน/ปี แล้ว report อัปเดตตามช่วงเวลา
  - AC3: Export — กดปุ่ม export ได้ไฟล์ CSV
- Sub-tasks:
  - `ABC-3101` [BE] - API endpoint `GET /api/reports/monthly` with date range filter
  - `ABC-3102` [FE-Admin] - Monthly report page + table component
  - `ABC-3103` [FE-Admin] - CSV export from report data

## References

- [ADF Core Rules](../shared-references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Story Template](../shared-references/templates-story.md) - Story ADF template + best practices
- [Subtask Template](../shared-references/templates-subtask.md) - Subtask ADF template + QA
- [Vertical Slice Guide](../shared-references/vertical-slice-guide.md) - VS patterns, decomposition, labels
- [Verification Checklist](../shared-references/verification-checklist.md) - INVEST, quality checks
