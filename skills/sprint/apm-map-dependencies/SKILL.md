---
name: apm-map-dependencies
context: fork
agent: Explore
model: haiku
x-compatibility: [atlassian-cache, mcp-atlassian]
argument-hint: "[--sprint <id>] [--keys ABC-1,ABC-2]"
effort: medium
allowed-tools: Read, Glob, Grep, Bash, Agent, TodoWrite, mcp__mcp-atlassian__jira_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_sprint_issues, mcp__plugin_atlassian-pm_atlassian-cache__cache_search
description: |
  Sprint dependency analysis: build dependency graphs, identify critical paths, generate parallel
  execution plans (swim lanes) per team member, and suggest decoupling strategies.

  Triggers: "dependency chain", "dependency analysis", "critical path", "swim lane",
  "blocking analysis", "parallel execution plan", "who blocks whom", "วิเคราะห์ dependencies", "dependency map"
  Use when: (1) planning a new sprint and need to check for blocking dependencies,
  (2) asked to analyze dependencies between sprint/backlog items, (3) need to create
  parallel execution plans or swim lanes, (4) want to identify critical path in a sprint,
  (5) looking for ways to reduce blocking between team members (API Contract First, MSW mocks, etc.)
  Do NOT use for: sprint capacity planning (use plan-sprint); closing sprint (use close-sprint)
---

# /atlassian-pm:apm-map-dependencies

**Role:** Dependency Analyst + Parallel Execution Planner
**Output:** Dependency graph (mermaid) + Critical path + Swim lane plan + Mitigation recommendations

## Workflow

5-phase analysis: Collect → Map → Analyze → Plan → Output

### Phase 1: Collect Sprint Data

Determine scope — sprint ID, issue list, or JQL query:

`jira_search(jql="sprint = <id> ORDER BY rank", fields="summary,status,assignee,issuetype,issuelinks,priority,labels", limit=30)`

Extract per item: key, summary, assignee, status, priority, issue links (Blocks/Relates/Duplicate), size estimate, service tag (`[BE]`, `[FE-Web]`, `[FE-Admin]`, `[QA]`).

Load: `../../../references/team-capacity.md` · `.claude/project-config.json`

**Size defaults:** Bug/Sub-task → S (1.5d) · Story/Task → M (2.5d) · Epic → L (3.5d)

**Gate:** Data collected — show item count + team members

### Phase 2: Map Dependencies

**Source A — Explicit (Jira links):** `Blocks` → FS edge · `Relates` → flag for manual review

**Source B — Inferred (heuristic):**

1. Same API/module → potential merge conflict
2. FE ticket references BE endpoint in same sprint → FS dependency
3. New FE feature needs new BE endpoint → BE deploy first
4. Multiple DB migrations → must coordinate order
5. QA test plan depends on dev completing feature

Mark confidence: HIGH / MEDIUM / LOW.

**Output:** Edge list: `ABC-3165 ──[Blocks, HIGH]──> ABC-3157`

### Phase 3: Analyze Critical Path

Read: `../../../references/dependency-frameworks.md` (section: Critical Path Method)

1. Forward pass: ES/EF per item
2. Backward pass: LS/LF per item
3. Identify critical path (zero float items)
4. Calculate float for non-critical items
5. Score risks (fan-out, delay impact, team concentration)

Output: Critical Path table (Order/Key/Summary/Duration/ES/EF/Assignee/Fan-out) + Risk Items table (Key/Risk Type/Score/Description/Mitigation)

### Phase 4: Generate Swim Lane Plan

Read: `../../../references/dependency-frameworks.md` (section: Swim Lane Rules)

Schedule per member respecting dependencies:

1. Critical path items first
2. Fill parallel slots with independent items
3. If blocked → assign buffer work (tech-debt, spike, refactor)
4. Apply decoupling: FE blocked by BE → API Contract First + MSW · Multiple devs same module → Interface-First · QA blocked → start test plan writing

Present as `| Day | Alice | Bob | ... |` swim lane table.

### Phase 5: Output

**1. Dependency Graph (Mermaid)** — `graph LR` with red fill (`fill:#ff6b6b`) for critical path items.

**2. Critical Path Summary** — total duration / sprint duration / buffer / risk level (LOW >2d / MEDIUM 1-2d / HIGH <1d)

**3. Swim Lane Execution Plan** — per-member daily plan with start/end dates, blocking dependencies noted.

**4. Mitigation Recommendations** — ranked list: `Priority 1: [Action] — eliminates [N] blocking dependencies`

## Options

| Flag | Description |
| --- | --- |
| `--sprint <id>` | Analyze specific sprint (default: current active sprint) |
| `--keys ABC-XX,ABC-YY` | Analyze specific issues instead of full sprint |
| `--team-only` | Show only swim lane plan (skip dependency graph) |
| `--mermaid-only` | Show only mermaid dependency graph |
| `--output jira-comment` | Post result as Jira comment on sprint's first item |

## Examples

```text
/map-dependencies                               # defaults to current active sprint
/map-dependencies --sprint 47                   # sprint ID from jira_get_sprints_from_board(board_id={{BOARD_ID}})
/map-dependencies --keys {{PROJECT_KEY}}-210,{{PROJECT_KEY}}-211,{{PROJECT_KEY}}-212  # analyze specific issues
/map-dependencies --sprint 47 --mermaid-only    # graph only
```

## References

[Dependency Frameworks](../../../references/dependency-frameworks.md) · [Team Capacity](../../../references/team-capacity.md) · [Sprint Frameworks](../../../references/sprint-frameworks.md)

## 🎓 Domain Expert Notes

- Never hardcode sprint ID — always call `jira_get_sprints_from_board()` first (HR7)
- Use `/map-dependencies` for analysis only; assignments go through `/plan-sprint`
- Inferred dependency detection is noisy beyond 30 items — use `--keys` to scope down
- API Contract First + MSW mocks are the primary FE/BE decoupling pattern
- Fix identified blocking dependencies before sprint start; Phase 5 mitigations require manual follow-up
