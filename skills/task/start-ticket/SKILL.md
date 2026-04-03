---
name: start-ticket
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian]
argument-hint: "[issue-key] [--force]"
effort: low
allowed-tools: Read, Bash, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_get_transitions, mcp__mcp-atlassian__jira_transition_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Bundle: read Jira ticket + transition to In Progress in one command.
  Shows AC summary ready for brainstorming.

  Triggers: "start ticket", "start working on", "begin ticket", "เริ่มงาน", "รับงาน", "start {{PROJECT_KEY}}-XXX"
  Use when: beginning work on a ticket — replaces manual jira_get_issue + jira_transition_issue
  Do NOT use for: reading a ticket without transitioning (use jira_get_issue directly)
---

# /start-ticket

**Role:** Developer starting a ticket
**Output:** Ticket transitioned to In Progress + AC summary displayed

## Dynamic Context

- **Config:** @.claude/project-config.json
- **Note:** `board.columns` is consumed by the WIP gate hook automatically — the skill does not query it directly

## Steps

**Step 1 — Fetch**

Call `jira_get_issue` with fields: `summary,status,description,labels,issuetype`

> Try `cache_get_issue` first; on cache miss or stale data, call `jira_get_issue`.

**Step 2 — Tiered Guard**

Check current status:

| Status | Action |
|--------|--------|
| To Do / Backlog / Open | Proceed normally |
| In Progress / Reopened | Warn: "already In Progress — proceeding" but continue |
| Done / Closed / Cancelled | **STOP** — "ticket is {status}. Use --force to override." Only continue if user typed `--force` in argument |

**Step 3 — WIP Check + Transition**

1. Call `jira_get_transitions` → find transition named "In Progress" (or containing "progress", case-insensitive)
2. The `pre_wip_limit_check` hook will **automatically block** if WIP limit is reached
3. If blocked by hook:
   - Run the JQL the hook provides
   - Count results
   - If count < wip_max: run `export CLAUDE_WIP_CONFIRMED={issue_key}:{col_name}` where `{col_name}` is the column name shown in the hook's block message (e.g., "In Progress"), then retry `jira_transition_issue`
   - If count >= wip_max: **STOP** — report "WIP limit reached for In Progress ({count}/{wip_max}). Finish an existing item first."
4. Call `jira_transition_issue` — pass the transition **name** (not numeric ID) using the `transition` field so the `pre_wip_limit_check` hook can detect the target column correctly

**Step 4 — HR6**

`cache_invalidate(issue_key="{issue_key}")`

**Step 5 — Output**

Parse ACs from description (look for numbered list, bullet list, or "Acceptance Criteria" section).

Format output:

```
{issue_key} -> In Progress [OK]

[{labels joined with "]["}] {summary}

Acceptance Criteria:
1. {ac_1}
2. {ac_2}
...

Next: brainstorm feature จาก {issue_key}
```

If no ACs found: show description excerpt (first 300 chars) with note "No explicit AC found — review description above before brainstorming."

## Edge Cases

| Situation | Handling |
|-----------|---------|
| Transition "In Progress" not found | Show available transitions, ask user to pick |
| No description | Show "No description available" in AC section |
| `--force` on Done ticket | Warn prominently, proceed, log to stderr |

## Examples

### ✅ Good

```text
/start-ticket {{PROJECT_KEY}}-42                        # read + transition to In Progress
/start-ticket {{PROJECT_KEY}}-42 --force                # force start on Done/Cancelled ticket
```

### ❌ Bad

```text
/start-ticket                              # no issue key — cannot fetch ticket
/start-ticket {{PROJECT_KEY}}-42 {{PROJECT_KEY}}-43                  # only one issue at a time
/start-ticket --force                      # --force requires an issue key
```

**Common mistakes:**

- Running on Done ticket without `--force` — blocked by guard; explicitly confirm with `--force`
- Expecting AC extraction from non-standard formats — only numbered/bullet lists and "Acceptance Criteria" sections are parsed
- Forgetting that WIP limits apply — the hook will block if "In Progress" column is at capacity

## Domain Expert Notes

DLC discipline requires reading the ticket before touching code. Bundling the transition prevents the common failure mode where a developer starts work and forgets to move the Jira card — leaving the board state stale and blocking sprint metrics (cycle time starts at In Progress, not at actual code commit).

The WIP gate enforces Little's Law in practice: throughput = WIP × cycle time⁻¹. Uncapped WIP degrades both metrics simultaneously (Anderson, *Kanban*, 2010).

## References

- [HR Rules](../../../references/hr-rules.md) — HR6: cache_invalidate after every Jira write
- [WIP Gate](../../../hooks/plugin/guards/pre_wip_limit_check.py) — Hard WIP enforcement via CLAUDE_WIP_CONFIRMED env var
