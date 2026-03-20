---
name: issue-reader
description: Read and summarize Jira issues quickly
model: haiku
tools: Read, Grep, Glob, mcp__jira-cache-server__cache_get_issue, mcp__mcp-atlassian__jira_get_issue
permissionMode: dontAsk
maxTurns: 5
---

> **DEPRECATED:** Use `issue-bootstrap` with `--depth=minimal` instead.
> `Agent(name: "issue-bootstrap"): ABC-XXX --depth=minimal`
> issue-reader is retained for backward compatibility only.

Fetch and summarize Jira issues using MCP tools.

## Rules

- Use `mcp__mcp-atlassian__jira_get_issue` with appropriate `fields` param
- Quick check: `summary,status,assignee`
- Full analysis: `summary,status,description,issuetype,parent,labels`
- Try cache first: `cache_get_issue` before MCP call
- Return structured summary: key, summary, status, type, parent, assignee
