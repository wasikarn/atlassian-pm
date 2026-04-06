---
name: apm-scan-tech-debt
context: fork
agent: Explore
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence]
description: |
  This skill should be used when aggregating tech-debt, chore, and spike issues into an Effort×Impact priority matrix dashboard on Confluence. Clusters by service tag + age. Scores effort vs impact. Supports trend comparison via Confluence history.
  
  Use --update to refresh an existing page instead of creating new.
  
  Trigger phrases: "tech debt", "debt radar", "tech debt dashboard", "chore audit", "สรุป tech debt", "tech debt matrix"
  
  This skill should NOT be used for creating individual tasks (use create-task) or sprint planning (use plan-sprint).
argument-hint: "[--update]"
effort: high
---

# /atlassian-pm:apm-scan-tech-debt

**Role:** Tech Lead — Debt Visibility
**Output:** Confluence Tech Debt Radar page with priority matrix + trend

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md)

## Phase 1 — Fetch Issues

JQL (HR2-safe — no parent filter):

```jql
project={{PROJECT_KEY}} AND issuetype=Task AND labels in (tech-debt,chore,spike) ORDER BY created ASC
```

Via `jira_search` with fields: `summary,status,assignee,labels,customfield_10016,{{START_DATE_FIELD}},duedate,created`

Display: "Found [N] tech debt items: [X] tech-debt, [Y] chore, [Z] spike"

## Phase 2 — Cluster

Group by:

1. **Service tag** from issue summary prefix: [BE] / [FE-Admin] / [FE-Web] / [Video] / Other
2. **Age bucket** from `created` date:
   - Fresh: < 1 month
   - Aging: 1–3 months
   - Stale: > 3 months

## Phase 3 — Priority Matrix

For each issue, score:

- **Effort** = SP from `customfield_10016` (missing SP → estimate S=2/M=5/L=8 from summary length)
- **Impact** (1–5 scale):
  - 5: keywords: "block", "critical", "performance", "security", "auth"
  - 4: keywords: "slow", "velocity", "recurring", "flaky"
  - 3: keywords: "bug", "error", "fail"
  - 2: keywords: "onboard", "doc", "readme"
  - 1: everything else

Assign 2×2 quadrant:

- **Quick Win**: low effort (SP ≤ 3) + high impact (≥ 4)
- **Major Work**: high effort (SP > 5) + high impact (≥ 4)
- **Fill-in**: low effort + low impact (< 4)
- **Avoid**: high effort + low impact

## Phase 4 — Trend (--update only)

Read previous snapshot from Confluence page body HTML comment:

```html
<!-- tech-debt-snapshot: {"date":"...","total":N,"be":N,"fe-admin":N,"fe-web":N} -->
```

Compute delta: `+N` added / `-N` resolved since last update.

## Phase 5 — Quality Gate

Score content ≥ 90% (HR1) before writing to Confluence.
Check: issue count > 0, at least one quadrant populated, all required sections present.

> **🟢 AUTO (validate_adf.py):**
>
> ```bash
> uv run scripts/api/validate_adf.py {{artifacts_dir}}/tech-debt-radar.json --type task --json
> ```
>
> Score ≥ 90 = PASS. If FAIL → check `issues[].fix_hint` → run `--fix` → re-score. Max 1 fix cycle.

## Phase 6 — Confluence Page

**If `--update`:** `confluence_get_page` + `confluence_update_page`
**Else:** `confluence_create_page` in {{PROJECT_KEY}} space: "Tech Debt Radar"

Page structure (storage format — HR4: no macros via MCP):

```text
# Tech Debt Radar — [date]

## Summary
Total: [N] items | [BE]: X | [FE-Admin]: X | [FE-Web]: X

## Priority Matrix

[Mermaid quadrant chart]

## By Service

### [BE] — X items
| Key | Summary | SP | Impact | Age | Quadrant |
...

## Trend
Compared to [prev_date]: +N added, -M resolved

<!-- tech-debt-snapshot: {"date":"[today]","total":N,"be":N,"fe-admin":N,"fe-web":N} -->
```

Mermaid quadrant chart format:

```mermaid
quadrantChart
    title Tech Debt Priority Matrix
    x-axis Low Effort --> High Effort
    y-axis Low Impact --> High Impact
    quadrant-1 Major Work
    quadrant-2 Quick Win
    quadrant-3 Avoid
    quadrant-4 Fill-in
    {{PROJECT_KEY}}-123: [0.2, 0.8]
    ...
```

## Examples

### ✅ Good

```text
/scan-tech-debt                         # first-time run — creates new "Tech Debt Radar" Confluence page
/scan-tech-debt --update                # refresh existing Tech Debt Radar page and compute trend delta
```

### ❌ Bad

```text
/scan-tech-debt --update                # --update when no Tech Debt Radar page exists yet —
                                        # Phase 4 trend read will fail; omit --update for first-time creation
/scan-tech-debt                         # running without --update when a page already exists —
                                        # creates a second "Tech Debt Radar" page (duplicate)
/scan-tech-debt "{{PROJECT_KEY}}-99 is high priority"   # free-text args are ignored — skill takes no filter args
/scan-tech-debt --create {{PROJECT_KEY}}-55         # wrong expectation: this skill only aggregates existing labeled
                                        # issues into Confluence; it does not create Jira tasks
```

**Common mistakes:**

- Running without `--update` when a Tech Debt Radar page already exists in Confluence — this creates a duplicate page instead of refreshing the existing one
- Running with `--update` on the very first invocation — the skill looks for an existing page snapshot to compute the trend delta and will fail if none exists
- Expecting the skill to create Jira tasks for the tech-debt items it finds — `/scan-tech-debt` is read-only on Jira; it only writes the priority matrix dashboard to Confluence
- Issues must be labeled `tech-debt`, `chore`, or `spike` in Jira for them to appear — unlabeled tasks are invisible to this skill

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)

## References

[Task Template](../../../references/templates-task.md) · [Dependency Frameworks](../../../references/dependency-frameworks.md) · [JQL Quick Reference](../../../references/jql-quick-ref.md)
