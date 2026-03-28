---
name: daily-ops
description: |
  Daily operations workflow: standup report → flow check → blockers summary.

  Chains: standup-report → flow-check → synthesize blockers and priorities for the day.

  Use at the start of each workday to get a complete picture of team status and priorities.

  Triggers: "daily ops", "morning check", "start of day", "daily standup", "ops เช้า"
model: haiku
---

# Daily Operations Workflow

Run the following skills in sequence:

## Phase 1: Standup Report

Run `/atlassian-pm:standup-report` to get the current In Progress issues, recent completions, and blockers.

## Phase 2: Flow Check

Run `/atlassian-pm:flow-check` to check WIP limits, bottlenecks, and column health.

## Phase 3: Priority Summary

After both skills complete, synthesize the output into:

1. **Completed since last standup** — issues moved to Done
2. **In Progress** — who is working on what, any blockers
3. **Blocked items** — items needing attention today
4. **WIP violations** — columns over limit
5. **Top 3 priorities for today** — recommended focus based on flow health

Keep the summary concise — this is a morning briefing, not a full report.
