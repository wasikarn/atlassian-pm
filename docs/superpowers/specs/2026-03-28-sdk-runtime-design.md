# SDK Runtime Integration Design

**Date:** 2026-03-28
**Status:** Approved
**Scope:** Add LLM-reasoning layer to atlassian-pm plugin using `claude -p` (non-interactive mode)

---

## Key Technical Finding

`claude -p` (non-interactive mode) uses **subscription OAuth from macOS Keychain** directly —
no `ANTHROPIC_API_KEY` required. Any machine with Claude Code installed and logged in can use this.

```bash
claude -p "analyze this ADF and suggest improvements" --output-format json
# ↑ uses same auth as Claude Code session — works out of the box
```

---

## Problem

atlassian-pm hooks use pure Python stdlib (regex, JSON parsing) — no LLM reasoning available inside hook scripts. Three gaps:

- **a) Hooks are dumb:** intent detection uses regex → misses Thai variants and ambiguous phrasing; AC coverage check counts subtasks, not semantics
- **b) No AI enrichment pipeline:** ADF descriptions written from scratch by Claude session; no pre-QG polish step; impact analysis is heuristic only
- **c) No autonomous operation:** plugin is entirely reactive (user prompt → response); zero background monitoring of Jira board, sprint health, or PR events

---

## Constraints

- Hook scripts: stdlib only, timeout 5–10s — async hooks have no timeout pressure
- Existing hooks must remain as fallback; AI layer is additive, not replacement
- No additional installation required — only `claude` CLI (already present in Claude Code)
- Recursive loop risk: `claude -p` inside a hook fires a new Claude session → must set `ATLASSIAN_PM_HOOK_DEPTH=1` env guard to prevent nesting

---

## Architecture

```text
atlassian-pm/
├── hooks/plugin/ai/              ← NEW: AI-powered async hooks (stdlib + subprocess)
│   ├── intent_detect.py          LLM classify intent → replaces regex in pre_prompt_skill_redirect
│   ├── ac_coverage.py            semantic AC↔subtask alignment check
│   └── path_quality.py           rate Explore agent result quality
├── scripts/ai/                   ← NEW: standalone enrichment scripts
│   ├── enrich_description.py     rough text → structured ADF JSON
│   ├── suggest_subtasks.py       story_key → subtask breakdown + AC mapping
│   ├── impact_suggest.py         enhanced impact_suggester.py + LLM reasoning
│   └── pre_qg_polish.py          ADF draft → fix weak sections before QG check
├── monitor/                      ← NEW: autonomous background monitor
│   ├── board_monitor.py          cron/launchd loop, detects Jira changes
│   ├── handlers/
│   │   ├── issue_changed.py      c1: field change → claude -p analyze → jira comment
│   │   ├── sprint_health.py      c2: WIP > limit / sprint < 3 days → iMessage alert
│   │   └── pr_sync.py            c3/c4: PR merged → Jira transition + comment
│   └── run.sh                    launchd / CronCreate entry point
├── hooks/plugin/                 ← unchanged (stdlib only, remain as fallback)
└── hooks.json                    ← add async: true hooks pointing to hooks/plugin/ai/
```

No new venv, no new packages. Pure Python stdlib + `subprocess` calling `claude -p`.

---

## Component Details

### a) AI Hooks (`hooks/plugin/ai/`)

Integrated into `hooks.json` as `async: true` entries alongside existing sync hooks.
Existing sync hook = instant fallback. AI hook = background enrichment, result injected next turn.

| Existing hook | Problem | AI replacement |
|---|---|---|
| `pre_prompt_skill_redirect.py` | regex misses Thai variants | `intent_detect.py` — `claude -p` classify intent |
| `post_hr9_alignment_suggest.py` | count-based only | `ac_coverage.py` — `claude -p` semantic AC↔subtask match |
| `post_explore_fallback_suggest.py` | pattern match only | `path_quality.py` — `claude -p` rate path specificity |

Example `hooks.json` addition:

```json
{
  "matcher": "Skill",
  "hooks": [{
    "type": "command",
    "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/ai/intent_detect.py",
    "async": true
  }]
}
```

Recursion guard in every AI hook:

