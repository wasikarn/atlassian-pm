---
name: vibe-plan
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Feature → Epic + Stories + AI-Ready Subtasks in one command.
  Maximum 2 user interactions (decomposition review + optional annotation).

  The fastest path from idea to delegatable, AI-executable work items.
  Each subtask is a self-contained prompt: team member runs `implement TP-XXX` in Claude Code.

  Triggers: "vibe plan", "vibe-plan", "plan feature", "feature to tasks", "วางแผน feature", "แตก feature"
  Use when: turning a feature idea into a complete set of AI-executable Jira tickets
  Do NOT use for: updating existing issues (use update-*), creating a single story (use create-story), blueprint debate (use blueprint)
argument-hint: '"feature description" | --epic TP-XXX'
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

## Phases

---

### 1. Understand

> **🟢 AUTO** — Fully automated, no user interaction.

**Goal:** Parse feature description, fetch existing context, search for duplicates, explore codebase.
**Required inputs:** Feature description string OR `--epic <project_key>-XXX`
**Constraints:** AUTO — no user interaction; only gather what's needed (Context Engineering rule: just-in-time context)
**Output:** `feature_context`, `services_impacted[]`, `file_paths[]`, `patterns[]`, `existing_issues[]`

**Step 1 — Parse argument:**

- If `--epic <project_key>-XXX` → fetch epic via MCP, extract scope/stories if any:

  ```text
  MCP: cache_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")
  → fallback: jira_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")
  MCP: jira_search(jql="parent = EPIC-KEY", fields="summary,status,issuetype", limit=20)
  ```

- If no epic → work from description text only

**Step 2 — Search duplicates:**

```text
MCP: cache_text_search(query="[feature keywords extracted from description]", limit=5)
```

If duplicates found → show warning but don't block. Continue.

**Step 3 — Identify impacted services:**

Match description keywords against `project-config.json` services tags:

| Tag | Keywords to match |
|-----|-------------------|
| `[BE]` | backend, API, service, endpoint, database, server |
| `[FE-Admin]` | admin, dashboard, management, platform-admin |
| `[FE-Web]` | website, web, checkout, landing, user-facing |
| `[Video]` | video, upload, processing, transcode, stream |
| `[Player]` | player, playback, vision |
| `[AI-Agent]` | AI, agent, LLM, automation |

**Step 4 — Explore codebase:**

> **🟢 AUTO + PARALLEL** — Launch 1 Explore agent covering all impacted service repos.

For each impacted service, explore the relevant codebase path from `project-config.json` services:

```text
Agent(name: "explore"):
  services: [services_impacted]
  description: [feature_context]
  goal: "Find existing patterns, entry points, and related files for: [feature description]"
```

Must return validated file paths with CONFIDENCE level (HIGH/MEDIUM/LOW). Only keep HIGH and MEDIUM.

**Context Engineering rule:** Only gather what's needed — don't read entire codebases. Focus on entry points, pattern files (REF), and directly related modules.

---

### 2. Decompose

> **🟢 AUTO** — AI generates everything in one pass.

**Goal:** Generate the full decomposition tree: Epic → Stories → Subtasks with Implementation Hints.
**Required inputs:** `feature_context`, `services_impacted[]`, `file_paths[]`, `patterns[]` from Phase 1
**Constraints:** AUTO — single pass generation; max 5 stories per invocation; 1 subtask per service boundary; Context Engineering rules apply
**Output:** `decomposition_tree` (nested structure: epic → stories[] → subtasks[])

**Step 1 — Epic scope (if no existing epic):**

Generate:
- Title: concise feature name
- Overview: 2-3 sentence problem → solution narrative
- Success metrics: measurable outcomes (3-5 bullet points)

If existing epic → use its scope, skip generation.

**Step 2 — Decompose into stories (max 5):**

For each story:
- **Narrative:** As a [persona], I want to [action], So that [benefit]
- **ACs:** Given/When/Then format, max 5 per story
- **VS label:** from service tags (e.g., `[BE]`, `[FE-Web]`, `[BE]+[FE-Web]`)
- **SP estimate:** S(1-2) / M(3) / L(5) — based on scope complexity
- **Atomicity:** 1-3 days each, single vertical slice

**Step 3 — Decompose each story into subtasks:**

For each story → 1 subtask per service boundary:

| Field | Requirement |
|-------|-------------|
| **Summary** | `[TAG] - description` (e.g., `[BE] - Create coupon redemption service`) |
| **Objective** | 1 sentence — what this subtask achieves |
| **Scope table** | CREATE/MODIFY/REF with real file paths from Phase 1 |
| **ACs** | Max 3, Given/When/Then format |
| **Implementation Hints** | Entry Point, Pattern to Follow, Test Command, Dependencies |
| **Original Estimate** | Hours (2h/4h/6h/8h) |

