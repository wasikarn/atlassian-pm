---
name: map-dependencies
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache, mcp-atlassian]
allowed-tools: Read, Glob, Grep, Bash, Agent, TodoWrite, mcp__mcp-atlassian__jira_search, mcp__plugin_atlassian-pm_jira-cache__cache_get_issue, mcp__plugin_atlassian-pm_jira-cache__cache_sprint_issues, mcp__plugin_atlassian-pm_jira-cache__cache_search
description: |
  Sprint dependency analysis: build dependency graphs, identify critical paths, generate parallel
  execution plans (swim lanes) per team member, and suggest decoupling strategies.

  Use when: (1) planning a new sprint and need to check for blocking dependencies,
  (2) asked to analyze dependencies between sprint/backlog items, (3) need to create
  parallel execution plans or swim lanes, (4) want to identify critical path in a sprint,
  (5) looking for ways to reduce blocking between team members (API Contract First, MSW mocks, etc.)

  Triggers: "dependency chain", "dependency analysis", "critical path", "swim lane",
  "blocking analysis", "parallel execution plan", "who blocks whom"
---

# /map-dependencies

**Role:** Dependency Analyst + Parallel Execution Planner
**Output:** Dependency graph (mermaid) + Critical path + Swim lane plan + Mitigation recommendations

## Workflow

5-phase analysis: Collect → Map → Analyze → Plan → Output

### Phase 1: Collect Sprint Data

Determine scope — sprint ID, issue list, or JQL query:

```text
MCP: jira_search(jql="sprint = <id> ORDER BY rank", fields="summary,status,assignee,issuetype,issuelinks,priority,labels", limit=30)
```

For each item, extract:

- Key, summary, assignee, status, priority
- Issue links (type: Blocks, Relates, Duplicate)
- Size estimate from labels or story points (fallback: infer from issuetype)
- Service tag from summary: `[BE]`, `[FE-Web]`, `[FE-Admin]`, `[QA]`

Load team info:

```text
Read: ../../../references/team-capacity.md (capacity formulas, skill matrix, thresholds)
Read: .claude/project-config.json (team roster: members[], skill_profile, avg_throughput)
```

**Size defaults** (if no estimate available):

| Type | Default |
| --- | --- |
| Bug | S (1.5d) |
| Sub-task | S (1.5d) |
| Story | M (2.5d) |
| Task | M (2.5d) |
| Epic | L (3.5d) |

**Gate:** Data collected — show item count + team members

### Phase 2: Map Dependencies

Build dependency graph from two sources:

**Source A — Explicit (Jira issue links)**

```text
For each item with issuelinks:
  if link.type == "Blocks" → add edge: blocker → blocked (FS dependency)
  if link.type == "Relates" → flag for manual review (may be implicit dependency)
```

**Source B — Inferred (heuristic)**
Analyze items for implicit dependencies not in Jira:

1. **Same API/module**: Multiple tickets touching same endpoint/service → potential merge conflict
2. **FE→BE**: FE ticket references an API from a BE ticket in same sprint → FS dependency
3. **Deploy order**: New FE feature needs new BE endpoint → BE must deploy first
4. **Shared migration**: Multiple DB migrations → must coordinate order
5. **QA→Dev**: QA test plan depends on dev completing feature

For inferred dependencies, mark confidence: HIGH (obvious from context) / MEDIUM (likely) / LOW (possible).

**Output:** Edge list with type and confidence:

```text
ABC-3165 ──[Blocks, HIGH]──> ABC-3157
ABC-3156 ──[Inferred:FE→BE, MEDIUM]──> ABC-2743
```

### Phase 3: Analyze Critical Path

Read reference for algorithm details:

```text
Read: ../../../references/dependency-frameworks.md (section: Critical Path Method)
```

1. Calculate ES/EF for each item (forward pass)
2. Calculate LS/LF for each item (backward pass)
3. Identify critical path (items with zero float)
4. Calculate float for non-critical items
5. Score risks (fan-out, delay impact, team concentration)

**Output tables:**

**Critical Path:**

| Order | Key | Summary | Duration | ES | EF | Assignee | Fan-out |
|-------|-----|---------|----------|----|----|----------|---------|

**Risk Items:**

| Key | Risk Type | Score | Description | Mitigation |
|-----|-----------|-------|-------------|------------|

### Phase 4: Generate Swim Lane Plan

