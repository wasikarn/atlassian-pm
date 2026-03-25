# Hooks — atlassian-pm

49 hooks enforce HR1-HR10 hard rules, prevent silent failures, and inject context automatically. Hooks are transparent — they either block with an explanation or silently enhance.

## Directory structure

```text
hooks/
├── hooks_lib.py      — shared I/O, logging, data extraction utilities
├── hooks_state.py    — session state manager (file-locked JSON)
├── config_loader.py  — project-config.json reader (cached per process)
├── hooks.json        — hook registry (wires hooks to Claude events)
├── plugin/
│   ├── guards/       — HR1-HR10 enforcement: block + track hard rule violations (17 hooks)
│   ├── quality/      — ADF structure, write quality, story size gates (4 hooks)
│   ├── cache/        — read optimization, dedup, field presets (6 hooks)
│   └── session/      — session management, compaction, token filtering, skill telemetry (15 hooks)
└── dev/              — developer workflow: DoR/DoD gates, WIP limit, PR sync (6 hooks)
```

## How hooks work

**PreToolUse** hooks fire before Claude calls a tool. They can block (exit 1 + message to stderr) or pass through silently (exit 0). **PostToolUse** hooks fire after a tool returns and inject guidance or tracking data. **Session hooks** manage state across compaction and subagent boundaries. All hooks receive tool input via the `TOOL_INPUT` environment variable as JSON.

## Hook categories

### Guard hooks (HR enforcement)

Enforce the hard rules defined in CLAUDE.md. Blocking hooks output a human-readable explanation so Claude can self-correct.

| Rule | Hook | Blocks |
|------|------|--------|
| HR1 | `pre_hr1_quality_gate.py` | Jira writes when Quality Gate score < 90% |
| HR2 | `pre_hr2_jql_order_guard.py` | JQL with `ORDER BY` + `parent =` / `parent in` (parser error) |
| HR3 | `pre_hr3_block_mcp_assignee.py` | Setting assignee via MCP (silently fails) — forces acli |
| HR4 | `pre_hr4_confluence_macro_guard.py` | HTML-escaped macros in Confluence — forces storage format script |
| HR5 | `pre_hr5_parent_verify_block.py` | Subtask creation without verified parent link |
| HR6 | `pre_hr6_stale_read_guard.py` | Reading cache after a recent write (stale data warning) |
| HR7 | `pre_hr7_sprint_id_guard.py` | Hardcoded sprint IDs — enforces dynamic lookup |
| HR8 | `pre_hr8_subtask_date_guard.py` | Subtask dates outside parent story's date range |
| HR9 | `post_hr9_alignment_suggest.py` | Suggests `/verify-issue --with-subtasks` when AC:subtask ratio is poor |
| HR10 | `pre_hr10_subtask_sprint_guard.py` | Setting sprint field on subtasks (API error + cascade failure) |
| DoR | `pre_dor_check.py` | Blocks moving to In Progress without story subtasks + AC + QG ≥ 90% |
| WIP | `pre_wip_limit_check.py` | Injects reminder to verify assignee WIP < team limit before moving to In Progress |

### Enhancement hooks

Silently improve tool calls without blocking.

| Hook | When | What it does |
|------|------|--------------|
| `pre_adf_structure_validate.py` | PreToolUse Bash | Validates ADF JSON structure before any write attempt |
| `pre_event_ac_check.py` | PreToolUse Bash | Checks Event issue types have ACs before proceeding |
| `pre_field_preset_guard.py` | jira_get_issue, jira_search | Injects recommended field presets when `fields` param is missing/minimal |
| `pre_cache_prefer.py` | jira_get_issue | Redirects to `cache_get_issue` when cached data is fresh |
| `pre_qmd_auto_search.py` | Glob, Grep | Auto-searches QMD knowledge base for relevant context before file searches |
| `pre_search_before_create.py` | jira_create_issue, jira_batch_create_issues | Checks for duplicate issues before creating |
| `pre_dod_check.py` | jira_transition_issue | Blocks transitioning to Done without DoD checklist confirmation |
| `post_filter_mcp_response.py` | jira_get_issue, jira_search | Strips noise fields from MCP response to save context tokens |
| `post_auto_parse_large_output.py` | search/sprint/get tools | Auto-parses large issue lists into structured summaries |
| `post_cache_suggest.py` | jira_get_issue, jira_search | Suggests cache tools for future reads |
| `post_pr_sync.py` | PostToolUse Bash | Detects `gh pr create` → injects context to transition linked {{PROJECT_KEY}} issue to "In Review" |

