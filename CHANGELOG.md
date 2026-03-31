# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6.11] - 2026-03-31

### Fixed

- `SessionStart` hook now auto-clears cache dir `.mcp.json` files on every startup — prevents ghost `atlassian-cache: ${CLAUDE_PLUGIN_ROOT}/... ✗ Failed to connect` entry for all users after `claude plugin update`. No manual action required.

## [2.6.10] - 2026-03-31

### Fixed

- `bump-version.sh`: cache dir `.mcp.json` clearing now polls up to 10s for async download to complete, then clears all cached versions (not just the new one) — prevents ghost `atlassian-cache: ${CLAUDE_PLUGIN_ROOT}/... ✗ Failed to connect` entry after every release.

## [2.6.9] - 2026-03-31

### Fixed

- Duplicate `atlassian-cache: ${CLAUDE_PLUGIN_ROOT}/... ✗ Failed to connect` entry — Claude Code loads `.mcp.json` from **both** marketplace dir (with variable expansion + `plugin:` prefix) and cache dir (no expansion, no prefix). Fixed by clearing cache dir `.mcp.json` after each release in `bump-version.sh`.

## [2.6.8] - 2026-03-31

### Fixed

- `atlassian-cache` MCP server "Failed to connect" — root cause: Claude Code reads `.mcp.json` from the **marketplace dir** only (not cache). Only marketplace-loaded servers get the `plugin:` namespace and `${CLAUDE_PLUGIN_ROOT}` expansion. `bump-version.sh` was incorrectly clearing the marketplace `.mcp.json` after every release, breaking the server for all users.
- `bump-version.sh`: removed marketplace `.mcp.json` clearing step. Cache `.mcp.json` files remain empty to avoid duplicate registration.

## [2.6.7] - 2026-03-31

### Fixed

- `atlassian-cache` MCP registration — restored to official `.mcp.json` plugin pattern using `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` variables (confirmed supported per Claude Code plugin docs). Previous workaround (`setup.sh` writing to `~/.claude.json`) was non-standard and broke for users who installed the plugin without running setup manually.
- Added `mcp-servers/atlassian-cache/run.sh` — portable `uv` locator that checks `PATH` first, then common per-user install locations (`~/.local/bin`, `~/.cargo/bin`, `/opt/homebrew/bin`), fixing "uv not found" in MCP server subprocess environments.
- Removed `~/.claude.json` manipulation from `setup.sh` — venv installation is still performed by setup; MCP registration is now automatic via `.mcp.json`.

## [2.6.6] - 2026-03-31

### Fixed

- `atlassian-cache` MCP server duplicate warning ("skipped — same command/URL") — root cause: Claude Code loads `.mcp.json` from both marketplace and cache dirs. `bump-version.sh` now clears the marketplace `.mcp.json` after each release so only the cache dir copy remains active.

## [2.6.5] - 2026-03-31

### Added

- ci: add GitHub Actions QA workflow (9 gates: shellcheck, markdownlint, plugin.json, SKILL.md frontmatter, agent frontmatter, hooks.json references, Python pytest, CHANGELOG version, required files)

### Fixed

- fix(hooks): run.sh fallback now uses silent exit 0 instead of invalid JSON output

## [Unreleased]

## [2.6.2] - 2026-03-31

### Fixed

- `.mcp.json` — use `cwd: "${CLAUDE_PLUGIN_ROOT}"` with relative paths for `args` so the server resolves correctly in both plugin context (CLAUDE_PLUGIN_ROOT expanded) and project context (cwd defaults to project root). Also add explicit `PATH` to env so `uv` is found regardless of how Claude Code spawns the subprocess.

## [2.6.1] - 2026-03-31

### Fixed

- `.mcp.json` — add `UV_PROJECT_ENVIRONMENT=${CLAUDE_PLUGIN_DATA}/venv` so the atlassian-cache MCP server uses the pre-installed venv from `/atlassian-pm:setup` instead of creating a new one on each restart. Fixes "Failed to connect" on plugin install/update.

## [1.8.0] - 2026-03-25

### Added

