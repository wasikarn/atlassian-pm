---
name: alignment-checker
description: Check alignment between related tickets (story-subtask-epic)
model: sonnet
effort: medium
tools: Read, Glob, Grep, mcp__atlassian-cache__cache_get_issue, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__atlassian-cache__cache_search, mcp__mcp-atlassian__jira_update_issue, mcp__mcp-atlassian__jira_add_comment, mcp__atlassian-cache__cache_invalidate
maxTurns: 15
permissionMode: dontAsk
---

Verify and predict alignment between related Jira tickets: Epic→Story→Subtask hierarchy.

## Rules

- HR9: Story ACs must be covered by subtask objectives
- HR9: Epic scope must reflect in child Stories
- HR9: Blocked/blocking tickets must reference each other
- Check: parent-child links, scope coverage, date alignment
- HR8: Subtask dates within parent range, points sum reasonable
- Return: alignment score (A1-A6), mismatches, predicted risks, suggested fixes

## Data Fetching

> **🟢 PARALLEL** — After fetching the story (Step 1), launch Step 2 and Step 3 simultaneously (single message, 2 Tool calls): they have no dependency on each other.

1. Fetch story: `cache_get_issue(story_key)` — get ACs, scope, parent key, subtask list
2. Fetch parent epic: `cache_get_issue(story.parent.key)` — get epic scope, must-have list (skip if no parent)
3. Fetch subtasks: `jira_search(jql: "parent = story_key")` — get all subtask objectives and tags (skip if subtask list already in context)

## Checks

### Current Alignment (A1-A6)

- A1: All subtasks have parent link set
- A2: Sum of subtask SP ≈ story SP (within ±2)
- A3: Subtask dates within story date range
- A4: Each story AC has at least one subtask objective covering it
- A5: No scope drift (subtask scope files not covered by story description)
- A6: Blocked/blocking links are bidirectional

### AC Coverage Matrix

For each story AC (AC1, AC2, AC3...):

- Scan subtask objectives for coverage of that AC
- Mark: ✅ covered by BEP-XXX | ❌ no subtask covers this AC

Output the coverage matrix in the report.

### Predictive Risk Flags

Beyond detecting current misalignment, flag risks about to materialize:

- Date compression risk: "Story due Mar 25, latest subtask due Mar 24 → if any subtask slips 1 day, story misses deadline. Buffer: 0 days."
- Capacity risk: "Sum of subtask OE = 32h but story SP suggests ~24h → 33% over-estimate. Verify scope."
- Orphan AC risk: "AC3 (Error handling) has no subtask covering it → will be missed unless added."
- Dependency order risk: "{{PROJECT_KEY}}-YYY (FE) has earlier due date than {{PROJECT_KEY}}-ZZZ (BE) it depends on → FE cannot start on time."

### Scope Drift Detection

Compare story description scope keywords with subtask scope table entries:

- Files mentioned in story but not in any subtask scope table → potential miss
- Files in subtask scope but not related to story description → potential scope creep

## Write Path (optional — only when --fix flag passed)

When caller passes `--fix`:

- Date misalignment: update subtask dates via `jira_update_issue` ({{START_DATE_FIELD}}, duedate)
- Missing parent link: flag — cannot auto-fix (requires REST API, escalate to caller)
- Scope gap: add comment on story via `jira_add_comment` listing the gap
- After any write: `cache_invalidate(issue_key)` — required HR6

Without `--fix`: return report only, no writes.

## Output Format

```text
## Alignment Report: [story_key]

Alignment Score: [N]/6 (A[pass]-A[fail] breakdown)

### AC Coverage Matrix

| AC | Description | Covered By | Status |
|----|------------|------------|--------|
| AC1 | [name] | {{PROJECT_KEY}}-ZZZ objective | ✅ |
| AC3 | [name] | — | ❌ no coverage |

### Predictive Risks

| Risk | Severity | Detail |
|------|---------|--------|
| Date compression | HIGH | 0-day buffer on story deadline |
| Orphan AC | CRITICAL | AC3 has no subtask |

### Current Mismatches (if any)

- [A-check]: [what is wrong] → Fix: [instruction]

### Recommended Actions

1. [specific action]
```
