---
name: scan-tech-debt
context: fork
agent: Explore
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence]
description: |
  Aggregate all tech-debt/chore/spike issues into a priority matrix dashboard on Confluence.
  Clusters by service tag + age. Scores effort vs impact. Supports trend comparison via Confluence history.
  --update refreshes existing page instead of creating new.
  Triggers: "tech debt", "debt radar", "tech debt dashboard", "chore audit", "สรุป tech debt"
  Use when: aggregating tech-debt and spike issues into an Effort×Impact matrix dashboard on Confluence
  Do NOT use for: creating individual tasks (use create-task); sprint planning (use plan-sprint)
argument-hint: "[--update]"
effort: high
---

# /scan-tech-debt

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

---

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

---

## 🎓 Domain Expert Notes

### Why This Approach

Technical debt is a financial analogy (Ward Cunningham, 1992): the "principal" is the effort to fix suboptimal code; the "interest" is the ongoing productivity drag of working around it. The skill's effort × impact priority matrix operationalises this — high-interest debt (high impact, low effort) compounds fastest and must be paid down first, regardless of how old it is.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Martin Fowler's Tech Debt Quadrant | Phase 3 impact scoring keywords | Fowler's quadrant (Prudent/Reckless × Deliberate/Inadvertent) maps directly to keyword heuristics: "block/security/auth" → Reckless Inadvertent debt (highest interest rate, fix immediately); "refactor/clean" → Prudent Deliberate (acceptable, schedule it); "doc/readme" → Prudent Inadvertent (low interest, low priority) |
| Effort × Impact (Eisenhower-derived) | Phase 3 quadrant assignment | Quick Win (high impact + low effort) / Major Work (high impact + high effort) / Fill-in (low impact + low effort) / Avoid (low impact + high effort) — this is a standard effort-impact triage, commonly applied in tech debt contexts. Note: SQALE uses a separate priority order (quality pyramid); these are complementary, not equivalent |
| SQALE Quality Pyramid (Letouzey, 2012) | Phase 2 age bucketing + Phase 3 keyword priority order | SQALE defines remediation priority as a pyramid: **Testability** (base) → **Reliability** → **Security** → **Maintainability** → **Efficiency** → **Portability** (top). Applied here: `spike` items (testability debt) open > 3 months → structural blockers; `security/auth` keywords → reliability/security layer, always prioritised over `refactor` (maintainability layer); `doc` → bottom-tier unless it blocks testability |

### Key Metrics

- **Tech Debt Ratio:** `(total SP of debt items) / (total SP delivered last 3 sprints)` — industry healthy threshold is ≤20%; above 30% signals velocity ceiling approaching
- **Interest rate proxy:** Count of issues in "Quick Win" quadrant — if Quick Wins accumulate sprint-over-sprint without being picked up, the team is paying interest without reducing principal
- **Debt age distribution:** Percentage of items in "Stale" bucket (>3 months) — target <20% stale; high stale percentage means debt is being logged but never prioritised
- **Resolution rate trend:** Delta computed in Phase 4 (`--update`) — a negative delta (more resolved than added) over 2+ consecutive sprints indicates healthy debt management culture

### Expert Decision Criteria

- If >50% of debt items have no SP estimate → the effort axis of the priority matrix is unreliable; run a quick SP estimation session before using the matrix for sprint planning
- If the "Avoid" quadrant (high effort + low impact) is the largest → these items should be closed as "Won't Fix" or converted to backlog epics; keeping them as active tasks inflates the debt count and hides real priorities
- If `spike` label items are older than 2 sprints → they have become decision debt (a finding not acted on); escalate to the tech lead for a decision to proceed, park, or close
- Scrum teams should allocate 15–20% of sprint capacity to debt reduction (ScrumInc field data; echoed by Google's 20% technical health time — Fitzpatrick & Collins-Sussman, "Team Geek", 2012) — if the `total SP` of Quick Wins exceeds 20% of sprint velocity, the team is under-investing in debt paydown
- If a service tag (e.g., `[BE]`) consistently has the most Stale items → it is a candidate for a dedicated debt-reduction sprint or a mob refactoring session

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Priority matrix is all "Fill-in" (low effort + low impact) | Impact keywords missing from issue summaries | Coach team to write debt issue titles with impact context: "slow" / "blocks" / "recurring" — keyword scoring depends on this |
| `--update` fails with page not found | Tech Debt Radar page was deleted or renamed in Confluence | Drop `--update` flag for one run to recreate, then use `--update` going forward |
| Mermaid quadrant chart renders as raw text in Confluence | Confluence macro renderer not activated for the space | Use `update_page_storage.py` to wrap the Mermaid block in the proper Confluence code macro format (HR4) |
| New debt items appear but trend shows no change | Snapshot HTML comment was manually edited or stripped | Restore snapshot comment format exactly: `<!-- tech-debt-snapshot: {...} -->` with no whitespace changes |
| Debt count grows every sprint with no resolution | Team logs debt but never picks it up | Enforce the 15–20% sprint capacity rule; add a "Debt Review" agenda item to sprint planning |

### Authoritative References

- **Martin Fowler (martinfowler.com/bliki/TechnicalDebt):** "The interest analogy is important — not all debt is bad, but you need to be conscious of both the principal and the interest you're paying"
- **Fowler's Technical Debt Quadrant (2009):** Deliberate+Prudent debt ("we know we're cutting corners now") is the only acceptable form — all other quadrants represent unintentional or negligent debt that should be addressed immediately
- **SQALE Method (Letouzey, 2012):** Remediation priority follows the quality pyramid — fix Testability first, then Reliability, then Security; the keyword-based impact scoring in this skill approximates this order

---

## References

- [Task Template](../../../references/templates-task.md) - ADF template for tech-debt task creation
- [Dependency Frameworks](../../../references/dependency-frameworks.md) - Effort×Impact matrix, risk scoring
- [JQL Quick Reference](../../../references/jql-quick-ref.md) - JQL patterns for tech-debt issue filtering
