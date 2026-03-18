# HR Rules — Canonical Reference

Single source of truth for all Hard Rules.
Referenced by: `CLAUDE.md`, `skill-orchestration.md`, `workflow-patterns.md`

Hooks enforce **HR2–HR7, HR10** automatically (PreToolUse blocking).
HR8 has suggestion-only hook. HR9 has no hook — manual via `/verify-issue --with-subtasks`.

---

## HR1. Quality Gate ≥ 90% Before Atlassian Writes

**Constraint:** NEVER create or edit issues on Jira/Confluence before passing QG ≥ 90%.

**Why:** MCP `jira_create_issue` writes wiki markup directly to Jira, bypassing quality checks. Low-quality issues require manual cleanup and break downstream operations (subtask creation, planning, verify cascade).

**Enforcement:** `pre_hr1_quality_gate.py` (blocks acli writes below threshold)

**Flow:**

```text
Explore → ADF → Self-check (verification-checklist.md) → Score → QG ≥ 90% → Atlassian
```

- ✅ Generate ADF → score 92% → proceed to MCP create + acli edit
- ❌ Draft ADF → immediately `acli workitem create --from-json` → "will fix later"

---

## HR2. JQL `parent` — No ORDER BY

**Constraint:** NEVER add `ORDER BY` to JQL containing `parent =`, `parent in`, or `key in (...)`.

**Why:** Jira JQL parser rejects this combination — returns zero results with a parser error. Silent failure: Claude sees empty results and may assume no issues exist.

**Enforcement:** `pre_hr2_jql_order_guard.py` (blocks the tool call)

- ✅ `parent = BEP-123`
- ❌ `parent = BEP-123 ORDER BY created DESC`
- ✅ `project = BEP AND issuetype = Story ORDER BY created DESC` (no parent filter)

---

## HR3. MCP Assignee — Use acli Only

**Constraint:** NEVER use `jira_update_issue` to set assignee. Always use `acli jira workitem assign`.

**Why:** MCP `jira_update_issue` with `assignee` field silently returns success but does nothing. The assignment is silently dropped — no error, no indication.

**Enforcement:** `pre_hr3_block_mcp_assignee.py` (blocks MCP assignee updates)

- ✅ `acli jira workitem assign -k "BEP-123" -a "email" -y`
- ❌ `jira_update_issue(issue_key="BEP-123", additional_fields={"assignee": {"accountId": "..."}})`

---

## HR4. Confluence Macros — Use Script Only

**Constraint:** NEVER use MCP to update Confluence pages containing structured macros (ToC, Children, Code blocks).

**Why:** MCP `confluence_update_page` HTML-escapes `<ac:structured-macro>` tags → raw XML appears in page body, breaking macro rendering. The page looks corrupted to users.

**Enforcement:** `pre_hr4_confluence_macro_guard.py` (blocks MCP Confluence macro updates)

- ✅ `python atlassian-scripts/update_page_storage.py --page-id 123456 --file page.html`
- ❌ `confluence_update_page(page_id="123456", body="...<ac:structured-macro>...")` via MCP

---

## HR5. Subtask = Two-Step + Verify Parent

**Constraint:** Always use three-step subtask creation: (1) MCP create with parent, (2) verify parent set via `jira_get_issue`, (3) acli edit for ADF description.

**Why:** MCP `jira_create_issue` may silently ignore the `parent` field — creating an orphan subtask with no parent link. Orphans don't appear in story burndown and break sprint planning.

**Enforcement:** `pre_hr5_parent_verify_block.py` (blocks next subtask if prior unverified), `post_hr5_parent_verify_remind.py` (injects reminder after create), `post_hr5_parent_verify_clear.py` (auto-clears after confirmed)

- ✅ `jira_create_issue(parent={"key":"BEP-123"})` → `jira_get_issue(fields="parent")` → confirm → `acli edit --from-json`
- ❌ Create 5 subtasks back-to-back without verifying parent links

---

## HR6. Cache Invalidate After Every Write

**Constraint:** After any MCP write to Jira → immediately run `cache_invalidate(issue_key)`.

**Why:** The jira-cache-server caches issue data in SQLite. Stale cache causes wrong data in `/verify-issue`, cascade updates, and sprint planning. Reading from stale cache after a write is silent data corruption.

**Enforcement:** `post_hr6_queue_invalidation.py` (queues keys after MCP writes), `pre_hr6_stale_read_guard.py` (blocks cache reads for pending keys), `stop_hr6_unflushed_check.py` (blocks session exit if pending)

- ✅ `jira_update_issue(...)` → `cache_invalidate(issue_key="BEP-123", force_refresh=true)`
- ❌ Update issue → immediately read from `cache_get_issue` without invalidating

---

## HR7. Sprint ID — Always Lookup, Never Hardcode

**Constraint:** NEVER hardcode sprint IDs (e.g., `{{SPRINT_FIELD}}: 607`). Always call `jira_get_sprints_from_board(board_id, state="active")` first.

**Why:** Sprint IDs are instance-specific and change every sprint. Hardcoded IDs silently land tickets in a wrong (often past) sprint with no error.

**Enforcement:** `pre_hr7_sprint_id_guard.py` (blocks sprint field if no lookup in session), `post_hr7_sprint_lookup_track.py` (tracks that lookup was done)

- ✅ `jira_get_sprints_from_board(board_id=2, state="active")` → use returned id
- ❌ `jira_update_issue(additional_fields={"{{SPRINT_FIELD}}": {"id": 607}})`

---

## HR8. Subtask Size + Dates Must Align with Parent

**Constraint:** Subtask start/end dates must fall within parent's date range. Sum of subtask story points should be reasonable relative to parent estimate.

**Why:** Misaligned dates break capacity tracking and burndown charts. Subtask points summing to 3× parent points indicates planning error that confuses sprint velocity.

**Enforcement:** `post_subtask_alignment_suggest.py` (suggestion only — no block)

> **Enforcement gap:** This rule has no blocking hook. Requires manual check or `/verify-issue --with-subtasks` (A3-A4 checks).

- ✅ Parent due 2026-03-31 → subtasks due ≤ 2026-03-31
- ❌ Parent 3 SP, subtasks total 15 SP

---

## HR9. Related Ticket Descriptions Must Align

**Constraint:** Story ACs must be covered by subtask objectives. Epic scope must be reflected in child Stories. Linked tickets must reference each other.

**Why:** Misaligned descriptions create ambiguity — a Story says "user can X" but no subtask implements X. Leads to QA finding gaps after development.

**Enforcement:** None (no hook)

> **Enforcement gap:** This rule has no hook enforcement. Run `/verify-issue --with-subtasks` (A1-A6 alignment checks) manually after creating subtasks.

- ✅ Story has AC1: Login with email → subtask "[BE] Implement email auth endpoint"
- ❌ Story has 5 ACs → only 2 subtasks with vague objectives

---

## HR10. Never Set Sprint on Subtasks

**Constraint:** NEVER set `{{SPRINT_FIELD}}` (sprint field) on subtasks. Subtasks inherit sprint from their parent Story.

**Why:** Setting sprint on a subtask causes a Jira API error and can cascade-fail parallel tool calls in the same batch. Even when it "succeeds", it has no effect — sprint is always inherited.

**Enforcement:** `pre_hr10_subtask_sprint_guard.py` (blocks update if issue is detected as subtask)

- ✅ Set sprint on the parent Story → subtasks inherit automatically
- ❌ `jira_update_issue(issue_key="BEP-456", additional_fields={"{{SPRINT_FIELD}}": {"id": 607}})` where BEP-456 is a subtask
