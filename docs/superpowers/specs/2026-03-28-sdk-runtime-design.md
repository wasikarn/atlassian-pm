# SDK Runtime Integration Design

**Date:** 2026-03-28
**Status:** Approved
**Scope:** Add Anthropic SDK + Claude Agent SDK layer to atlassian-pm plugin

---

## Problem

atlassian-pm hooks use pure Python stdlib (regex, JSON parsing) — no LLM reasoning available inside hook scripts. Three gaps:

- **a) Hooks are dumb:** intent detection uses regex → misses Thai variants and ambiguous phrasing; AC coverage check counts subtasks, not semantics
- **b) No AI enrichment pipeline:** ADF descriptions written from scratch by Claude session; no pre-QG polish step; impact analysis is heuristic only
- **c) No autonomous operation:** plugin is entirely reactive (user prompt → response); zero background monitoring of Jira board, sprint health, or PR events

---

## Constraints

- Hook scripts: stdlib only, timeout 5–10s — cannot install `anthropic` directly into hooks
- MCP server (atlassian-cache): already uses uv + external deps — pattern to follow
- Anthropic SDK requires `ANTHROPIC_API_KEY` (not claude.ai login)
- Claude Agent SDK risk: `UserPromptSubmit` hook → SDK spawn = recursive loop — must avoid
- Existing hooks must remain as fallback; SDK layer is additive, not replacement

---

## Architecture

```text
atlassian-pm/
├── sdk-runtime/                  ← NEW: dedicated uv project
│   ├── pyproject.toml            (anthropic>=0.40, httpx; claude_agent_sdk — verify pkg name Phase 1)
│   ├── ai_hooks/                 ← a) LLM-powered async hook scripts
│   │   ├── intent_detect.py      replace regex in pre_prompt_skill_redirect
│   │   ├── ac_coverage.py        semantic AC↔subtask alignment
│   │   └── path_quality.py       rate Explore agent result quality
│   ├── ai_scripts/               ← b) standalone enrichment scripts
│   │   ├── enrich_description.py rough text → structured ADF JSON
│   │   ├── suggest_subtasks.py   story_key → subtask breakdown + AC mapping
│   │   ├── impact_suggest.py     enhanced impact_suggester.py + LLM reasoning
│   │   └── pre_qg_polish.py      ADF draft → fix weak sections before QG check
│   ├── monitor/                  ← c) autonomous Agent SDK process
│   │   ├── board_monitor.py      main loop, 5-min poll cycle
│   │   ├── handlers/
│   │   │   ├── issue_changed.py  c1: field change → analyze → jira_add_comment
│   │   │   ├── sprint_health.py  c2: WIP > limit / sprint < 3 days → iMessage alert
│   │   │   └── pr_sync.py        c3/c4: PR merged → Jira transition + comment
│   │   └── run.sh                launchd / CronCreate entry point
│   └── logs/                     monitor crash logs (gitignored)
├── hooks/plugin/                 ← unchanged (stdlib only, remain as fallback)
├── hooks.json                    ← add async hooks pointing to sdk-runtime/ai_hooks/
└── mcp-servers/atlassian-cache/  ← unchanged
```

---

## Component Details

### a) AI Hooks

Integrated into `hooks.json` as `async: true` entries. The existing sync hook runs first (instant, stdlib); the async SDK hook fires in background and injects additional context on the next turn.

| Existing hook | Problem | SDK replacement |
|---|---|---|
| `pre_prompt_skill_redirect.py` | regex misses Thai variants | `intent_detect.py` — LLM classify intent, 1-shot, ≤3s |
| `post_hr9_alignment_suggest.py` | count-based only | `ac_coverage.py` — embed AC + subtask text, cosine similarity |
| `post_explore_fallback_suggest.py` | pattern match only | `path_quality.py` — LLM rate path specificity, suggest better queries |

Hook event additions in `hooks.json`:

```json
{
  "matcher": "Skill",
  "hooks": [{
    "type": "command",
    "command": "cd ${CLAUDE_PLUGIN_ROOT}/sdk-runtime && uv run ai_hooks/intent_detect.py",
    "async": true
  }]
}
```

