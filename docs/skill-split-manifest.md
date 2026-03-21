# Skill Split Manifest

Generated: 2026-03-21
Spec: docs/superpowers/specs/2026-03-21-skill-split-design.md

---

## GLOBAL: SSOT — shared-references/subtask-design-patterns.md

Content to move FROM analyze-story AND create-story INTO this new file:

| Content block | Located under heading |
|---|---|
| "What each agent MUST discover" table | `### 3. Codebase Exploration` (analyze-story) / `### 6. Codebase Exploration` (create-story) |
| "Critical validation:" subsection | Under "Critical validation:" in Codebase Exploration |
| "Scope table format per subtask" section | Under Phase 4 (analyze-story) / Phase 7 (create-story) |
| "AC specificity requirements (Tech Lead level):" | Under Phase 4 / Phase 7 |
| "Config/enum awareness:" | Under Phase 4 / Phase 7 |
| Alignment Check checklist | `### 5. Alignment Check` (analyze-story) / `### 8. Alignment Check` (create-story) |
| QG Subtasks delegation workflow | `### 5b. Quality Gate — Subtasks` (analyze-story) / `### 9. Quality Gate — Subtasks` (create-story) |

Both skills: replace each extracted section with:
`> See [shared-references/subtask-design-patterns.md](../shared-references/subtask-design-patterns.md) for [description].`

**Est. savings:** ~560 tokens total (analyze-story ~550 tokens, create-story ~525 tokens)

---

## blueprint (~2,475 tokens → est. ~1,511 tokens)

### Remove from SKILL.md

- Line `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\`.` (under `## Phases`): boilerplate — already covered by`workflow-patterns.md`

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## When to Use vs Skip` (includes the `### \`/blueprint\` vs \`/refine-epic\`` comparison table and `**Token budget:**` line) | `references/decision-guide.md` | `> See [references/decision-guide.md](references/decision-guide.md) for when to use this skill vs alternatives and comparison with /refine-epic.` |
| `## S-tier Shortcut` | `references/s-tier-shortcut.md` | `> See [references/s-tier-shortcut.md](references/s-tier-shortcut.md) for S-tier single-pass generation steps.` |
| `## Example` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for a full input/output example with Round 1 and Round 2 highlights.` |

### Keep (execution-critical)

- Phases 1–10: all contain gate markers, tool calls, and HR rule reminders
- `## Document Structure (8 Sections)` table: referenced during Phase 6 Converge synthesis
- `## Size Tiers` table: referenced during Phase 2 sizing decision
- `## Context Object` table: execution-critical
- Phase 4/5 agent tables (model + maxTurns): directly governs agent launch
- Phase 9 `blueprint_backlog_map` JSON schema and conversion mapping: used to generate handoff artifact

---

## setup (~3,050 tokens → est. ~2,890 tokens)

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Error Handling Reference` | `references/error-handling.md` | `> See [references/error-handling.md](references/error-handling.md) for per-phase error handling reference.` |

### Keep (execution-critical)

- Phases 0–5: all execution-critical bash logic, config interview, auth flows, health check
- Fast path logic (second-run detection): execution-critical

---

## create-story (~2,975 tokens → est. ~2,174 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (appears twice — under `## Part A` and `## Part B`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Benefits vs Separate Workflow` | `references/decision-guide.md` | `> See [references/decision-guide.md](references/decision-guide.md) for when to use /create-story vs /analyze-story.` |
| `## Example` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for a full input/output example.` |
| SSOT content: 7 blocks per GLOBAL section above | `../shared-references/subtask-design-patterns.md` | `> See [shared-references/subtask-design-patterns.md](../shared-references/subtask-design-patterns.md) for codebase exploration requirements, scope format, AC specificity, alignment check, and QG subtasks.` |

### Keep (execution-critical)

- Blueprint Handoff Check (⛔ GATE): must stay
- Phases 1–11 (Parts A and B): all gate markers, tool calls, HR5/HR6/HR8/HR10 reminders
- `## Context Object` table: execution-critical
- Phase 7 `### 7b. Estimation Calibration`: governs agent invocation

---

