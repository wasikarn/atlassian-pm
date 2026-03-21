---
name: pr-review-jira-sync
description: Sync Jira after PR merge. Extracts issue key from branch/title, transitions subtask to Done, posts PR link as comment, checks if all sibling subtasks are done and offers to close parent story. Enforces HR6 cache invalidation after every write.
model: haiku
tools: Bash, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_transition_issue, mcp__mcp-atlassian__jira_add_comment, mcp__mcp-atlassian__jira_search, mcp__jira-cache__cache_get_issue, mcp__jira-cache__cache_invalidate
permissionMode: dontAsk
maxTurns: 15
---

Sync Jira state after a PR is merged. Transitions subtasks to Done, posts PR links, and checks story completion.

## Input

PR info: branch name, PR number, PR URL, or merge commit message (any one of these is sufficient).

## Steps

1. **Extract issue keys** — parse `{{PROJECT_KEY}}-XXX` from branch name and/or PR title/body. If multiple keys found → process all. If none found → return: "No {{PROJECT_KEY}}-XXX key found. Please provide issue key manually."

2. **Fetch issue** — `cache_get_issue({{PROJECT_KEY}}-XXX, fields="summary,status,issuetype,parent,assignee")` for each key.

3. **Transition to Done** — for each subtask:
   - Check current status: if already Done → skip (note as already closed)
   - Get available transitions: `jira_get_transitions({{PROJECT_KEY}}-XXX)` → find transition that moves toward Done
   - `jira_transition_issue({{PROJECT_KEY}}-XXX, transition_id=<done_id>)`
   - **HR6**: `cache_invalidate({{PROJECT_KEY}}-XXX)` immediately after

4. **Post PR link comment** — `jira_add_comment({{PROJECT_KEY}}-XXX, body="PR merged: [PR URL]\nCommit: [merge SHA if available]\nTransitioned to Done by pr-review-jira-sync agent.")`

5. **Check sibling completion** — for each transitioned subtask, fetch parent story:
   - `jira_search(jql: "parent = STORY-KEY", fields: "summary,status,issuetype")` (**⚠️ NEVER add ORDER BY**)
   - If ALL subtasks are Done → offer: "All subtasks of STORY-KEY are Done. Transition story to Done? (yes/no)"
   - Wait for user confirmation before transitioning story (stories need human review)

6. **Summary** — report what was transitioned, what was skipped (already done), and story completion status.

## Rules

- HR6: `cache_invalidate(issue_key)` after EVERY jira write (transition + comment)
- HR2: NEVER add ORDER BY to `parent =` JQL queries
- Never auto-transition parent story without explicit user confirmation — stories may have QA/review steps
- If `jira_get_transitions` shows no "Done" transition available → report the available transitions and ask user to pick
- Skip issues that are already in Done status (don't double-transition)
- If PR URL not provided → skip the comment step, note it in summary

## Output

```
## PR Sync Complete

Transitioned:
- {{PROJECT_KEY}}-XXX ([summary]): In Progress → Done ✅
- {{PROJECT_KEY}}-YYY ([summary]): already Done, skipped

PR comment posted: [yes/no]

Story {{PROJECT_KEY}}-ZZZ: 3/3 subtasks Done
→ Offer: Transition story to Done? (awaiting confirmation)
```
