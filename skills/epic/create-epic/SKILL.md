---
name: create-epic
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__confluence_create_page, mcp__mcp-atlassian__confluence_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Create Epic + Epic Doc from product vision with a 6-phase PM workflow

  Triggers: "create epic", "new epic", "new initiative", "product vision", "RICE", "สร้าง epic"
  Use when: creating a NEW Epic from a product vision or initiative idea that needs RICE prioritization and a Confluence Epic doc
  Do NOT use for: stories or subtasks (use create-story); updating an existing epic (use update-epic)
argument-hint: "[epic-title]"
effort: medium
---

# /create-epic

**Role:** Senior Product Manager
**Output:** Epic in Jira + Epic Doc in Confluence

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 0. Blueprint (optional) | `blueprint_page_id`, `blueprint_url`, `blueprint_stories[]` |
| 1. Discovery | `stakeholder_input`, `problem_narrative`, `vs_plan`, `user_requirements` |
| 2. RICE | `rice_score`, `priority` |
| 3. Scope | `scope_items[]`, `vs_stories[]`, `mvp_definition` |
| 4. QG | `qg_score`, `passed_qg` |
| 5. Create | `epic_key`, `epic_doc_id` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

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

---

## Phases

### 1. Discovery

- Interview stakeholder:
  - **Problem narrative:** What is the current situation? What is the problem? What happens if we don't act?
  - Target users? Business value? Success metrics?
- If existing docs available → read context
- **Narrative Arc:** Summarize as `[Current situation] → [Problem] → [This Epic solves it by...]`
- **VS Planning:** Identify potential vertical slices (what distinct user flows exist?)
- **⛔ GATE — DO NOT PROCEED** without stakeholder confirmation of problem narrative + VS planning.

### 2. RICE Prioritization

- **R**each (1-10): Number of users affected
- **I**mpact (0.25-3): Level of impact on user
- **C**onfidence (0-100%): Confidence in estimate
- **E**ffort (person-weeks): Effort required
- Formula: `(R × I × C) / E`
- **🟡 REVIEW** — Present RICE scoring to stakeholder. Proceed unless stakeholder objects.

### 3. Define Scope + VS Planning

> **If `vs_stories[]` pre-populated from blueprint:** ข้าม VS derivation — ใช้ `vs_stories[]` จาก blueprint โดยตรง แสดงให้ user confirm แทน
> **If `non_goals[]` present from blueprint:** ใช้เป็น out-of-scope items ใน scope definition (ไม่ต้องถามใหม่)

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