## plan-sprint (~3,050 tokens → est. ~2,504 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (appears 3 times — under `## Part A`,`## Part B`,`## Part C`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Pre-Meeting Checklist` | `references/pre-meeting-checklist.md` | `> See [references/pre-meeting-checklist.md](references/pre-meeting-checklist.md) for the pre-meeting preparation checklist.` |
| `### 5. Workload Distribution` — the `**Assignment Algorithm:**` numbered steps (items 1–4) and `**Rules:**` bullet list only; `**Output:**`/`**Input:**`/`**Method:**` lines stay | `references/assignment-algorithm.md` | `> See [references/assignment-algorithm.md](references/assignment-algorithm.md) for the detailed skill-match scoring algorithm and assignment rules.` |
| `## Example` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for a full sprint planning input/output example.` |

### Keep (execution-critical)

- `## ⚠️ Critical: Capacity Before Assignment` block: anti-pattern warning governs execution order
- `## Context Object` table: execution-critical
- `## Dynamic Context` block: execution-critical
- Phases 1–8: all gate markers, HR3/HR6/HR7/HR8/HR10 reminders, MCP/acli commands
- Phase 2 capacity formulas (2a/2b/2c): required for correct computation
- Phase 6b Risk Forecast agent invocation: execution-critical
- Phase 7 plan card format + `🔄 ITERATE` gate: execution-critical
- `## Options` table: governs argument parsing

---

## analyze-story (~1,900 tokens → est. ~1,123 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Batch Sub-task Creation` | `references/batch-creation.md` | `> See [references/batch-creation.md](references/batch-creation.md) for the batch pattern when creating ≥3 sub-tasks.` |
| `## Example` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for a full input/output example.` |
| SSOT content: 7 blocks per GLOBAL section above | `../shared-references/subtask-design-patterns.md` | `> See [shared-references/subtask-design-patterns.md](../shared-references/subtask-design-patterns.md) for codebase exploration requirements, scope format, AC specificity, alignment check, and QG subtasks.` |

### Keep (execution-critical)

- Phases 1–7: all gate markers, HR reminders, tool calls
- `## Context Object` table: execution-critical
- `## Dynamic Context` block: execution-critical
- Phase 4 `**Tech Lead Decomposition — dependency ordering:**` numbered list: procedural ordering rules (distinct from SSOT content)
- Phase 4 `1 sub-task per service boundary` rules and VS Integrity check: execution-critical

---

## refine-epic (~2,000 tokens → est. ~1,251 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\`.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## When to Use vs Skip` (includes `**Token budget:**` line) | `references/decision-guide.md` | `> See [references/decision-guide.md](references/decision-guide.md) for when to use this skill vs alternatives.` |
| `## Example` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for a full Round 1 and Round 2 debate example with output stories.` |

### Keep (execution-critical)

- Phases 1–5: all gate markers, agent launch tables, HR references
- `## Context Object` table: execution-critical
- `## Dynamic Context` block: execution-critical
- Phase 2/3 agent-prompts.md pointers: execution-critical
- Phase 4a–4d (Refined Stories source, Debate Summary, Consensus Checks, Quality Gate): execution-critical output formats and gate logic

---

## sync-artifacts (~1,850 tokens → est. ~1,581 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Edge Cases` | `references/edge-cases.md` | `> See [references/edge-cases.md](references/edge-cases.md) for edge case handling reference.` |
| `## When to Use` | `references/decision-guide.md` | `> See [references/decision-guide.md](references/decision-guide.md) for when to use this skill vs alternatives.` |

### Keep (execution-critical)

- `## Artifact Graph` diagram: defines discovery traversal structure used in Phase 2
- Phases 1–8: all gate markers, tool calls, HR1/HR3/HR4/HR5/HR6 reminders
- `## Context Object` table: execution-critical
- Phase 3 Change Type classification table: governs impact level assignment
- Phase 4 Impact types (ORIGIN/UPDATE/FLAG/NO CHANGE) and directions: governs sync plan generation
- Phase 7 Tool selection table: governs which tool to use per change type

---

## create-epic (~1,475 tokens → est. ~1,201 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Epic Structure (ADF)` | `references/epic-adf-structure.md` | `> See [references/epic-adf-structure.md](references/epic-adf-structure.md) for the full Epic ADF section layout and panel type reference.` |
| `## Example` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for a full input/output example.` |

### Keep (execution-critical)

- Blueprint Handoff Check (⛔ GATE): must stay
- Phases 1–6: all gate markers, HR reminders, tool calls
- `## Context Object` table: execution-critical
- Phase 5 Create Artifacts steps (MCP + acli commands + HR6): execution-critical

