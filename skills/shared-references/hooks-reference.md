# Hooks Reference

Complete index of all 37 hooks in `.claude/hooks/`. Organized by category.

**Shared modules** (not hooks): `hooks_lib.py` (utilities), `hooks_state.py` (session state)

**Action types:** Block = exits 2 (tool call aborted) · Warn = exits 0 with message · Track = state update only · Suggest = injects additionalContext

---

## Session Lifecycle

| File | Event | Matcher | Action | Purpose |
|------|-------|---------|--------|---------|
| `start_prerequisite_check.py` | SessionStart | _(all)_ | Warn | Check acli, qmd, cache DB, state dir — advisory only, never blocks |
| `start_compact_reinject.py` | SessionStart | `compact` | Inject | Re-inject HR reminders + pending state after compaction |
| `compact_pre_save.py` | PreCompact | _(all)_ | Save | Snapshot session state to file before compaction (not injected into context) |

---

## HR Rule Enforcement — Blocking

| File | Event | Matcher | Action | HR | Purpose |
|------|-------|---------|--------|----|---------|
| `pre_hr1_quality_gate.py` | PreToolUse | `Bash` (acli) | Block | HR1 | Block acli writes with QG score < 90% |
| `pre_hr2_jql_order_guard.py` | PreToolUse | `jira_search` | Block | HR2 | Block JQL with `parent =` + `ORDER BY` |
| `pre_hr3_block_mcp_assignee.py` | PreToolUse | `jira_update_issue` | Block | HR3 | Block MCP `assignee` field (silently ignored by API) |
| `pre_hr4_confluence_macro_guard.py` | PreToolUse | `confluence_update_page` | Block | HR4 | Block MCP update when body contains structured macros |
| `pre_hr5_parent_verify_block.py` | PreToolUse | `jira_create_issue` / `batch` / `update` | Block | HR5 | Block next subtask create if prior parent unverified |
| `pre_hr6_stale_read_guard.py` | PreToolUse | `cache_get_issue` | Block | HR6 | Block cache read for keys pending invalidation |
| `pre_hr7_sprint_id_guard.py` | PreToolUse | `jira_update_issue` | Block | HR7 | Block sprint field update without prior `get_sprints` call |
| `pre_hr10_subtask_sprint_guard.py` | PreToolUse | `jira_update_issue` | Block | HR10 | Block sprint field on subtask issue types |
| `stop_hr6_unflushed_check.py` | Stop | _(all)_ | Block | HR6 | Block session exit if cache invalidation queue not flushed |

---

## HR Rule State Tracking

| File | Event | Matcher | Action | HR | Purpose |
|------|-------|---------|--------|----|---------|
| `post_hr5_parent_verify_remind.py` | PostToolUse | `jira_create_issue` / `batch` | Suggest | HR5 | Inject reminder to verify parent field after subtask create |
| `post_hr5_parent_verify_clear.py` | PostToolUse | `jira_get_issue` | Track | HR5 | Clear pending-verify flag when parent confirmed |
| `post_hr6_queue_invalidation.py` | PostToolUse | `jira_create/update/transition` | Track | HR6 | Queue issue key for required cache invalidation |
| `post_hr6_queue_invalidation_acli.py` | PostToolUse | `Bash` (acli writes) | Track | HR6 | Queue issue key for invalidation via acli path |
| `post_hr6_confirm_invalidation.py` | PostToolUse / PostToolUseFailure | `cache_invalidate` | Track | HR6 | Clear pending-invalidate flag when invalidation confirmed |
| `post_hr7_sprint_lookup_track.py` | PostToolUse | `jira_get_sprints_from_board` | Track | HR7 | Mark sprint lookup done for session (enables HR7 gate) |

---

## Quality & Validation

| File | Event | Matcher | Action | Purpose |
|------|-------|---------|--------|---------|
| `pre_adf_structure_validate.py` | PreToolUse | `Bash` (acli) | Warn | Validate ADF JSON structure before acli write (schema check) |
| `pre_event_ac_check.py` | PreToolUse | `Bash` (acli) | Warn | Check event names in Story ACs against Domain Model catalog |
| `post_vs_integrity_track.py` | PostToolUse | `jira_get_issue` / `jira_create_issue` | Track | Track Story AC titles and subtask coverage; alert on gaps |
| `post_event_model_track.py` | PostToolUse | `jira_get_issue` | Track | Extract Domain Events from Epic descriptions for AC consistency |
| `post_subtask_alignment_suggest.py` | PostToolUse | `cache_sprint_issues` / `get_sprint_issues` | Suggest | Warn when subtask dates/SP don't align with parent (HR8) |

---

## Cache Management

| File | Event | Matcher | Action | Purpose |
|------|-------|---------|--------|---------|
| `pre_cache_prefer.py` | PreToolUse | `jira_get_issue` | Suggest | Redirect to `cache_get_issue` instead of direct MCP call |
| `pre_field_preset_guard.py` | PreToolUse | `jira_get_issue` / `jira_search` | Block | Block calls missing `fields` param (and `limit` for search) |
| `post_cache_suggest.py` | PostToolUse | `jira_get_issue` / `jira_search` | Suggest | After direct MCP read, suggest cache warm-up; mark issue as cache-checked |
| `post_cache_checked_track.py` | PostToolUse | `cache_get_issue` | Track | Record that cache was used for this issue key |

---

## Search & Dedup

| File | Event | Matcher | Action | Purpose |
|------|-------|---------|--------|---------|
| `pre_search_before_create.py` | PreToolUse | `jira_create_issue` / `batch` | Warn | Warn if no `jira_search` done yet in session (dedup check) |
| `post_search_track.py` | PostToolUse | `jira_search` | Track | Record that a search was done this session (used by dedup guard) |
| `post_search_before_create.py` | PostToolUse | `jira_search` / sprint/project/board gets | Track+Suggest | Dedup reminder post-create; integrates with VS integrity tracking |

---

## Workflow Suggestions

| File | Event | Matcher | Action | Purpose |
|------|-------|---------|--------|---------|
| `post_workflow_chain_suggest.py` | PostToolUse | `jira_create_issue` | Suggest | After issue create, suggest next workflow step (e.g. create subtasks, verify) |
| `post_auto_verify_suggest.py` | PostToolUse | `Bash` (acli) | Suggest | After acli write, suggest running `/verify-issue` |
| `post_explore_fallback_suggest.py` | PostToolUse | `Task` | Suggest | When Explore agent returns generic paths, suggest hybrid mode |

---

## QMD Integration

| File | Event | Matcher | Action | Purpose |
|------|-------|---------|--------|---------|
| `pre_qmd_auto_search.py` | PreToolUse | `Glob` / `Grep` | Suggest | Auto-inject QMD search results before file pattern search |
| `post_qmd_usage_track.py` | PostToolUse | `mcp__qmd__*` | Track | Track QMD usage for session analytics |

---

## Transition & Output

| File | Event | Matcher | Action | Purpose |
|------|-------|---------|--------|---------|
| `pre_transition_guard.py` | PreToolUse | `jira_transition_issue` | Warn | Inject context reminding Claude to verify transition + run cache invalidate |
| `post_auto_parse_large_output.py` | PostToolUse | `Bash` | Suggest | When MCP output exceeds token limit, auto-run parse script and inject summary |

---

## Shared Modules

| File | Purpose |
|------|---------|
| `hooks_lib.py` | Common utilities: `parse_stdin`, `inject_context`, `log_event`, regex patterns |
| `hooks_state.py` | Session state (SQLite): HR5/HR6/HR7 flags, search done, VS coverage, event model |
