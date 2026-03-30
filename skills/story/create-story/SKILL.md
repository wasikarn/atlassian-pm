---
name: create-story
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Create User Story + Sub-tasks — vibe mode by default (fast, no ceremony)
  Use --thorough for full interview + annotation workflow

  Phases: Discovery → Write Story → INVEST → QG → Create Story → Impact → Explore Codebase → Design + Estimation → Alignment → QG Subtasks → Create Sub-tasks → Summary

  Composite: No need to copy-paste issue keys, context preserved throughout workflow

  Triggers: "create story", "new story", "story + subtasks", "สร้าง story"
  Use when: creating a User Story with sub-tasks end-to-end — from discovery and INVEST check through codebase exploration, subtask design, and Jira creation
  Do NOT use for: creating standalone tasks (use create-task); creating an epic (use create-epic); refining scope before writing (use refine-epic)
argument-hint: "[--thorough | --no-subtasks] [story-description]"
effort: high
---

# /create-story

**Role:** PO + TA Combined · **Output:** User Story + Sub-tasks (complete workflow)

## Mode Selection

| Flag | Behavior | Interactions |
| --- | --- | --- |
| *(none)* | **Vibe mode (default)** — auto-extract context, single-pass generation, no annotation rounds | 0–1 |
| `--thorough` | **Thorough mode** — full interview gates, ITERATE annotation rounds (max 3), all REVIEW gates | Multiple |
| `--no-subtasks` | **Story only** — stop after Phase 5; skip Phases 6–11. Add subtasks later via `/analyze-story`. | 0–1 |

> Strip `--thorough` or `--no-subtasks` flag from argument before processing. `--no-subtasks`: run Phases 1–5 only, then jump to Phase 12.

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Project Key:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['project_key'])"`

## Context Object

| Phase | Adds to Context |
| ----- | -------------- |
| 0. Blueprint (optional) | `blueprint_page_id`, `selected_story_index`, `blueprint_acs_hints[]` |
| 1. Discovery | `epic_data`, `vs_assignment`, `user_requirements`, `user_context` |
| 2. Write Story | `story_narrative`, `acs[]`, `scope`, `dod` |
| 3. INVEST | `invest_score`, `vs_validated` |
| 4. QG Story | `story_adf_json`, `story_qg_score` |
| 5. Create Story | `story_key` (ABC-XXX) |
| 6. Impact | `services_impacted[]`, `vs_verified` |
| 7. Explore | `file_paths[]`, `patterns[]`, `dependencies[]` |
| 8. Design + Estimation | `subtask_designs[]` (with calibrated SP) |
| 9. Alignment | `alignment_checklist` |
| 10. QG Subtasks | `qg_score`, `passed_qg` |
| 11. Create | `subtask_keys[]` |

> **Workflow Patterns:** See [workflow-compact.md](../../../references/workflow-compact.md) for Gate Levels, QG Scoring, Two-Step, and Explore patterns.

## Blueprint Handoff Check

**If `blueprint_backlog_map` present in conversation history:**

1. Show numbered story list from blueprint. Ask: "ต้องการสร้าง story ข้อไหน? (ระบุหมายเลข)" — if invalid index, re-display.
2. Extract `stories[N-1]`: title → summary draft · `narrative_hint` → narrative · `acs_hint[]` → AC starting points · `vs_label` → VS · `sp_estimate` → SP · `blueprint_page_id` → link in References. Skip missing fields.
3. Show: `"Story: [title] | VS: [vs_label] | SP: [sp_estimate]\nใช้ข้อมูลจาก blueprint สำหรับ story นี้ confirm?"`

**⛔ GATE** — รอ user confirm ก่อนดำเนินต่อ

**In Phase 1:** Still fetch epic via MCP if key present → `epic_data`. Skip interview questions and VS assignment (use blueprint values).

**If no blueprint in history:** ดำเนิน Phase 1 Discovery ตามโหมดที่เลือก

## Part A: Create Story (Phases 1-5)

---

### 1. Discovery

#### Vibe Mode (Default)

- Parse description to infer: persona, action, benefit, affected services
- If Epic key in argument → `cache_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")` → fallback `jira_get_issue` · `jira_search(jql="parent = EPIC-KEY", fields="summary,status,issuetype", limit=10)` — run 🟢 PARALLEL with Confluence search
- If description < 10 words with no context → ask ONE question: "Tell me more about this feature" · otherwise proceed directly to Phase 2
- **VS Assignment:** auto-assign from services in description (`[BE]`/`[FE]` mentions → vs2, both → vs2-e2e)
- **Confluence Domain Knowledge (🟢 AUTO non-blocking):** `cache_search_confluence(query="[story_keywords]", space_key="<space_key>", limit=3)` → store as `domain_context` if found

