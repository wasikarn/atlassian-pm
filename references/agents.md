# Subagents Reference

All agents live in `agents/` as `.md` files. Invoke via Agent tool with `subagent_type: "atlassian-pm:<name>"`.

| Agent | Model | Tier | Color | Used by |
|---|---|---|---|---|
| `jira-search` | haiku | L1 | cyan | duplicate detection, issue lookup |
| `issue-bootstrap` | haiku | L1 | cyan | pre-fetch issue + parent + children before processing |
| `pr-description-writer` | haiku | L1 | blue | PR description from branch + diff |
| `pr-review-jira-sync` | haiku | L1 | red | sync Jira after PR merge |
| `velocity-tracker` | haiku | L1 | yellow | harvest sprint velocity into project-config |
| `sprint-transition-agent` | haiku | L1 | red | batch sprint issue moves + sprint state transitions; close-sprint Phase 4 |
| `spec-parser-agent` | haiku | L1 | blue | parse Confluence page → structured requirements; spec-to-stories Phase 2; tools: Read only |
| `bug-evidence-writer` | haiku | L1 | blue | ADF bug description from test failure evidence; execute-testplan Phase 6 + bug-triage |
| `retro-data-extractor` | haiku | L1 | magenta | pre-processor for retrospective-analyst: fetches sprint issues + changelogs, computes raw metrics, writes compact retro-metrics-{sprint_id}.json |
| `estimation-calibrator` | haiku | L3 | yellow | SP estimate calibration via semantic similarity + velocity trend + story-outcome carry-over rates |
| `adf-surgeon` | haiku | L3 | blue | deep ADF structural repair after quality-gate flags |
| `quality-gate` | sonnet | L2 | green | validate ADF content; QG score ≥ 90% check |
| `story-writer` | sonnet | L2 | blue | generate ADF for stories + subtasks |
| `alignment-checker` | sonnet | L2 | green | verify story-subtask-epic alignment |
| `backlog-groomer` | sonnet | L2 | green | pre-sprint backlog health assessment |
| `retrospective-analyst` | sonnet | L2 | magenta | data-driven sprint retrospective; outputs structured action-items block for retro-actions |
| `sprint-planner` | sonnet | L2 | yellow | capacity-based sprint allocation |
| `risk-forecaster` | sonnet | L3 | yellow | delivery risk score before sprint starts |
| `team-pattern-advisor` | sonnet | L3 | magenta | multi-sprint pattern analysis for team strategy |
| `test-case-runner` | sonnet | L2 | red | execute single Playwright test case; execute-testplan Phase 4 |
