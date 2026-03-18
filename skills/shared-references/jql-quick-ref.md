# JQL Quick Reference

> JQL patterns for the BEP project

---

## Common Patterns (BEP Project)

### Find Stories by Sprint

```text
project = BEP AND type = Story AND sprint IN openSprints()
```

### Find Sub-tasks of Story

```text
parent = {{PROJECT_KEY}}-XXX
```

> 🚨 **CRITICAL — JQL queries that ALWAYS cause parse errors:**
>
> ```text
> ❌ parent = {{PROJECT_KEY}}-XXX ORDER BY created DESC       → Error: Expecting ')' but got 'ORDER'
> ❌ parent = {{PROJECT_KEY}}-XXX AND issuetype = Story ORDER BY  → same error
> ❌ key in (BEP-1, BEP-2) ORDER BY created       → Error: parse error
> ```
>
> **Safe alternatives:**
>
> ```text
> ✅ parent = {{PROJECT_KEY}}-XXX                              → no ORDER BY needed
> ✅ "Parent Link" = {{PROJECT_KEY}}-XXX ORDER BY created DESC → use "Parent Link" if sorting needed
> ✅ key in (BEP-1, BEP-2)                         → remove ORDER BY
> ```
>
> **Rule: NEVER add ORDER BY to `parent =` or `key in (...)` queries**

### Find My Assigned Issues

```text
project = BEP AND assignee = currentUser() AND status != Done
```

### Find Unassigned Work

```text
project = BEP AND assignee IS EMPTY AND status = "To Do"
```

### Find Recently Updated

```text
project = BEP AND updated >= -7d ORDER BY updated DESC
```

### Find by Tag (Label)

```text
project = BEP AND labels = "BE"
project = BEP AND labels IN ("FE-Admin", "FE-Web")
```

### Find QA Sub-tasks

```text
project = BEP AND type = Sub-task AND summary ~ "[QA]"
```

### Find Epics

```text
project = BEP AND type = Epic AND status != Done
```

### Find Stories in Epic

```text
"Epic Link" = {{PROJECT_KEY}}-XXX AND type = Story
```

---

## Operators

| Operator | Usage | Example |
| --- | --- | --- |
| `=` | Exact match | `status = "Done"` |
| `!=` | Not equal | `status != "Done"` |
| `~` | Contains | `summary ~ "credit"` |
| `IN` | Multiple values | `status IN ("To Do", "In Progress")` |
| `IS EMPTY` | No value | `assignee IS EMPTY` |
| `IS NOT EMPTY` | Has value | `fixVersion IS NOT EMPTY` |

---

## Date Functions

```text
created >= -7d              # Last 7 days
updated >= startOfDay()     # Today
created >= startOfWeek()    # This week
created >= startOfMonth()   # This month
```

---

## User Functions

```text
assignee = currentUser()    # Me
reporter = currentUser()    # Created by me
```

---

## Sprint Functions

```text
sprint IN openSprints()     # Current sprint
sprint IN futureSprints()   # Future sprints
sprint IN closedSprints()   # Past sprints
```

---

## Order Results

```text
ORDER BY priority DESC              # Priority first
ORDER BY created DESC               # Newest first
ORDER BY updated DESC               # Recently active
ORDER BY duedate ASC               # Earliest due
ORDER BY priority DESC, created ASC # Combined
```

---

## Examples for /search-issues Command

| Use Case | JQL |
| --- | --- |
| Find story before creating | `project = BEP AND type = Story AND summary ~ "keyword"` |
| Check my sprint work | `project = BEP AND assignee = currentUser() AND sprint IN openSprints()` |
| Review sub-tasks | `"Parent Link" = {{PROJECT_KEY}}-XXX ORDER BY created` |
| Find blockers | `project = BEP AND priority = Highest AND status != Done` |
| Overdue items | `project = BEP AND duedate < now() AND status != Done` |

---

## Related

- Full JQL reference: `~/.claude/skills/atlassian-cli/references/jql-patterns.md`
