---
name: create-epic
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__confluence_create_page, mcp__mcp-atlassian__confluence_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Create Epic + Epic Doc — vibe mode by default (fast, no ceremony)
  Use --thorough for full interview + RICE scoring + annotation workflow

  Triggers: "create epic", "new epic", "new initiative", "product vision", "RICE", "สร้าง epic"
  Use when: creating a NEW Epic from a product vision or initiative idea
  Do NOT use for: stories or subtasks (use create-story); updating an existing epic (use update-epic)
argument-hint: "[--thorough | --no-doc] [epic-title]"
effort: medium
---

# /create-epic

**Role:** Senior Product Manager
**Output:** Epic in Jira + Epic Doc in Confluence

## Mode Selection

| Flag | Behavior | User interactions |
| --- | --- | --- |
| *(none)* | **Vibe mode (default)** — auto-extract context, skip RICE, single-pass scope, no annotation rounds | 0–1 (only if description is ambiguous) |
| `--thorough` | **Thorough mode** — full stakeholder interview, RICE scoring, ITERATE on scope (max 3 rounds) | Multiple checkpoints |
| `--no-doc` | **Epic only** — skip Confluence Doc creation (Phase 5 step 1). Creates Epic in Jira only. | 0–1 |

> If the argument contains `--thorough`, strip the flag and treat the remaining text as the description. Proceed with thorough mode for all phases.
> If the argument contains `--no-doc`, strip the flag. Run all phases normally but skip Confluence doc creation in Phase 5.

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 0. Blueprint (optional) | `blueprint_page_id`, `blueprint_url`, `blueprint_stories[]` |
| 1. Discovery | `stakeholder_input`, `problem_narrative`, `vs_plan`, `user_requirements` |
| 2. RICE | `rice_score`, `priority` |
| 3. Scope | `scope_items[]`, `vs_stories[]`, `mvp_definition` |
| 4. QG | `qg_score`, `passed_qg` |
| 5. Create | `epic_key`, `epic_doc_id` |

