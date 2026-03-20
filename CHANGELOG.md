# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-20

### Added

- **4 new Layer 3 Synthesis agents:**
  - `estimation-calibrator`: SP calibration from historical similar issues via `cache_similar_issues`; HIGH/MEDIUM/LOW confidence; adjustment rules for auth/payment/integration/large-scope stories
  - `risk-forecaster`: 4-dimension delivery risk scoring (Capacity 30%, Complexity 25%, Dependency 25%, Team 20%); named mitigations; adjusted risk scenario after applying mitigations
  - `adf-surgeon`: structural ADF repair with 10 known Jira quirks (QUIRK-1–QUIRK-10); content-safe (never changes text); auto-fixable vs needs-human-judgment classification
  - `team-pattern-advisor`: multi-sprint strategic pattern analysis across 5 dimensions (bottlenecks, estimation accuracy, QA rejections, carry-over culprits, velocity seasonality); only reports patterns with ≥3 data points

- **Skill wiring for new agents:**
  - `story-full` Phase 7b: estimation-calibrator invoked after subtask design before ITERATE gate
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
- Hook matchers updated to use canonical plugin MCP tool names (`mcp__plugin_atlassian-pm_jira-cache-server__`)
- `post_subtask_alignment_suggest.py`: fixed SPRINT_TOOLS set comparison with correct tool names
- `setup.sh`: corrected CONFIG_TEMPLATE path (`config/` not `.claude/`)
- `setup.sh`: added dependency checks at top (acli, uv, jira-cache-server venv)
- `setup.sh`: skip git filter config when not in a git repository (cache install)
- `sync-skills`: replaced hardcoded dev path with script-relative `SRC_BASE`
- `skills/setup/SKILL.md`: replaced hardcoded version fallback with dynamic `find` for latest cached version
- `hooks/hooks.json`: fixed all `mcp__jira-cache-server__` matchers to use full plugin namespace
- `scripts/sprint/*.py` added to `.gitattributes` filter coverage

### Added

- `hooks/config_loader.py`: shared config loader utility for hooks
- `hooks_state.py`: derives `QMD_COLLECTIONS` dynamically from `project-config.json`
- `pre_prompt_issue_prefetch.py`: derives `KEY_RE` and `PROJECT_KEY` from `project-config.json`
- `skills/setup/SKILL.md`: guided first-time setup skill (`/atlassian-pm:setup`)
- `.claude-plugin/marketplace.json`: plugin marketplace catalog
- Legacy cache migration: removes `~/.cache/jira-generator` on setup

### Changed

- MCP jira-cache-server DB path now uses `CLAUDE_PLUGIN_DATA` for persistence across plugin updates
- `setup.sh` and `skills/setup/SKILL.md`: venv installed in `CLAUDE_PLUGIN_DATA/venv` when available
- SessionStart hook added for automatic venv reinstall detection on plugin update
- `hooks/hooks.json`: `SubagentStart` event handler added
- `README.md`: added Online Installation section

## [1.0.0] - 2026-03-01

### Added

- Initial release as `atlassian-pm` plugin
- 21 skills: story-full, plan-sprint, verify-issue, analyze-story, update-story, sync-alignment, and more
- 8 subagents: story-writer, sprint-planner, quality-gate, alignment-checker, and more
- Hook system: 37 hooks enforcing HR1–HR10 guardrails
- jira-cache-server MCP: SQLite-backed Jira issue cache with semantic search
- atlassian-scripts: 17 Python scripts for Jira/Confluence REST API operations
- Git smudge/clean filter for placeholder ↔ real value conversion
