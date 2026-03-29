---
name: assign-issue
context: fork
agent: general-purpose
x-compatibility: [acli]
description: |
  Quick assign a Jira issue to a team member using acli (bypasses MCP silent failure)

  Triggers: "assign", "assign issue", "assign to", "มอบหมาย", "assign to someone", "set assignee"
  Use when: assigning an issue to a team member via acli (bypasses MCP silent failure)
  Do NOT use for: creating issues (use create-story or create-task)
argument-hint: "ABC-XXX [name]"
effort: low
---

# /assign

**Shortcut:** Assigns issue using `acli` (HR3-safe — never MCP).

## Usage

```text
/assign ABC-XXX Kobi        → assign to Kobi
/assign ABC-XXX Natthakarn  → assign to Natthakarn
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
| Natthakarn | Jira display name differs from config `name` — always lookup email from config |

> HR3: NEVER use MCP `jira_update_issue` with assignee — silently fails.
> HR6: `cache_invalidate(issue_key)` after assign.

## Examples

### ✅ Good

```text
/assign-issue {{PROJECT_KEY}}-88 joakim             # assign by first name (case-insensitive lookup)
/assign-issue {{PROJECT_KEY}}-88 wanchalerm         # assign to another team member
/assign-issue {{PROJECT_KEY}}-88 unassign           # remove current assignee
/assign-issue {{PROJECT_KEY}}-112 Natthakarn        # special case: email resolved from config, not Jira display name
```

### ❌ Bad

```text
/assign-issue                           # missing issue key and name — both are required
/assign-issue {{PROJECT_KEY}}-88                    # missing assignee name — skill cannot guess who to assign to
/assign-issue {{PROJECT_KEY}}-88 kanya@example.com  # email works but prefer first-name lookup from project-config.json
/assign-issue {{PROJECT_KEY}}-88 "Product Owner"    # role name, not a team member name — lookup will fail
```

**Common mistakes:**

- Using MCP `jira_update_issue` with an `assignee` field instead of this skill — HR3: MCP assignee silently fails with no error, leaving the issue unassigned
- Passing a display name that doesn't match the `name` field in `project-config.json` — always use the config `name` value (e.g., `joakim`, not the full display name)
- Not confirming the resolved email before assigning — especially important for members whose Jira display name differs from their config name (e.g., Natthakarn)

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)
## References

- [Tools](../../../references/tools.md) - MCP vs acli decision rules, acli assign command
- [HR Rules](../../../references/hr-rules.md) - HR3: MCP assignee silently fails — always use acli