> **Workflow Patterns:** See [workflow-compact.md](../../../references/workflow-compact.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Blueprint Handoff Check

> **Check first:** ดู conversation history ว่ามี `/blueprint` output หรือไม่

**If `blueprint_backlog_map` is present in history:**

Extract from blueprint output:

- `epic.title` → ใช้เป็น epic title (ข้ามการถามจาก user)
- `stories[]` → เก็บเป็น `vs_stories[]` สำหรับ Phase 3
- `non_goals[]` → เก็บเป็น out-of-scope items สำหรับ Phase 3 scope definition
- `blueprint_page_id` → link ใน Epic Doc section "References"

Skip interview questions in Phase 1 for information already documented.
แสดง summary ให้ user confirm:
> "พบ blueprint: [Feature Name] — ใช้ข้อมูลจาก blueprint สำหรับ epic นี้ confirm?"

**⛔ GATE** — รอ user confirm ก่อนดำเนินต่อ

**If no blueprint in history:** ดำเนิน Phase 1 Discovery ปกติ


## Phases

### 1. Discovery

#### Vibe Mode (Default)

- Auto-extract from description + blueprint (if available):
  - **Narrative Arc:** Infer `[Current situation] → [Problem] → [This Epic solves it by...]` from description
  - **VS Planning:** Auto-identify vertical slices from description keywords
- If existing docs available → read context silently
- Ask only if description is too vague to infer problem narrative (max 1 question)
- **No GATE** — proceed to Phase 2 immediately

#### --thorough Mode

- Interview stakeholder:
  - **Problem narrative:** What is the current situation? What is the problem? What happens if we don't act?
  - Target users? Business value? Success metrics?
- If existing docs available → read context
- **Narrative Arc:** Summarize as `[Current situation] → [Problem] → [This Epic solves it by...]`
- **VS Planning:** Identify potential vertical slices (what distinct user flows exist?)
- **⛔ GATE — DO NOT PROCEED** without stakeholder confirmation of problem narrative + VS planning.

### 2. RICE Prioritization

#### Vibe Mode (Default)

- **Skip entirely** — RICE scoring requires stakeholder data that isn't available yet. Score later when there's real usage data.
- Proceed directly to Phase 3.

#### --thorough Mode

- **R**each (1-10): Number of users affected
- **I**mpact (0.25-3): Level of impact on user
- **C**onfidence (0-100%): Confidence in estimate
- **E**ffort (person-weeks): Effort required
- Formula: `(R × I × C) / E`
- **🟡 REVIEW** — Present RICE scoring to stakeholder. Proceed unless stakeholder objects.

### 3. Define Scope + VS Planning

> **If `vs_stories[]` pre-populated from blueprint:** ข้าม VS derivation — ใช้ `vs_stories[]` จาก blueprint โดยตรง แสดงให้ user confirm แทน
> **If `non_goals[]` present from blueprint:** ใช้เป็น out-of-scope items ใน scope definition (ไม่ต้องถามใหม่)

#### Vibe Mode (Default)

- Auto-generate scope from description + narrative arc:
  - Identify high-level requirements
  - Auto-select VS pattern based on description complexity
  - Break into User Stories by VS (max 5 stories)
  - Auto-define MVP boundary (all stories = MVP unless description implies phases)
- **No ITERATE** — single-pass generation, proceed to QG immediately

#### --thorough Mode

- Identify high-level requirements
- **VS Pattern Selection:** (see [vertical-slice-guide.md](../../../references/vertical-slice-guide.md))
  - Walking Skeleton? → `vs1-skeleton`
  - Enablers needed? → `vs-enabler`
  - Business rule splits? → `vs2-*`, `vs3-*`
- Break into User Stories by VS (draft):
  - vs1-skeleton: Story A, Story B
  - vs2-{rule}: Story C, Story D
- Define MVP: Which VS are must-have vs nice-to-have?
- Identify Dependencies and Risks
- **🔄 ITERATE** — Present scope + VS plan + MVP as plan cards (stories grouped by VS, in/out scope). Ask: Approve / Annotate / Major rework.
  - Annotate → stakeholder specifies items to change (add/remove stories, adjust VS, change MVP boundary)
  - Approve → proceed to Quality Gate
  - Major rework → back to Discovery
  - See [Annotation Cycle](../../../references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send Epic to Atlassian without QG ≥ 90%.
>
> [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Epic Quality X/4 | Overall X%`
>
> **🟢 AUTO (validate_adf.py):**
>
> ```bash
> uv run scripts/api/validate_adf.py {{artifacts_dir}}/epic.json --type epic --json
> ```
>
> Score ≥ 90 = PASS. If FAIL → check `issues[].fix_hint` → run `--fix` → re-score. Max 1 fix cycle.

### 5. Create Artifacts

> **🟢 AUTO** — If QG passed → create automatically. No user interaction needed.

1. **Epic Doc** → `MCP: confluence_create_page(space_key: "{{PROJECT_KEY}}")` *(skip if `--no-doc`)*
   - Include VS Map table in Epic Doc
2. **Epic** → `acli jira workitem create --from-json {{artifacts_dir}}/epic.json`
   - Add labels: feature label + `vs-planned`
3. **Link** Epic to Doc *(skip if `--no-doc`)*

> **🟢 AUTO** — HR6: `cache_invalidate(epic_key)` after create.

### 6. Handoff

```text
## Epic Created: [Title] ({{PROJECT_KEY}}-XXX)
RICE Score: X | Stories: N planned
Epic Doc: [link] | Epic: [link]
→ Use /create-story to continue
```

**`--no-doc` variant:**

```text
## Epic Created: [Title] ({{PROJECT_KEY}}-XXX)
Epic: [link]  (no Confluence doc)
→ /atlassian-pm:create-story     add stories under this epic
→ /atlassian-pm:create-doc {{PROJECT_KEY}}-XXX   create doc later if needed
```


## Epic Structure (ADF)

> See [references/epic-adf-structure.md](references/epic-adf-structure.md) for the full Epic ADF section layout and panel type reference.


## Examples

### ✅ Good

```text
/create-epic "Video Playback Quality Improvements"   # clear title seeds discovery with focused problem scope
/create-epic {{PROJECT_KEY}}-45                                  # existing epic key → reads current state, prompts for update scope
/create-epic "Multi-language subtitle support"       # after running /blueprint — picks up blueprint_backlog_map automatically
/create-epic "Offline Download Feature"              # triggers full 5-phase workflow: discovery → RICE → scope → QG → create
/create-epic --no-doc "Payment Refund Flow"          # epic in Jira only — skip Confluence doc
สร้าง epic สำหรับ feature X ไม่ต้องสร้าง doc ก่อน  # natural language with --no-doc intent
```

### ❌ Bad

```text
/create-epic                                         # no title → discovery phase asks generic questions, output is shallow
/create-epic "improve performance"                   # vague — no clear problem narrative, RICE scoring will be guesswork
/create-epic "Add dark mode toggle"                  # single-screen UI change → use /create-story directly, epic is overkill
/create-epic "{{PROJECT_KEY}}-50 fix scope"                     # updating an existing epic → use /update-epic {{PROJECT_KEY}}-50 instead
```

**Common mistakes:**

- Creating an epic for work that fits in 1-2 stories — epics represent multi-sprint initiatives; use `/create-story` for smaller scope.
- Skipping the RICE prioritization step by providing arbitrary scores — RICE requires stakeholder input on Reach and Confidence; guessing produces meaningless priority rankings.
- Creating an epic before running `/blueprint` for complex multi-service features — blueprint generates the VS plan and story breakdown that create-epic needs for Phase 3.
- Approving Phase 1 without confirming the narrative arc — vague problem statements propagate into the Epic Doc and make scope decisions in Phase 3 ambiguous.

## Example

> See [references/examples.md](references/examples.md) for a full input/output example.


## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)
## References

[ADF Core Rules](../../../references/templates-core.md) · [Epic Template](../../../references/templates-epic.md) · [Tool Selection](../../../references/tools.md) · [VS Checklist](../../../references/vs-checklist-compact.md) · [Epic ADF Structure](references/epic-adf-structure.md) · [Examples](references/examples.md)

After creation: `/verify-issue {{PROJECT_KEY}}-XXX`
