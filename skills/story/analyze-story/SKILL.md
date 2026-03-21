---
name: analyze-story
disable-model-invocation: true
context: fork
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Analyze User Story and create Sub-tasks + Technical Note with a 7-phase TA workflow
  MANDATORY: Must explore codebase before creating Sub-tasks
argument-hint: "[issue-key]"
---

# /analyze-story

**Role:** Senior Technical Analyst
**Output:** Sub-tasks + Technical Note

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`

## Context Object (accumulated across phases)

| Phase | Adds to Context |
| ----- | -------------- |
| 1. Discovery | `story_data`, `epic_context`, `vs_assignment` |
| 2. Impact | `services_impacted[]`, `vs_verified` |
| 3. Explore | `file_paths[]`, `patterns[]`, `dependencies[]` |
| 4. Design | `subtask_designs[]` |
| 5. Alignment | `alignment_checklist` |
| 5b. QG | `qg_score`, `passed_qg` |
| 6. Create | `subtask_keys[]` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

### 1. Discovery

- `Agent(name: "issue-bootstrap"): {{PROJECT_KEY}}-XXX --depth=full` → receives story + epic + subtasks context in one pass (cache-first, no redundant MCP calls)
- Read: Narrative, ACs, Links, Epic context from bootstrap output
- **⛔ GATE — DO NOT PROCEED** without user confirmation of story understanding.

### 2. Impact Analysis

| Service | Impact | Reason |
| --- | --- | --- |
| Backend | ✅/❌ | [why] |
| Admin | ✅/❌ | [why] |
| Website | ✅/❌ | [why] |

**⚡ Event Flow (optional — include for complex domains):**

| Command | Event Emitted | Consumer(s) | Side Effect |
| --- | --- | --- | --- |
| [user action] | [DomainEvent] | [service/policy] | [state change] |

> Use when story has cross-service event flow or policy trigger — helps Phase 4 subtask design be more accurate

**VS Verification:** Story touches all layers for e2e slice? (not layer-only)

**🟡 REVIEW** — Present impact table + VS verification to user. Proceed unless user objects.

### 3. Codebase Exploration ⚠️ MANDATORY

> [Parallel Explore](../../../references/workflow-patterns.md#parallel-explore): Launch 2-3 agents (Backend/Frontend/Shared) IN PARALLEL.
> Validate paths with Glob. Generic paths REJECTED. Re-explore max 2 attempts.
> See [shared-references/subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for codebase exploration requirements, scope format, AC specificity, alignment check, and QG subtasks.

### 4. Design Sub-tasks

**Tech Lead Decomposition — dependency ordering:**

```text
1. Data layer (migration + model)   ← foundation, blocks everything
2. Auth/OAuth (if new auth flow)    ← must exist before API validates identity
3. Backend API (endpoints + routes) ← FE service contract depends on this
4. Backend service/channel          ← business logic, depends on model
5. FE service layer                 ← depends on BE API contract
6. FE component/page                ← depends on FE service
7. FE interactions/events           ← depends on FE component + FE service
```

- 1 sub-task per service boundary (split only if complexity warrants)
- **VS Integrity:** Each subtask contributes to VS completion (not horizontal layer)
- Summary: `[TAG] - Description`
- ACs: Thai narrative + English technical terms

- **🔄 ITERATE** — Present subtask design as plan cards (tag, scope files, ACs, OE per subtask). Ask: Approve all / Annotate (specify subtask #) / Major rework.
  - Annotate → user specifies subtask + notes → revise ONLY annotated subtasks → re-present (max 3 rounds)
  - Approve → proceed to Alignment Check
  - Major rework → back to Codebase Exploration
  - See [Annotation Cycle](../../../references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 5. Alignment Check

> **🟢 AUTO** — Verify programmatically. Auto-fix misalignment. Escalate only if unfixable.
> See [shared-references/subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for codebase exploration requirements, scope format, AC specificity, alignment check, and QG subtasks.

### 5b. Quality Gate — Subtasks (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT create subtasks in Jira without QG ≥ 90%.
> See [shared-references/subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for codebase exploration requirements, scope format, AC specificity, alignment check, and QG subtasks.

### 6. Create Artifacts

> **🟢 AUTO** — Create → verify parent → edit descriptions. All automated. Escalate only if parent verify fails after retry.
> HR5: Two-Step + Verify Parent. acli does not support the `parent` field. MCP may silently ignore parent.
> [Two-Step Subtask](../../../references/workflow-patterns.md#two-step-subtask-creation): MCP create shell → verify parent → acli edit. Batch ≥3: create all → verify all → edit all.
> **🟢 AUTO** — HR6: `cache_invalidate(subtask_key)` after EVERY Atlassian write.
> **🟢 AUTO** — HR3: If assignee needed, use `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).

