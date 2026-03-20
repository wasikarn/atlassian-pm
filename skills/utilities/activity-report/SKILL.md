---
name: activity-report
disable-model-invocation: true
context: fork
model: haiku
x-compatibility: [claude-mem]
allowed-tools: Read, Glob, Grep, Bash, Agent
description: |
  Generate activity report from claude-mem database showing past work sessions, observations, and effort.
  Default: today. Supports date ranges, project filters, observation type filters.

  Triggers: "activity report", "work summary", "what did I do", "recent work", "session review"
argument-hint: "[--hours <N>] [--start <date>] [--end <date>] [--project <name>] [--types <types>]"
---

# /activity-report

**Role:** Any
**Output:** Markdown activity report from claude-mem history

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Session ID:** ${CLAUDE_SESSION_ID}

## Phase 1: Parse Arguments

**Parse from user request:**

- Time range: `--hours N` (last N hours) OR `--start/--end YYYY-MM-DD` (default: today)
- Filters: `--project <name>` (default: auto-detect from cwd), `--types <csv>`
- Output: `--format markdown|json` (default: markdown), `--output <file>`

**Valid types:** `bugfix`, `change`, `decision`, `discovery`, `feature`, `refactor`

## Phase 2: Run Script

```bash
python .claude/skills/activity-report/generate_report.py [args]
```

**Examples:**

```bash
# Today
python .claude/skills/activity-report/generate_report.py

# Date range
python .claude/skills/activity-report/generate_report.py --start 2026-02-05 --end 2026-02-06

# Last 48 hours, specific project
python .claude/skills/activity-report/generate_report.py --hours 48 --project jira-generator

# Only decisions and bugs
python .claude/skills/activity-report/generate_report.py --types decision,bugfix

# Save to file
python .claude/skills/activity-report/generate_report.py --output report.md
```

## Phase 3: Present

- Show markdown output to user
- If `--output` was used, confirm file was saved
- Offer follow-up: filter by type, expand date range, save to file