**Epic Readiness Pre-check (🟢 AUTO — warn only, never block in vibe mode):**

| Check | Pass Condition |
| --- | --- |
| ACs defined | Epic description contains ≥ 3 AC lines |
| SP estimated | `customfield_10016` set (not null/0) |
| No blockers | No linked "Blocks" issues in Open/In Progress |

---

#### --thorough Mode

- Ask: Who? What? Why? Constraints? Story Context (for 📍 line)?
- Fetch epic via MCP (same calls as vibe mode); run 🟢 PARALLEL with Confluence search
- Show Epic Readiness warnings in table form; **⛔ GATE if ≥ 2 checks fail** (require `y`); **🟡 REVIEW if 1 fails**
- Ask VS Assignment: which vertical slice? (`vs1-skeleton`, `vs2-*`, `vs-enabler`)
- **⛔ GATE** — DO NOT PROCEED without user confirmation of requirements + VS assignment

---

### 2. Write User Story

```text
📍 [User's current situation — what they're doing, what's difficult]  ⚡ optional
As a [persona],
I want to [action],
So that [benefit].
```

- ⚡ **Context line:** include when persona is new or workflow is complex
- Define ACs, Scope, DoD · **AC Naming:** `AC{N}: [Verb] — [Scenario Name]`
- **VS Check:** story delivers e2e value? all layers touched?
- **📐 Technical Notes (⚡ if `domain_context` exists):** populate from `domain_context` + epic tech notes; leave `Key files:` blank (filled post-Phase 7)
- → ADF format: see [references/templates-story.md](../../../references/templates-story.md)

**Vibe:** Show story as information, proceed immediately to Phase 3 (no gate).