Read reference for scheduling rules:

```text
Read: ../../../references/dependency-frameworks.md (section: Swim Lane Rules)
```

For each team member, schedule items respecting dependencies:

```text
1. Place critical path items first (must start on time)
2. Fill parallel slots with independent items
3. If blocked → assign buffer work (tech-debt, spike, refactor)
4. Apply decoupling patterns where possible:
   - FE blocked by BE? → API Contract First + MSW (see reference)
   - Multiple devs on same module? → Interface-First Development
   - QA blocked by dev? → Start with test plan writing
```

**Present as swim lane table:**

```text
| Day | Alice       | Bob    | Charlie    | Dave       | Eve        |
|-----|-------------|--------|------------|------------|------------|
| 1-2 | ABC-XXX     | ABC-XX | ABC-XX     | ABC-XX     | ABC-XX     |
| 3-4 | ABC-XXX     | ...    | ...        | ...        | ...        |
```

### Phase 5: Output

Generate final deliverable with 4 sections:

**1. Dependency Graph (Mermaid)**

```mermaid
graph LR
  A[ABC-3165: Fix maxPerUser] -->|Blocks| B[ABC-3157: API Integration]
  C[ABC-3156: Collection API] -->|Inferred| D[ABC-2743: Collection Page]
  style A fill:#ff6b6b
  style C fill:#ff6b6b
```

Use red fill for critical path items, default for others.

**2. Critical Path Summary**

- Total critical path duration: X days
- Sprint duration: Y days
- Buffer: Y - X days
- Risk level: LOW (buffer > 2d) / MEDIUM (buffer 1-2d) / HIGH (buffer < 1d)

**3. Swim Lane Execution Plan**
Per-member daily plan with start/end dates, blocking dependencies noted.

**4. Mitigation Recommendations**
Ranked list of actions to reduce blocking:

```text
Priority 1: [Action] — eliminates [N] blocking dependencies
Priority 2: [Action] — reduces delay impact by [N] days
...
```

---

## Options

| Flag | Description |
| --- | --- |
| `--sprint <id>` | Analyze specific sprint (default: current active sprint) |
| `--keys ABC-XX,ABC-YY` | Analyze specific issues instead of full sprint |
| `--team-only` | Show only swim lane plan (skip dependency graph) |
| `--mermaid-only` | Show only mermaid dependency graph |
| `--output jira-comment` | Post result as Jira comment on sprint's first item |

## Examples

### Good

```text
/map-dependencies                               # defaults to current active sprint — resolves via jira_get_sprints_from_board
/map-dependencies --sprint 47                   # sprint ID obtained from jira_get_sprints_from_board(board_id=2, state="active")
/map-dependencies --keys {{PROJECT_KEY}}-210,{{PROJECT_KEY}}-211,{{PROJECT_KEY}}-212  # analyze a specific subset of issues instead of the full sprint
/map-dependencies --sprint 47 --mermaid-only    # output only the dependency graph, skip swim lane and CPM tables
```

### Bad

```text
/map-dependencies --sprint 47                   # ❌ sprint ID hardcoded without calling jira_get_sprints_from_board first (HR7)
/map-dependencies                               # ❌ run without an active sprint and no --keys specified — Phase 1 returns empty scope
/plan-sprint                                    # ❌ wrong skill — /map-dependencies is analysis only; use /plan-sprint to assign work
/map-dependencies --keys {{PROJECT_KEY}}-210               # ❌ single issue with no linked items — dependency graph is meaningless without context
```

**Common mistakes:**

- Using `/map-dependencies` to assign work — this skill produces analysis (graph + swim lane plan) only; execute assignments with `/plan-sprint`
- Not acting on identified blocking dependencies before sprint start — the mitigation recommendations in Phase 5 require manual follow-up
- Passing a very broad sprint scope (30+ items) without `--keys` filtering — inferred dependency detection becomes noisy and slow
- Hardcoding a sprint ID instead of calling `jira_get_sprints_from_board()` first (HR7)

## References

- [Dependency Frameworks](../../../references/dependency-frameworks.md) — Dependency types, CPM algorithm, decoupling patterns, swim lane rules, risk scoring
- [Team Capacity](../../../references/team-capacity.md) — Capacity formulas, skill matrix, thresholds (roster data in project-config.json)
- [Sprint Frameworks](../../../references/sprint-frameworks.md) — Vertical slicing, carry-over model