**Context Engineering rules:**
- Lean descriptions, rich hints (detail goes in Section 4 Implementation Hints)
- Point to pattern files — every subtask must reference a concrete REF file
- Single concern per subtask — if 4+ CREATE files, split it
- Canonical examples over descriptions — point to working files, not prose

---

### 3. Review

> **⛔ GATE** — Must get approval before proceeding. This is the only mandatory user interaction.

**Goal:** Let the Tech Lead review the full decomposition before any Jira write.
**Required inputs:** `decomposition_tree` from Phase 2
**Constraints:** GATE — must get explicit approval; max 1 annotation round
**Output:** `approved_tree` (user-confirmed decomposition)

**Display compact tree:**

```text
Epic: [title] (total SP)
├─ Story 1: [title] (M=3SP)
│  ├─ [BE] subtask-1 (4h) — 2 CREATE, 1 MODIFY
│  └─ [FE-Web] subtask-2 (4h) — 1 CREATE, 2 MODIFY
├─ Story 2: [title] (S=2SP)
│  └─ [BE] subtask-3 (2h) — 1 MODIFY
└─ Story 3: [title] (M=3SP)
   ├─ [BE] subtask-4 (4h) — 2 CREATE
   └─ [FE-Admin] subtask-5 (4h) — 1 CREATE, 1 MODIFY

Total: 3 stories, 5 subtasks, 8SP, 18h OE

Approve / Annotate (specify story#) / Reject
```

**User responses:**

- **Approve** → proceed to Phase 4
- **Annotate** → user specifies story # and changes → revise ONLY specified stories → re-present tree (max 1 round, then auto-approve)
- **Reject** → abort skill, explain what to do instead (e.g., `/blueprint` for scope debate, `/create-story` for single story)

---

### 4. Quality Gate

> **🟢 AUTO** — Score → auto-fix → re-score. HR1: QG >= 90%.

**Goal:** Generate and validate all ADF JSON files.
**Required inputs:** `approved_tree` from Phase 3
**Constraints:** HR1 — NEVER create issues in Jira without QG >= 90%; AUTO — score, auto-fix, re-score; max 2 fix cycles per file
**Output:** ADF files at `{{artifacts_dir}}/vibe-plan/`, `qg_scores{}`

**Step 1 — Generate ADF JSON files:**

Write to `{{artifacts_dir}}/vibe-plan/`:
- `epic.json` (if new epic) — using [references/templates-epic.md](../../../references/templates-epic.md)
- `story-N.json` (1 per story) — using [references/templates-story.md](../../../references/templates-story.md)
- `subtask-N-M.json` (per story per subtask) — using [references/templates-subtask.md](../../../references/templates-subtask.md) with Section 4: Implementation Hints

**Step 2 — Validate each file:**

```bash
# Epic (if new)
uv run scripts/api/validate_adf.py {{artifacts_dir}}/vibe-plan/epic.json --type epic --json

# Stories
uv run scripts/api/validate_adf.py {{artifacts_dir}}/vibe-plan/story-*.json --type story --json

# Subtasks
uv run scripts/api/validate_adf.py {{artifacts_dir}}/vibe-plan/subtask-*.json --type subtask --json
```

**Step 3 — Auto-fix failures:**

If score < 90 → check `issues[].fix_hint` → apply fixes → re-validate. Max 2 cycles per file.

All files must pass >= 90% before proceeding.

---

### 5. Create All

> **🟢 AUTO** — Create all issues in correct dependency order. No user interaction.

**Goal:** Create all issues in Jira in correct order (Epic → Stories → Subtasks).
**Required inputs:** ADF files (QG PASS from Phase 4), `approved_tree`
**Constraints:** HR5 (two-step subtask), HR6 (cache invalidate after every write), HR8 (subtask dates within parent range), HR10 (NEVER set sprint on subtasks)
**Output:** `epic_key`, `story_keys[]`, `subtask_keys[]`

**Step 1 — Create Epic (if new):**

```bash
acli jira workitem create --from-json {{artifacts_dir}}/vibe-plan/epic.json
```

Capture `epic_key`.

> **🟢 AUTO** — HR6: `cache_invalidate(epic_key, auto_refresh=true)` after create.

**Step 2 — Create Stories (sequential — each must capture key):**

For each story:

