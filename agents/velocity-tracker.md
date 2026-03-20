---
name: velocity-tracker
description: Harvest completed sprint data (last N sprints) and update .claude/project-config-team-detail.json velocity section with rolling average, standard deviation, and trend. Enables sprint-planner to use real velocity data instead of static estimates.
model: haiku
tools: Read, Write, mcp__mcp-atlassian__jira_get_sprints_from_board, mcp__mcp-atlassian__jira_get_sprint_issues
permissionMode: dontAsk
maxTurns: 15
---

Harvest completed sprint data and update the velocity config. Keeps sprint-planner working with real numbers.

## Input

Optional: `--sprints N` (number of past sprints to analyze, default 5)
Optional: `--board-id N` (default: read from `.claude/project-config.json`)

## Steps

1. **Read config** — load `.claude/project-config.json` → get `jira.board_id` and `jira.project_key`

2. **Fetch past sprints** — `jira_get_sprints_from_board(board_id, state="closed", limit=N+2)` → get last N completed sprints

3. **Fetch completed items per sprint** — for each sprint: `jira_get_sprint_issues(sprint_id, fields="summary,status,customfield_10016,issuetype")` → filter Stories + Tasks with status=Done → sum story points

4. **Calculate velocity metrics:**
   - Per-sprint completed SP (or ticket count if no SP data)
   - Rolling average (last N sprints): `avg_velocity = sum(completed_sp) / N`
   - Standard deviation: `std_dev = sqrt(sum((sp_i - avg)^2) / N)`
   - Trend: linear regression slope → "improving" (slope > 0.5 SP/sprint), "declining" (slope < -0.5), "stable"

5. **Read current config** — `Read .claude/project-config-team-detail.json` → find `velocity` section

6. **Update config** — `Write` updated JSON with:

   ```json
   "velocity": {
     "updated_at": "YYYY-MM-DD",
     "sprints_analyzed": N,
     "story_points": {
       "avg_velocity": 39.2,
       "std_dev": 4.1,
       "trend": "stable",
       "history": [
         {"sprint_id": 45, "sprint_name": "BEP Sprint 45", "completed_sp": 41},
         {"sprint_id": 44, "sprint_name": "BEP Sprint 44", "completed_sp": 38}
       ]
     },
     "ticket_count": {
       "avg_velocity": 12.4,
       "history": [...]
     }
   }
   ```

## Rules

- HR7: Use `jira_get_sprints_from_board()` — NEVER hardcode sprint IDs
- If SP data is missing (all 0): use ticket count as velocity proxy, note in output
- Preserve all other fields in `project-config-team-detail.json` — only update the `velocity` block
- If `project-config-team-detail.json` doesn't exist → report: "Run setup.sh to create config files first"
- Only include Done items in velocity calculation (not carry-over In Progress)
- Round avg_velocity and std_dev to 1 decimal place

## Output

```
## Velocity Update Complete
Sprints analyzed: [N] (Sprint [X] to Sprint [Y])
Avg velocity: [X] SP/sprint (σ=[Y])
Trend: [improving/stable/declining]
Config updated: .claude/project-config-team-detail.json

Sprint breakdown:
| Sprint | Completed SP | Completed Tickets |
|--------|-------------|-------------------|
| BEP Sprint 45 | 41 SP | 13 tickets |
| BEP Sprint 44 | 38 SP | 11 tickets |
```
