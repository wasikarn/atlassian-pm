---
name: analyze-story
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Analyze User Story and create Sub-tasks — vibe mode by default (fast, no ceremony)
  MANDATORY: Must explore codebase before creating Sub-tasks
  Use --thorough for full review gates + annotation workflow

  Triggers: "analyze story", "TA", "technical analysis", "create subtasks", "break down story", "explore story", "วิเคราะห์ story"
  Use when: exploring an existing Story to design its implementation Sub-tasks (TA role). Start here when a Story is already created and needs Sub-tasks.
  Do NOT use for: creating a new Story from scratch (use create-story); updating existing Sub-tasks (use sync-artifacts).
argument-hint: "[--thorough | --skip-explore] [issue-key]"
effort: high
---

> **⚠️ DEPRECATED in v3.0.0:** This skill is replaced by `/create-task` (feature mode with --thorough).
> Task descriptions now include file paths and implementation hints directly — no separate analysis step needed.

# /analyze-story

**Role:** Senior Technical Analyst
**Output:** Sub-tasks + Technical Note

## Mode Selection

| Flag | Behavior | Interactions |
| --- | --- | --- |
| *(none)* | **Vibe (default)** — auto-fetch, skip REVIEW gates, single-pass + Implementation Hints | 0 |
| `--thorough` | **Thorough** — confirmation gates, ITERATE on design (max 3 rounds), all REVIEW gates | Multiple |
| `--skip-explore` | Skip Phase 3. Caller supplies file paths directly in prompt. | 0 |

> Strip `--thorough` / `--skip-explore` from the issue key before proceeding.

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`

## Context Object

| Phase | Adds |
| --- | --- |
| 1. Discovery | `story_data`, `epic_context`, `vs_assignment`, `domain_context` |
| 2. Impact | `services_impacted[]`, `vs_verified` |
| 3. Explore | `file_paths[]`, `patterns[]`, `dependencies[]` |
| 4. Design | `subtask_designs[]` |
| 5. Alignment | `alignment_checklist` |
| 6. QG | `qg_score`, `passed_qg` |
| 7. Create | `subtask_keys[]` |

> **Workflow Patterns:** [workflow-patterns.md](../../../references/workflow-patterns.md)

## Phases

### 1. Discovery

**Goal:** Full story context (narrative, ACs, epic linkage, domain knowledge) before design.
**Constraints:** HR6 — invalidate cache after writes; story must be Story type (not Epic).

> **🟢 PARALLEL** — Single message, 2 calls:
>
> 1. `cache_get_issue(STORY-KEY)` → fallback `jira_get_issue(fields="summary,description,status,parent,subtasks,labels,customfield_10016")`
> 2. `jira_search(jql="parent=STORY-KEY", fields="summary,status,customfield_10016", limit=20)`

If `parent` set → fetch epic via `cache_get_issue(EPIC-KEY)`.

**Story Readiness Pre-check (🟢 AUTO):**

| Check | Pass | If Fail |
| --- | --- | --- |
| ACs defined | ≥ 1 AC panel in description | ⛔ STOP — suggest `/create-story` |
| Story type | `issuetype.name = "Story"` | ⛔ STOP — orphan subtasks |
| Not Done | Status not Done/Closed/Cancelled | ⚠️ Warn |
| Epic linked | `parent` field set | ⚠️ Warn — broken VS traceability |
| No subtasks | `subtasks[]` empty | ⚠️ Warn — suggest `/sync-artifacts` |

**If ACs or type fail → ⛔ STOP.** If status/epic/subtask warn → 🟡 REVIEW, continue on confirm.

**Confluence Domain Knowledge (🟢 AUTO — non-blocking):**
`cache_search_confluence(query="[story_title_keywords]", space_key="<space_key>", limit=3)` — extract business rules/constraints into `domain_context`; skip silently if none found.

**Mode:**

- **Vibe:** Auto-proceed after pre-check passes. Show brief story summary, no confirmation wait.
- **--thorough:** ⛔ GATE — confirm story understanding before proceeding.

### 2. Impact Analysis

**Goal:** Identify impacted services; verify vertical slice (not horizontal layer).

| Service | Impact | Reason |
| --- | --- | --- |
| Backend | ✅/❌ | [why] |
| Admin | ✅/❌ | [why] |
| Website | ✅/❌ | [why] |

**⚡ Event Flow (complex domains):**

| Command | Event Emitted | Consumer(s) | Side Effect |
| --- | --- | --- | --- |
| [action] | [DomainEvent] | [service/policy] | [state change] |

> If event consumer appears in Event Flow but not Impact table → add before Phase 3.

- **Vibe:** 🟢 AUTO — generate + proceed immediately.
- **--thorough:** 🟡 REVIEW — present to user, proceed unless objection.

### 3. Codebase Exploration ⚠️ MANDATORY

**Goal:** Discover real file paths, patterns, dependencies for every impacted service.
**Constraints:** Generic paths (e.g. `src/controllers/`) REJECTED — re-explore max 2 attempts. Skip `--skip-explore` entirely; use caller-supplied paths as `file_paths[]`.

> Launch **1 Explore agent** scoped to all impacted services. Validate paths with Glob.
> See [subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for exploration requirements, scope format, AC specificity, alignment check.

### 4. Design Sub-tasks

**Goal:** Subtask designs with real file paths, dependency-ordered, 1 per service boundary, each AC traced.
**Constraints:** Count target 3–6; each story AC in ≥1 subtask objective. → ADF format: [templates-subtask.md](../../../references/templates-subtask.md)

**Phase-based ordering:**

| Phase | Contains | Marker |
| --- | --- | --- |
| `Setup` | Migration, config, scaffolding, env vars | [P] if independent |
| `Foundational` | Core service/model that blocks feature subtasks | Sequential |
| `Feature` | Implementation subtasks (grouped by service) | [P] across services |
| `Polish` | Docs, monitoring, cleanup, tech-note | [P] always |

```text
Phase: Setup
  1. [BE] - DB migration + model [P]
  2. [BE] - Config/env setup [P]
