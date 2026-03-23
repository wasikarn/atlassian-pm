---
name: plan-release
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Create a multi-sprint release plan from epics — calculates velocity-based timeline, maps dependencies,
  generates Confluence release page + Jira Fix Version.
  Triggers: "release plan", "release timeline", "release planning", "plan release", "วาง release", "multi-sprint release"
  Use when: planning a multi-sprint release across epics — need velocity-based timeline, dependency map, Confluence release page, and Jira Fix Version
  Do NOT use for: single-sprint work (use plan-sprint); generating release notes after a release (use release-notes)
argument-hint: "[--epics <key1,key2>] [--date <YYYY-MM-DD>] [--name <release-name>]"
effort: high
---

# /plan-release

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

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md)

## Phase 1 — Input Resolution

Accept args: `--epics`, `--date`, `--name`.

If no `--epics`: ask "Which epics are in this release? (provide {{PROJECT_KEY}}-XXX keys)"
If no `--name`: ask "Release name? (e.g. v2.3.0)"

## Phase 2 — Fetch Epics + Stories

For each epic key:

1. `cache_get_issue(key)` — epic details, summary, status
2. JQL: `project={{PROJECT_KEY}} AND parent = KEY ORDER BY created ASC` — child stories + tasks
3. Sum SP: `total_sp = sum(story.customfield_10016 for all children)`

Display summary table: Epic | Summary | Stories | Total SP

## Phase 3 — Velocity Calculation

1. Read `.claude/project-config-team-detail.json` velocity section.
   - Use `rolling_avg_sp` if available; fallback to `project-config.json` `team.avg_throughput_per_sprint` (39 SP)
2. Apply 10% carry-over buffer: `effective_velocity = velocity * 0.9`
3. `sprints_needed = ceil(total_sp / effective_velocity)`
4. Map sprint slots from today forward using `sprint_length_days`

## Phase 4 — Dependency Analysis

Using map-dependencies pattern:

1. JQL per epic: issues with `issue_link_types` = "Blocks" / "is blocked by"
2. Build cross-epic dependency graph
3. Identify critical path (longest chain)

## Phase 5 — Sprint Sequence

🔄 ITERATE (max 3 rounds): Present sprint allocation plan:

