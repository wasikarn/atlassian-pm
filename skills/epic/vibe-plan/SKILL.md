---
name: vibe-plan
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
allowed-tools: Read, Bash, Agent, Skill, Write, Glob, Grep, TodoWrite, mcp__mcp-atlassian__jira_create_issue, mcp__mcp-atlassian__jira_update_issue, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_text_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Feature → Epic + Stories + AI-Ready Subtasks in one command.
  Maximum 2 user interactions (decomposition review + optional annotation).

  The fastest path from idea to delegatable, AI-executable work items.
  Each subtask is a self-contained prompt: team member runs `implement {{PROJECT_KEY}}-XXX` in Claude Code.

  Triggers: "vibe plan", "vibe-plan", "plan feature", "feature to tasks", "idea to tasks",
    "วางแผน feature", "แตก feature", "feature ครบ", "สร้าง feature", "break down feature",
    "one-shot plan", "feature breakdown", "create feature tasks", "implement feature",
    "สร้าง epic+story", "auto-plan feature", "ต้องการสร้าง feature"
  Use when: turning a feature idea into a complete set of AI-executable Jira tickets
  Do NOT use for: updating existing issues (use update-*), creating a single story (use create-story), blueprint debate (use blueprint)
argument-hint: '"feature description" | --epic {{PROJECT_KEY}}-XXX | --dry-run'
effort: high
---

# /vibe-plan

**Role:** Tech Lead (full-stack planning)
**Output:** Epic + Stories + AI-Ready Subtasks in Jira (all with Implementation Hints)

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Project Key:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['project_key'])"`

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Understand | `feature_context`, `services_impacted[]`, `file_paths[]`, `patterns[]`, `existing_issues[]` |
| 2. Decompose | `decomposition_tree` (epic → stories[] → subtasks[]) |
| 3. Review | `approved_tree` (user-confirmed) |
| 4. QG | ADF files at `{{artifacts_dir}}/vibe-plan/`, `qg_scores{}` |
| 5. Create | `epic_key`, `story_keys[]`, `subtask_keys[]` |
| 6. Summary | delegation view output |

