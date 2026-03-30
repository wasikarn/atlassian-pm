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

**Role:** PO + TA Combined
**Output:** User Story + Sub-tasks (complete workflow)

## Mode Selection

| Flag | Behavior | User interactions |
| --- | --- | --- |
| *(none)* | **Vibe mode (default)** — auto-extract context, single-pass generation, no annotation rounds | 0–1 (only if description is ambiguous) |
| `--thorough` | **Thorough mode** — full interview gates, ITERATE annotation rounds (max 3), all REVIEW gates | Multiple checkpoints |
| `--no-subtasks` | **Story only** — stop after Phase 5 (Create Story); skip Phases 6–11 entirely. Use when subtasks will be added later via `/analyze-story`. | 0–1 |

> If the argument contains `--thorough`, strip the flag and treat the remaining text as the description. Proceed with thorough mode for all phases.
> If the argument contains `--no-subtasks`, strip the flag and treat the remaining text as the description. Run Phases 1–5 only, then jump to Phase 12 (Summary).

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Project Key:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['project_key'])"`

## Context Object (accumulated across phases)

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

> **Workflow Patterns:** See [workflow-compact.md](../../../references/workflow-compact.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Blueprint Handoff Check

**Goal:** Detect whether a `/blueprint` output is present in conversation history and pre-populate story context from it, skipping redundant interview steps.
**Required inputs:** Conversation history scan for `blueprint_backlog_map`; if present, user selection of story index (1-based)
**Constraints:** GATE — do not proceed past story selection without user confirm; if index invalid, re-display list
**Output:** `blueprint_page_id`, `selected_story_index`, `blueprint_acs_hints[]` added to context (or no-op if no blueprint in history)

> **Check first:** ดู conversation history ว่ามี `/blueprint` output หรือไม่

**If `blueprint_backlog_map` is present in history:**

**Step 1 — แสดง story list:**
แสดง stories จาก blueprint เป็น numbered list (1-based) ให้ user เลือก:

```text
Blueprint stories:
1. [stories[0].title] — [stories[0].vs_label] ([stories[0].sp_estimate])
2. [stories[1].title] — [stories[1].vs_label] ([stories[1].sp_estimate])
...
```

Ask: "ต้องการสร้าง story ข้อไหน? (ระบุหมายเลข)"

- ถ้า index ไม่มีใน list → แสดง list ใหม่ให้ user เลือกอีกครั้ง

**Step 2 — Extract selected story (stories[N-1] where N = user's 1-based choice):**

- `stories[N-1].title` → ใช้เป็น story summary draft
- `stories[N-1].narrative_hint` → เริ่ม narrative จาก hint นี้
- `stories[N-1].acs_hint[]` → ใช้เป็น starting points สำหรับ ACs
- `stories[N-1].vs_label` → pre-assign VS label
- `stories[N-1].sp_estimate` → suggest SP (S/M/L)
- `blueprint_page_id` (ถ้ามี) → link ใน story description "References"
- ถ้า field ใด missing → ข้ามการ populate field นั้น

**Step 3 — Confirm before proceeding:**
แสดง summary:
> "Story: [title] | VS: [vs_label] | SP: [sp_estimate]\nใช้ข้อมูลจาก blueprint สำหรับ story นี้ confirm?"

**⛔ GATE** — รอ user confirm ก่อนดำเนินต่อ

**In Phase 1 (Discovery):**

- ✅ ยังคง fetch epic via direct MCP calls ถ้า epic key ใน blueprint → ได้ `epic_data`:

  ```text
  MCP: cache_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")
  → fallback: jira_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")
  MCP: jira_search(jql="parent = EPIC-KEY", fields="summary,status,issuetype", limit=10)
  ```

- ❌ ข้าม interview questions (Who/What/Why/Constraints) — มีข้อมูลจาก blueprint แล้ว
- ❌ ข้าม VS assignment question — ใช้ `vs_label` จาก blueprint แทน

ดำเนินต่อ Phase 2 Write User Story โดยใช้ blueprint context เป็น draft

**If no blueprint in history:** ดำเนิน Phase 1 Discovery ตามโหมดที่เลือก

## Part A: Create Story (Phases 1-5)

---

### 1. Discovery

**Goal:** Establish Epic context, domain knowledge, and user intent before writing the story.

---

#### Vibe Mode (Default)

**Required inputs:** description argument (auto-parsed), epic key if provided in argument
**Constraints:** Only ask a question if description < 10 words with no inferrable context; otherwise proceed automatically
**Output:** `epic_data`, `vs_assignment`, `user_requirements`, `user_context` inferred from description

**Auto-extract from argument description:**

- Parse description to infer: persona, action, benefit, affected services
- If Epic key in argument → fetch epic via MCP to enrich context
- If description < 10 words with no context → ask ONE question: "Tell me more about this feature"
- Otherwise → proceed directly to Phase 2 with inferred context
- **VS Assignment:** auto-assign based on services mentioned in description (`[BE]` mentions → vs2, `[FE]` mentions → vs2, both → vs2-e2e)

If Epic key provided → direct MCP calls (🟢 PARALLEL with Confluence search):

```text
MCP: cache_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")
→ fallback: jira_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")
MCP: jira_search(jql="parent = EPIC-KEY", fields="summary,status,issuetype", limit=10)
```

**Epic Readiness Pre-check (🟢 AUTO):** After epic fetch, run quality checks:

| Check | Pass Condition | If Fail |
| --- | --- | --- |
| ACs defined | Epic description contains ≥ 3 AC lines or bullet points | Warn only — continue |
| SP estimated | `customfield_10016` is set (not null/0) | Warn only — continue |
| No blockers | No linked issues with type "Blocks" in Open/In Progress status | Warn only — continue |

In vibe mode, epic quality warnings are shown but never block progress.

**Confluence Domain Knowledge (🟢 AUTO — non-blocking):**

```text
MCP: cache_search_confluence(query="[story_keywords]", space_key="<space_key>", limit=3)
```

If relevant pages found → extract key sections and store as `domain_context` for Phase 2. If not found → skip silently.

---

#### --thorough Mode

**Required inputs:** epic_key (ask if missing), user answers to Who / What / Why / Constraints, VS assignment
**Constraints:** GATE — do not proceed without user confirmation of requirements + VS assignment; skip interview questions if blueprint context is present
**Output:** `epic_data`, `vs_assignment`, `user_requirements`, `user_context`, and optional `domain_context` available for Phase 2

- Ask: Who? What? Why? Constraints?
  - **Story Context:** What is the user currently doing? What's difficult? (for 📍 context line)
- If Epic exists → direct MCP calls:

  ```text
  MCP: cache_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")
  → fallback: jira_get_issue(issue_key="EPIC-KEY", fields="summary,description,customfield_10016,status,issuetype,labels")
  MCP: jira_search(jql="parent = EPIC-KEY", fields="summary,status,issuetype", limit=10)
  ```

**Epic Readiness Pre-check (🟢 AUTO — runs after epic fetch, before GATE):**

| Check | Pass Condition | If Fail |
| --- | --- | --- |
| ACs defined | Epic description contains ≥ 3 AC lines or bullet points | Warn — story ACs will be vague |
| SP estimated | `customfield_10016` is set (not null/0) | Warn — story estimation reference missing |
| No blockers | No linked issues with type "Blocks" in Open/In Progress status | Warn — story may be blocked before dev starts |

**If 1+ checks fail:** Show warning table to user:

```text
⚠️ Epic Readiness Warning
Epic {{PROJECT_KEY}}-XXX has quality gaps that may affect this story:
  ❌ No SP estimate — consider /refine-epic {{PROJECT_KEY}}-XXX first
  ❌ Only 1 AC defined — story ACs will be weak
Proceed anyway? (y = continue, n = stop and fix epic first)
```

**⛔ GATE if ≥ 2 checks fail** — require explicit user `y` before continuing.
**🟡 REVIEW if 1 check fails** — show warning, continue if user doesn't object within 10s.

- **VS Assignment:** Which vertical slice? (`vs1-skeleton`, `vs2-*`, `vs-enabler`)

**Confluence Domain Knowledge (🟢 AUTO — non-blocking):**

> **🟢 PARALLEL** — Epic MCP fetch and `cache_search_confluence` can run simultaneously.

```text
MCP: cache_search_confluence(query="[story_keywords]", space_key="<space_key>", limit=3)
```

- **⛔ GATE — DO NOT PROCEED** without user confirmation of requirements + VS assignment.

---

### 2. Write User Story

**Goal:** Produce a well-formed story narrative, acceptance criteria, scope, and DoD.

---

#### Vibe Mode (Default)

**Required inputs:** `epic_data`, inferred `user_requirements`, `vs_assignment` from Phase 1
**Constraints:** Single pass — generate story with best judgment, show to user as information only (no gate)
**Output:** `story_narrative`, `acs[]`, `scope`, `dod` ready for INVEST validation

```text
📍 [User's current situation — what they're doing, what's difficult]  ⚡ optional
As a [persona],
I want to [action],
So that [benefit].
```

- ⚡ **Context line:** Include when persona is new or workflow is complex — not needed for every story
- Define ACs, Scope, DoD
- **AC Naming:** Use `AC{N}: [Verb] — [Scenario Name]` (not just "AC1: Title")
- **VS Check:** Story delivers e2e value? All layers touched? (not shell-only)

**📐 Technical Notes (⚡ populate if `domain_context` from Phase 1 exists):**

Include the optional `📐 Technical Notes` section in the story ADF when domain context is available.

Leave `Key files:` blank at this stage — it will be filled post-Phase 7 exploration if needed.

> Show the generated story to the user as information. Proceed immediately to Phase 3 (no approval gate).

---

#### --thorough Mode

**Required inputs:** `epic_data`, `user_requirements`, `vs_assignment` from Phase 1
**Constraints:** ITERATE gate — max 3 annotation rounds; if no consensus after 3 rounds escalate to `/blueprint`
**Output:** `story_narrative`, `acs[]`, `scope`, `dod` approved and ready for INVEST validation

```text
📍 [User's current situation — what they're doing, what's difficult]  ⚡ optional
As a [persona],
I want to [action],
So that [benefit].
```

- ⚡ **Context line:** Include when persona is new or workflow is complex — not needed for every story
- Define ACs, Scope, DoD
- **AC Naming:** Use `AC{N}: [Verb] — [Scenario Name]` (not just "AC1: Title")
- **VS Check:** Story delivers e2e value? All layers touched? (not shell-only)

**📐 Technical Notes (⚡ populate if `domain_context` from Phase 1 exists):**

Include the optional `📐 Technical Notes` section in the story ADF when domain context is available. Populate from:

- `domain_context` — business rules, API contracts, constraints extracted from Confluence in Phase 1
- Epic technical notes (if epic description has architectural guidance)

Leave `Key files:` blank at this stage — it will be filled post-Phase 7 exploration if needed.

- **🔄 ITERATE** — Present story draft as plan card (narrative, ACs, scope, DoD). Ask: Approve / Annotate / Major rework.
  - Annotate → user specifies items to change → revise ONLY those items → re-present (max 3 rounds)
  - Approve → proceed to INVEST validation
  - Major rework → back to Discovery
  - See [Annotation Cycle](../../../references/workflow-patterns.md#annotation-cycle-iterate-gate)

---

### 3. INVEST + VS Validation

**Goal:** Verify the story meets all six INVEST criteria and delivers a true vertical slice before any Jira write.
**Required inputs:** `story_narrative`, `acs[]`, `scope` from Phase 2
**Constraints:** AUTO — auto-fix if any criterion fails; escalate to user only if unfixable after 2 attempts; do NOT create story if INVEST fails
**Output:** `invest_score`, `vs_validated`; story ready for QG if all criteria pass

- [ ] **I**ndependent - Not dependent on other stories
- [ ] **N**egotiable - Room for discussion
- [ ] **V**aluable - Clear business value
- [ ] **E**stimable - Can estimate effort
- [ ] **S**mall + **Vertical** - Completable in 1 sprint? **End-to-end slice?**
- [ ] **T**estable - All ACs verifiable in isolation

**VS Anti-pattern Check:**

- ❌ Shell-only (UI has no logic) → Add minimal happy path
- ❌ Layer-split (BE separated from FE) → Combine into single story

**🟢 AUTO** — Validate all criteria. If any fail or VS anti-pattern detected → auto-fix and re-validate. Escalate to user only if unfixable.

### 4. Quality Gate — Story (HR1)

**Goal:** Ensure story ADF JSON meets ≥ 90% quality score before any Jira write.
**Required inputs:** story content from Phase 2-3, `artifacts_dir` path
**Constraints:** HR1 — NEVER send story to Atlassian without QG ≥ 90%; AUTO — score → auto-fix → re-score; escalate only if still < 90% after 2 attempts
**Output:** `story_adf_json` at `{{artifacts_dir}}/story.json`, `story_qg_score`; PASS status required to proceed to Phase 5

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate to user only if still < 90% after 2 attempts.
> HR1: DO NOT send Story to Atlassian without QG ≥ 90%.
> **⚠️ MANDATORY:** Read `references/templates-story.md` before generating any ADF. Use `panel` nodes — NEVER use `heading` nodes in issue descriptions.

1. Generate ADF JSON → `{{artifacts_dir}}/story.json`

2. **Pre-QG polish + subtask suggestions (🟢 PARALLEL):**

   > **🟢 PARALLEL** — Launch both simultaneously (single Bash call via `parallel_runner.py`). They share no state: polish reads `story.json`, suggest reads ACs text from Phase 2 context.

   ```bash
   python3 scripts/ai/parallel_runner.py
   ```

   Or invoke directly as two independent Bash calls in the same message:
   - `python3 scripts/ai/pre_qg_polish.py --file {{artifacts_dir}}/story.json --type story` → overwrites `story.json` with polished ADF
   - `python3 scripts/ai/suggest_subtasks.py --story {{story_key_placeholder}} --acs "{{acs_text}}"` → stdout JSON array of suggested subtask summaries (store as `suggested_subtasks[]` for Phase 8 reference)

   Both are optional/non-blocking: if either exits 1 (claude unavailable), continue with existing content.

3. **Quick structural pre-check (🟢 AUTO):**

   ```bash
   python3 scripts/ai/qg_quick.py --file {{artifacts_dir}}/story.json --type story
   ```

   Returns `{quick_pass, structural_issues[], content_issues[], ac_count, score_estimate, skip_full_agent}`.

   - If `skip_full_agent: true` (score_estimate ≥ 95, no issues) → skip Step 4, proceed to Phase 5 directly
   - If `structural_issues[]` not empty → apply QUIRK fixes (panelType, empty paragraphs) inline before Step 4
   - If `quick_pass: false` AND `score_estimate < 70` → show issues to user, offer: "Fix now or proceed to full QG?"
   - Otherwise → continue to Step 4 (full agent)

   Non-blocking: if `qg_quick.py` exits 1 (claude unavailable or parse error) → skip pre-check, go straight to Step 4.

4. **QG Scoring (🟢 AUTO):**

   ```bash
   uv run scripts/api/validate_adf.py {{artifacts_dir}}/story.json --type story --json
   ```

   Returns `{score, status, issues[{id, status, message}]}`. Score ≥ 90 = PASS.
   If FAIL → check `issues[]` for auto-fixable items → run `--fix` to apply → re-score. Max 1 fix cycle.

### 5. Create Story in Jira

**Goal:** Persist the approved, QG-passed story to Jira and set estimation fields.
**Required inputs:** `story_adf_json` (QG PASS from Phase 4), SP estimate, size, start/due dates
**Constraints:** HR1 — only execute if QG passed; HR6 — `cache_invalidate(story_key)` after create AND after field update; AUTO — no user interaction needed if Phase 4 passed
**Output:** `story_key` (ABC-XXX) captured in context; estimation fields set; QG score recorded to history

> **🟢 AUTO** — If Phase 4 QG passed → create automatically. No user interaction needed.

```bash
acli jira workitem create --from-json {{artifacts_dir}}/story.json
```

**Labels (MANDATORY):** Feature label + VS label (e.g., `coupon-web`, `vs2-collect-e2e`)

Capture story key → ABC-XXX

> **🟢 AUTO** — HR6: `cache_invalidate(story_key)` after create.
> **🟢 AUTO** — Record QG score to history (uses `story_qg_score` from Phase 4 context). Run: `python scripts/qg_record.py --issue-key "ABC-XXX" --type Story --score STORY_QG_SCORE --status PASS --service "SERVICE_TAG"`. Replace ABC-XXX with actual story key, STORY_QG_SCORE with numeric score, SERVICE_TAG with service label (e.g. `[BE]`, `[FE-Admin]`, or empty if mixed). If QG failed and story was not created, record with `--status FAIL --checks-failed "FAILED_IDS"` for learning.

**Set story estimation fields:**

```text
MCP: jira_update_issue(issue_key="ABC-XXX", additional_fields={
  "customfield_10016": <SP>,                  # Story Points (XS=1,S=2,M=3,L=5,XL=8)
  "customfield_10107": {"value": "<SIZE>"},   # Size
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",          # Start Date
  "duedate": "YYYY-MM-DD"                     # Due Date
})
```

> **🟢 AUTO** — HR6: `cache_invalidate(story_key)` after field update.
> **`--no-subtasks` exit point:** If `--no-subtasks` flag was passed → skip Part B entirely. Jump to Phase 12 Summary with `subtask_keys[] = []`.

## Part B: Create Sub-tasks (Phases 6-12)

> **Skip entirely if `--no-subtasks`** — proceed directly to Phase 12.

---

### 6. Impact Analysis

**Goal:** Identify which services are affected by the story and confirm the VS integrity before exploring the codebase.
**Required inputs:** `story_key`, `story_narrative`, `acs[]` from Phase 2

---

#### Vibe Mode (Default)

**Constraints:** AUTO — infer impact from story description and VS assignment; proceed automatically
**Output:** `services_impacted[]`, `vs_verified`

| Service | Impact | Reason |
| --- | --- | --- |
| Backend | ✅/❌ | [why] |
| Admin | ✅/❌ | [why] |
| Website | ✅/❌ | [why] |

**VS Verification:** Story touches all layers for e2e slice? (not layer-only)

> **🟢 AUTO** — Infer services from story narrative and VS assignment. Proceed to Phase 7 automatically. Show impact table as information only.

---

#### --thorough Mode

**Constraints:** REVIEW gate — present impact table to user and proceed unless user objects; flag shell-only anti-pattern (FE-only impact with no BE) for user confirmation
**Output:** `services_impacted[]`, `vs_verified`; impact table approved before Phase 7 exploration begins

| Service | Impact | Reason |
| --- | --- | --- |
| Backend | ✅/❌ | [why] |
| Admin | ✅/❌ | [why] |
| Website | ✅/❌ | [why] |

**VS Verification:** Story touches all layers for e2e slice? (not layer-only)

**🟡 REVIEW** — Present impact table + VS verification to user. Proceed unless user objects.

---

### 7. Codebase Exploration ⚠️ MANDATORY

**Goal:** Locate the exact file paths, patterns, and dependencies in each impacted service that the subtask designs will reference.
**Required inputs:** `services_impacted[]` from Phase 6, service repo paths from `project-config.json`
**Constraints:** Generic paths are REJECTED — re-explore max 2 attempts; validate all paths with Glob; launch **1 Explore agent** covering all impacted services; do NOT design subtasks without concrete file evidence

**Output:** `file_paths[]`, `patterns[]`, `dependencies[]` per service; all paths validated and ready for Phase 8 design

> ⚡ If user has provided file paths in requirements → skip Phase 7 (add `--skip-explore` flag to command)
> Launch 1 Explore agent covering all impacted services.
> Validate paths with Glob. Generic paths REJECTED. Re-explore max 2 attempts.
> See [shared-references/subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for codebase exploration requirements, scope format, AC specificity, alignment check, and QG subtasks.

Each Explore agent **must** return results using this structure (used to validate before proceeding):

```text
SERVICE: [BE|FE-Admin|FE-Web|Shared]
CONFIDENCE: [HIGH|MEDIUM|LOW]
FILES:
- [full/absolute/path/to/file.ts]  # action: CREATE|MODIFY|REF
- [full/absolute/path/to/file.ts]  # action: MODIFY
PATTERNS: [brief description of relevant patterns found]
DEPENDENCIES: [key imports or shared modules identified]
```

**Validation rules (apply before passing to Phase 8):**

| Condition | Action |
|---|---|
| `CONFIDENCE: LOW` | REJECTED — re-explore this service (max 2 attempts total) |
| Any path is a top-level glob (`src/...` without full path) | REJECTED — re-explore |
| Any path fails `Glob` validation | REJECTED — re-explore |
| `FILES:` section is empty | REJECTED — re-explore |
| All services return `CONFIDENCE: HIGH` or `MEDIUM` with valid paths | ✅ Proceed to Phase 8 |

### 8. Design + Estimation

**Goal:** Produce concrete subtask plan cards (tag, scope files, ACs, OE) then calibrate SP estimates against historical data.
**Required inputs:** `file_paths[]`, `patterns[]`, `dependencies[]` from Phase 7; `acs[]` from Phase 2

---

#### Vibe Mode (Default)

**Constraints:** Single pass — generate subtask designs with Implementation Hints populated from Phase 7 results; show designs as information only (no annotation gate)
**Output:** `subtask_designs[]` with calibrated SP values; ready for Phase 9 alignment check

**Tech Lead Decomposition — dependency ordering:** See [analyze-story/SKILL.md](../analyze-story/SKILL.md) for TL decomposition ordering.

- 1 sub-task per service boundary (split only if complexity warrants)
- **VS Integrity:** Each subtask contributes to VS completion (not horizontal layer)
- Summary: `[TAG] - Description`
- ACs: Thai narrative + English technical terms

**Implementation Hints (🟢 AUTO — MANDATORY in vibe mode):**

Include Section 4 Implementation Hints in every subtask ADF. Populate from Phase 7 exploration results:

| Field | Source |
| --- | --- |
| Entry Point | First CREATE file from scope table for this service |
| Pattern to Follow | First REF file from scope table |
| Test Command | Project's test command scoped to the new file (e.g., `node ace test --files "tests/unit/..."`) |
| Related API | Any HTTP endpoint found in exploration (BE subtasks only) |
| Dependencies | Key imports/services found in exploration (from REF file's constructor signature) |

See [templates-vibe.md](../../../references/templates-vibe.md) for the full ADF JSON structure and Claude Code Prompt format.

**Estimation Calibration (🟢 AUTO + PARALLEL):** Launch all estimation-calibrator agents simultaneously — one per subtask. Apply recommendation if confidence is HIGH or MEDIUM; skip if LOW.

For each subtask in the current design (all in parallel):

```text
Agent(name: "estimation-calibrator"):
  story_summary: [subtask summary]
  service_tag: [BE/FE-Admin/FE-Web]
  initial_sp: [SP from design]
  scope_file_count: [count of CREATE+MODIFY rows in scope table]
  ac_count: [number of ACs in subtask design]
```

If recommendation differs from initial estimate AND confidence ≥ MEDIUM:

- Update subtask SP to recommended value
- Note in plan card: "SP adjusted [M→L] based on historical pattern: [reason from calibrator]"

If LOW confidence: keep initial estimate, note "insufficient historical data for calibration".

> Show subtask designs to the user as information. Proceed immediately to Phase 9 (no approval gate).

---

#### --thorough Mode

**Constraints:** ITERATE gate — max 3 annotation rounds; major rework returns to Phase 7; 1 subtask per service boundary unless complexity warrants more; VS integrity required (no horizontal layer subtasks)
**Output:** `subtask_designs[]` with calibrated SP values approved by user; ready for Phase 9 alignment check

**Tech Lead Decomposition — dependency ordering:** See [analyze-story/SKILL.md](../analyze-story/SKILL.md) for TL decomposition ordering.

- 1 sub-task per service boundary (split only if complexity warrants)
- **VS Integrity:** Each subtask contributes to VS completion (not horizontal layer)
- Summary: `[TAG] - Description`
- ACs: Thai narrative + English technical terms

**Estimation Calibration (🟢 AUTO + PARALLEL):** Launch all estimation-calibrator agents simultaneously — one per subtask. Apply recommendation if confidence is HIGH or MEDIUM; skip if LOW.

For each subtask in the current design (all in parallel):

```text
Agent(name: "estimation-calibrator"):
  story_summary: [subtask summary]
  service_tag: [BE/FE-Admin/FE-Web]
  initial_sp: [SP from design]
  scope_file_count: [count of CREATE+MODIFY rows in scope table]
  ac_count: [number of ACs in subtask design]
```

If recommendation differs from initial estimate AND confidence ≥ MEDIUM:

- Update subtask SP to recommended value
- Note in plan card: "SP adjusted [M→L] based on historical pattern: [reason from calibrator]"

If LOW confidence: keep initial estimate, note "insufficient historical data for calibration".

- **🔄 ITERATE** — Present subtask design as plan cards (tag, scope files, ACs, OE per subtask). Ask: Approve all / Annotate (specify subtask #) / Major rework.
  - Annotate → user specifies subtask + notes → revise ONLY annotated subtasks → re-present (max 3 rounds)
  - Approve → proceed to Alignment Check
  - Major rework → back to Codebase Exploration
  - See [Annotation Cycle](../../../references/workflow-patterns.md#annotation-cycle-iterate-gate)

---

### 9. Alignment Check

**Goal:** Verify that subtask ACs collectively cover all story ACs and that scope tables are consistent with codebase exploration findings.
**Required inputs:** `subtask_designs[]` from Phase 8, `acs[]` from Phase 2, `file_paths[]` from Phase 7
**Constraints:** AUTO — auto-fix misalignment; escalate only if unfixable; all story ACs must be traceable to at least one subtask AC
**Output:** `alignment_checklist` with PASS status; subtask designs corrected and ready for QG

> **🟢 AUTO** — Verify programmatically. Auto-fix misalignment. Escalate only if unfixable.
> See [shared-references/subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for codebase exploration requirements, scope format, AC specificity, alignment check, and QG subtasks.

### 10. Quality Gate — Subtasks (MANDATORY)

**Goal:** Ensure all subtask ADF JSON files meet ≥ 90% quality score before creating in Jira.
**Required inputs:** `subtask_designs[]` (aligned, from Phase 9), `artifacts_dir` path
**Constraints:** HR1 — NEVER create subtasks in Jira without QG ≥ 90%; AUTO — score → auto-fix → re-score; escalate only if still < 90% after 2 attempts
**Output:** `qg_score`, `passed_qg`; subtask ADF JSON files at `{{artifacts_dir}}/subtask-*.json` ready for Phase 11

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT create subtasks in Jira without QG ≥ 90%.
> See [shared-references/subtask-design-patterns.md](../../../references/subtask-design-patterns.md) for codebase exploration requirements, scope format, AC specificity, alignment check, and QG subtasks.

For each subtask file:

```bash
uv run scripts/api/validate_adf.py {{artifacts_dir}}/subtask-*.json --type subtask --json
```

### 11. Create Sub-tasks

**Goal:** Create all subtask shells in Jira, verify parent linkage, set dates/OE, and update descriptions — fully automated.
**Required inputs:** `story_key` (parent), subtask ADF JSON files (QG PASS from Phase 10), date range from Phase 5 story fields
**Constraints:** HR5 — two-step create + verify parent; HR6 — `cache_invalidate` after every write; HR8 — subtask dates within parent range; HR10 — NEVER set sprint on subtasks; HR3 — use acli for assignee; escalate only if parent verify fails after retry
**Output:** `subtask_keys[]`; all subtasks created, parent-verified, dated, described, and QG scores recorded

> **🟢 AUTO** — Create → verify parent → edit descriptions. All automated. Escalate only if parent verify fails after retry.
> HR5: Two-Step + Verify Parent. acli does not support the parent field. MCP may silently ignore parent.
> [Two-Step Subtask](../../../references/workflow-patterns.md#two-step-subtask-creation): MCP create shell → verify parent → acli edit. Batch ≥3: create all → verify all → edit all.

```text
# Step 1: Create shells (parallel)
MCP: jira_create_issue({project_key: "<project_key>", summary:"[BE] - ...", issue_type:"Subtask", additional_fields:{parent:{key:"ABC-XXX"}, timetracking:{originalEstimate:"4h"}}})
MCP: jira_create_issue({project_key: "<project_key>", summary:"[FE-Web] - ...", issue_type:"Subtask", additional_fields:{parent:{key:"ABC-XXX"}, timetracking:{originalEstimate:"4h"}}})

# Step 2: Verify parent (HR5) — DO NOT SKIP
MCP: jira_get_issue(issue_key: "ABC-YYY", fields: "parent") → confirm parent.key = "ABC-XXX"
MCP: jira_get_issue(issue_key: "ABC-ZZZ", fields: "parent") → confirm parent.key = "ABC-XXX"
# If parent missing → fix via REST API before continuing

# Step 3: Set subtask dates + OE (HR8 alignment — dates must be within parent range)
MCP: jira_update_issue(issue_key="ABC-YYY", additional_fields={
  "timetracking": {"originalEstimate": "<N>h"},
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",  # Start Date (≥ parent start)
  "duedate": "YYYY-MM-DD"             # Due Date (≤ parent due)
})
# ⚠️ HR10: NEVER set sprint on subtasks — inherits from parent
# ⚠️ HR8: Distribute subtask dates evenly within parent date range

# Step 4: Update descriptions
acli jira workitem edit --from-json {{artifacts_dir}}/subtask-be.json --yes
acli jira workitem edit --from-json {{artifacts_dir}}/subtask-fe.json --yes
```

> **🟢 AUTO** — HR6: `cache_invalidate(subtask_key)` after EVERY Atlassian write.
> **🟢 AUTO** — HR3: If assignee needed, use `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).
> **🟢 AUTO** — Record subtask QG scores to history (uses `qg_score` and `passed_qg` from Phase 10 context). For each service tag in the subtask batch: `python scripts/qg_record.py --issue-key "ABC-XXX" --type Subtask --score QG_SCORE --status PASS --service "[SERVICE_TAG]" --checks-failed "FAILED_IDS_IF_ANY"`. Use parent story key as `--issue-key` if subtask key not yet assigned.

### 12. Summary

**Goal:** Present the completed workflow result, delegation view, and suggest next actions.
**Required inputs:** `story_key`, `subtask_keys[]` from Phase 11
**Constraints:** None
**Output:** Completion summary with story + subtask keys, Claude Code Prompt per subtask, and suggested follow-up commands

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

> Column source: Assignee from `project-config.json` team roster · Subtask key from Phase 11 · Claude Code Prompt verbatim from Implementation Hints note panel.

See [references/decision-guide.md](references/decision-guide.md) for when to use /create-story vs /analyze-story.

See [references/examples.md](references/examples.md) for a full input/output example.

## Examples

### Good

```text
/create-story "coupon redemption at checkout for logged-in users"   # vibe mode — auto-extracts persona + feature, 0 questions
/create-story "video upload progress indicator for content creators" # vibe mode — persona + feature area, straight to phases
/create-story                                                        # after /blueprint output in history → picks up blueprint_backlog_map, skips interview
/create-story "password reset via SMS OTP"                          # small, testable scope → INVEST passes cleanly
/create-story --thorough "new payment gateway integration"          # complex feature — use thorough mode for full interview + annotation
/create-story --no-subtasks "payment refund flow"                   # story only — add subtasks later via /analyze-story
สร้าง story สำหรับ Google SSO ไม่ต้องสร้าง subtask ก่อน            # natural language with --no-subtasks intent
```

### Bad

```text
/create-story {{PROJECT_KEY}}-123                    # passing existing issue key — story already exists; use /analyze-story {{PROJECT_KEY}}-123 instead
/create-story "authentication"           # too vague AND < 10 words no context → will ask ONE clarifying question
/create-story "redesign entire checkout" # scope too large → INVEST Small check fails, needs epic decomposition first
/create-story "add feature"             # no context → will ask ONE clarifying question; run /blueprint first for complex features
```

**Common mistakes:**

- Passing a Jira issue key (e.g. `{{PROJECT_KEY}}-123`) — that story already exists; use `/analyze-story` to add subtasks to it instead.
- Skipping `/blueprint` for complex features with multiple stories — without blueprint context the Discovery phase must interview from scratch every time, and VS assignment is error-prone.
- Using `/create-story` when no epic exists and the feature spans multiple vertical slices — create the epic first (`/create-epic`) so the story has a parent and VS labels to anchor to.
- Confusing this skill with `/analyze-story` — `/create-story` creates a brand-new story + subtasks end-to-end; `/analyze-story` works on an existing story that already has a Jira key.
- Using `--thorough` for simple, well-described features — vibe mode produces the same quality output with less friction.

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[ADF Core Rules](../../../references/templates-core.md) · [Story Template](../../../references/templates-story.md) · [Subtask Template](../../../references/templates-subtask.md) · [Vibe Mode Templates](../../../references/templates-vibe.md) · [VS Checklist](../../../references/vs-checklist-compact.md) · [Verification Checklist](../../../references/verification-checklist.md) · [Subtask Design Patterns](../../../references/subtask-design-patterns.md)