### b) AI Scripts

Called from skill phases via Bash tool:

```bash
cd sdk-runtime && uv run ai_scripts/enrich_description.py \
  --text "rough description" --type story
```

Output: ADF JSON to stdout. Claude uses output directly in skill flow.
Failure contract: exit 1 + empty stdout → Claude falls back to writing ADF manually (graceful degrade).

Scripts are stateless — no session state dependency, safe to call any time.

### c) Autonomous Monitor

Uses `claude_agent_sdk` for multi-step reasoning loops. Runs as a **separate background process** — completely isolated from Claude Code session (no shared stdin/stdout).

**Startup:** `launchd` plist (macOS) or `CronCreate` hook.

**Poll cycle:** 5 minutes. Each cycle:

1. Fetch Jira board snapshot via REST
2. Diff against last snapshot (stored in `~/.claude/plugins/data/atlassian-pm-atlassian-pm/monitor-state.json`)
3. Dispatch changed items to handlers

**Handlers:**

- `issue_changed.py` — detect meaningful field changes (status, assignee, description); spawn Agent SDK agent to analyze impact; post Jira comment via REST
- `sprint_health.py` — check WIP columns against `board.columns[*].wip_max`; check sprint end date; send iMessage alert via plugin if threshold exceeded
- `pr_sync.py` — watch `hooks-logs/` for `post_pr_sync` events written by existing `post_pr_sync.py` hook; call Jira transition API; add PR link comment

**Isolation guarantee:** Monitor never calls Claude Code hooks or reads Claude session state. It uses REST API + Agent SDK only.

---

## API Key Management

```text
~/.claude/plugins/data/atlassian-pm-atlassian-pm/sdk-runtime.env
```

Contents:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

- Gitignored (in plugin data dir, not repo)
- Loaded by all sdk-runtime scripts at startup
- Setup step added to `/atlassian-pm:doctor` prerequisite check
- If missing: SDK scripts exit 0 with warning log, Claude session unaffected

---

## Error Handling

| Scenario | Behavior |
|---|---|
| API key missing | exit 0, log `SDK_KEY_MISSING`, session unaffected |
| SDK call timeout (>5s) | async hooks: no impact; scripts: exit 1 → fallback |
| Monitor crash | launchd restart (max 3/hour); error in `sdk-runtime/logs/` |
| Jira API rate limit | exponential backoff, max 3 retries, then skip cycle |
| atlassian-pm upgrade | sdk-runtime venv is separate → no conflict |
| Claude Code not running | monitor works independently via REST; no dependency on session |

---

## Implementation Phases

### Phase 1: SDK Runtime Foundation

- Create `sdk-runtime/pyproject.toml` with `anthropic` + verify claude_agent_sdk package name
- Create `sdk-runtime.env` loader utility
- Add setup step to `start_prerequisite_check.py`
- Smoke test: `cd sdk-runtime && uv run ai_scripts/enrich_description.py --help`

### Phase 2: AI Hooks (a)

- Implement `intent_detect.py` (replaces regex in skill redirect)
- Implement `ac_coverage.py` (semantic alignment check)
- Add async entries to `hooks.json`
- Test: Thai-language intent detection edge cases

### Phase 3: AI Scripts (b)

- Implement `enrich_description.py` (ADF enrichment)
- Implement `suggest_subtasks.py` (story → subtask breakdown)
- Implement `pre_qg_polish.py` (pre-QG ADF improvement)
- Update create-story skill to optionally call enrich step

### Phase 4: Autonomous Monitor (c)

- Implement `board_monitor.py` main loop
- Implement `issue_changed.py`, `sprint_health.py`, `pr_sync.py` handlers
- Create `run.sh` + launchd plist
- Add CronCreate-based alternative startup
- Integration test: end-to-end PR merge → Jira transition flow

---

## Out of Scope

- Replacing existing hooks with SDK versions (SDK is additive only)
- MCP tools backed by Anthropic SDK (Phase 2 of future work)
- Multi-tenant / team API key sharing
- Real-time webhooks (poll-based only in v1)