- `start-ticket` skill — DLC workflow shortcut: reads ticket AC + transitions to In Progress; tiered status guard (warn for In Progress/Reopened, block for Done/Closed); handles hard WIP gate via `CLAUDE_WIP_CONFIRMED` env var
- `ship-to-qa` skill — DLC workflow shortcut: auto-detects PR via `gh pr view`, constructs CF Pages preview URLs from `environments.preview` config (branch slug, 28-char truncation), posts Jira comment (PR + preview + optional staging BE), transitions to Ready for QA with WIP gate enforcement
- `environments.preview` in `project-config.json.template` — CF Pages project names for branch preview URL construction (`admin`, `web` keys)
- "Ready for QA" added to QA column `statuses` in `project-config.json.template` — ensures `pre_wip_limit_check` WIP gate fires on ship-to-qa transitions

## [1.7.0] - 2026-03-25

### Added

- `flow-check` skill — board health snapshot + Scrumban replenishment (WSJF-approximated pull queue)
- Hard WIP gate hook (`plugin/guards/pre_wip_limit_check.py`) — blocks `jira_transition_issue` until Claude confirms WIP count below limit (DoR/DoD pattern with `CLAUDE_WIP_CONFIRMED=<key>:<col>` env var)
- Auto-trigger hook (`plugin/session/post_done_flow_check.py`) — injects `/flow-check --replenish` imperative on Done transitions
- `workflow` + `board.columns` config in `project-config.json.template` — Scrumban config schema with WIP limits per column and `kanban_board_id`

### Removed

- `hooks/dev/pre_wip_limit_check.py` (soft warn) — replaced by hard gate in `plugin/guards/`

### Fixed

- `scripts/setup.sh` — removed `--extra embeddings` flag (extra was removed from `mcp-servers/atlassian-cache/pyproject.toml`)

### Breaking

- WIP enforcement is now a hard block (was soft warn). Claude must confirm WIP count before transitioning. Set `CLAUDE_WIP_CONFIRMED=<key>:<column>` after verifying count is below limit.

## [1.6.2] - 2026-03-23

### Changed

- **Domain Expert Notes quality audit — all 32 skills** — systematic audit across PM (15 skills), Engineer (11 skills), QA (3 skills), Setup (2 skills), and Utilities (5 skills); 4 Adequate Engineer skills and 15 PM/remaining skills elevated to Strong with specialist-level framework citations, primary author attributions, and causal reasoning
- **Citation integrity fixes** — removed 4 fabricated/unverifiable references: "University of Waterloo Atlassian JQL Best Practices" (search-issues), "32% of agile teams link OKRs" (create-epic), "Infisical Local Development Secrets Guide" (setup), "BetterStack Health Check Guide" (doctor); replaced with NIST SP 800-57 Part 1 Rev 5, Beyer et al. SRE Book Ch.17, 12-Factor App (Wiggins 2011), and real Atlassian Developer Docs
- **Framework attribution completeness** — added primary author + year + venue for: JTBD (Christensen 1997 vs Ulwick ODI 2005 as distinct frameworks), T-shaped skills (Guest 1991 + Tim Brown/IDEO 2010), SMART Goals (Doran 1981 Management Review), Goodhart's Law (1975), 4Ls (Diana Larsen), Walk-the-Board (Scrum.org / Sutherland 2014), Docs as Code (Anne Gentle 2017), CLM (AIIM/Gartner), Keep a Changelog (Olivier Lacan)
- **Numeric threshold disambiguation** — plan-release: 3 distinct buffer concepts separated (10% velocity buffer / 10-15% buffer sprint / 20% carry-over pre-allocation); spec-to-stories: cosine similarity tiers clarified (>0.8 auto-flag vs 0.7–0.8 manual review, <0.7 distinct)
- **P1 escalation consistency** — bug-triage: all 3 triggers (PII/auth bypass, payment failure, database corruption) now share base actions (freeze deployments + Tech Lead escalation) with path-specific follow-on steps
- **Empirical observation labeling** — atlassian-scripts: `~15% MCP parent-drop` statistic marked as "observed empirically — not a documented Atlassian behavior"
- **qa-full Step 0 Guard** — idempotency check added before create-testplan invocation: detects existing `[QA]` sub-tasks and routes to 3 options (A: execute existing / B: update+execute / C: create new); prevents duplicate test plans per sprint
- **README counts corrected** — 31→32 skills, 18→20 agents, 9→10 commands; `test-case-runner` and `bug-evidence-writer` added to agents architecture tree

