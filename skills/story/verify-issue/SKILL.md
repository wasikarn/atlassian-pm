---
name: verify-issue
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Glob, Grep, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__mcp-atlassian__confluence_search, mcp__mcp-atlassian__confluence_get_page
description: |
  Verify and improve issue quality (ADF format, INVEST, language, hierarchy alignment) with a 6-phase workflow

  Checks: ADF render, panel structure, links, inline code, INVEST criteria, Given/When/Then, file paths, language consistency, hierarchy alignment (Epic↔Story↔Subtasks↔Docs)

  Supports: --with-subtasks (batch + alignment check), --fix (auto-fix + format migration)

  Triggers: "verify", "validate", "check quality", "improve", "migrate format", "QG score", "quality gate", "ตรวจสอบ issue"
  Use when: quality-checking ADF format, INVEST criteria, or hierarchy alignment of any issue before or after creation
  Do NOT use for: creating issues (use create-story/create-epic/create-task); deliberate scope or AC rewrites (use update-story/update-epic)
argument-hint: "[issue-key] [--with-subtasks] [--fix] [--dry-run]"
effort: medium
---

# /verify-issue

**Role:** Any
**Output:** Verification report (default) or Improved issues (with `--fix`)

## Phases

### 1. Fetch & Identify

- `MCP: jira_get_issue(issue_key: "ABC-XXX")`
- If `--with-subtasks` → `MCP: jira_search(jql: "parent = ABC-XXX", fields: "summary,status,assignee,issuetype")` (**⚠️ NEVER add ORDER BY to parent queries**)
- Identify type → Select checklist
- Build inventory: Key, Type, Current Format
- **Gate (--fix only):** User confirms scope

### 2. Technical Verification

| Check | Pass Criteria |
| --- | --- |
| ADF Format | Has `type: "doc"` |
| Panels | Correct `panelType` |
| Inline Code | Technical terms marked |
| Links | Parent/child exist |
| Fields | Required fields filled |

### 3. Quality Verification

| Dimension | Check |
| --- | --- |
| Format | ADF with panels? Inline code marks? |
| Language | Thai + transliterated loanwords? |
| Structure | Follows template? |
| Completeness | All sections present? |
| Clarity | ACs testable? Given/When/Then? |

Score: ⭐⭐⭐☆☆ (per dimension, 5-point scale)

**Type-specific checks:**

- **Story:** INVEST criteria (6 points), Narrative format, AC Given/When/Then
- **Sub-task:** Objective clear, File paths real (not generic), AC format correct
- **QA:** All Story ACs covered, Test scenarios clear, Priority assigned

### 4. Hierarchy Alignment (`--with-subtasks` only)

> **Principle:** Use only real data fetched from Jira/Confluence — never guess.
> If unsure which AC maps to which subtask → flag as "unclear mapping"

**Data fetching:**

```text
1. Story → jira_get_issue(story_key) — ACs, scope, services impacted   ← must come first (need story.parent key)
   Then in parallel (single message, 2 calls):
2a. Epic → jira_get_issue(story.parent) — scope, must-have list (skip if none)
2b. Confluence → confluence_search("ABC-XXX") — Tech Note (skip if none)
(Subtasks already in memory from Phase 1 — no I/O needed)
```

**Alignment Check (when --with-subtasks flag used):**

After QG scoring, run alignment verification:

```text
Agent(name: "alignment-checker"): {
  story_key: "[STORY-KEY]",
  mode: "--fix" if --fix flag provided else "read-only"
}
```

alignment-checker verifies: parent links (A1), SP consistency (A2), date range alignment (A3), AC coverage by subtasks (A4), scope drift (A5), bidirectional blocking links (A6).

**Alignment checks:**

| ID | Check | How to Verify | Pass Criteria |
| --- | --- | --- | --- |
| A1 | AC ↔ Subtask Coverage | Map each Story AC → subtask(s) that implement it | Every AC has ≥1 subtask covering it |
| A2 | Service Tag Match | Story "Services Impacted" → Subtask tags `[BE]`/`[FE-*]` | Every service has a subtask |
| A3 | Scope Consistency | Story in-scope items → Subtask objectives cover them | No scope gaps |
| A4 | Epic ↔ Story Fit | Story scope falls within Epic must-have/should-have | Story does not exceed Epic scope |
| A5 | Parent-Child Links | Subtask.parent = Story, Story.parent = Epic | Links are correct |
| A6 | Confluence Alignment | Tech Note content aligns with Story ACs (if exists) | No conflicts |

**Rules:**

- If no Epic (standalone Story) → skip A4
- If no Confluence page → skip A6, flag as info
- If mapping is unclear → flag "unclear mapping" (never guess)
- Report only what can be verified from actual data

### 5. Report