**--thorough:** **🔄 ITERATE** — Present draft (narrative, ACs, scope, DoD). Ask: Approve / Annotate / Major rework. Annotate → revise only noted items → re-present (max 3 rounds). Major rework → back to Discovery. See [Annotation Cycle](../../../references/workflow-patterns.md#annotation-cycle-iterate-gate).

---

### 3. INVEST + VS Validation

**🟢 AUTO** — validate all; auto-fix failures; escalate only if unfixable after 2 attempts.

- [ ] **I**ndependent · **N**egotiable · **V**aluable · **E**stimable · **S**mall+**Vertical** (1 sprint, e2e slice) · **T**estable
- **VS Anti-pattern Check:** ❌ Shell-only → add minimal happy path · ❌ Layer-split → combine into single story

---

### 4. Quality Gate — Story (HR1)

> **⚠️ MANDATORY:** Read `references/templates-story.md` before generating ADF. Use `panel` nodes — NEVER `heading` nodes in issue descriptions.
> HR1: DO NOT send Story to Atlassian without QG ≥ 90%.

1. Generate ADF JSON → `{{artifacts_dir}}/story.json`
2. **Pre-QG polish + subtask suggestions (🟢 PARALLEL):**
   - `python3 scripts/ai/pre_qg_polish.py --file {{artifacts_dir}}/story.json --type story` → overwrites with polished ADF
   - `python3 scripts/ai/suggest_subtasks.py --story {{story_key_placeholder}} --acs "{{acs_text}}"` → `suggested_subtasks[]` for Phase 8
   - Both non-blocking: if exits 1, continue with existing content
3. **Quick pre-check (🟢 AUTO):** `python3 scripts/ai/qg_quick.py --file {{artifacts_dir}}/story.json --type story` → if `skip_full_agent: true` (score ≥ 95) skip Step 4 · if `structural_issues[]` → apply QUIRK fixes · non-blocking if exits 1
4. **QG Scoring:** `uv run scripts/api/validate_adf.py {{artifacts_dir}}/story.json --type story --json` → score ≥ 90 = PASS · if FAIL → `--fix` → re-score (max 1 cycle) · escalate to user if still < 90

---

### 5. Create Story in Jira

> **🟢 AUTO** — If Phase 4 QG passed → create automatically.

```bash
acli jira workitem create --from-json {{artifacts_dir}}/story.json
```

- **Labels (MANDATORY):** Feature label + VS label (e.g., `coupon-web`, `vs2-collect-e2e`)
- Capture story key → `story_key`
- **🟢 AUTO** HR6: `cache_invalidate(story_key)` after create
- **Set estimation fields:** `jira_update_issue(issue_key="ABC-XXX", additional_fields={"customfield_10016": <SP>, "customfield_10107": {"value": "<SIZE>"}, "{{START_DATE_FIELD}}": "YYYY-MM-DD", "duedate": "YYYY-MM-DD"})`
- **🟢 AUTO** HR6: `cache_invalidate(story_key)` after field update
- **Record QG:** `python scripts/qg_record.py --issue-key "ABC-XXX" --type Story --score STORY_QG_SCORE --status PASS --service "SERVICE_TAG"`
- **`--no-subtasks` exit point:** skip Part B, jump to Phase 12 with `subtask_keys[] = []`

---

## Part B: Create Sub-tasks (Phases 6-12)

> **Skip entirely if `--no-subtasks`** — proceed directly to Phase 12.

---

### 6. Impact Analysis

**Vibe:** 🟢 AUTO — infer from story narrative + VS assignment. Show impact table as information, proceed to Phase 7.

**--thorough:** 🟡 REVIEW — present table + VS verification to user; proceed unless user objects; flag shell-only anti-pattern.

| Service | Impact | Reason |
| --- | --- | --- |
| Backend | ✅/❌ | [why] |
| Admin | ✅/❌ | [why] |
| Website | ✅/❌ | [why] |

**VS Verification:** story touches all layers for e2e slice? (not layer-only)

---

### 7. Codebase Exploration ⚠️ MANDATORY

> ⚡ If user provided file paths in requirements → skip (add `--skip-explore`)
> Launch 1 Explore agent covering all impacted services. Validate paths with Glob. Generic paths REJECTED — re-explore max 2 attempts.
> See [subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for exploration requirements.

Each Explore agent must return:

```text
SERVICE: [BE|FE-Admin|FE-Web|Shared]
CONFIDENCE: [HIGH|MEDIUM|LOW]
FILES:
- [full/absolute/path/to/file.ts]  # action: CREATE|MODIFY|REF
PATTERNS: [brief description]
DEPENDENCIES: [key imports or shared modules]
```

**Validation before Phase 8:**

| Condition | Action |
|---|---|
| `CONFIDENCE: LOW` | REJECTED — re-explore (max 2 attempts) |
| Top-level glob path or Glob fails | REJECTED — re-explore |
| `FILES:` empty | REJECTED — re-explore |
| All CONFIDENCE: HIGH or MEDIUM with valid paths | ✅ Proceed |

---

### 8. Design + Estimation

- 1 sub-task per service boundary (split only if complexity warrants)
- **VS Integrity:** each subtask contributes to VS completion (not horizontal layer)
- Summary: `[TAG] - Description` · ACs: Thai narrative + English technical terms
- See [analyze-story/SKILL.md](../analyze-story/SKILL.md) for TL decomposition ordering

**Implementation Hints (🟢 AUTO — MANDATORY in vibe mode):** Include Section 4 in every subtask ADF from Phase 7 results:

| Field | Source |
| --- | --- |
| Entry Point | First CREATE file from scope table |
| Pattern to Follow | First REF file from scope table |
| Test Command | Project test command scoped to new file |
| Related API | HTTP endpoint found in exploration (BE only) |
| Dependencies | Key imports from REF file constructor |

→ ADF format: see [templates-vibe.md](../../../references/templates-vibe.md)

**Estimation Calibration (🟢 AUTO + PARALLEL):** Launch all `estimation-calibrator` agents simultaneously — one per subtask:

```text
Agent(name: "estimation-calibrator"):
  story_summary, service_tag, initial_sp, scope_file_count, ac_count
```

If recommendation differs AND confidence ≥ MEDIUM → update SP, note "SP adjusted [M→L] based on: [reason]". If LOW confidence → keep initial, note "insufficient historical data".

**Vibe:** Show designs as information. Proceed to Phase 9 immediately (no gate).

**--thorough:** **🔄 ITERATE** — Present plan cards (tag, scope, ACs, OE). Ask: Approve all / Annotate (specify subtask #) / Major rework. Max 3 rounds. Major rework → back to Phase 7.

---

### 9. Alignment Check

**🟢 AUTO** — verify all story ACs traceable to ≥ 1 subtask AC; scope tables consistent with Phase 7 findings. Auto-fix misalignment. Escalate only if unfixable.

See [subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for alignment check rules.

---

### 10. Quality Gate — Subtasks (MANDATORY)

> HR1: DO NOT create subtasks without QG ≥ 90%.
> **🟢 AUTO** — score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.

```bash
uv run scripts/api/validate_adf.py {{artifacts_dir}}/subtask-*.json --type subtask --json
```

---

### 11. Create Sub-tasks

> **🟢 AUTO** — Create → verify parent → edit descriptions. Escalate only if parent verify fails after retry.
> HR5 two-step + verify; HR6 cache_invalidate after every write; HR8 dates within parent range; HR10 NEVER set sprint on subtasks; HR3 use acli for assignee.
> See [Two-Step Subtask](../../../references/workflow-patterns.md#two-step-subtask-creation).

```text
# Step 1: Create shells (🟢 PARALLEL)
MCP: jira_create_issue({project_key:"<project_key>", summary:"[BE] - ...", issue_type:"Subtask", additional_fields:{parent:{key:"ABC-XXX"}, timetracking:{originalEstimate:"4h"}}})

# Step 2: Verify parent (HR5) — DO NOT SKIP
MCP: jira_get_issue(issue_key:"ABC-YYY", fields:"parent") → confirm parent.key = "ABC-XXX"
# If parent missing → fix via REST API before continuing

# Step 3: Set dates + OE (HR8 — within parent range, HR10 — NO sprint field)
MCP: jira_update_issue(issue_key="ABC-YYY", additional_fields={"timetracking":{"originalEstimate":"<N>h"}, "{{START_DATE_FIELD}}":"YYYY-MM-DD", "duedate":"YYYY-MM-DD"})

# Step 4: Update descriptions
acli jira workitem edit --from-json {{artifacts_dir}}/subtask-be.json --yes
```

- **🟢 AUTO** HR6: `cache_invalidate(subtask_key)` after every write
- **🟢 AUTO** HR3: `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP)
- **🟢 AUTO** Record QG scores: `python scripts/qg_record.py --issue-key "ABC-XXX" --type Subtask --score QG_SCORE --status PASS --service "[SERVICE_TAG]"`

---

### 12. Summary

```text
## Story Full Complete
Story: ABC-XXX
Sub-tasks: ABC-YYY [BE], ABC-ZZZ [FE-Admin]
→ /create-testplan ABC-XXX for QA
→ /verify-issue ABC-XXX --with-subtasks
```

**`--no-subtasks` variant:**

```text
## Story Created
Story: ABC-XXX — [title]
Sub-tasks: none (--no-subtasks)
→ /atlassian-pm:analyze-story ABC-XXX   when ready to add subtasks
→ /atlassian-pm:verify-issue ABC-XXX    to check story quality
```

**Delegation View (vibe mode — show after summary):**

| Assignee | Subtask | Type | OE | Claude Code Prompt |
|---|---|---|---|---|
| [dev email] | ABC-YYY [BE] | CREATE | Nh | "Implement X following Y..." |
| [fe email] | ABC-ZZZ [FE-Admin] | CREATE | Nh | "Implement Z following W..." |

> Column source: Assignee from `project-config.json` · Subtask key from Phase 11 · Claude Code Prompt from Implementation Hints panel.

## Examples

### Good

```text
/create-story "coupon redemption at checkout for logged-in users"    # vibe — auto-extracts, 0 questions
/create-story "video upload progress indicator for content creators" # vibe — straight to phases
/create-story                                                        # after /blueprint → picks up blueprint_backlog_map
/create-story --thorough "new payment gateway integration"           # complex — full interview + annotation
/create-story --no-subtasks "payment refund flow"                    # story only, add subtasks later
สร้าง story สำหรับ Google SSO ไม่ต้องสร้าง subtask ก่อน             # natural language --no-subtasks intent
```

### Bad

```text
/create-story {{PROJECT_KEY}}-123             # story already exists → use /analyze-story {{PROJECT_KEY}}-123
/create-story "authentication"   # too vague → will ask ONE clarifying question
/create-story "redesign entire checkout"  # too large → INVEST Small fails, use /create-epic first
```

**Common mistakes:** Passing an existing Jira key · Skipping `/blueprint` for multi-story features · No parent epic · Confusing with `/analyze-story` (which works on existing stories) · Using `--thorough` for simple features.

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[ADF Core Rules](../../../references/templates-core.md) · [Story Template](../../../references/templates-story.md) · [Subtask Template](../../../references/templates-subtask.md) · [Vibe Mode Templates](../../../references/templates-vibe.md) · [VS Checklist](../../../references/vs-checklist-compact.md) · [Verification Checklist](../../../references/verification-checklist.md) · [Subtask Design Patterns](../../../references/subtask-design-patterns.md)
