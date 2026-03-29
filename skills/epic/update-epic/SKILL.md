---
name: update-epic
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__confluence_search, mcp__mcp-atlassian__confluence_get_page, mcp__mcp-atlassian__confluence_update_page, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Update an existing Epic with a 6-phase update workflow

  Phases: Fetch Current → Impact Analysis → Preserve Intent → Generate Update → Quality Gate → Apply Update

  Supports: adjust scope, update RICE, add success metrics, format migration

  Triggers: "update epic", "edit epic", "adjust epic", "แก้ไข epic", "update RICE", "fix epic scope"
  Use when: modifying scope, RICE score, success metrics, or description of an existing Epic
  Do NOT use for: creating new epics (use create-epic); story updates (use update-story)
argument-hint: "[issue-key] [changes]"
effort: medium
---

# /update-epic

**Role:** Senior Product Manager
**Output:** Updated Epic

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Fetch | `epic_data`, `child_stories[]`, `epic_doc` |
| 2. Impact | `change_type`, `impact_level` |
| 3. Preserve | `preservation_rules` |
| 4. Generate | `update_adf_json` |
| 5. QG | `qg_score`, `passed_qg` |
| 6. Apply | `applied` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

### 1. Fetch Current State

- `MCP: jira_get_issue(issue_key: "{{PROJECT_KEY}}-XXX")`
- `MCP: jira_search(jql: "parent = {{PROJECT_KEY}}-XXX OR 'Epic Link' = {{PROJECT_KEY}}-XXX", fields: "summary,status,assignee,issuetype,priority")` (**⚠️ NEVER add ORDER BY to parent queries**)
- `MCP: confluence_search(query: "Epic: [title]")`
- Read: RICE, objectives, success metrics, child stories
- **🟡 REVIEW** — Present current state to user. Proceed unless user objects.

### 2. Impact Analysis

| Change Type | Impact on Stories | Impact on Planning |
| --- | --- | --- |
| Add scope | Need to create new stories | Re-estimate |
| Remove scope | Need to close stories | Timeline shorter |
| RICE update | ❌ No impact | May reprioritize |
| Format only | ❌ No impact | ❌ No impact |

**⛔ GATE — DO NOT PROCEED** without user confirmation of changes.

### 3. Preserve Intent

- ✅ Adjusting wording/clarifying is allowed
- ✅ Updating RICE is allowed
- ✅ Adding success metrics is allowed
- ⚠️ Be careful changing scope (affects stories)
- ❌ Do not change core business value without informing

### 4. Generate Update

> **⚠️ MANDATORY:** Read `references/templates-epic.md` before generating any ADF. Use `panel` nodes — NEVER use `heading` nodes in issue descriptions.

- Generate ADF JSON → `{{artifacts_dir}}/tp-xxx-epic-update.json`
- Show comparison: Before/After for RICE, objectives, scope
- **⛔ GATE — DO NOT APPLY** without user approval of all generated changes.

### 5. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send updates to Atlassian without QG ≥ 90%.

