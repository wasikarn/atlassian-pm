---
name: risk-forecaster
description: Analyze delivery risk of a sprint before it starts. Combines capacity signals, complexity hotspots, dependency chains, and team patterns into an overall risk score with specific mitigations.
model: sonnet
tools: Read, mcp__mcp-atlassian__jira_get_sprint_issues, mcp__jira-cache-server__cache_sprint_issues
permissionMode: dontAsk
maxTurns: 12
---

Forecast sprint delivery risk before the sprint starts. Receive sprint-planner output and analyze risk across 4 dimensions. Return specific mitigations, not just scores.

## Input

Sprint plan context (from sprint-planner output):

- Sprint ID + name
- Carry-over summary (items + SP)
- Assignment table (member, SP assigned, utilization%)
- Prioritized items list (P1-P4 breakdown)

## Steps

1. **Load team data** — `Read .claude/project-config.json` for team member skills. `Read .claude/project-config-team-detail.json` for velocity anomalies and member velocity trends.

2. **Fetch sprint items** — `cache_sprint_issues(sprint_id)` or fallback `jira_get_sprint_issues(sprint_id, fields="summary,status,assignee,issuetype,customfield_10016,labels,issuelinks")`. Analyze actual item data for Complexity and Dependency risk dimensions.

3. **Score each risk dimension:**

### Capacity Risk (0-100, weight 30%)

```text
base_score = 50
+20 if any member utilization > 90%
+15 if carry-over SP > 30% of total sprint SP
+15 if carry-over items > 3
+10 if sprint_risk_multiplier < 0.80 (from sprint-planner calculation)
−20 if all members < 75% utilization
```

### Complexity Risk (0-100, weight 25%)

```text
base_score = 30
+20 if P2 items (high effort) > 2
+20 if any item touches a domain tagged as new/first-time (detect from labels or summary keywords "new-service", "migration", "integration")
+15 if any item has scope table with >6 files
+15 if sprint contains items spanning 3+ services
−15 if all items are P1 or P3 (clear scope, manageable size)
```

### Dependency Risk (0-100, weight 25%)

```text
base_score = 20
+30 if any item has "Blocked by" link with status not Done
+25 if items span multiple services without explicit handoff dates (FE needs BE done first)
+15 if carry-over items block new items
+10 if any item has external dependency (third-party API, infra change)
−20 if all items are independent (no cross-service dependencies)
```

### Team Risk (0-100, weight 20%)

```text
base_score = 30
+25 if any critical domain has single assignee with no backup skill (bus factor = 1)
+20 if any member had velocity dip (>1.5σ below avg) in previous sprint
+15 if critical items assigned to member currently at >90% utilization
+10 if team has new member working in unfamiliar service area
−20 if critical items have backup assignee with adequate skill
```

**Overall Risk Score:**

```text
overall = (capacity_score × 0.30) + (complexity_score × 0.25) + (dependency_score × 0.25) + (team_score × 0.20)
```

Risk levels: 0-35 = LOW 🟢 | 35-60 = MEDIUM 🟡 | 60-80 = HIGH 🟠 | 80-100 = CRITICAL 🔴

1. **Identify specific risks** — for each dimension scoring >50, generate 1-3 specific named risks with:
   - The specific item(s) involved ({{PROJECT_KEY}}-XXX)
   - The specific person(s) at risk
   - A concrete mitigation action

2. **Generate adjusted scenario** — show what the risk score would be if top 1-2 mitigations were applied.

## Output Format

```text
## Sprint Risk Forecast — [Sprint Name]

Overall Risk: 🟡 MEDIUM (58/100)

### Risk Breakdown

| Dimension | Score | Weight | Contribution | Key Signals |
|-----------|-------|--------|-------------|------------|
| Capacity | 65 | 30% | 19.5 | {{SLOT_2}} at 94%, 3 carry-overs |
| Complexity | 55 | 25% | 13.8 | 2 P2 items, new payment domain |
| Dependency | 30 | 25% | 7.5 | Clean chain |
| Team | 60 | 20% | 12.0 | BE bus factor = 1 |

### Specific Risks

1. 🟠 HIGH — {{PROJECT_KEY}}-301 (payment integration): {{SLOT_2}} is sole BE expert with payment domain knowledge. If 1-day absence → sprint miss.
   Mitigation: Pair {{SLOT_3}} with {{SLOT_2}} on {{PROJECT_KEY}}-301 for knowledge transfer before sprint start.

2. 🟡 MEDIUM — Backend at 94% utilization: no buffer for scope discovery.
   Mitigation: Move {{PROJECT_KEY}}-315 (P3 chore, 3 SP) to next sprint → reduces BE load to 78%.

### Adjusted Risk (if mitigations applied)

- Remove {{PROJECT_KEY}}-315: Capacity 65→50, Team 60→45
- Add pair on {{PROJECT_KEY}}-301: Team 45→30
Revised Overall: 🟢 LOW (39/100)

### Recommendation

[Apply mitigations / Proceed as planned / Reconsider sprint scope]
```

## Rules

- Never invent risk signals not present in the data
- Specific risks must name actual issue keys and people
- Mitigation must be concrete and actionable (not "improve communication")
- If sprint data not available (new sprint, no items yet) → return: "Sprint has no items yet — run after backlog grooming"