### Workflow hooks

Manage state, tracking, and cross-hook coordination.

| Hook | Event | Purpose |
|------|-------|---------|
| `start_prerequisite_check.py` | SessionStart | Checks acli + MCP prerequisites; warns if missing |
| `start_subagent_context.py` | SessionStart, SubagentStart | Injects HR rule reminders into subagent context |
| `start_cleanup_artifacts.py` | SessionStart | Removes stale task artifacts and trims unbounded JSONL files |
| `start_compact_reinject.py` | SessionStart (compact) | Re-injects critical context when session starts from a compacted state |
| `compact_pre_save.py` | PreCompact | Saves in-progress state before context compaction |
| `post_compact_reinject.py` | PostCompact | Re-injects HR rules + active state after compaction |
| `pre_skill_usage_log.py` | PreToolUse (Skill) | Logs every skill invocation for telemetry and usage measurement |
| `post_event_model_track.py` | PostToolUse (async) | Tracks Domain Model events from Epic descriptions |
| `stop_hr6_unflushed_check.py` | Stop | Warns on unflushed HR6 cache invalidations before session ends |
| `stop_hr5_pending_check.py` | Stop | Checks for subtasks with unverified parent links (HR5) before session ends |
| `pre_prompt_issue_prefetch.py` | UserPromptSubmit | Pre-fetches Jira issue when user mentions {{PROJECT_KEY}}-XXX in prompt |
| `post_hr5_parent_verify_remind.py` | jira_create_issue, jira_batch_create_issues | Reminds to verify parent link after creation |
| `post_hr5_parent_verify_clear.py` | (after parent verify) | Clears parent verify state after successful verification |
| `post_hr6_queue_invalidation.py` | any Jira write | Queues cache_invalidate after every Jira write |
| `post_hr6_queue_invalidation_acli.py` | acli Bash write | Same invalidation for writes via acli bash |
| `post_hr6_confirm_invalidation.py` | cache_invalidate | Confirms invalidation was completed |
| `post_hr7_sprint_lookup_track.py` | jira_get_sprints_from_board | Records that sprint was looked up dynamically |
| `post_vs_integrity_track.py` | jira_create_issue, jira_batch_create_issues | Tracks vertical slice label integrity after issue creation |
| `post_search_track.py` | jira_search | Tracks search patterns for QG learning |
| `post_subtask_alignment_suggest.py` | cache_sprint_issues, jira_get_sprint_issues | Suggests subtask alignment check after fetching sprint |
| `post_auto_verify_suggest.py` | (after creation) | Suggests running verify-issue after creating issues |
| `post_cache_checked_track.py` | (cache tools) | Tracks cache hit/miss stats |
| `post_explore_fallback_suggest.py` | PostToolUseFailure | Suggests alternatives when cache/search fails |

## Full hook table by event

### PreToolUse