Note: `templates-epic.md` is an existing shared-references file and must NOT be modified per spec prohibition.

---

## verify-issue (~1,811 tokens → est. ~1,730 tokens)

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Common Scenarios` | `references/scenarios.md` | `> See [references/scenarios.md](references/scenarios.md) for command examples by scenario, integration workflows, and a full example run.` |
| `## Integration` | `references/scenarios.md` | (merge into same file — append as `## Integration` section) |
| `## Example` | `references/scenarios.md` | (merge into same file — append as `## Example` section) |

### Keep (execution-critical)

- Phases 1–6: all gate markers (⛔ GATE, 🟢 AUTO), tool calls, HR2/HR3/HR5/HR6, adf-surgeon delegation block
- `## Batch Mode` output table: kept (borderline — format spec for `--with-subtasks` output)
- Alignment checks table (A1–A6, Phase 4): execution-critical decision table
- Technical and Quality Verification tables (Phases 2–3): scoring decision tables

---

## bug-triage (~1,435 tokens → est. ~1,390 tokens)

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Common Scenarios` | `references/scenarios.md` | `> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.` |

### Keep (execution-critical)

- Phases 1–6: all gate markers (⛔ GATE, 🟡 REVIEW, 🟢 AUTO), HR3/HR6 reminders, acli commands
- Severity matrix table (Phase 2): decision table used live during scoring — must stay
- Bug intake collection table (Phase 1): drives the intake interview
- Quality Gate checks table (B1–B5, Phase 5): scoring decision table
- `## Context Object` table: execution-critical
- `## Dynamic Context` block: execution-critical

---

## create-task (~1,547 tokens → est. ~1,440 tokens)

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Common Scenarios` | `references/scenarios.md` | `> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.` |
| `## Example` | `references/scenarios.md` | (merge into same file — append as `## Example` section) |

### Keep (execution-critical)

- `## Task Types` table: execution decision table in Phase 1
- Phases 1–6: gate markers, HR6 reminders, acli commands, estimation field instructions
- ADF JSON template skeletons in Phase 2: define required section structure per task type

---

## create-testplan (~990 tokens → est. ~940 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Example` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for input/output examples.` |

### Keep (execution-critical)

- `## Context Object` table: execution-critical
- Phases 1–6: gate markers, HR1/HR3/HR5/HR6 reminders, Two-Step Workflow instructions, tool calls
- `## Common Errors & Fixes` table: operational guidance referenced during Phase 5 execution

---

## update-story (~1,047 tokens → est. ~997 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Common Scenarios` | `references/scenarios.md` | `> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.` |

### Keep (execution-critical)

- `## Context Object` table: execution-critical
- Phases 1–6: gate markers, HR2/HR6/HR8 reminders, acli commands, subtask date alignment script
- Impact Analysis table (Phase 2): execution decision table
- Preserve Intent rules (Phase 3): procedural constraints

---

## update-epic (~1,050 tokens → est. ~960 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Common Scenarios` | `references/scenarios.md` | `> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.` |
| `## Epic Structure (ADF)` | `references/epic-structure.md` | `> See [references/epic-structure.md](references/epic-structure.md) for the Epic ADF section layout and panel type reference.` |

### Keep (execution-critical)

- `## Context Object` table: execution-critical
- Phases 1–6: gate markers, HR6 reminder, acli commands, tool calls
- Impact Analysis table (Phase 2): execution decision table
- Preserve Intent rules (Phase 3): procedural constraints

---

## update-subtask (~950 tokens → est. ~915 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Common Scenarios` | `references/scenarios.md` | `> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.` |

### Keep (execution-critical)

- `## Context Object` table: execution-critical
- Phases 1–6: gate markers, HR1/HR6/HR8/HR10 reminders, acli commands, date validation logic
- Change types table (Phase 2): execution decision table
- Preserve Intent rules (Phase 3): procedural constraints

---

## update-task (~1,287 tokens → est. ~1,170 tokens)

### Remove from SKILL.md