```
Sprint 1 (2026-04-01 → 2026-04-14): Epic {{PROJECT_KEY}}-50 (stories: 4, SP: 35)
Sprint 2 (2026-04-15 → 2026-04-28): Epic {{PROJECT_KEY}}-51 (stories: 3, SP: 28)
Sprint 3 (2026-04-29 → 2026-05-12): Epic {{PROJECT_KEY}}-52 (stories: 5, SP: 40)  ← buffer sprint
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

Create page: "[release_name] Release Plan" in {{PROJECT_KEY}} space.

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

## Examples

### ✅ Good

```text
/plan-release --epics {{PROJECT_KEY}}-50,{{PROJECT_KEY}}-51,{{PROJECT_KEY}}-52 --name v2.3.0 --date 2026-06-30   # full args → no prompts, runs all 9 phases automatically
/plan-release --epics {{PROJECT_KEY}}-50,{{PROJECT_KEY}}-51 --name v2.3.0                             # no target date → calculates end date from velocity
/plan-release --epics {{PROJECT_KEY}}-48 --name v2.2.1 --date 2026-04-15                  # single-epic patch release with hard deadline
```

### ❌ Bad

```text
/plan-release                                              # no epics → Phase 1 prompts for keys; partial info produces a shallow plan
/plan-release --name v2.3.0                                # release name without epics → can't calculate SP or sprint count
/plan-release --epics {{PROJECT_KEY}}-50,{{PROJECT_KEY}}-51                        # epics with no story-point estimates → velocity calculation will be 0 or wrong
/plan-release --epics {{PROJECT_KEY}}-50 --date 2026-04-01             # date in the past — sprint sequencing produces negative slots
```

**Common mistakes:**

- Planning a release before all epics have estimated stories — Phase 3 velocity calculation sums `customfield_10016` SP; unestimated stories show as 0 SP, making the sprint count meaningless.
- Hardcoding sprint IDs anywhere in the plan — `/plan-release` uses velocity + sprint length to derive slots from today forward; sprint IDs come from `jira_get_sprints_from_board()` at execution time (HR7).
- Not running `/doctor` before plan-release if `project-config-team-detail.json` is missing — Phase 3 falls back to the 39 SP default, which may not reflect your team's actual velocity.
- Confirming the Jira Fix Version gate (Phase 9) before the Confluence page is reviewed — Fix Version links epics to the release in Jira; reversing it requires unlinking each epic manually.

## 🎓 Domain Expert Notes

### Why This Approach

Release planning at the multi-epic level is a forecasting exercise, not a commitment exercise. The velocity-based timeline (Phase 3) plus dependency-aware sequencing (Phase 4) mirrors SAFe PI Planning's core output — a Program Board showing team commitments and cross-team dependencies across a fixed time horizon. The 10% carry-over buffer encodes the empirical finding that teams consistently over-plan sprint capacity by 10-20%.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SAFe PI Planning (Program Increment) | Phases 3-5 — sprint sequencing, capacity allocation | PI spans 4-6 sprints with a buffer sprint at the end; the sprint_plan output mirrors a PI plan's epic-to-sprint allocation |
| ROAM Risk Framework (SAFe) | Phase 6 Risk Assessment | ROAM = Resolved / Owned / Accepted / Mitigated; all identified risks must be categorized this way before a release plan is approved |
| Critical Path Method (CPM) | Phase 4 Dependency Analysis | Longest chain of blocking dependencies determines the earliest possible release date regardless of capacity; ignoring critical path produces optimistic but unreachable release dates |
| Agile Release Train (ART) cadence | Phase 3 — effective_velocity calculation | Rolling average SP with 10% buffer matches ART's capacity model for PIs; single-sprint velocity is too volatile for multi-sprint forecasting |
| Definition of Done for releases | Phase 7 Quality Gate | Release DoD: all epics linked, all sprints have dates, critical path documented, risk register populated — these are the release-level exit criteria |

### Key Metrics

- **Release predictability:** Planned SP vs. actual SP delivered at release cut; teams with <15% variance have reliable velocity data; >30% variance signals estimation or scope instability
- **Critical path buffer ratio:** Buffer sprint SP / total release SP; SAFe recommends 1 buffer sprint per PI (typically 10-15% of total capacity); less than 5% leaves no room for unplanned work
- **Dependency density:** Number of cross-epic blocking links / number of epics; >1.5 blocking links per epic signals the release may need to be re-scoped or sequenced differently
- **Risk ROAM completion:** All Phase 6 risks must be ROAM-categorized before Fix Version is created; unROAMed risks are unknown schedule threats

### Expert Decision Criteria

- **When to add a buffer sprint:** Any release with > 3 cross-epic dependencies, any epic with stories not yet pointed, or any external dependency (third-party API, compliance review) not yet confirmed — add a buffer sprint automatically
- **Hard deadline vs. velocity-driven date:** If `--date` is provided and it conflicts with velocity calculation, surface the gap explicitly: "Velocity forecast: [date]. Target: [date]. Gap: [N] SP. Options: (1) reduce scope, (2) increase capacity, (3) move date." Never silently adjust the timeline.
- **Fix Version creation gate:** Fix Version in Jira is a public commitment signal — it appears in release notes, dashboards, and stakeholder reports. Do not create it until the Confluence release plan is reviewed and the scope is stable. Reversing a Fix Version requires manual unlinking of every epic.
- **Carry-over buffer calibration:** If `rolling_avg_sp` from team detail is available, use it. If the rolling average was computed during a sprint with unusual conditions (hackathon, team member out), discount it by 15% for the release plan.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Release date slips every sprint | Velocity used was best-case, not rolling average | Pull the last 6 sprints of actual SP completed; compute trimmed mean (drop highest + lowest); use that as `effective_velocity` |
| Dependencies discovered after Fix Version created | Phase 4 dependency analysis ran on epic-level only, missing story-level blocks | Before creating Fix Version, run a JQL for all `is blocked by` links across all stories in the release, not just epics |
| Buffer sprint fills up immediately | Carry-over stories from previous sprint weren't accounted for | Apply carry-over rule: buffer sprint pre-allocates 20% of capacity for carry-over before any new work is added |
| Scope grows after Fix Version creation ("release scope creep") | No scope freeze process defined | Add a release scope change rule to the Confluence page: any new story added after Fix Version creation requires a corresponding story to be deferred |
| Critical path not visible to stakeholders | Risk register exists but dependency graph is not shown | Include a Mermaid dependency diagram in the Confluence release page (Phase 8) showing critical path highlighted in red |

### Authoritative References

- SAFe 6.0 PI Planning: "PI Objectives are the team's commitment to stakeholders for what will be delivered in the PI; uncommitted objectives are risks, not promises" — Phase 6 risk register maps directly to uncommitted PI objectives
- ROAM framework (SAFe Inspect & Adapt): All risks surface during planning must be ROAMed before the plan is baselined; "we'll handle it" is not ROAM — it must be Owned by a specific person
- Mike Cohn, *Agile Estimating and Planning*: Release planning using velocity requires at least 3 sprints of historical data; fewer than 3 sprints means the estimate is a guess, not a forecast — communicate this to stakeholders
- Atlassian Agile Coach: Fix Versions in Jira are the release coordination mechanism — they drive release notes generation, JQL filtering, and burndown reporting; treat creation as a commitment gate

---

## References

- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Epic Template](../../../references/templates-epic.md) - Epic ADF template
- [Sprint Frameworks](../../../references/sprint-frameworks.md) - Velocity-based release forecasting, RICE scoring
- [Mermaid Guide](../../../references/mermaid-guide.md) - Diagrams for Confluence release plan page
