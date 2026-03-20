---
name: tech-debt-radar
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache-server, mcp-atlassian, mcp-confluence]
description: |
  Aggregate all tech-debt/chore/spike issues into a priority matrix dashboard on Confluence.
  Clusters by service tag + age. Scores effort vs impact. Supports trend comparison via Confluence history.
  --update refreshes existing page instead of creating new.
  Triggers: "tech debt", "debt radar", "tech debt dashboard", "chore audit", "สรุป tech debt"
argument-hint: "[--update]"
---

# /tech-debt-radar

**Role:** Tech Lead — Debt Visibility
**Output:** Confluence Tech Debt Radar page with priority matrix + trend

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`

> **Workflow Patterns:** See [workflow-patterns.md](../../shared-references/workflow-patterns.md)

## Phase 1 — Fetch Issues

JQL (HR2-safe — no parent filter):

```
project=BEP AND issuetype=Task AND labels in (tech-debt,chore,spike) ORDER BY created ASC
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

## Phase 6 — Confluence Page

**If `--update`:** `confluence_get_page` + `confluence_update_page`
**Else:** `confluence_create_page` in BEP space: "Tech Debt Radar"

Page structure (storage format — HR4: no macros via MCP):

```
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
    BEP-123: [0.2, 0.8]
    ...
```