- `> **Phase Tracking:** Use TodoWrite to mark each phase \`in_progress\` → \`completed\` as you work.` (under `## Phases`): boilerplate

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Common Scenarios` | `references/scenarios.md` | `> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.` |
| `## Task Type Detection` | `references/task-type-detection.md` | `> See [references/task-type-detection.md](references/task-type-detection.md) for auto-detection patterns by content.` |

### Keep (execution-critical)

- `## Context Object` table: execution-critical
- Phases 1–6: gate markers, HR1/HR6 reminders, acli commands, ADF EDIT JSON skeleton, Changes Preview format
- Change types table (Phase 2): execution decision table
- Preserve Intent table (Phase 3): procedural constraints applied during generation
- ADF EDIT JSON skeleton (Phase 4): defines required output format for acli edit

---

## map-dependencies (~1,275 tokens → est. ~1,275 tokens)

> No extraction needed — already lean (~1,275 tokens). All sections are execution-critical phase steps with decision tables and flag reference.

### Keep (execution-critical)

- Phases 1–5: full workflow with gate markers and decision logic
- "Size defaults" table: needed for inferred issue sizing when no estimate available
- "Options" table: execution-critical flag reference

---

## close-sprint (~800 tokens → est. ~800 tokens)

> No extraction needed — already lean (~800 tokens). No decorative or reference-only sections.

### Keep (execution-critical)

- Phases 1–8: full workflow with ⛔ GATE, 🟡 REVIEW markers, tool calls, HR6/HR4/HR7 reminders
- `## Context Object` table: execution-critical
- `## Dynamic Context` block: execution-critical

---

## standup-report (~530 tokens → est. ~530 tokens)

> No extraction needed — already lean (~530 tokens).

### Keep (execution-critical)

- Phases 1–4: complete workflow with 🟡 REVIEW gate
- Anomaly detection rules (Phase 3): execution-critical thresholds
- Inline output format sample (Phase 4): required output format spec

---

## reschedule-sprint (~560 tokens → est. ~560 tokens)

> No extraction needed — already lean (~560 tokens).

### Keep (execution-critical)

- Phases 1–5: complete workflow with ⛔ GATE, 🟡 REVIEW markers, HR8/HR6 reminders
- Phase 3 HR8 violation resolution options: execution-critical decision branch

---

## spec-to-stories (~800 tokens → est. ~800 tokens)

> No extraction needed — already lean (~800 tokens).

### Keep (execution-critical)

- Phases 1–8: complete workflow with ⛔ GATE, 🔄 ITERATE, 🟡 REVIEW markers, HR1/HR5/HR6 reminders
- Phase 4 similarity threshold (> 0.8): execution-critical decision rule
- Phase 6 QG scoring criteria (T1-T5, S1-S6): execution-critical

---

## plan-release (~925 tokens → est. ~925 tokens)

> No extraction needed — already lean (~925 tokens).

### Keep (execution-critical)

- Phases 1–9: complete workflow with ⛔ GATE, 🔄 ITERATE markers, HR1/HR6/HR7 reminders
- `## Context Object` table: execution-critical
- Phase 3 velocity formula and buffer calculation: execution-critical
- Phase 6 risk identification criteria: execution-critical

---

## scan-tech-debt (~825 tokens → est. ~825 tokens)

> No extraction needed — already lean (~825 tokens). Impact scoring tables and quadrant rules are execution-critical decision tables.

### Keep (execution-critical)

- Phases 1–6: complete workflow with `--update` branching, HR1/HR4/HR2 reminders
- Phase 3 Impact scoring table (keywords → 1–5 scale): execution-critical
- Phase 3 quadrant assignment rules: execution-critical
- Phase 4 HTML comment snapshot format: execution-critical for `--update` branch

---

## release-notes (~1,250 tokens → est. ~1,175 tokens)

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Common Scenarios` | `references/usage-guide.md` | `> See [references/usage-guide.md](references/usage-guide.md) for common scenario commands.` |

### Keep (execution-critical)

- Phases 1–6: 🟢 AUTO, 🟡 REVIEW gate markers, tool calls, HR4 reminder, `--dry-run` branch
- `## Context Object` table: execution-critical
- Phase 2 issue grouping criteria table: execution-critical (determines Features/Bug Fixes/Improvements/Other grouping)
- Phase 3 page structure: defines exact Confluence page format
- `## Flags` table: needed to parse user arguments in Phase 1

---

## atlassian-scripts (~2,025 tokens → est. ~1,625 tokens)

