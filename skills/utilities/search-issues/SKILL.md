---
name: search-issues
disable-model-invocation: true
context: fork
model: haiku
x-compatibility: [jira-cache, mcp-atlassian]
allowed-tools: Read, Glob, Grep, Bash, Agent, mcp__mcp-atlassian__jira_search, mcp__plugin_atlassian-pm_jira-cache__cache_search, mcp__plugin_atlassian-pm_jira-cache__cache_text_search, mcp__plugin_atlassian-pm_jira-cache__cache_similar_issues
description: |
  Search for existing Jira issues to prevent duplicates — invoke proactively whenever the user
  wants to create any new issue (story/task/epic/subtask) before they start creating.
  3-phase workflow with JQL + semantic similarity check.

  Supports: keyword search, JQL query, issue key, filters (sprint, assignee, status, type)

  Triggers: "search", "find", "find issue", "does it already exist", "look for", "check if exists",
  "before creating", "is there already", "find related", "search sprint", "search backlog",
  "any similar issues", "ค้นหา", "มี issue อยู่แล้วไหม"
argument-hint: "[keyword] [--filters]"
---

# /search-issues

**Role:** Any
**Output:** List of matching issues

## Phases

### 1. Parse Search Criteria

| Input | Generated JQL |
| --- | --- |
| `"credit"` | `project = {{PROJECT_KEY}} AND summary ~ "credit"` |
| `ABC-123` | `key = ABC-123` |
| `ABC-123 --children` | `parent = ABC-123` |
| `--sprint current` | `sprint IN openSprints()` |
| `--assignee me` | `assignee = currentUser()` |
| `--status "In Progress"` | `status = "In Progress"` |
| `--type Story` | `type = Story` |

### 2. Execute Search

```text
MCP: jira_search(jql: "[generated JQL]", fields: "summary,status,assignee,issuetype,priority", limit: 20)
```

### 2.5 Semantic Similarity Check (keyword search only)

**Skip if:** input is issue key (`ABC-123`), uses `--jql`, or uses `--children` flag.

```text
cache_similar_issues(query: "<keyword>", limit: 5, exclude_keys: [<keys from Phase 2>])
```

Filter results by distance (cosine distance, 0 = identical):

| Distance | Label | Action |
| --- | --- | --- |
| < 0.25 | ⚠️ Likely duplicate | แจ้งเตือนชัดเจน |
| 0.25–0.45 | 🔍 Possibly related | แสดงไว้อ้างอิง |
| > 0.45 | (skip) | noise — ไม่แสดง |

Similarity % = `(1 - distance/2) × 100`

If embeddings not available (sqlite-vec not installed) → skip gracefully, no error.

### 3. Display Results

```text
## Search Results
Query: `project = {{PROJECT_KEY}} AND summary ~ "credit"`
Found: 5 issues

| Key | Type | Summary | Status |
|-----|------|---------|--------|
| ABC-123 | Story | Credit feature | In Progress |
| ABC-124 | Sub-task | [BE] Credit API | To Do |

## 🔍 Semantic Matches (BERT similarity)
| Key | Summary | Similarity |
|-----|---------|------------|
| ABC-120 | [BE] เติมเครดิต wallet | ⚠️ 94% (likely duplicate) |
| ABC-118 | Credit payment flow | 🔍 72% (possibly related) |

💡 พบ likely duplicate → ยืนยันก่อนสร้าง issue ใหม่
```

If no semantic matches above threshold → omit the section entirely.

---

## Filter Options

| Flag | Example |
| --- | --- |
| `--sprint` | `--sprint current`, `--sprint "Sprint 5"` |
| `--assignee` | `--assignee me` |
| `--status` | `--status "In Progress"` |
| `--type` | `--type Story` |
| `--label` | `--label BE` |
| `--children` | `ABC-XXX --children` |
| `--jql` | `--jql "custom query"` |

---

## Use Cases

> See [references/use-cases.md](references/use-cases.md) for example commands by use case.

---

## Examples

### ✅ Good

```text
/search-issues "credit wallet"                          # keyword search + semantic similarity check
/search-issues {{PROJECT_KEY}}-42 --children                        # list all subtasks of a parent issue
/search-issues --sprint current --assignee me           # my open items in active sprint
/search-issues --type Story --status "In Progress"      # filter by type + status
/search-issues --jql "labels = tech-debt AND sprint IN openSprints()"   # custom JQL filter
```

### ❌ Bad

```text
/search-issues                                          # no query — produces empty or full-project dump
/search-issues --jql "parent = {{PROJECT_KEY}}-42 ORDER BY created"    # HR2 violation: ORDER BY with parent= causes JQL parser error
/search-issues "payment flow" --sprint current          # valid, but using this for sprint planning decisions —
                                                        # use /plan-sprint instead; search-issues only surfaces issues
/create-story "Add credit feature"                      # creating without running /search-issues first —
                                                        # skips duplicate check; may create redundant issue
```

**Common mistakes:**

- Using `ORDER BY` together with `parent =`, `parent in`, or `key in (...)` in a `--jql` query — this triggers a Jira JQL parser error (HR2); remove the `ORDER BY` clause
- Treating search results as a sprint planning tool — `/search-issues` surfaces issues but does not evaluate capacity or priority; use `/plan-sprint` for planning decisions
- Not running `/search-issues` before `/create-story` or `/create-task` — the semantic similarity check catches near-duplicates that exact JQL misses

---

## References

- [references/use-cases.md](references/use-cases.md) — example commands by use case
- [JQL Quick Reference](../../../references/jql-quick-ref.md)
