# Workflow Patterns (Shared Reference)

> Referenced by SKILL.md files — single source of truth for common workflow patterns.

---

## Gate Levels

| Level | Symbol | Behavior |
| --- | --- | --- |
| **AUTO** | 🟢 | Validate automatically. Pass → proceed. Fail → auto-fix (max 2). Still fail → escalate to user. |
| **REVIEW** | 🟡 | Present results to user, wait for quick confirmation. Default: proceed unless user objects. |
| **APPROVAL** | ⛔ | STOP. Wait for explicit user approval before proceeding. |
| **ITERATE** | 🔄 | Present structured plan → ask user to annotate/approve → if annotated: revise + re-present (max 3 rounds) → if approved: proceed. |

---

## Phase Tracking

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed` as you work.

---

## Quality Gate Scoring

> HR1: NEVER create/edit issues on Jira/Confluence before QG ≥ 90%.

Score against `verification-checklist.md`:

1. Score each check with confidence (0-100%). Only report issues with confidence ≥ 80%.
2. Report: `Technical X/5 | [Domain] Quality X/N | Overall X%`
3. If < 90% → auto-fix → re-score (max 2 attempts)
4. If ≥ 90% → proceed to next phase automatically
5. If still < 90% after 2 fixes → escalate to user
6. Low-confidence items (< 80%) → flag as "needs review" but don't fail QG

### Report Format by Type

| Skill Type | Report Format |
|-----------|-------------|
| Epic | `Technical X/5 \| Epic Quality X/4 \| Overall X%` |
| Story | `Technical X/5 \| Story Quality X/6 \| Overall X%` |
| Subtask | `Technical X/5 \| Subtask Quality X/5 \| Overall X%` |
| Task | `Technical X/5 \| Quality X/6 \| Overall X%` |
| QA | `Technical X/5 \| QA Quality X/5 \| Overall X%` |

---

## Two-Step Subtask Creation

> HR5: MCP `jira_create_issue` may silently ignore parent field → orphan subtask.

**Step 1:** MCP `jira_create_issue` (create shell + parent link) — parallel calls OK

```text
MCP: jira_create_issue({
  project_key: "{{PROJECT_KEY}}",
  summary: "[TAG] - Description",
  issue_type: "Subtask",
  additional_fields: {parent: {key: "ABC-XXX"}}
})
```

**Step 2:** Verify parent — `jira_get_issue(issue_key, fields: "parent")` → confirm `parent.key`

- If parent missing → fix via REST API or re-create

**Step 3:** `acli jira workitem edit --from-json {{artifacts_dir}}/subtask-xxx.json --yes`

**Batch (≥3 subtasks):** Create all shells → verify all parents → batch edit descriptions

---

## Parallel Explore

> MANDATORY before creating subtasks — ensures real file paths, not generic guesses.

Launch 2-3 Explore agents **IN PARALLEL** (single message, multiple Task calls):

```text
# Agent 1: Backend (models, controllers, routes, services)
Task(subagent_type: "Explore", prompt: "Find [feature] in backend: models, controllers, routes, services")

# Agent 2: Frontend (pages, components, hooks, stores)
Task(subagent_type: "Explore", prompt: "Find [feature] in frontend: pages, components, hooks")

# Agent 3 (if needed): Shared/infra (config, middleware, types, utils)
Task(subagent_type: "Explore", prompt: "Find [feature] in shared: config, middleware, types")
```

Each agent returns: `file_paths[]`, `patterns[]`, `dependencies[]`
Merge results into context.

**Validation:** Validate file paths with Glob. If zero real paths found → re-explore (max 2 attempts). Generic paths like `/src/` are REJECTED.

**Conditional:** Skip if format-only changes (no new scope).

---

## Annotation Cycle (ITERATE Gate)

> Iterative plan review — user annotates, Claude revises, loop until approved.
> Inspired by [Boris Tane's workflow](https://boristane.com/blog/how-i-use-claude-code/): separate thinking from doing.

### Flow

1. Present structured plan (numbered items, not prose)
2. AskUserQuestion: "Approve" / "Annotate" / "Major rework"
3. If Annotate → user specifies items to change + notes
4. Claude revises ONLY annotated items (don't touch approved parts)
5. Re-present revised plan with diff summary → back to step 2
6. Max 3 rounds — if still not approved → escalate to user

### Plan Card Formats

**Story:**

| # | Section | Content |
|---|---------|---------|
| 1 | Narrative | 📍 context + As a/I want/So that |
| 2 | AC1 | AC1: [Verb] — [Scenario] |
| 3 | AC2 | AC2: [Verb] — [Scenario] |
| N | Scope | Services impacted |

**Subtask Design:**

| # | Subtask | Tag | Scope | ACs | OE |
|---|---------|-----|-------|-----|-----|
| 1 | Description | [BE] | 3 files | 2 ACs | 4h |
| 2 | Description | [FE-Web] | 4 files | 3 ACs | 6h |

### Rules

- **Revise only annotated items** — preserve approved parts unchanged
- **Show diff** each round (what changed vs previous version)
- **Max 3 rounds** per ITERATE gate — prevent infinite loops
- **"Major rework"** = go back to previous phase (re-explore, re-discover)
- **"Approve"** = proceed to next phase immediately

### AskUserQuestion Template

```text
AskUserQuestion({
  question: "Review [Story/Subtask Design] — approve or annotate?",
  options: [
    { label: "Approve", description: "Plan looks good — proceed to next phase" },
    { label: "Annotate", description: "I have notes — specify which items to change" },
    { label: "Major rework", description: "Needs significant changes — go back" }
  ]
})
```

If user selects "Annotate" → follow up asking which numbered items to change and what notes they have.

---

## HR Quick Reference

> Full definitions, examples, enforcement details: [hr-rules.md](hr-rules.md)
> Full hook inventory: [hooks-reference.md](hooks-reference.md)

| HR | Rule | Enforcement |
|----|------|-------------|
| HR1 | QG ≥ 90% before Atlassian writes | `pre_hr1_quality_gate.py` |
| HR3 | Assignee via `acli` only (never MCP) | `pre_hr3_block_mcp_assignee.py` |
| HR5 | Two-Step + Verify Parent | `pre_hr5_parent_verify_block.py` + `post_hr5_parent_verify_remind.py` |
| HR6 | `cache_invalidate(key)` after every write | `post_hr6_queue_invalidation.py` + `pre_hr6_stale_read_guard.py` |
| HR7 | Sprint ID lookup, never hardcode | `pre_hr7_sprint_id_guard.py` |
