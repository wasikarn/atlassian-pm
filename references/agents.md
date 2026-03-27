# Subagents Reference

All agents live in `agents/` as `.md` files. Invoke via Agent tool with `subagent_type: "atlassian-pm:<name>"`.

| Agent | Model | Tier | Used by |
|---|---|---|---|
| `code-explorer` | haiku | L1 | general codebase investigation |
| `jira-search` | haiku | L1 | duplicate detection, issue lookup |
| `issue-bootstrap` | haiku | L1 | pre-fetch issue + parent + children before processing |
| `pr-description-writer` | haiku | L1 | PR description from branch + diff |
| `pr-review-jira-sync` | haiku | L1 | sync Jira after PR merge |
| `velocity-tracker` | haiku | L1 | harvest sprint velocity into project-config |
| `sprint-transition-agent` | haiku | L1 | batch sprint issue moves + sprint state transitions; close-sprint Phase 4 |
| `spec-parser-agent` | haiku | L1 | parse Confluence page → structured requirements; spec-to-stories Phase 2; tools: Read only |
| `bug-evidence-writer` | haiku | L1 | ADF bug description from test failure evidence; execute-testplan Phase 6 + bug-triage |
| `estimation-calibrator` | haiku | L3 | SP estimate calibration via semantic similarity |
| `adf-surgeon` | haiku | L3 | deep ADF structural repair after quality-gate flags |
| `quality-gate` | sonnet | L2 | validate ADF content; QG score ≥ 90% check |
| `story-writer` | sonnet | L2 | generate ADF for stories + subtasks |
| `alignment-checker` | sonnet | L2 | verify story-subtask-epic alignment |
| `backlog-groomer` | sonnet | L2 | pre-sprint backlog health assessment |
| `retrospective-analyst` | sonnet | L2 | data-driven sprint retrospective |
| `sprint-planner` | sonnet | L2 | capacity-based sprint allocation |
| `risk-forecaster` | sonnet | L3 | delivery risk score before sprint starts |
| `team-pattern-advisor` | sonnet | L3 | multi-sprint pattern analysis for team strategy |
| `test-case-runner` | sonnet | L2 | execute single Playwright test case; execute-testplan Phase 4 |
