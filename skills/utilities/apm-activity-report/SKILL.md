---
name: apm-activity-report
context: fork
agent: Explore
model: haiku
effort: low
x-compatibility: [claude-mem]
allowed-tools: Read, Glob, Grep, Bash, Agent
description: |
  Generate activity report from claude-mem database showing past work sessions, observations, and effort.
  Default: today. Supports date ranges, project filters, observation type filters.

  Triggers: "activity report", "work summary", "what did I do", "recent work", "session review"
  Use when: generating a work activity report from session history stored in claude-mem
  Do NOT use for: sprint planning (use plan-sprint); standup reports (use standup-report)
argument-hint: "[--hours <N>] [--start <date>] [--end <date>] [--project <name>] [--types <types>]"
---

# /atlassian-pm:apm-activity-report

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
python ${CLAUDE_SKILL_DIR}/generate_report.py [args]
```

**Examples:**

```bash
# Today
python ${CLAUDE_SKILL_DIR}/generate_report.py

# Date range
python ${CLAUDE_SKILL_DIR}/generate_report.py --start 2026-02-05 --end 2026-02-06

# Last 48 hours, specific project
python ${CLAUDE_SKILL_DIR}/generate_report.py --hours 48 --project jira-generator

# Only decisions and bugs
python ${CLAUDE_SKILL_DIR}/generate_report.py --types decision,bugfix

# Save to file
python ${CLAUDE_SKILL_DIR}/generate_report.py --output report.md
```

## Phase 3: Present

- Show markdown output to user
- If `--output` was used, confirm file was saved
- Offer follow-up: filter by type, expand date range, save to file

## Examples

### ✅ Good

```text
/activity-report                                        # today's session summary (plugin debugging)
/activity-report --hours 48                             # last 48 hours across all projects
/activity-report --hours 24 --project atlassian-pm      # filter to this plugin's sessions only
/activity-report --types decision,bugfix --output report.md   # targeted audit saved to file
```

### ❌ Bad

```text
/activity-report --project {{COMPANY_LOWER}}-platform-api          # valid syntax, but wrong use case —
                                                        # this is a plugin meta-tool, not a PM workflow tool
/activity-report                                        # running without claude-mem installed —
                                                        # generate_report.py will fail; claude-mem is required
/activity-report --sprint current                       # --sprint is not a valid flag; use /plan-sprint
                                                        # or /search-issues for sprint-scoped queries
/standup-report                                         # using activity-report as a substitute for /standup-report —
                                                        # /standup-report formats output for team communication;
                                                        # activity-report is raw session history for debugging
```

**Common mistakes:**

- Using `/activity-report` as a team-facing PM tool — it reads the claude-mem session database (plugin internals), not Jira; use `/standup-report` for daily standups or `/plan-sprint` for sprint-level reporting
- Running without claude-mem installed or configured — the underlying `generate_report.py` script requires the claude-mem database; verify with `claude-mem status` first
- Passing `--sprint` or Jira-related filters — this skill has no Jira awareness; valid filters are `--hours`, `--start/--end`, `--project`, and `--types`
- Expecting Jira issue references in the output — observations are captured from Claude Code sessions, not Jira API calls

## Output Format

```text
Activity Report — 2026-04-03

Sessions: 3 | Observations: 12 | Effort: 4.5h

By Type:
- feature: 6 observations (3h)
- bugfix: 4 observations (1h)
- chore: 2 observations (30m)

Top Issues:
1. {{PROJECT_KEY}}-3001 — Payment integration (2h, feature)
2. {{PROJECT_KEY}}-3005 — Fix login timeout (1h, bugfix)
3. {{PROJECT_KEY}}-3010 — Update dependencies (30m, chore)

Recent Work:
- Implemented payment retry logic ({{PROJECT_KEY}}-3001)
- Fixed session timeout bug ({{PROJECT_KEY}}-3005)
- Upgraded npm packages ({{PROJECT_KEY}}-3010)
```

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)
