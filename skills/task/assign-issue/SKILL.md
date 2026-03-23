---
name: assign-issue
disable-model-invocation: true
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
- Passing a display name that doesn't match the `name` field in `project-config.json` — always use the config `name` value (e.g., `{{SLOT_3}}`, not the full display name)
- Not confirming the resolved email before assigning — especially important for members whose Jira display name differs from their config name (e.g., {{SLOT_5}})

## 🎓 Domain Expert Notes

### Why This Approach

Pull-based assignment (developers choose work matching their current capacity and skills) consistently outperforms push-based (manager allocates) in throughput and quality — but in mixed-seniority teams, a recommended-then-confirmed model balances autonomy with senior oversight. This skill implements that hybrid: auto-recommend via skill matrix, human confirms.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| T-shaped skills model (David Guest, 1991; Tim Brown/IDEO, 2010) | Team config `skill_profile` matching | T-shape = deep expertise in one domain (vertical bar) + broad ability to collaborate across others (horizontal bar). `expert` = vertical bar owner; `intermediate`/`basic` = horizontal bar breadth. Assign vertical bar owners to their domain by default; use horizontal bar assignments intentionally for skill growth |
| WIP limits per person (Anderson, *Kanban*, 2010) | Assignment recommendation logic | Anderson: >2 concurrent items introduces context-switching overhead that degrades both throughput and quality. The ≤2 WIP target is the individual-level equivalent of the team-level WIP limit on the Kanban board |
| Skill-based routing (ITIL Service Management) | Phase 4 of bug-triage (service tag → assignee) | ITIL formalises skill-based routing as matching work items to agents with the appropriate skill level — reduces rework by 30-40% in service desk contexts (Axelos, ITIL 4 Foundation) |

### Key Metrics

- **WIP per person:** target ≤ 2 active issues; >3 is a leading indicator of context switching and missed sprint goals
- **Assignment accuracy:** % of issues completed by originally assigned person without reassignment — below 80% signals poor initial matching
- **Time-to-assign:** P1 bugs should be assigned within 15 minutes of creation; P2 within 1 business day

### Expert Decision Criteria

- If `skill_profile[domain] = "expert"` AND current WIP < 2 → strong recommend
- If `skill_profile[domain] = "intermediate"` AND task is P1 → pair with an expert or escalate to Tech Lead
- If `skill_profile[domain] = "intermediate"` AND task is non-critical → this is a **growth assignment** — intentionally assigning 1 level above current skill to develop capability. Growth assignments require: (a) no sprint-critical timeline, (b) senior reviewer listed as watcher, (c) note in the issue description that this is a learning opportunity
- If `focus_factor < 0.6` (e.g., 0.5 for {{SLOT_1}}) → reserve for complex/review work, avoid routine chores
- If member has `email: null` → QA roles ({{SLOT_6}}, {{SLOT_7}}) cannot be assigned via acli; flag for manual Jira assignment
- Never assign a P1 Critical bug to a single junior without a senior reviewer listed as watcher

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
|---------|-----------|-----------|
| Issue stays unassigned after skill runs | `email: null` in config OR MCP used instead of acli (HR3) | Always use `acli assign`; populate email in config for QA members |
| Same person always overloaded | Assignment ignores current WIP, only matches skill | Check open issues per member before assigning; rotate chores |
| Jira shows wrong assignee | Display name mismatch ({{SLOT_5}} case) | Always resolve via `project-config.json` email, never Jira display name |
| Unassigned after "unassign" command | acli called with non-empty string instead of `""` | Use `-a ""` (empty string) not `-a "unassign"` |

### Authoritative References

- **Cognitive Load Theory (Sweller, 1988):** Simultaneous task overload degrades working memory capacity — the empirical basis for WIP limits per person. Sweller's intrinsic, extraneous, and germane load model explains why context switching between 3+ items causes quality degradation beyond what simple multi-tasking studies show
- **Tim Brown, IDEO — "Change by Design" (2009):** T-shaped people are "at the heart of the creative process"; the horizontal bar enables collaboration without requiring cross-domain expertise; use `skill_profile` breadth ratings to find collaborators, not just owners
- **Anderson, David J. — "Kanban" (2010):** WIP limits are the single most impactful change a team can make to improve flow; per-person WIP targets are the individual application of the same principle

---

## References

- [Tools](../../../references/tools.md) - MCP vs acli decision rules, acli assign command
- [HR Rules](../../../references/hr-rules.md) - HR3: MCP assignee silently fails — always use acli
