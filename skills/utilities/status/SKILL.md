---
name: status
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian]
description: |
  This skill should be used when starting a session, resuming after a break, or when unsure what to work on next. Shows active sprint status, team WIP, pending HR issues, and suggests next action.
  
  Trigger phrases: "status", "what's next", "sprint status", "what should I work on", "where were we", "session status", "สถานะ sprint", "ทำอะไรต่อ", "plugin ใช้ได้ไหม"
  
  This skill should NOT be used for detailed sprint planning (use plan-sprint) or closing sprint (use close-sprint).
argument-hint: ""
effort: low
allowed-tools: [mcp__mcp-atlassian__jira_get_sprints_from_board, mcp__plugin_atlassian-pm_atlassian-cache__cache_sprint_issues, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__mcp-atlassian__jira_search, Bash]
---

# /atlassian-pm:status

**Role:** Session Navigator
**Output:** Prioritized action table for the current session

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Project Key:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['project_key'])"`
- **Board ID:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['board_id'])"`

## Instructions

Run all steps and produce the final status report. Do not stop early.

### Step 1 — Active Sprint

Fetch active sprint and its issues:

```text
MCP: jira_get_sprints_from_board(board_id={{BOARD_ID}}, state="active") → get sprint_id, sprint_name, endDate
MCP: cache_sprint_issues(sprint_id=<active_sprint_id>) → get all issues
```

From sprint issues, extract:

| Status | Issues |
| --- | --- |
| In Progress | issue keys + summaries + assignees |
| In Review | issue keys waiting for review |
| Blocked | issue keys with "Blocks" link type or flag |
| To Do (ready) | issue keys with subtasks + ACs (DoR-ready) |

### Step 2 — Stuck Issues

Check for issues flagged by the board monitor as stuck (no status change beyond threshold):

```bash
python3 -c "
import json, os
from pathlib import Path
data_dir = Path(os.environ.get('CLAUDE_PLUGIN_DATA', str(Path.home() / '.claude/plugins/data/atlassian-pm-atlassian-pm')))
stuck_file = data_dir / 'stuck_issues.json'
if not stuck_file.exists():
    print('No stuck issues file — board monitor may not be running')
else:
    data = json.loads(stuck_file.read_text())
    pending = data.get('pending', [])
    surfaced = data.get('surfaced', [])
    if pending:
        print(f'PENDING ({len(pending)} unreviewed):')
        for i in pending:
            print(f'  {i[\"issue_key\"]} — {i[\"status\"]} for {i[\"age_days\"]:.1f}d: {i.get(\"summary\",\"\")}')
    elif surfaced:
        recent = sorted(surfaced, key=lambda x: x.get('surfaced_at',''), reverse=True)[:3]
        print(f'Recently surfaced ({len(surfaced)} total, showing latest 3):')
        for i in recent:
            print(f'  {i[\"issue_key\"]} — {i[\"status\"]} for {i[\"age_days\"]:.1f}d (surfaced {i.get(\"surfaced_at\",\"\")[:10]})')
    else:
        print('No stuck issues detected')
"
```

### Step 4 — Pending HR State

Check session state file for unflushed HR violations:

```bash
SESSION_STATE=$(ls /tmp/claude-hooks-state/*.json 2>/dev/null | tail -1)
if [ -f "$SESSION_STATE" ]; then
  python3 -c "
import json, sys
s = json.load(open('$SESSION_STATE'))
hr5 = s.get('hr5_pending', [])
hr6 = s.get('hr6_pending', [])
if hr5:
    print('HR5 pending:', ', '.join(p['child'] + '->' + p['parent'] for p in hr5))
if hr6:
    print('HR6 pending:', ', '.join(hr6))
if not hr5 and not hr6:
    print('No pending HR violations')
"
fi
```

### Step 3 — Days Left in Sprint

```bash
python3 -c "
from datetime import datetime, date
end = '{{SPRINT_END_DATE}}'  # replace with actual endDate from Step 1
try:
    days = (datetime.strptime(end[:10], '%Y-%m-%d').date() - date.today()).days
    print(f'{days} days left in sprint ({end[:10]})')
except:
    print('Sprint end date unknown')
"
```

### Step 5 — Build Status Report

Output a structured status report:

```text
## 📊 Sprint Status — {{SPRINT_NAME}} ({{N}} days left)

### 🔴 Needs Immediate Attention
[HR5/HR6 pending violations — must resolve before next Jira write]
[Blocked issues — unblock or escalate]

### 🟡 In Progress ({{N}} issues)
| Key | Summary | Assignee | Status |
|-----|---------|----------|--------|
| {{PROJECT_KEY}}-XXX | [summary] | [name] | In Progress |

### 🟢 Ready for Review ({{N}} issues)
[Stories/tasks in "In Review" needing review]

### ⬜ Next Up (DoR-ready backlog)
[Top 3 To Do issues with subtasks + ACs — ready to start]

### 💡 Suggested Next Actions
1. [Most urgent action based on above data]
2. [Second priority]
3. [Third priority — e.g. /plan-sprint if sprint ends in < 3 days]
```

**Priority logic for suggestions:**

- HR5/HR6 pending → "Resolve pending HR violations first: run `jira_get_issue(key, fields='parent')`"
- Blocked issues → "Unblock [KEY]: remove blocker or escalate to Tech Lead"
- ≥ 3 In Progress per assignee → "WIP limit risk: [name] has {N} tasks in progress"
- Sprint ends in < 3 days and unfinished tasks → "Sprint closing soon — run `/atlassian-pm:close-sprint`"
- All In Progress tasks done → "Run `/atlassian-pm:verify-issue KEY --with-subtasks` before moving to Done"

## Examples

### ✅ Good

```text
/atlassian-pm:status         # get current session overview at any time
/status                      # shorter alias if not namespaced
```

### ❌ Bad

```text
/status {{PROJECT_KEY}}-123              # takes no arguments — use /verify-issue for single issue check
/status --verbose            # no flags supported
```

**Common mistakes:**

- Using `/status` as a substitute for `/verify-issue` — status shows sprint-level view, not issue quality scores
- Running status mid-skill when context is already loaded — status makes extra MCP calls; use it at session start, not between skill phases

## 🎓 Domain Expert Notes

The session navigator pattern addresses a core problem in AI-assisted PM work: **session amnesia**. Each Claude session starts without knowledge of what was done in prior sessions. Status solves this by fetching live Jira state (not relying on session memory) and cross-referencing with hook state files that do survive across sessions.

The pending HR check reads from `/tmp/claude-hooks-state/` — these files are written by hooks during tool calls and persist across session boundaries (until machine restart). They are the only cross-session state available without a Jira read.