> **Workflow Patterns:** See [workflow-compact.md](../../../references/workflow-compact.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Flags

| Flag | Behavior |
|------|----------|
| *(none)* | Full workflow — Understand → Decompose → Review → QG → Create All → Summary |
| `--epic {{PROJECT_KEY}}-XXX` | Use existing epic instead of creating new one |
| `--dry-run` | Stop after Phase 3 (Review). Show approved decomposition tree — **no Jira writes**. Use to preview plan before committing. |

> If `--dry-run` → after user approves tree in Phase 3, output the full plan and stop. Skip Phases 4–5. Phase 6 shows preview summary with `(dry-run — not created)` label on all keys.

## Phases

---

### 1. Understand

> **🟢 AUTO** — Fully automated, no user interaction.

**Step 1 — Parse argument:**

- If `--epic <project_key>-XXX` → `cache_get_issue(issue_key, fields="summary,description,customfield_10016,status,issuetype,labels")` (fallback: `jira_get_issue`) + `jira_search(jql="parent = EPIC-KEY", fields="summary,status,issuetype", limit=20)`
- If no epic → work from description text only

**Step 2 — Search duplicates:**

> **🟢 AUTO** — `Skill(atlassian-pm:search-issues)` with feature keywords. If duplicates found → warn, don't block.

**Step 3 — Identify impacted services:** Match description keywords against `project-config.json` services tags:

| Tag | Keywords |
|-----|----------|
| `[BE]` | backend, API, service, endpoint, database, server |
| `[FE-Admin]` | admin, dashboard, management, platform-admin |
| `[FE-Web]` | website, web, checkout, landing, user-facing |
| `[Video]` | video, upload, processing, transcode, stream |
| `[Player]` | player, playback, vision |
| `[AI-Agent]` | AI, agent, LLM, automation |

**Step 4 — Explore codebase:**

> **🟢 AUTO + PARALLEL** — Launch 1 Explore agent covering all impacted service repos.

```text
Agent(name: "explore"):
  services: [services_impacted]
  description: [feature_context]
  goal: "Find existing patterns, entry points, and related files for: [feature description]"
```

Return validated file paths with CONFIDENCE (HIGH/MEDIUM/LOW) — keep HIGH and MEDIUM only.

---

### 2. Decompose

> **🟢 AUTO** — AI generates everything in one pass.

**Step 1 — Epic scope (if no existing epic):** Title + 2-3 sentence overview + 3-5 measurable success metrics. If existing epic → use its scope.

**Step 2 — Decompose into stories (max 5):** Each story needs: narrative (As a/I want/So that), ACs (Given/When/Then, max 5), VS label (`[BE]`/`[FE-Web]`/etc.), SP estimate (S=1-2 / M=3 / L=5), atomicity (1-3 days, single vertical slice).

**Step 3 — Decompose each story into subtasks (1 per service boundary):**

| Field | Requirement |
|-------|-------------|
| **Summary** | `[TAG] - description` |
| **Objective** | 1 sentence — what this subtask achieves |
| **Scope table** | CREATE/MODIFY/REF with real file paths from Phase 1 |
| **ACs** | Max 3, Given/When/Then |
| **Implementation Hints** | Entry Point, Pattern to Follow, Test Command, Dependencies |
| **Original Estimate** | 2h/4h/6h/8h |

Rules: lean descriptions + rich hints · every subtask references a concrete REF file · single concern per subtask (4+ CREATE files → split it).

---

### 3. Review

> **⛔ GATE** — Must get approval before proceeding. This is the only mandatory user interaction.

Display compact tree:

```text
Epic: [title] (total SP)
├─ Story 1: [title] (M=3SP)
│  ├─ [BE] subtask-1 (4h) — 2 CREATE, 1 MODIFY
│  └─ [FE-Web] subtask-2 (4h) — 1 CREATE, 2 MODIFY
└─ Story 2: [title] (S=2SP)
   └─ [BE] subtask-3 (2h) — 1 MODIFY

Total: N stories, N subtasks, NSP, Nh OE

Approve / Annotate (specify story#) / Reject
```

- **Approve** → Phase 4
- **Annotate** → revise specified stories only → re-present (max 1 round, then auto-approve)
- **Reject** → abort, suggest `/blueprint` for scope debate or `/create-story` for single story

---

### 4. Quality Gate

> **🟢 AUTO** — Score → auto-fix → re-score. HR1: QG >= 90%.

Write ADF JSON to `{{artifacts_dir}}/vibe-plan/`: `epic.json` (if new), `story-N.json`, `subtask-N-M.json` using [templates-epic.md](../../../references/templates-epic.md), [templates-story.md](../../../references/templates-story.md), [templates-subtask.md](../../../references/templates-subtask.md).

Validate:

```bash
uv run scripts/api/validate_adf.py {{artifacts_dir}}/vibe-plan/epic.json --type epic --json
uv run scripts/api/validate_adf.py {{artifacts_dir}}/vibe-plan/story-*.json --type story --json
uv run scripts/api/validate_adf.py {{artifacts_dir}}/vibe-plan/subtask-*.json --type subtask --json
```

If score < 90 → apply `issues[].fix_hint` → re-validate. Max 2 cycles per file. All files must pass before Phase 5.

---

### 5. Create All

> **🟢 AUTO** — Create all issues in correct dependency order. No user interaction.

**Step 1 — Create Epic (if new):**

```bash
acli jira workitem create --from-json {{artifacts_dir}}/vibe-plan/epic.json
```

> **🟢 AUTO** — HR6: `cache_invalidate(epic_key, auto_refresh=true)`

**Step 2 — Create Stories (sequential):**

```bash
acli jira workitem create --from-json {{artifacts_dir}}/vibe-plan/story-N.json
uv run scripts/api/jira_set_parent.py --issues STORY-KEY --parent EPIC-KEY
```

Set via MCP: SP (`customfield_10016`), size (`customfield_10107`), dates (`{{START_DATE_FIELD}}`, `duedate`), labels.
> **🟢 AUTO** — HR6: `cache_invalidate(story_key, auto_refresh=true)` after each.

**Step 3 — Create Subtasks (two-step HR5):**

```text
# Step 1: MCP create shell
jira_create_issue(project_key, "Subtask", summary, parent={key: "STORY-KEY"}, timetracking={originalEstimate: "4h"})

# Step 2: Verify parent (HR5 — DO NOT SKIP)
jira_get_issue(issue_key="SUBTASK-KEY", fields="parent") → confirm parent.key = STORY-KEY
# If missing → jira_set_parent.py before continuing

# Step 3: Edit description
acli jira workitem edit --from-json {{artifacts_dir}}/vibe-plan/subtask-N-M.json --yes

# Step 4: Set dates (HR8 — within parent range)
jira_update_issue(issue_key, additional_fields={{{START_DATE_FIELD}}, duedate, timetracking})
```

> **🟢 AUTO** — HR6: `cache_invalidate(subtask_key, auto_refresh=true)` after EVERY write.
> **🟢 AUTO** — HR3: assignee → `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).
> HR10: NEVER set `{{SPRINT_FIELD}}` (sprint) on subtasks.

---

### 6. Summary + Delegation View

```text
## Vibe Plan Complete

Epic: <project_key>-XXX — [Feature Name]

### Ready to Delegate:
| Assignee | Subtask | Type | OE | Claude Code Prompt |
|----------|---------|------|----|--------------------|
| (assign) | <project_key>-101 [BE] setup service | CREATE | 4h | "Implement RedeemCouponService following ApplyCouponService pattern..." |

→ /assign-issue <project_key>-101 member@email.com
→ /create-testplan <project_key>-XXX
→ /verify-issue <project_key>-XXX --with-subtasks
```

> Assignee from `project-config.json` team roster (match service tag to owner). Claude Code Prompt verbatim from Implementation Hints note panel.

---

## Examples

```text
/vibe-plan "coupon redemption at checkout for logged-in users"
/vibe-plan --epic <project_key>-100
/vibe-plan "video upload progress indicator with thumbnail generation"

# Too vague → use /create-task: /vibe-plan "fix bug"
# Too large → use /blueprint first: /vibe-plan "redesign entire platform"
# Single story → use /create-story instead of /vibe-plan
# Epic has existing stories → use --epic flag to avoid duplicates
```

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[ADF Core Rules](../../../references/templates-core.md) · [Story Template](../../../references/templates-story.md) · [Subtask Template](../../../references/templates-subtask.md) · [Epic Template](../../../references/templates-epic.md) · [Vibe Template](../../../references/templates-vibe.md) · [Subtask Design Patterns](../../../references/subtask-design-patterns.md)

After creation: `/verify-issue <project_key>-XXX --with-subtasks`