```text
## Verification: ABC-XXX

| Category | Score | Status |
|----------|-------|--------|
| Technical | 5/5 | ✅ Pass |
| Quality | 4/6 | ⚠️ Warning |
| Alignment | 5/6 | ⚠️ Warning |  ← (--with-subtasks only)
| **Overall** | 14/17 | ⚠️ |

Issues:
1. ⚠️ AC3 missing "Then"
2. ❌ Language mixed

Alignment Issues (--with-subtasks):
1. ⚠️ AC3 has no subtask covering it
2. ⚠️ Story specifies [FE-Web] but no subtask has [FE-Web] tag

→ /verify-issue ABC-XXX --fix
```

### 6. Fix (--fix flag only)

If `--fix` is present → apply all fixes found in Phases 2-4:

1. **Load Templates** — Fetch template for the issue type from `shared-references/`
2. **Generate** — Preserve original intent, apply template + ADF + Thai + inline code → `{{artifacts_dir}}/tp-xxx-fixed.json`
3. **Gate:** User reviews and approves

   **ADF Surgery (if auto-fixable structural issues found)**

   If Phases 2-3 inline checks found structural ADF issues AND classified them as auto-fixable:

   > **AUTO** — Invoke adf-surgeon before writing. Surgeon fixes structural issues only. Calling skill retains write responsibility.

   ```text
   Agent(name: "adf-surgeon"):
     file_path: {{artifacts_dir}}/[issue_key].json
     issues: [list of auto-fixable structural issues from Phases 2-3 checks]
   ```

   After adf-surgeon returns:

   - Review changelog to confirm only structural fixes were applied (no content changes)
   - Proceed to acli write with the repaired file
   - HR6: `cache_invalidate(issue_key)` after write (as normal)

4. **Apply** — `acli jira workitem edit --from-json {{artifacts_dir}}/tp-xxx-fixed.json --yes`
5. **Cleanup** — `rm {{artifacts_dir}}/tp-*-fixed.json`

```text
## Fix Complete
Updated: ABC-XXX, ABC-YYY, ABC-ZZZ
Quality: wiki → ADF, EN → Thai
```

---

## Batch Mode

```text
/verify-issue ABC-XXX --with-subtasks
/verify-issue ABC-XXX --with-subtasks --fix
```

| Key | Technical | Quality | Alignment | Overall |
| --- | --- | --- | --- | --- |
| ABC-XXX (Story) | 5/5 ✅ | 4/6 ⚠️ | 5/6 ⚠️ | ⚠️ |
| ABC-YYY [BE] | 5/5 ✅ | 6/6 ✅ | — | ✅ |
| ABC-ZZZ [FE-Web] | 5/5 ✅ | 5/6 ⚠️ | — | ⚠️ |

---

## Common Scenarios

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario, integration workflows, and a full example run.

---

## Examples

### ✅ Good

```text
/verify-issue {{PROJECT_KEY}}-123                            # quick quality check on a story — reports ADF, INVEST, language issues
/verify-issue {{PROJECT_KEY}}-123 --with-subtasks            # full hierarchy check — includes A1-A6 alignment checks across story + all subtasks
/verify-issue {{PROJECT_KEY}}-123 --with-subtasks --fix      # review alignment report first, then apply all auto-fixes in one pass
/verify-issue {{PROJECT_KEY}}-456 --fix                      # targeted fix on a single subtask with known ADF/language issues
```

### ❌ Bad

```text
/verify-issue                                    # no issue key → Phase 1 cannot fetch anything; skill cannot proceed
/verify-issue {{PROJECT_KEY}}-123                            # story has subtasks but --with-subtasks omitted → A1-A6 alignment checks never run, gaps missed
/verify-issue {{PROJECT_KEY}}-234 --fix                      # using --fix without first reading the report — changes applied without understanding what is being altered
/verify-issue {{PROJECT_KEY}}-10                             # passing an Epic key when you meant the child Story — Epic-level INVEST and AC checks don't apply
```

**Common mistakes:**

- Omitting `--with-subtasks` when the story has subtasks — alignment checks A1-A6 (AC coverage, service tag match, scope consistency) are completely skipped, leaving the most important issues undetected.
- Using `--fix` as the first invocation instead of running a read-only check first — always verify the report output before applying fixes so you understand exactly what will change.
- Manually crafting JQL with `ORDER BY` inside the `parent =` clause — this causes a JQL parse error (HR2); the skill already handles search correctly, do not override it.
- Running on a subtask key when the goal is to check the whole story hierarchy — pass the parent Story key with `--with-subtasks` instead.

---

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

---

## References

- [Verification Checklist](../../../references/verification-checklist.md)
- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Templates Index](../../../references/templates.md) - Load by issue type (epic, story, subtask, task)
- [Writing Style](../../../references/writing-style.md)
- [Scenarios](references/scenarios.md) - Command examples, integration workflows, and full example run
