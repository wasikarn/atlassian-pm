---
name: assign-issue
disable-model-invocation: true
x-compatibility: [acli]
description: |
  Quick assign a Jira issue to a team member using acli (bypasses MCP silent failure)

  Triggers: "assign", "assign issue", "assign to"
argument-hint: "ABC-XXX [name]"
---

# /assign

**Shortcut:** Assigns issue using `acli` (HR3-safe — never MCP).

## Usage

```text
/assign ABC-XXX Kobi        → assign to Kobi
/assign ABC-XXX {{SLOT_5}}  → assign to {{SLOT_5}}
/assign ABC-XXX unassign    → remove assignee
```

## Team Lookup

Read team from `project-config.json` → `team.members[]`. Match by first name (case-insensitive).

## Steps

1. Parse issue key + name from argument
2. Lookup email from `project-config.json` → `team.members[].email` (match by `name` field, case-insensitive first name)
3. Run: `acli jira workitem assign -k "KEY" -a "email" -y`
4. If "unassign" → Run: `acli jira workitem assign -k "KEY" -a "" -y`
5. Confirm: `Assigned ABC-XXX to [name] ([email])`

## Special Cases

| Name | Note |
|------|------|
| {{SLOT_5}} | Jira display name differs from config `name` — always lookup email from config |

> HR3: NEVER use MCP `jira_update_issue` with assignee — silently fails.
> HR6: `cache_invalidate(issue_key)` after assign.

## Examples

### ✅ Good

```text
/assign-issue {{PROJECT_KEY}}-88 {{SLOT_3}}             # assign by first name (case-insensitive lookup)
/assign-issue {{PROJECT_KEY}}-88 {{SLOT_4}}         # assign to another team member
/assign-issue {{PROJECT_KEY}}-88 unassign           # remove current assignee
/assign-issue {{PROJECT_KEY}}-112 {{SLOT_5}}        # special case: email resolved from config, not Jira display name
```

### ❌ Bad

```text
/assign-issue                           # missing issue key and name — both are required
/assign-issue {{PROJECT_KEY}}-88                    # missing assignee name — skill cannot guess who to assign to
/assign-issue {{PROJECT_KEY}}-88 {{SLOT_6}}@example.com  # email works but prefer first-name lookup from project-config.json
/assign-issue {{PROJECT_KEY}}-88 "Product Owner"    # role name, not a team member name — lookup will fail
```

**Common mistakes:**

- Using MCP `jira_update_issue` with an `assignee` field instead of this skill — HR3: MCP assignee silently fails with no error, leaving the issue unassigned
- Passing a display name that doesn't match the `name` field in `project-config.json` — always use the config `name` value (e.g., `{{SLOT_3}}`, not `Joakim Svensson`)
- Not confirming the resolved email before assigning — especially important for members whose Jira display name differs from their config name (e.g., {{SLOT_5}})