### Remove from SKILL.md

- `## Related Skills` section: boilerplate cross-reference table — no execution value; skills reference each other organically

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Script Selection Guide` | `references/script-selection-guide.md` | `> See [references/script-selection-guide.md](references/script-selection-guide.md) for a decision tree on which script to use.` |
| `## When to Use Scripts vs MCP` | `references/when-to-use.md` | `> See [references/when-to-use.md](references/when-to-use.md) for MCP vs script decision rules and known issues.` |

### Keep (execution-critical)

- `## Architecture`: module inventory table and directory tree — needed to locate the right script at execution time
- `## Available Scripts`: script lookup table — needed at every invocation to select the correct script
- `## Prerequisites`: credentials path required before any script call
- `## Supporting Files`: on-demand loading index — controls which docs are read and when

---

## doctor (~1,900 tokens → est. ~1,900 tokens)

> No extraction needed — already lean (~1,900 tokens). Content is a single executable bash block with inline error handling; no decorative sections present.

### Keep (execution-critical)

- `## Instructions` (full bash block): all check implementations are the deliverable
- `## Error Handling`: fallback behavior rules needed at runtime

---

## search-issues (~825 tokens → est. ~750 tokens)

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Use Cases` | `references/use-cases.md` | `> See [references/use-cases.md](references/use-cases.md) for example commands by use case.` |

### Keep (execution-critical)

- Phases 1–3: MCP call templates, JQL generation table, semantic similarity threshold and skip conditions, output format
- `## Filter Options`: flag-to-JQL mapping needed to parse user arguments in Phase 1

---

## activity-report (~450 tokens → est. ~450 tokens)

> No extraction needed — already lean (~450 tokens). All three phases are tightly procedural.

### Keep (execution-critical)

- Phases 1–3: argument parsing rules, valid type enum, bash invocation examples, output handling

---

## assign-issue (~275 tokens → est. ~275 tokens)

> No extraction needed — already lean (~275 tokens). Entire file is execution steps.

### Keep (execution-critical)

- `## Usage`, `## Team Lookup`, `## Steps`, `## Special Cases`, HR3/HR6 inline reminders

---

## create-doc (~2,050 tokens → est. ~1,000 tokens)

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `**tech-spec Template:**` body (full markdown template block inside `### 2. Generate Content`) | `references/templates.md` | `> See [references/templates.md](references/templates.md) for tech-spec, adr, and parent template bodies.` |
| `**adr Template:**` body (full markdown template block inside `### 2. Generate Content`) | `references/templates.md` | (same file — all three templates combined) |
| `**parent Template:**` body (full markdown template block inside `### 2. Generate Content`) | `references/templates.md` | (same file — all three templates combined) |
| `## Common Scenarios` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for common command examples.` |

Note: `### 2. Generate Content` keeps its structural instruction ("Generate markdown content based on template") and heading references (`**tech-spec Template:**` etc. become pointers to `references/templates.md`). Only the full template bodies move out.

### Keep (execution-critical)

- `## Templates` lookup table: identifies correct template type in Phase 1
- `### 1. Discovery`: gating questions, info-gathering table, parent search call
- `### 2. Generate Content` (structural instruction only): the generate instruction and macro note remain
- `### 3. Review`: preview format and user approval gate
- `### 4. Create`: MCP call, mandatory code block fix step, output format

---

## update-doc (~1,650 tokens → est. ~1,350 tokens)

### Extract to references/

| Section heading (exact) | To file | Trigger line to add |
|---|---|---|
| `## Error Handling` | `references/error-handling.md` | `> See [references/error-handling.md](references/error-handling.md) for error causes and solutions.` |
| `## Common Scenarios` | `references/examples.md` | `> See [references/examples.md](references/examples.md) for common command and tool examples.` |

### Keep (execution-critical)

- `## Update Types` table: classifies request type in Phase 1
- Phases 1–5: all gates, tool calls, conditional logic
- `## Decision Flow`: maps update type → correct script/tool — needed at Phase 5 to select Option A/B/C

---

## shared-references (~275 tokens → est. ~275 tokens)

> No extraction needed — already lean (~275 tokens). Entire file is the on-demand loading index.

### Keep (execution-critical)

- `## Loading Guide`: the category/files/when table is the decision surface for on-demand doc loading
