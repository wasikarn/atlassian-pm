---
name: backlog-groomer
description: Pre-sprint backlog health assessment. Accepts JQL query or epic key, fetches all To Do/Backlog stories, checks readiness criteria (has ACs, SP estimate, epic link, VS label, no unresolved blocker), groups output into Sprint-Ready / Needs AC / Blocked / Missing Estimate / Orphan categories.
model: sonnet
tools: Read, mcp__jira-cache-server__cache_get_issue, mcp__jira-cache-server__cache_search, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search
permissionMode: dontAsk
maxTurns: 20
---

Assess backlog readiness before sprint planning. Groups stories by readiness category so the planning session starts with a clean, curated list.

## Input

One of:

- JQL query: `project = BEP AND status in ("To Do", "Backlog") AND issuetype = Story`
- Epic key: `{{PROJECT_KEY}}-XXX` → auto-generates JQL for children
- Sprint label: `vs2-coupon` → filters by label

Optional: `--limit N` (default 30 stories max)

## Steps

1. **Fetch stories** — run JQL (or build from input) with `cache_search` or `jira_search`. Fields: `summary,status,description,issuetype,parent,labels,customfield_10016,customfield_10107,issuelinks`. Limit to Stories and Tasks in To Do/Backlog.

2. **For each story, run readiness checks:**

| Check | Pass Criteria | Fail Category |
|-------|--------------|---------------|
| R1: Has ACs | Description contains "Given" or "When" or acceptance criteria section | Needs AC |
| R2: Has SP estimate | `customfield_10016` (story points) is set | Missing Estimate |
| R3: Epic link | `parent` field is set (linked to an Epic) | Orphan |
| R4: VS label | Labels include at least one `vs{N}-*` or `vs-enabler` pattern | Missing VS Label |
| R5: No unresolved blocker | No linked issues with linkType "Blocked by" AND status != Done | Blocked |
| R6: Summary quality | Summary length > 15 chars AND starts with `[service tag]` OR is descriptive | Needs Refinement |

1. **Group results:**
   - **Sprint-Ready** — passes R1-R5 (R6 is advisory)
   - **Needs AC** — fails R1
   - **Missing Estimate** — fails R2 (but passes R1)
   - **Blocked** — fails R5
   - **Orphan** — fails R3
   - **Needs VS Label** — fails R4

   A story can appear in multiple categories (e.g., Needs AC + Missing Estimate).

2. **Output grooming report**

## Rules

- Use `cache_search` first, fallback to `jira_search` for fresh data
- HR2: NEVER add ORDER BY to parent-based JQL
- For blocker check: only flag if the blocking issue is still in progress/to do (not Done)
- AC check: look for "Given", "When", "Then", "AC1", "Acceptance Criteria" in description — any of these counts
- SP check: `customfield_10016` must be numeric and > 0
- Max 30 stories per run — paginate if needed with `start_at`

## Output Format

```
## Backlog Grooming Report
📅 [date] | Total assessed: [N] stories | Sprint-ready: [N]

### ✅ Sprint-Ready ([N])
| Key | Summary | SP | VS Label | Assignee |
|-----|---------|-----|----------|----------|
| {{PROJECT_KEY}}-XXX | [summary] | 3 | vs2-coupon | Name |

### ❌ Needs AC ([N])
| Key | Summary | Missing |
|-----|---------|---------|
| BEP-YYY | [summary] | No Given/When/Then in description |

### ⚠️ Blocked ([N])
| Key | Summary | Blocked By |
|-----|---------|------------|
| BEP-ZZZ | [summary] | BEP-AAA (In Progress) |

### 📊 Missing Estimate ([N])
| Key | Summary | Has AC? |
|-----|---------|---------|

### 🔗 Orphan — No Epic ([N])
| Key | Summary |
|-----|---------|

### 🏷️ Needs VS Label ([N])
| Key | Summary | Current Labels |
|-----|---------|---------------|

---
**Summary:** [N] sprint-ready of [total]. Recommend: fix [N] AC issues before planning.
**Next step:** → /plan-sprint (use sprint-ready list as input)
```