> [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Epic Quality X/4 | Overall X%`

### 5. Create Artifacts

> **🟢 AUTO** — If QG passed → create automatically. No user interaction needed.

1. **Epic Doc** → `MCP: confluence_create_page(space_key: "{{PROJECT_KEY}}")`
   - Include VS Map table in Epic Doc
2. **Epic** → `acli jira workitem create --from-json {{artifacts_dir}}/epic.json`
   - Add labels: feature label + `vs-planned`
3. **Link** Epic to Doc

> **🟢 AUTO** — HR6: `cache_invalidate(epic_key)` after create.

### 6. Handoff

```text
## Epic Created: [Title] ({{PROJECT_KEY}}-XXX)
RICE Score: X | Stories: N planned
Epic Doc: [link] | Epic: [link]
→ Use /create-story to continue
```

---

## Epic Structure (ADF)

> See [references/epic-adf-structure.md](references/epic-adf-structure.md) for the full Epic ADF section layout and panel type reference.

---

## Examples

### ✅ Good

```text
/create-epic "Video Playback Quality Improvements"   # clear title seeds discovery with focused problem scope
/create-epic {{PROJECT_KEY}}-45                                  # existing epic key → reads current state, prompts for update scope
/create-epic "Multi-language subtitle support"       # after running /blueprint — picks up blueprint_backlog_map automatically
/create-epic "Offline Download Feature"              # triggers full 5-phase workflow: discovery → RICE → scope → QG → create
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

---

## 🎓 Domain Expert Notes

### Why This Approach

The 5-phase PM workflow (Discovery → RICE → Scope → QG → Create) encodes the industry-standard separation between problem space (Phases 1-2) and solution space (Phase 3). Committing to scope before validating the problem narrative is the single most common cause of epics that deliver on-time but miss the actual user need. The RICE gate at Phase 2 prevents high-effort low-value epics from entering the backlog through stakeholder enthusiasm alone.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SAFe Epic Hypothesis Statement | Phase 1 Discovery — problem narrative | Every SAFe epic starts as a hypothesis: "We believe [this capability] will result in [this outcome], as evidenced by [this leading indicator]." Narrative Arc is the lightweight equivalent |
| RICE Prioritization (Intercom) | Phase 2 | Converts subjective stakeholder preference into a comparable score; particularly valuable when multiple epics compete for the same sprint capacity |
| Jobs-to-be-Done (Christensen, *Innovator's Dilemma*, 1997; Ulwick, *What Customers Want*, 2005) | Phase 1 — target users + business value | Note: Christensen's JTBD frames the *context* of use ("hire/fire" framing); Ulwick's ODI (Outcome-Driven Innovation) frames *desired outcomes*. Both converge on the same principle for epic work: "When I [situation], I want to [motivation], so I can [outcome]" — prevents solution-first epic definitions |
| OKR → Epic traceability (Doerr, *Measure What Matters*, 2018) | Phase 1 — success metrics | Each epic should trace to at least one Key Result; if it doesn't, question whether the epic belongs in the portfolio at all. OKR-to-epic linkage is the agile equivalent of MBO portfolio alignment — without it, epics optimize for output (features shipped) rather than outcomes (business results) |
| Lean Startup MVP framing | Phase 3 — MVP definition | MVP boundary in VS planning answers: "What is the minimum set of vertical slices that validates our hypothesis?" Not "what is the minimum we can ship" |

### Key Metrics

- **RICE score threshold:** Epics scoring < 5.0 RICE should be challenged or deferred; use as a relative ranking signal, not an absolute gate
- **Discovery-to-scope cycle time:** Time from first stakeholder interview (Phase 1) to approved scope (Phase 3); >2 weeks signals unclear problem ownership or stakeholder availability issues
- **Epic story count at creation:** An epic created with 0 VS stories defined is an idea, not a plan; target 3+ identified stories before QG pass
- **Narrative arc completeness:** All three arc elements present — Current situation, Problem, Solution direction — before Phase 2 starts; missing any one element means the epic scope will drift

### Expert Decision Criteria

- **Epic vs. story threshold:** An initiative that can be delivered in a single sprint by one engineer is a story. An initiative spanning multiple sprints, multiple engineers, or multiple services is an epic. When in doubt, ask: "Can we ship meaningful user value in parts?" If yes → epic.
- **RICE Confidence calibration:** Confidence < 50% signals the team needs a spike or prototype before committing full epic scope. Do not let high Reach × Impact override low Confidence — the denominator (Effort) also has uncertainty at this stage.
- **VS Walking Skeleton rule:** Every epic must include a `vs1-skeleton` story that delivers an end-to-end thin slice users can touch. If the first VS in the plan is purely backend/infrastructure, the PO cannot validate the hypothesis until mid-epic — too late.
- **Blueprint prerequisite gate:** If the epic involves 3+ services or a new bounded context and no `/blueprint` has been run, Phase 1 Discovery will produce a shallow problem narrative. Push back and run blueprint first.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Epic scope grows every sprint ("scope creep") | MVP definition in Phase 3 was aspirational, not minimal | Re-run Phase 3 scope definition with explicit "must-have vs. nice-to-have" binary for each VS story; anything not confirmed must-have defers to next epic |
| RICE score has no effect on sprint planning | Scores calculated but never compared against competing epics | Build a portfolio view: rank all active epics by RICE and review before each sprint planning; enforce WIP limit (config: `team.wip_limit`) |
| Epic created with no Epic Doc | Phase 5 Confluence create was skipped | Epic Doc is not optional — it is the single source of truth for scope decisions; recreate via `/update-epic {{PROJECT_KEY}}-XXX "create epic doc"` |
| Discovery narrative agrees with stakeholder's pre-existing solution | PM accepted solution framing without surfacing the problem | Restart Phase 1 with the "5 Whys" — ask why the proposed solution is needed until a root problem emerges; document that as the narrative |
| Vertical slices are backend-only for first 2 sprints | Team decomposed by technical layer, not user value delivery | Apply the walking skeleton rule: vs1 must be end-to-end (even if thin); reject any VS plan where the first user-visible slice appears past Sprint 2 |

### Authoritative References

- Cprime / SAFe: "No hypothesis, no epic" — the Epic Hypothesis Statement (For / Who / The / Unlike / Our solution) is the quality gate for entering the portfolio Kanban
- Sean McBride, Intercom (RICE framework): Confidence is the most under-valued RICE input; teams routinely inflate it, which is why low-confidence items need spikes, not estimates
- Marty Cagan, *Inspired*: "Fall in love with the problem, not the solution" — Phase 1 Discovery exists to prevent teams from writing epics backward from a pre-decided implementation
- SAFe 6.0 Lean Portfolio Management: Epic MVP must be defined before the epic is approved for implementation; MVP = the minimum investment needed to validate or invalidate the hypothesis

## References

- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Epic Template](../../../references/templates-epic.md) - Epic ADF template + best practices
- [Tool Selection](../../../references/tools.md) - Tool selection, effort sizing
- [Vertical Slice Guide](../../../references/vertical-slice-guide.md) - VS patterns, decomposition
- [Epic ADF Structure](references/epic-adf-structure.md) - Epic ADF section layout and panel type reference
- [Examples](references/examples.md) - Full input/output example
- After creation: `/verify-issue {{PROJECT_KEY}}-XXX`