```bash
acli jira workitem create --from-json {{artifacts_dir}}/vibe-plan/story-N.json
```

Capture `story_key`. Then set parent to epic:

```bash
uv run scripts/api/jira_set_parent.py --issues STORY-KEY --parent EPIC-KEY
```

Set fields via MCP: SP (`customfield_10016`), size (`customfield_10107`), dates (`customfield_10015`, `duedate`), labels.

> **🟢 AUTO** — HR6: `cache_invalidate(story_key, auto_refresh=true)` after each story create.

**Step 3 — Create Subtasks (batch per story, two-step HR5):**

For each story's subtasks:

```text
# Step 1: MCP create shells (parallel per story)
MCP: jira_create_issue({
  project_key: "<project_key>",
  summary: "[TAG] - description",
  issue_type: "Subtask",
  additional_fields: {
    parent: {key: "STORY-KEY"},
    timetracking: {originalEstimate: "4h"}
  }
})

# Step 2: Verify parent (HR5 — DO NOT SKIP)
MCP: jira_get_issue(issue_key="SUBTASK-KEY", fields="parent")
→ confirm parent.key = STORY-KEY
# If parent missing → fix via jira_set_parent.py before continuing

# Step 3: Edit description
acli jira workitem edit --from-json {{artifacts_dir}}/vibe-plan/subtask-N-M.json --yes

# Step 4: Set dates (HR8 — within parent range)
MCP: jira_update_issue(issue_key="SUBTASK-KEY", additional_fields={
  "customfield_10015": "YYYY-MM-DD",
  "duedate": "YYYY-MM-DD",
  "timetracking": {"originalEstimate": "Nh"}
})

# HR6: cache_invalidate after every write
# HR10: NEVER set customfield_10020 (sprint) on subtasks
```

> **🟢 AUTO** — HR6: `cache_invalidate(subtask_key, auto_refresh=true)` after EVERY write.
> **🟢 AUTO** — HR3: If assignee needed, use `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).

---

### 6. Summary + Delegation View

**Goal:** Present delegation-ready output with Claude Code prompts for each subtask.
**Required inputs:** `epic_key`, `story_keys[]`, `subtask_keys[]` from Phase 5
**Constraints:** None
**Output:** Delegation view table + next action suggestions

```text
## Vibe Plan Complete

Epic: <project_key>-XXX — [Feature Name]

### Ready to Delegate:
| Assignee | Subtask | Type | OE | Claude Code Prompt |
|----------|---------|------|----|--------------------|
| (assign) | <project_key>-101 [BE] setup service | CREATE | 4h | "Implement RedeemCouponService following ApplyCouponService pattern..." |
| (assign) | <project_key>-102 [FE-Web] checkout UI | CREATE | 4h | "Add coupon input to CheckoutPage following DiscountSection pattern..." |

→ /assign-issue <project_key>-101 member@email.com
→ /create-testplan <project_key>-XXX
→ /verify-issue <project_key>-XXX --with-subtasks
```

> Column source: Assignee from `project-config.json` team roster (match service tag to owner) · Subtask key from Phase 5 · Claude Code Prompt verbatim from Implementation Hints note panel.

---

## Examples

### Good

```text
/vibe-plan "coupon redemption at checkout for logged-in users"
/vibe-plan --epic <project_key>-100
/vibe-plan "video upload progress indicator with thumbnail generation"
```

### Bad

```text
/vibe-plan "fix bug" — too vague, use /create-task for bugs
/vibe-plan "redesign entire platform" — too large, use /blueprint first
```

**Common mistakes:**

- Using `/vibe-plan` for a single story that fits in one vertical slice — use `/create-story` instead; vibe-plan is for multi-story features.
- Skipping `/blueprint` for ambiguous, large-scope features — if the feature scope is debatable, run `/blueprint` first to get PO/TL/QA alignment, then feed the blueprint output to `/vibe-plan --epic`.
- Providing a vague description like "improve performance" — the more specific the input, the more accurate the codebase exploration and Implementation Hints. Include affected user flows, services, and expected behavior.
- Running `/vibe-plan` when the epic already has stories — use `--epic` flag to fetch existing context and avoid creating duplicate stories.

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[ADF Core Rules](../../../references/templates-core.md) · [Story Template](../../../references/templates-story.md) · [Subtask Template](../../../references/templates-subtask.md) · [Epic Template](../../../references/templates-epic.md) · [Vibe Template](../../../references/templates-vibe.md) · [Subtask Design Patterns](../../../references/subtask-design-patterns.md)

After creation: `/verify-issue <project_key>-XXX --with-subtasks`