## [1.6.1] - 2026-03-23

### Added

- **9 orchestration Commands** — end-to-end workflow chains in `.claude/commands/`: `story-full`, `epic-full`, `blueprint-full`, `bug-full`, `story-analyze-full`, `sprint-plan-full`, `sprint-close-full`, `release-full`, `tech-debt-full`; each chains existing skills with confirmation gates
- **Parallel dispatch annotation** — `> **🟢 PARALLEL**` and `> **🟢 AUTO + PARALLEL**` blockquote convention in skill/agent phases marks independent tool calls for single-message dispatch; documented in CLAUDE.md Efficiency section and applied across 11 skill/agent files
- **HR5 Stop hook** (`stop_hr5_pending_check.py`) — session-end guard that flags any subtask creation where parent verification was not confirmed; prevents orphaned subtasks from being silently abandoned
- **Skill usage telemetry hook** (`pre_skill_usage_log.py`) — PreToolUse:Skill hook logs skill invocations with timestamp, model, and session ID for usage analysis
- **Model tracking hook** (`post_event_model_track.py`) — PostToolUse async hook tracks domain model events per session
- **Session artifact cleanup hook** (`start_cleanup_artifacts.py`) — SessionStart hook removes stale task artifacts beyond configurable TTL
- **`<important if>` conditional tags on HR1–HR10** in CLAUDE.md — context-sensitive rule loading; only the relevant rules surface in context based on the current operation
- **Dynamic config injection** — 4 skills now read `project_key` and `board_id` directly from `.claude/project-config.json` at runtime instead of hardcoded placeholders
- **Skill trigger descriptions (P3 pattern)** — all 31 skills now have `Triggers:`, `Use when:`, `Do NOT use for:` in their `description:` block with Thai trigger phrases for bilingual discovery
- **Goal-oriented phase headers (P9 pattern)** — create-story, analyze-story, blueprint, close-sprint, plan-sprint phases now open with `**Goal:**`, `**Required inputs:**`, `**Constraints:**`, `**Output:**`

### Changed

- **README restructured** — 3 distinct sections (Commands → Skills → Agents) ordered by real usage flow; Commands section added with fast-path table; Agents section clarified as internal subagents
- **Workflow diagram updated** — added Commands fast-path node, `spec-to-stories` branch, `/bug-triage → /create-testplan` split from `/create-task`, and `close-sprint → retrospective-analyst` in sprint subgraph
- **`references/` count corrected** — 19 → 24 documents; missing entries (`hr-rules.md`, `hooks-reference.md`, `subtask-design-patterns.md`, `update-workflow.md`) added to skills/README.md shared references table
- **Hook count corrected** — 43 → 46 hooks; 5 previously undocumented session hooks added to hooks/README.md workflow and event tables

### Fixed

- **Hooks library refactor** — replaced inline duplication across 6 hook files with `hooks_lib` helpers (`get_tool_response`, `get_issue_keys_from_text`, `is_in_progress`); fixed `pre_dod_check.py` stdin API and config path
- **Hooks performance** — eliminated redundant `mkdir`/`utime`/`stat` calls per save with path caching; lazy-load QMD collections to avoid config reads on every hook invocation
- **Parallel script output** — `audit_confluence_pages.py` and `sprint_health_record.py` use `ThreadPoolExecutor` with atomic print for deterministic parallel output
- **P1 skill routing fixes** — verify-issue context clarification, blueprint branch logic, retrospective-analyst invocation, release-full and sprint-plan-full gate additions
- **Missing frontmatter fields** — `argument-hint` added to map-dependencies (was the only skill missing it); `x-compatibility: []` added to doctor, setup, atlassian-scripts

## [1.5.2] - 2026-03-22

### Fixed

- `scripts/test-install.sh` — removed `--extra embeddings` flag from `uv sync` call; `embeddings` optional-dependency was removed from `pyproject.toml` causing Phase 2 venv sync to fail (pipeline: 17→18 passed, 0 failed)

## [1.5.1] - 2026-03-22

### Fixed

- `hooks/plugin/session/check_prerequisites.sh` — corrected cache DB default path check to use `atlassian-pm-atlassian-pm` data dir; false-positive warning on fresh session start after clean install

