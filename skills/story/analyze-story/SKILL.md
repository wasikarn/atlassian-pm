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

## 🎓 Domain Expert Notes

### Why This Approach

Technical analysis works backward from user value: first establish what the story delivers end-to-end (vertical slice), then decompose into the minimum number of service-boundary subtasks that together produce that value. Forcing codebase exploration before design prevents subtasks from being written to abstract layers rather than real implementation paths.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Vertical Slicing (Mike Cohn) | Phase 2 VS Verification, Phase 4 VS Integrity | Ensures every subtask contributes to shippable value; avoids horizontal layer-only work that never independently ships |
| T-Shirt Sizing → Story Points | Phase 4 subtask OE (Original Estimate) | High-level sizing first (S/M/L) establishes confidence intervals before committing to hour estimates |
| Planning Poker consensus model | Phase 4 ITERATE annotation cycle | Subtask-level estimates require team discussion; single-expert estimates have 30-40% higher variance |
| Dependency Ordering (Critical Path) | Phase 4 Tech Lead decomposition | Data layer → Auth → API → Service → FE Service → FE Component mirrors real build dependency graph; violating this order causes blocked sprints |
| Event Storming (light) | Phase 2 Event Flow table | Command/Event/Consumer mapping surfaces cross-service side effects before subtask boundaries are drawn |

### Key Metrics

- **Subtask count per story:** Target 3-6 subtasks; fewer than 3 suggests under-decomposition or layer-only slice; more than 7 indicates the parent story may be too large (violates INVEST Small)
- **Codebase exploration coverage:** Every service marked "impacted" in Phase 2 must have at least one real file path discovered in Phase 3; zero file paths = blocked QG
- **Estimation variance threshold:** If subtask OE sum deviates more than 40% from parent SP equivalent (1 SP ≈ 4h), flag for re-estimation before creation
- **AC-to-subtask coverage ratio:** Each story AC must be traceable to at least one subtask objective; unmapped ACs indicate scope gaps caught in Alignment Check (Phase 5)

### Expert Decision Criteria

- If a subtask covers more than one service boundary → split it; cross-service subtasks create ambiguous ownership and blur burndown attribution
- If Phase 3 exploration returns only generic paths (e.g. `src/controllers/`) → reject and re-explore; generic paths produce generic ACs that fail QG
- If the Event Flow table (Phase 2) shows a consumer in a service NOT listed in the Impact table → add that service to the impact table before proceeding to Phase 3
- If story is in `In Progress` status when `/analyze-story` is called → verify no subtasks already exist (`/verify-issue --with-subtasks`) before creating new ones; duplicate subtask creation is the most common misuse of this skill
- Technical debt subtasks (refactoring, migration) should be explicitly labeled and estimated separately from feature subtasks — mixing them inflates velocity metrics

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| QG rejects subtask file paths | Phase 3 exploration used `find` or generic glob instead of `ast-grep` or service-specific paths | Re-run exploration using module-level paths; validate each path with Glob before designing ACs |
| Parent verify (HR5) fails silently | MCP `jira_create_issue` accepted the call but ignored the `parent` field | Always use Two-Step: create shell → `jira_get_issue(fields="parent")` → if missing, fix via `jira_set_parent.py` before continuing |
| Subtask sum SP >> parent SP | Phase 4 decomposed at task granularity rather than service-boundary granularity | Merge subtasks that belong to the same service; aim for 1 subtask per service unless complexity clearly justifies a split |
| Subtasks don't cover all story ACs | Phase 4 subtask design referenced the story narrative but not each individual AC | Go through ACs one by one in Phase 4; each AC must appear in at least one subtask objective |
| Sprint burndown shows subtask work not decreasing | Subtask dates fall outside parent date range (HR8 violation) | Run `sprint_subtask_alignment.py` to redistribute dates within parent range |

### Authoritative References

- **Mike Cohn, "User Stories Applied" (2004):** Vertical slices must deliver a thin, complete, testable capability — "a story is not a task, it is a promise of a conversation"
- **Jeff Patton, "User Story Mapping" (2014):** Decompose from user journey activities → backbone tasks → subtasks; never decompose from technical layer first
- **Atlassian Engineering Blog:** Subtask granularity sweet spot is 4-8h per subtask; below 2h indicates over-decomposition that inflates ceremony overhead
- **Daniel Vacanti, "Actionable Agile Metrics" (2015):** Work items that cross service boundaries have 2-3x higher cycle time variability — minimize cross-service subtasks

---

## References

- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Subtask Template](../../../references/templates-subtask.md) - Subtask ADF template + best practices
- [Vertical Slice Guide](../../../references/vertical-slice-guide.md) - VS decomposition, patterns
- [Tool Selection](../../../references/tools.md) - Tools, service tags, effort sizing
- [Subtask Design Patterns](../../../references/subtask-design-patterns.md) — codebase exploration, scope format, AC specificity, alignment check, QG subtasks
- After creation: `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks`