| Script | Triggered by |
|--------|-------------|
| `pre_adf_structure_validate.py` | Bash |
| `pre_event_ac_check.py` | Bash |
| `pre_hr1_quality_gate.py` | Bash |
| `pre_hr2_jql_order_guard.py` | jira_search |
| `pre_hr3_block_mcp_assignee.py` | jira_update_issue |
| `pre_hr4_confluence_macro_guard.py` | confluence_update_page |
| `pre_hr5_parent_verify_block.py` | jira_create_issue, jira_batch_create_issues |
| `pre_hr6_stale_read_guard.py` | cache_get_issue |
| `pre_hr7_sprint_id_guard.py` | jira_create_issue, jira_batch_create_issues, jira_update_issue |
| `pre_hr10_subtask_sprint_guard.py` | jira_update_issue |
| `pre_field_preset_guard.py` | jira_get_issue, jira_search |
| `pre_cache_prefer.py` | jira_get_issue |
| `pre_qmd_auto_search.py` | Glob, Grep |
| `pre_search_before_create.py` | jira_create_issue, jira_batch_create_issues |
| `pre_dod_check.py` | jira_transition_issue |
| `pre_wip_limit_check.py` | jira_transition_issue |
| `pre_skill_usage_log.py` | Skill |
| `pre_prompt_issue_prefetch.py` | UserPromptSubmit |

### PostToolUse

| Script | Triggered by |
|--------|-------------|
| `post_filter_mcp_response.py` | jira_get_issue, jira_search |
| `post_event_model_track.py` | jira_create_issue (async) |
| `post_hr5_parent_verify_remind.py` | jira_create_issue, jira_batch_create_issues |
| `post_hr5_parent_verify_clear.py` | (after parent verify) |
| `post_vs_integrity_track.py` | jira_create_issue, jira_batch_create_issues |
| `post_hr6_queue_invalidation.py` | any Jira write |
| `post_hr6_queue_invalidation_acli.py` | acli Bash write |
| `post_hr6_confirm_invalidation.py` | cache_invalidate |
| `post_search_track.py` | jira_search |
| `post_hr7_sprint_lookup_track.py` | jira_get_sprints_from_board |
| `post_auto_parse_large_output.py` | search/sprint/get tools |
| `post_subtask_alignment_suggest.py` | cache_sprint_issues, jira_get_sprint_issues |
| `post_cache_suggest.py` | jira_get_issue, jira_search |
| `post_auto_verify_suggest.py` | (after creation) |
| `post_cache_checked_track.py` | (cache tools) |
| `post_explore_fallback_suggest.py` | PostToolUseFailure |

### Session

| Script | Event |
|--------|-------|
| `start_prerequisite_check.py` | SessionStart |
| `start_subagent_context.py` | SessionStart, SubagentStart |
| `start_cleanup_artifacts.py` | SessionStart |
| `start_compact_reinject.py` | SessionStart (compact) |
| `compact_pre_save.py` | PreCompact |
| `post_compact_reinject.py` | PostCompact |
| `stop_hr6_unflushed_check.py` | Stop |
| `stop_hr5_pending_check.py` | Stop |

## Utility files

| File | Purpose |
|------|---------|
| `config_loader.py` | Loads `project-config.json` + `project-config-team-detail.json` |
| `hooks_lib.py` | Shared utilities: read `TOOL_INPUT`, JSON parsing, HR state helpers |
| `hooks_state.py` | Persistent state store for cross-hook coordination (HR5 parent verify, HR6 queue, etc.) |
| `hooks.json` | Wire file: maps events + matchers to hook scripts |

## Debugging hooks

If a hook blocks unexpectedly:

1. Check `TOOL_INPUT` — hooks read tool arguments from this env var as JSON.
2. Run the script directly: `TOOL_INPUT='{"key":"value"}' python3 hooks/plugin/guards/NAME.py`
3. Inspect persisted state: read `hooks_state.py` or look for a state file in the hooks directory.
4. Check `hooks.json` to confirm the event + matcher is wired correctly.

## Adding a hook

1. Create `hooks/plugin/<subdir>/your_hook.py` (or `hooks/dev/` for dev workflow hooks). Read `TOOL_INPUT` via `hooks_lib.py`. Exit 1 with stderr message to block; exit 0 to pass through. Set `sys.path` to `parents[2]` (plugin subdirs) or `parents[1]` (dev) so shared libs resolve.
2. Add an entry to `hooks.json`:

```json
{
  "event": "PreToolUse",
  "matcher": "tool_name",
  "command": "python3 hooks/plugin/guards/your_hook.py"
}
```

1. Test by triggering the matched tool in a Claude Code session and confirming expected behavior.