**Set subtask estimation (after verify parent, before acli edit):**

```text
MCP: jira_update_issue(issue_key="ABC-YYY", additional_fields={
  "timetracking": {"originalEstimate": "<N>h"},  # Original Estimate (from ⏱️ panel)
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",             # Start Date (within parent range — HR8)
  "duedate": "YYYY-MM-DD"                        # Due Date (within parent range — HR8)
})
# ⚠️ HR10: NEVER set sprint on subtasks — inherits from parent
```

- Technical Note (if needed):
  - Simple text → `MCP: confluence_create_page`
  - With code blocks → Python script (see `.claude/skills/utilities/atlassian-scripts/SKILL.md`)

### 7. Handoff

```text
## TA Complete: [Title] ({{PROJECT_KEY}}-XXX)
Sub-tasks: ABC-YYY, ABC-ZZZ
→ Use /create-testplan {{PROJECT_KEY}}-XXX to continue
```

---

> See [references/batch-creation.md](references/batch-creation.md) for the batch pattern when creating ≥3 sub-tasks.

---

> See [references/examples.md](references/examples.md) for a full input/output example.

---

## Examples

### ✅ Good

```text
/analyze-story {{PROJECT_KEY}}-123                   # existing story key → Phase 1 bootstraps from Jira, all 7 phases run correctly
/analyze-story {{PROJECT_KEY}}-456                   # story with complex cross-service ACs → codebase exploration discovers real file paths per service
/analyze-story {{PROJECT_KEY}}-789                   # story already has epic context → event flow table auto-populated in Phase 2
```

### ❌ Bad

```text
/analyze-story                           # no issue key → Phase 1 has nothing to bootstrap; skill cannot proceed
/analyze-story {{PROJECT_KEY}}-10                    # passing an Epic key — analyze-story expects a Story, not an Epic; orphan subtasks will be created
/analyze-story "add payment feature"     # free-text description instead of key — story doesn't exist yet; use /create-story instead
/analyze-story {{PROJECT_KEY}}-123 --skip-explore   # skipping codebase exploration is not a valid flag and violates the MANDATORY explore phase
```

**Common mistakes:**

- Passing an Epic key instead of a Story key — subtasks will be parented to the Epic directly, breaking hierarchy (HR5 will catch this but wastes a cycle).
- Skipping or rushing through Phase 3 codebase exploration — generic file paths (e.g. `src/controllers/`) get rejected at QG; real module paths are required.
- Running `/analyze-story` on a Story that already has subtasks without first checking for duplicates — results in double subtask creation; run `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks` first to review existing coverage.
- Using `/analyze-story` when the Story doesn't exist yet — run `/create-story` instead to go through the full PO+TA combined workflow.

## References

- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Subtask Template](../../../references/templates-subtask.md) - Subtask ADF template + best practices
- [Vertical Slice Guide](../../../references/vertical-slice-guide.md) - VS decomposition, patterns
- [Tool Selection](../../../references/tools.md) - Tools, service tags, effort sizing
- [Subtask Design Patterns](../../../references/subtask-design-patterns.md) — codebase exploration, scope format, AC specificity, alignment check, QG subtasks
- After creation: `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks`
