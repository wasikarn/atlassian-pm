# Update Workflow — Common Patterns

Shared reference for `update-story`, `update-subtask`, `update-task`, `update-epic`.
All 4 skills follow this 6-phase skeleton: Fetch → Identify Changes → Preserve Intent → Generate Update → Quality Gate → Apply Update.

## Standard Frontmatter Defaults

```yaml
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
argument-hint: "[issue-key] [changes]"
```

## Standard Phase 5 — Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send updates to Atlassian without QG ≥ 90%.

> [QG Scoring Rules](workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`

## Standard Phase 6 — Apply Update

> **🟢 AUTO** — If QG passed → apply automatically. No user interaction needed.

```bash
acli jira workitem edit --from-json {{artifacts_dir}}/tp-xxx-update.json --yes
```

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after apply.

## Standard Gate Phrases

Copy verbatim into the appropriate phases:

- **Phase 2 (identify changes):** `**⛔ GATE — DO NOT PROCEED** without user confirmation of changes.`
- **Phase 4 (generate update):** `**⛔ GATE — DO NOT APPLY** without user approval of all generated changes.`
- **Phase 1 (fetch state):** `**🟡 REVIEW** — Present current state to user. Proceed unless user objects.`

## Standard Preserve Intent Pattern

Phase 3 structure (specific bullets differ per issue type):

```
- ✅ [what is allowed]
- ✅ [what is allowed]
- ⚠️ Be careful: [scope-risk item]
- ❌ Do not [forbidden action] without informing the user
```

## Standard Boilerplate Lines

Add to every Jira update skill:

```markdown
> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed` as you work.
```

## What Differs Per Skill (stays in each SKILL.md)

| Area | Varies by |
|------|-----------|
| Role | PO / Technical Analyst / Developer / PM |
| Phase 1 fetch | subtasks, parent, child stories, Epic Doc |
| Phase 2 change types | AC / Format / Type / Scope |
| Phase 3 preserve bullets | Issue-type-specific rules |
| Phase 4 preview format | Narrative / comparison table / ADF JSON |
| Phase 6 post-apply | HR8, HR10, Epic Doc cascade |
| Context Object rows | Varies per schema |
| References footer | Template link per type |