## [1.5.0] - 2026-03-22

### Added

- **`allowed-tools` scope restriction on all 31 skills** — forked context skills now declare minimal MCP tool sets using fully qualified names (`mcp__<server>__<tool>`), preventing tool sprawl in subagent contexts
- **`effort` field on all 31 skills** — overrides session reasoning level per skill: `low` (doctor, setup, assign-issue, search-issues), `high` (create-story, analyze-story, plan-sprint, blueprint, spec-to-stories, sync-artifacts, close-sprint, plan-release, scan-tech-debt), `medium` (all others)
- **`context: fork` on 11 additional skills** — create-epic, update-epic, update-story, create-task, create-testplan, update-subtask, update-task, bug-triage, create-doc, update-doc, release-notes now run in isolated subagent contexts
- **`agent:` field on all 16 existing forked skills** — explicit agent type (`general-purpose` or `Explore`) per skill
- **`disable-model-invocation: true`** on doctor and setup — prevents accidental auto-invocation
- **Domain expert notes** added to all 31 skills — industry frameworks, key metrics, expert decision criteria, and common failure modes per skill
- **`quality-gate` agent** model upgraded from Haiku to Sonnet — higher accuracy QG scoring
- **`atlassian-cache` v1.0.0** — unified Jira + Confluence cache with 21 MCP tools; replaces `jira-cache-server`
  - Confluence tools: `cache_get_confluence_page`, `cache_get_confluence_children`, `cache_get_confluence_section`, `cache_search_confluence`, `cache_find_confluence_related`, `cache_sprint_confluence`, `cache_cross_search`, `cache_refresh_confluence`, `cache_invalidate_confluence`
  - Sprint tools: `cache_similar_sprints` — sprint goal vector search; `cache_sprint_issues` bulk sprint lookup
  - DB renamed: `jira.db` → `atlassian.db`; env vars renamed: `JIRA_CACHE_*` → `ATLASSIAN_CACHE_*`; class renamed: `JiraCache` → `AtlassianCache`
- **Write-invalidation hook** — `cache_write_invalidate.py` auto-clears cache entries after any MCP Atlassian write (HR6 enforcement)
- **Lazy version-check invalidation** — Jira `updated` field triggers cache refresh without explicit `cache_invalidate` call
- **Sprint goal embedding** (`cache_similar_sprints`) — vector search over sprint goals for sprint planning context
- **Confluence page-level embedding** — title + labels embedded for page retrieval via `cache_search_confluence`
- **Section heading in embeddings** — confluence section text now includes heading prefix for richer retrieval

### Changed

- `update-story` skill moved from `task/` → `story/` category (correct grouping)
- Token-optimize: 13 reference files (~1,432 tokens saved), 4 mermaid files (~2,930 tokens saved), 8 agent files (~700 tokens saved)
- `atlassian-cache`: renamed from `jira-cache-server` throughout all references

### Fixed

- `impact_suggester`: correct label extraction using `str.replace` instead of fragile regex; pre-compile regex at module load
- `thai_validator`: remove unused `KEEP_ENGLISH` set (93 dead strings)
- `cache_reindex`: remove dead `jira_api` glob import; update tool description
- `store_batch` calls wrapped in `asyncio.to_thread` — fixes event loop contention in async context
- `cache_sync`: validate `project_key` before sync; wrap blocking I/O in `asyncio.to_thread`
- `adf_validator`: pre-extract all sections once per `validate` call (was re-extracting per field)
- `jira_batch_update`: batch subtask type-check; parallelize updates with `ThreadPoolExecutor`
- `sprint_rank_by_date`: paginate sprint issue fetch to handle sprints with >50 issues
- `clear_sprint_dates`: parallelize Jira updates with `ThreadPoolExecutor`
- `sprint_subtask_alignment`: cache `estimate_oe` result; pre-compute field lookups

### Performance

- 17 performance and correctness fixes across `atlassian-cache`, `scripts/api/`, and `scripts/sprint/`

## [1.4.0] - 2026-03-21

### Added