```python
if os.environ.get("ATLASSIAN_PM_HOOK_DEPTH"):
    allow(); return
env = {**os.environ, "ATLASSIAN_PM_HOOK_DEPTH": "1"}
result = subprocess.run(["claude", "-p", prompt, "--output-format", "json"],
                        env=env, capture_output=True, timeout=15)
```

### b) AI Scripts (`scripts/ai/`)

Called from skill phases via Bash tool:

```bash
python3 scripts/ai/enrich_description.py --text "rough description" --type story
```

Each script:

1. Builds a focused prompt
2. Calls `claude -p "{prompt}" --output-format json`
3. Parses JSON stdout
4. Prints ADF JSON to stdout for Claude to consume

Failure contract: exit 1 + empty stdout → Claude falls back to writing ADF manually (graceful degrade).

### c) Autonomous Monitor (`monitor/`)

Background process. Uses `claude -p` for per-event analysis. Runs independently of Claude Code session.

**Startup:** `launchd` plist (macOS) — loaded once, restarts on crash.
**Alternative:** `CronCreate` hook for schedule-based polling.

**Poll cycle (5 min):**

1. Fetch Jira board snapshot via REST (`scripts/lib/jira_api.py` reused)
2. Diff against last snapshot (`monitor-state.json` in plugin data dir)
3. Dispatch changed items to handlers

**Handlers:**

- `issue_changed.py` — detect status/assignee/description changes; call `claude -p` to analyze impact; post Jira comment via REST
- `sprint_health.py` — check WIP vs `board.columns[*].wip_max`; check sprint end date; send iMessage alert via existing plugin if threshold exceeded
- `pr_sync.py` — tail `hooks-logs/*.jsonl` for `post_pr_sync` events; call Jira transition API; add PR link comment

**Isolation:** Monitor never writes to Claude Code session. One-way: monitor reads Jira → acts on Jira/iMessage.

---

## Recursion Guard (Critical)

All `claude -p` subprocess calls must set `ATLASSIAN_PM_HOOK_DEPTH=1` in env.
Hooks check this var on entry and exit immediately if set.
This prevents the spawned Claude session from firing AI hooks again.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| `claude` binary not found | exit 0, log `CLAUDE_NOT_FOUND`, session unaffected |
| `claude -p` timeout (>15s) | async hooks: no impact; scripts: exit 1 → fallback |
| Monitor crash | launchd restart (max 3/hour); error in `monitor/logs/` |
| Jira API rate limit | exponential backoff, max 3 retries, then skip cycle |
| Claude Code not running | monitor runs independently — `claude -p` works standalone |

---

## Implementation Phases

### Phase 1: Foundation + Recursion Guard

- Create `hooks/plugin/ai/__init__.py` + shared `claude_call(prompt)` utility
- Implement recursion guard (`ATLASSIAN_PM_HOOK_DEPTH` env check)
- Smoke test: `claude -p "hello" --output-format json` from hook subprocess
- Verify: no infinite loop when hook fires inside `claude -p` session

### Phase 2: AI Hooks (a)

- Implement `intent_detect.py` — classify Thai+English issue creation intent
- Implement `ac_coverage.py` — semantic AC↔subtask match scoring
- Implement `path_quality.py` — rate Explore agent path specificity
- Add `async: true` entries to `hooks.json`
- Test edge cases: ambiguous Thai prompts, partial AC coverage

### Phase 3: AI Scripts (b)

- Implement `enrich_description.py` — rough text → ADF JSON with all sections
- Implement `suggest_subtasks.py` — story AC list → subtask breakdown
- Implement `pre_qg_polish.py` — ADF draft → improve weak sections before QG
- Update create-story skill Phase 3 to optionally call `enrich_description.py`

### Phase 4: Autonomous Monitor (c)

- Implement `board_monitor.py` main loop + snapshot diffing
- Implement `issue_changed.py`, `sprint_health.py`, `pr_sync.py`
- Create `run.sh` + `com.atlassian-pm.monitor.plist` launchd config
- End-to-end test: PR merge → Jira auto-transition → iMessage alert

---

## Out of Scope

- Replacing existing hooks (AI hooks are additive only)
- Windows support (launchd is macOS-only; CronCreate alternative available)
- Streaming responses from `claude -p` (JSON mode only in v1)
- Real-time webhooks (poll-based only in v1)