Phase: Foundational
  3. [BE] - Core service (depends on Setup)
Phase: Feature
  4. [BE] - API endpoints [P]
  5. [FE-Admin] - UI component [P]
Phase: Polish
  6. [QA] - Test plan (depends on Feature)
```

> Dependency summary shown before subtask list. `[P]` = parallelizable (different files, no deps within phase).

- Summary: `[TAG] - Description` · ACs: Thai narrative + English technical terms
- **VS Integrity:** Each subtask contributes to VS completion (not horizontal layer).

- **Vibe:** Single-pass. Add **Implementation Hints** per subtask (Entry Point, Pattern to Follow, Test Command, Related API, Dependencies) — see [templates-vibe.md](../../../references/templates-vibe.md). Proceed to Alignment immediately.
- **--thorough:** 🔄 ITERATE — present plan cards (tag, scope files, ACs, OE). Approve / Annotate (revise only annotated, max 3 rounds) / Major rework → back to Phase 3. See [Annotation Cycle](../../../references/workflow-patterns.md#annotation-cycle-iterate-gate).

### 5. Alignment Check

**Goal:** Every story AC maps to ≥1 subtask objective; VS integrity holds.
**Constraints:** HR9 — auto-fix misalignment; escalate only if unfixable.

> **🟢 AUTO** — Verify programmatically. Auto-fix. Escalate only if unfixable.
> See [subtask-design-patterns.md](../../../references/subtask-design-patterns.md).

### 6. Quality Gate (MANDATORY)

**Goal:** All subtask designs ≥ 90% before any Jira write.
**Constraints:** HR1 — NEVER create without QG ≥ 90%; max 1 fix cycle.

**🟢 AUTO (validate_adf.py):**

```bash
uv run scripts/api/validate_adf.py {{artifacts_dir}}/subtask-*.json --type subtask --json
```

Score ≥ 90 = PASS. If FAIL → check `issues[].fix_hint` → `--fix` → re-score.

**🟢 AUTO** — Record: `python scripts/qg_record.py --issue-key "STORY_KEY" --type Subtask --score QG_SCORE --status PASS_OR_FAIL --service "[TAG]" --checks-failed "IDS"`

### 7. Create Artifacts

**Goal:** Create subtasks in Jira with correct parent, estimation, dates; create Technical Note if needed.
**Constraints:** HR5 Two-Step · HR6 cache_invalidate · HR3 acli assignee · HR10 no sprint on subtasks · HR8 dates within parent range.

> **🟢 AUTO** — Create → verify parent → edit descriptions. Escalate only if parent verify fails after retry.
> [Two-Step Subtask](../../../references/workflow-patterns.md#two-step-subtask-creation): MCP create → verify `parent.key` via `jira_get_issue` → acli edit if missing.
> Batch ≥3: create all → verify all → edit all.

Set estimation after verify parent:

```text
jira_update_issue(issue_key, additional_fields={
  "timetracking": {"originalEstimate": "<N>h"},
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",   # Start Date (HR8: within parent range)
  "duedate": "YYYY-MM-DD"              # Due Date (HR8: within parent range)
})
# ⚠️ HR10: NEVER set sprint on subtasks
```

Technical Note: simple text → `confluence_create_page` · with code blocks → Python script ([atlassian-scripts](../../utilities/atlassian-scripts/SKILL.md)).

### 8. Handoff

```text
## TA Complete: [Title] ({{PROJECT_KEY}}-XXX)
Sub-tasks: ABC-YYY, ABC-ZZZ
→ Use /create-testplan {{PROJECT_KEY}}-XXX to continue
```

> Batch pattern (≥3 subtasks): [references/batch-creation.md](references/batch-creation.md)
> Full example: [references/examples.md](references/examples.md)

## Examples

```text
✅ /analyze-story {{PROJECT_KEY}}-123              # story key → all 8 phases
✅ /analyze-story {{PROJECT_KEY}}-456 --thorough  # full gates + annotation
✅ /analyze-story {{PROJECT_KEY}}-789 --skip-explore  # caller supplies file paths

❌ /analyze-story                     # no key → cannot proceed
❌ /analyze-story {{PROJECT_KEY}}-10               # Epic key → orphan subtasks
❌ /analyze-story "add payment"       # free text → use /create-story
```

**Common mistakes:** Passing Epic key (HR5 catches but wastes cycle) · generic file paths rejected at QG · running on story with existing subtasks without `/verify-issue --with-subtasks` first · running when story doesn't exist yet (use `/create-story`).

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[ADF Core Rules](../../../references/templates-core.md) · [Subtask Template](../../../references/templates-subtask.md) · [Vertical Slice Guide](../../../references/vertical-slice-guide.md) · [Tool Selection](../../../references/tools.md) · [Subtask Design Patterns](../../../references/subtask-design-patterns.md)

After creation: `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks`