- **`atlassian-cache` MCP server** (initial integration) — Jira issue cache with vector search, in-session deduplication, and 9 Confluence MCP tools
- `cache_find_related`, `cache_reindex`, `cache_sync` tools
- In-session deduplication and compact list format for 20+ issues
- Resilient hook runner (`hooks/plugin/session/`) — handles stale `CLAUDE_PLUGIN_ROOT` after plugin update mid-session

### Changed

- **12 skills renamed** to verb-noun standard (e.g. `story-analyze` → `analyze-story`) with Good/Bad usage examples added to each SKILL.md
- `bump-version.sh` — removed `claude plugin update` call to prevent session hook errors when bumping version in the active session

### Fixed

- Hook runner stale path warning after plugin update without session restart
- `test-install.sh` — warn when install upgrades plugin but session `CLAUDE_PLUGIN_ROOT` still points to old version

## [1.3.1] - 2026-03-21

### Fixed

- `plugin.json` skills declaration changed from single string `"./skills/"` to explicit array of 7 category paths — required for Claude Code to discover skills in category subdirectories after the v1.3.0 restructure

## [1.3.0] - 2026-03-21

### Added

- `scripts/test-install.sh` — automated install validation pipeline: remove → install → setup simulation → doctor (18 checks, 11 doctor checks); validates config backup/restore and venv recreation
- `scripts/bump-version.sh` fully automated non-interactive mode — no prompts, reads title from latest commit, runs end-to-end

### Changed

- **Skills reorganized into 7 category subdirectories:** `setup/`, `epic/`, `story/`, `task/`, `sprint/`, `confluence/`, `utilities/` — slash-command skills only in `skills/`
- **`references/`** moved from `skills/shared-references/` to project root — shared docs now at `references/` (24 files), skills reference via `../../../references/`
- **Scripts consolidated:** `atlassian-scripts/` and `scripts/` merged into unified `scripts/` with `api/`, `lib/`, `sprint/`, `analysis/`, `docs/` subdirectories
- **Thin SKILL.md wrapper** at `skills/utilities/atlassian-scripts/SKILL.md` — entry point pointing to `scripts/api/` and `scripts/docs/`
- `.mcp.json` PYTHONPATH updated: `skills/atlassian-scripts` → `scripts`
- All internal `sys.path` references in `scripts/sprint/*.py` updated
- Hook paths updated: `hooks/plugin/guards/pre_hr1_quality_gate.py`, `pre_hr4_confluence_macro_guard.py`
- `mcp-servers/atlassian-cache-server/server.py` sys.path updated to use `scripts/`

## [1.1.0] - 2026-03-20

### Added

- **4 new Layer 3 Synthesis agents:**
  - `estimation-calibrator`: SP calibration from historical similar issues via `cache_similar_issues`; HIGH/MEDIUM/LOW confidence; adjustment rules for auth/payment/integration/large-scope stories
  - `risk-forecaster`: 4-dimension delivery risk scoring (Capacity 30%, Complexity 25%, Dependency 25%, Team 20%); named mitigations; adjusted risk scenario after applying mitigations
  - `adf-surgeon`: structural ADF repair with 10 known Jira quirks (QUIRK-1–QUIRK-10); content-safe (never changes text); auto-fixable vs needs-human-judgment classification
  - `team-pattern-advisor`: multi-sprint strategic pattern analysis across 5 dimensions (bottlenecks, estimation accuracy, QA rejections, carry-over culprits, velocity seasonality); only reports patterns with ≥3 data points

- **Skill wiring for new agents:**
  - `create-story` Phase 7b: estimation-calibrator invoked after subtask design before ITERATE gate
  - `plan-sprint` Phase 6b: risk-forecaster invoked after sprint-planner returns with REVIEW gate and mitigation acceptance flow
  - `verify-issue` Phase 6: adf-surgeon invoked before acli write when auto-fixable structural issues found

### Changed

