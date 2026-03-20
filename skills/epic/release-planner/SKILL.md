---
name: release-planner
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache-server, mcp-atlassian, mcp-confluence, acli]
description: |
  Create a multi-sprint release plan from epics — calculates velocity-based timeline, maps dependencies,
  generates Confluence release page + Jira Fix Version.
  Triggers: "release plan", "release timeline", "release planning", "plan release", "วาง release"
argument-hint: "[--epics <key1,key2>] [--date <YYYY-MM-DD>] [--name <release-name>]"
---

# /release-planner

**Role:** Release Manager + PO
**Output:** Confluence release plan page + Jira Fix Version

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team velocity:** `.claude/project-config-team-detail.json` → `velocity.rolling_avg_sp`
- **Sprint length:** @.claude/project-config.json → `team.sprint_length_days` (default: 10)

## Context Object

| Phase | Adds to Context |
|-------|----------------|
| 1. Input | `release_name`, `target_date`, `epic_keys[]` |
| 2. Fetch | `epics[]` with stories + SP totals |
| 3. Velocity | `sprints_needed`, `velocity_sp`, `sprint_slots[]` |
| 4. Dependencies | `dependency_graph`, `critical_path[]` |
| 5. Sequence | `sprint_plan[]` (epics per sprint) |
| 6. Risk | `risks[]` |
| 8. Confluence | `page_url` |
| 9. Version | `fix_version_id` |

> **Workflow Patterns:** See [workflow-patterns.md](../../shared-references/workflow-patterns.md)

## Phase 1 — Input Resolution

Accept args: `--epics`, `--date`, `--name`.

If no `--epics`: ask "Which epics are in this release? (provide {{PROJECT_KEY}}-XXX keys)"
If no `--name`: ask "Release name? (e.g. v2.3.0)"

## Phase 2 — Fetch Epics + Stories

For each epic key:

1. `cache_get_issue(key)` — epic details, summary, status
2. JQL: `project=BEP AND parent = KEY ORDER BY created ASC` — child stories + tasks
3. Sum SP: `total_sp = sum(story.customfield_10016 for all children)`

Display summary table: Epic | Summary | Stories | Total SP

## Phase 3 — Velocity Calculation

1. Read `.claude/project-config-team-detail.json` velocity section.
   - Use `rolling_avg_sp` if available; fallback to `project-config.json` `team.avg_throughput_per_sprint` (39 SP)
2. Apply 10% carry-over buffer: `effective_velocity = velocity * 0.9`
3. `sprints_needed = ceil(total_sp / effective_velocity)`
4. Map sprint slots from today forward using `sprint_length_days`

## Phase 4 — Dependency Analysis

Using dependency-chain pattern:

1. JQL per epic: issues with `issue_link_types` = "Blocks" / "is blocked by"
2. Build cross-epic dependency graph
3. Identify critical path (longest chain)

## Phase 5 — Sprint Sequence

🔄 ITERATE (max 3 rounds): Present sprint allocation plan:

```
Sprint 1 (2026-04-01 → 2026-04-14): Epic BEP-50 (stories: 4, SP: 35)
Sprint 2 (2026-04-15 → 2026-04-28): Epic BEP-51 (stories: 3, SP: 28)
Sprint 3 (2026-04-29 → 2026-05-12): Epic BEP-52 (stories: 5, SP: 40)  ← buffer sprint
```

Ask: "Adjust allocation? (annotate with changes or approve)"

## Phase 6 — Risk Assessment

Identify:

- **Dependency risk:** epic N blocks epic M but scheduled after it
- **Capacity risk:** any sprint > 110% velocity
- **Scope risk:** stories without SP estimates in plan

## Phase 7 — Quality Gate

Score ≥ 90% before Confluence write (HR1).
Check: all sprints have dates, all epics assigned, critical path documented.

## Phase 8 — Confluence Release Page

Create page: "[release_name] Release Plan" in BEP space.

Structure:

```
# [Release Name] — v[X.Y.Z]

Target: [date] | Status: Planning

## Timeline

| Sprint | Dates | Epics | SP | Risk |
...

## Scope

In scope: [epic summaries]
Out of scope: [explicitly excluded items]

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
...

## Open Questions

- [ ] ...
```

## Phase 9 — Jira Fix Version

**⛔ GATE** — Confirm before creating Fix Version in Jira.

1. `jira_create_version(project_key="{{PROJECT_KEY}}", name=release_name, release_date=target_date)`
2. For each epic: `jira_update_issue(key, additional_fields: {fixVersions: [{id: version_id}]})`
3. HR6: `cache_invalidate(key)` for each linked epic (note: jira_create_version is NOT in HR6 hook matcher — call cache_invalidate manually)

Display: "Fix Version [name] created. [N] epics linked."