> [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`

### 6. Apply Update

> **🟢 AUTO** — If QG passed → apply automatically. No user interaction needed.

```bash
acli jira workitem edit --from-json {{artifacts_dir}}/tp-xxx-epic-update.json --yes
```

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after apply.

**Output:**

```text
## Epic Updated: [Title] ({{PROJECT_KEY}}-XXX)
Changes: [list]
→ Update Epic Doc if needed
→ Review stories: ABC-YYY, ABC-ZZZ
```

---

## Examples

### ✅ Good

```text
/update-epic {{PROJECT_KEY}}-50                              # reads current state first, then asks what to change
/update-epic {{PROJECT_KEY}}-50 "add success metrics"        # targeted change — updates metrics section without touching scope
/update-epic {{PROJECT_KEY}}-50 "remove payment gateway scope, out of v2"   # scope reduction with rationale — triggers subtask impact check
/update-epic {{PROJECT_KEY}}-50 "update RICE: confidence 70% → 85%"        # RICE-only update, no story impact
```

### ❌ Bad

```text
/update-epic                                     # no epic key → can't fetch current state, workflow stalls
/update-epic "change epic title"                 # no issue key — must pass {{PROJECT_KEY}}-XXX as first argument
/update-epic {{PROJECT_KEY}}-50 "rewrite everything"         # major rework without reading current ACs → risks overwriting intentional decisions
/update-epic {{PROJECT_KEY}}-50 {{PROJECT_KEY}}-51                       # update-epic handles one epic at a time; batch updates not supported
```

**Common mistakes:**

- Changing scope without checking child stories first — Phase 2 impact analysis exists for this reason; skipping it means removed scope stays in open stories creating {{PROJECT_KEY}} misalignment.
- Passing changes as free-form text that covers multiple unrelated sections — break into separate update calls (RICE update + scope update) so each Phase 4 diff is reviewable.
- Running update-epic to fix formatting only without checking whether child story ACs still align — use `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks` after any scope change.

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.
> See [references/epic-structure.md](references/epic-structure.md) for the Epic ADF section layout and panel type reference.

## 🎓 Domain Expert Notes

### Why This Approach

Epic updates are scope change management decisions, not just text edits. The 6-phase workflow enforces the impact analysis step (Phase 2) that most teams skip, leading to orphaned stories (child stories referencing removed scope) and misaligned burndown charts. The "Preserve Intent" phase (Phase 3) implements the product management principle that core business value should only change with explicit stakeholder re-alignment, not as a side effect of wording improvements.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SAFe Epic Lifecycle (Portfolio Kanban) | Phase 2 Impact Analysis — change_type classification | SAFe defines four epic lifecycle states: Funnel → Analyzing → Portfolio Backlog → Implementing → Done; scope changes during Implementing require LPM re-approval in SAFe, equivalent to the Phase 2 GATE in this skill |
| Change Impact Analysis (PMBOK) | Phase 2 — impact matrix by change type | Structured impact assessment prevents the "small wording change" that silently invalidates 3 sprint's worth of story ACs |
| Configuration Baseline / Scope Freeze | Phase 3 Preserve Intent rules | Preserving intent mirrors the concept of a configuration baseline — once an epic is in-flight, changes to core business value require a formal change request, not silent editing |
| OKR health check cadence | Monthly epic review model | Epic health reviews (monthly) should ask: (1) Is the OKR this epic supports still valid? (2) Has scope drifted from original hypothesis? (3) Are child stories still aligned to current ACs? |
| ROAM for scope risks | Phase 2 — impact on planning | When scope is removed, blocked stories must be ROAM-categorized: Resolved (story closed), Owned (reassigned to another epic), Accepted (deferred), Mitigated (story scope reduced to fit remaining epic) |

### Key Metrics

- **Epic scope stability ratio:** Number of scope-change updates / total updates on a given epic; > 30% scope changes signals the original discovery phase was insufficient — the epic was created before the problem was understood
- **Child story orphan rate:** After a scope reduction update, percentage of child stories that remain open but reference removed scope; target 0% within 1 sprint of the epic update
- **Update-to-verify lag:** Time between `update-epic` completion and running `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks`; any lag > 24h risks stories and epic ACs diverging silently
- **RICE drift:** Delta between original RICE score at epic creation and current score after updates; > 50% drift means the epic should be re-evaluated for continuation vs. cancellation

### Expert Decision Criteria

- **Scope reduction vs. epic split:** If more than 40% of original scope is being removed, consider creating a new epic for the retained scope rather than editing the current one. Removing scope leaves a confusing history of "what this epic was supposed to be."
- **RICE-only update threshold:** RICE updates that don't change scope (Confidence or Impact revision) are safe to apply without child story review. RICE updates that change Effort imply scope change — treat as scope update and run full Phase 2.
- **Format-only update safety:** Format migrations (ADF panel type changes, section reordering) are genuinely safe only if no AC text is touched. If reformatting requires paraphrasing any AC, it is a scope change, not a format change.
- **When to cascade to child stories:** Scope additions always require new child stories. Scope reductions require closing or descoping existing child stories within the same sprint as the epic update — never leave orphaned stories open.
- **Epic cancellation trigger:** If an update removes > 60% of original scope or the core business value has changed fundamentally, the correct action is to close the epic and create a new one. Heavily edited epics accumulate misleading history that confuses future sprint planning.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Child stories reference scope no longer in epic | Scope was removed from epic but child stories were not updated | Always run `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks` after any scope change; the A1-A6 alignment checks will surface orphaned stories |
| RICE score becomes stale after market changes | RICE updated at creation, never revisited | Add a monthly epic health review cadence; review RICE Reach and Confidence first — these change most with market/user feedback |
| Epic intent changed silently during "wording cleanup" | Editor paraphrased the business value without noticing the meaning shifted | Phase 3 Preserve Intent check: show Before/After diff of objectives section specifically; any change to the "why" requires stakeholder re-confirmation |
| Multiple small updates create incoherent epic description | Each update optimized its own section without reading the whole | Before generating any update in Phase 4, read the full current epic (Phase 1 fetch) and check narrative consistency end-to-end |
| Fix Version linked to epic with outdated scope | Fix Version was created before scope stabilized | Never create a Fix Version while an epic is actively in scope-change update cycles; wait for scope to stabilize across 2 consecutive sprints |

### Authoritative References

- SAFe 6.0 Lean Portfolio Management: Epics in "Implementing" state require LPM approval for scope changes that affect the MVP definition or Business Outcome Hypothesis — the Phase 2 GATE is the lightweight equivalent for team-level epics
- Atlassian Agile Coach (Jira Epics guide): "As sprints are completed and understanding of customer needs increases, the scope of an epic will change" — planned scope evolution is healthy; untracked scope drift is not
- Roman Pichler — Product Strategy: Epic health reviews should happen monthly and assess both business validity (is the OKR still relevant?) and delivery health (are child stories progressing as expected?)
- Mike Cohn — *Agile Estimating and Planning*: Re-estimation after scope change is mandatory, not optional; teams that update scope without re-estimating carry false velocity data into future sprint planning

## References

- [Update Workflow Patterns](../../../references/update-workflow.md) — common Phase 5 QG, Phase 6 apply, gate phrases, preserve intent structure
- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Epic Template](../../../references/templates-epic.md) - Epic ADF template + best practices
- [Tool Selection](../../../references/tools.md) - Tool selection