- **`issue-bootstrap`**: maxTurns 10→8; `--preset` flag system (story-create/sprint-plan/verify); BOOTSTRAP_COMPACT output header; Smart Description Truncation (ADF→plain text, 500 chars)
- **`jira-search`**: maxTurns 8→6; duplicate confidence scoring (EXACT/HIGH/MEDIUM/LOW); ranked top-5 output with Match Reason and Recommendation line
- **`velocity-tracker`**: anomaly detection (1.5σ threshold); `completion_ratio` per sprint; `member_velocity{}` block; `planned_sp` tracking
- **`code-explorer`**: maxTurns 15→12; Memory-First Protocol; `--domain` flag; VERIFIED/INFERRED confidence levels; memory update after each session
- **`quality-gate`**: Pattern Memory Protocol (save pass/fail examples); Expert Explanation Requirements; Team Convention Check from `expert_notes[]`; Auto-fix Classification
- **`backlog-groomer`**: WSJF scoring (Business Value + Time Criticality + Risk Reduction / Job Size); `value_density` calculation; aging alerts (21+ days without SP/AC)
- **`alignment-checker`**: AC Coverage Matrix (✅/❌ per AC per subtask); Predictive Risk Flags; Scope Drift Detection
- **`story-writer`**: maxTurns 20→15; Convention Memory Protocol; Service-Aware AC Defaults per service tag ([BE]/[FE-Admin]/[FE-Web]); Self-Critique Pass (5 checks); QG Failure Handling (2 self-fix attempts)
- **`sprint-planner`**: maxTurns 30→20; Risk-Adjusted Capacity formula with `sprint_risk_multiplier` (min 0.65); Three Scenario Planning (Conservative 70%/Realistic 85%/Optimistic 100%); Skill Gap Warning; Dependency-Aware assignment
- **`retrospective-analyst`**: maxTurns 25→20; Phase 3b Cross-Sprint Comparison (vs rolling avg); Phase 4b Team Health Score (0-100, 4 dimensions); Bottleneck Attribution (DEV/REVIEW/QA/BLOCKED); SMART action item validation

## [1.0.1] - 2026-03-19

### Fixed

- Renamed project from `jira-generator` to `atlassian-pm` across all files and configs
- Hook matchers updated to use canonical plugin MCP tool names (`mcp__plugin_atlassian-pm_atlassian-cache-server__`)
- `post_subtask_alignment_suggest.py`: fixed SPRINT_TOOLS set comparison with correct tool names
- `setup.sh`: corrected CONFIG_TEMPLATE path (`config/` not `.claude/`)
- `setup.sh`: added dependency checks at top (acli, uv, atlassian-cache-server venv)
- `setup.sh`: skip git filter config when not in a git repository (cache install)
- `sync-skills`: replaced hardcoded dev path with script-relative `SRC_BASE`
- `skills/setup/SKILL.md`: replaced hardcoded version fallback with dynamic `find` for latest cached version
- `hooks/hooks.json`: fixed all `mcp__atlassian-cache-server__` matchers to use full plugin namespace
- `scripts/sprint/*.py` added to `.gitattributes` filter coverage

### Added

- `hooks/config_loader.py`: shared config loader utility for hooks
- `hooks_state.py`: derives `QMD_COLLECTIONS` dynamically from `project-config.json`
- `pre_prompt_issue_prefetch.py`: derives `KEY_RE` and `PROJECT_KEY` from `project-config.json`
- `skills/setup/SKILL.md`: guided first-time setup skill (`/atlassian-pm:setup`)
- `.claude-plugin/marketplace.json`: plugin marketplace catalog
- Legacy cache migration: removes `~/.cache/jira-generator` on setup

### Changed

- MCP atlassian-cache-server DB path now uses `CLAUDE_PLUGIN_DATA` for persistence across plugin updates
- `setup.sh` and `skills/setup/SKILL.md`: venv installed in `CLAUDE_PLUGIN_DATA/venv` when available
- SessionStart hook added for automatic venv reinstall detection on plugin update
- `hooks/hooks.json`: `SubagentStart` event handler added
- `README.md`: added Online Installation section

## [1.0.0] - 2026-03-01

### Added

- Initial release as `atlassian-pm` plugin
- 21 skills: create-story, plan-sprint, verify-issue, analyze-story, update-story, sync-artifacts, and more
- 8 subagents: story-writer, sprint-planner, quality-gate, alignment-checker, and more
- Hook system: 37 hooks enforcing HR1–HR10 guardrails
- atlassian-cache-server MCP: SQLite-backed Jira issue cache with semantic search
- atlassian-scripts: 17 Python scripts for Jira/Confluence REST API operations
- Git smudge/clean filter for placeholder ↔ real value conversion
