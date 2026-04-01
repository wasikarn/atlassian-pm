---
name: sprint-close-full
description: |
  Triggers: "close sprint full", "end sprint complete", "sprint closure with retro", "ปิด sprint ครบ"
  Orchestrates: close-sprint → retrospective-analyst → (optional) retro-actions
  Use --with-actions to also create Jira tasks from retrospective action items.
model: sonnet
argument-hint: "[--sprint SPRINT-ID] [--with-actions]"
---

# /sprint-close-full

Orchestrates: `close-sprint` → `retrospective-analyst` → _(optional)_ `retro-actions`

## Steps

### Step 1 — Close Sprint

Use the Skill tool to invoke `atlassian-pm:close-sprint` with `$ARGUMENTS`.

### Step 2 — Retrospective

> **Gate:** Confirm Step 1 completed successfully (sprint is closed, sprint ID is known). If close-sprint reported an error or no sprint was found, STOP.

Dispatch the `atlassian-pm:retrospective-analyst` agent to generate the retrospective analysis.
(Sprint data from Step 1 flows via conversation context — pass it explicitly in the agent prompt)

The retrospective-analyst will output an `action-items` block at the end of its report.

### Step 3 — Create Action Item Tasks (if `--with-actions` flag present)

> **Gate:** Only proceed if `--with-actions` was passed in `$ARGUMENTS` AND Step 2 produced an `action-items` block with at least one item. If the block is empty or missing, skip this step and note it in the summary.

Use the Skill tool to invoke `atlassian-pm:retro-actions` to parse the action items and create Jira tasks.

Pass `--sprint <sprint-id>` from Step 1 context.

### Step 4 — Summary

Present a completion summary:

- Sprint closed: done
- Retrospective generated: done (link to Confluence page if created)
- Action items created: N tasks ([KEY-1], [KEY-2], ...) — or "skipped (no --with-actions flag)"
