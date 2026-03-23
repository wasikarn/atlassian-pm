---
name: activity-report
disable-model-invocation: true
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
python .claude/skills/utilities/activity-report/generate_report.py [args]
```

**Examples:**

```bash
# Today
python .claude/skills/utilities/activity-report/generate_report.py

# Date range
python .claude/skills/utilities/activity-report/generate_report.py --start 2026-02-05 --end 2026-02-06

# Last 48 hours, specific project
python .claude/skills/utilities/activity-report/generate_report.py --hours 48 --project jira-generator

# Only decisions and bugs
python .claude/skills/utilities/activity-report/generate_report.py --types decision,bugfix

# Save to file
python .claude/skills/utilities/activity-report/generate_report.py --output report.md
```

## Phase 3: Present

- Show markdown output to user
- If `--output` was used, confirm file was saved
- Offer follow-up: filter by type, expand date range, save to file

---

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

---

## 🎓 Domain Expert Notes

### Why This Approach

Activity reports derive from the SPACE framework's "Activity" dimension — tracking developer actions over time to surface patterns, not just outputs. Raw session data (what was done, decided, or discovered) is the rawest signal of engineering work before it gets abstracted into Jira tickets or PR counts.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| SPACE Framework (Activity dimension) | Phase 2–3 output grouping | Structures observations by type (feature, bugfix, decision) rather than raw log lines, matching SPACE's principle of multi-dimensional activity capture |
| DORA Lead Time proxy | `--hours` range selection | Short-range reports (≤24h) approximate DORA's "lead time for changes" at the individual contributor level |
| OKR progress signal | `--types decision,feature` filter | Filtering by type lets managers extract signal relevant to OKR check-ins without noise from routine chores |

### Key Metrics

- **Session depth:** Number of distinct observation types in a session — low variety (all `change`) suggests mechanical work; high variety (mix of `decision`, `discovery`, `feature`) suggests exploratory or design work
- **Decision density:** Ratio of `decision` observations to total — target >10% on architecture-heavy weeks; <5% may indicate execution-only sprints with no strategic thinking
- **Bugfix recurrence:** Repeated `bugfix` observations on the same area across sessions signal systemic quality debt, not isolated incidents

### Expert Decision Criteria

- If `--hours 48` returns fewer than 3 observations per day → claude-mem may not be capturing sessions correctly; run `claude-mem status` to verify
- If `--types decision` returns 0 results for a full sprint period → likely missing architectural context documentation; use this as a trigger to add ADR (Architecture Decision Records) practice
- If report is used for team-facing standup → switch to `/standup-report`; activity-report is for individual session archaeology, not team communication

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Output shows 0 observations for a known work day | claude-mem database gap or wrong `--project` filter | Run `claude-mem status` to verify DB health; omit `--project` to see all sessions |
| All observations are type `change` with no `decision` or `discovery` | Sessions ran in non-interactive mode or observations weren't captured | Verify claude-mem hooks are active; check `~/.claude-mem/settings.json` |
| `--start/--end` range returns empty despite known work | Date format mismatch (expects `YYYY-MM-DD`) or timezone offset in DB | Use `--hours N` as fallback; verify system timezone matches DB timestamps |
| Report used by manager to evaluate individual performance | Measurement anti-pattern — activity ≠ productivity | SPACE framework explicitly warns against using activity metrics for performance reviews; use for team retrospectives only |

### Authoritative References

- **Nicole Forsgren et al. (SPACE, 2021):** "Activity metrics should never be used in isolation — they gain meaning only when correlated with satisfaction and efficiency dimensions"
- **DORA State of DevOps Report 2024:** Deployment frequency and lead time are the two DORA metrics most correlated with organizational performance — cross-reference activity report dates against deploy events for richer signal
- **Atlassian Engineering Blog:** Session-level observation capture (what this skill uses) maps to the "flow state" signals in SPACE's Efficiency dimension

---

## References

- [JQL Quick Reference](../../../references/jql-quick-ref.md) - JQL patterns for filtering by date and assignee
