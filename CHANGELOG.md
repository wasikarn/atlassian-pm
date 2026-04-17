# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.16.1] - 2026-04-17

### Fixed

- **Hotfix — Grandfather S7 as WARN by default** (`scripts/lib/adf_validator.py`): S7 (markdown-in-text) was introduced in v3.16.0 as `ERROR`/`FAIL`. This caused all existing tickets with legacy text blobs to fail immediately after upgrade. S7 now emits `WARN` by default (grandfather mode). Pass `markdown_strict=True` or `--markdown-strict` to restore `FAIL` behaviour. Default flips back to `FAIL` in v3.17.0.
- **`scripts/api/validate_adf.py`**: added `--dual-zone-strict` and `--markdown-strict` CLI flags, wired to `AdfValidator` constructor so both grandfather modes are controllable from the CLI.
- **`agents/story-writer.md`**, **`agents/adf-surgeon.md`**: added v3.16.1 note that S7 is WARN by default until v3.17.0.

### Migration Notes

- **S7 grandfather behaviour**: S7 violations are now `WARN` (non-blocking) by default. No immediate action required — existing tickets with legacy markdown-in-text will pass the quality gate.
- **S8 grandfather behaviour** (from v3.16.0): S8 missing-zone violations are `WARN` by default. Pass `--dual-zone-strict` to enforce errors.
- **v3.17.0 rollover**: both S7 and S8 grandfather modes will flip to `FAIL`/`ERROR` by default. Migrate tickets before upgrading to v3.17.0.

## [3.16.0] - 2026-04-17

### Added

- **Dual-Zone Acceptance Criteria convention** — every issue's AC section now requires two H3 subsections under `เงื่อนไขที่ต้องผ่าน (Acceptance Criteria)`:
  - `Acceptance Criteria — Business (มุมธุรกิจ/PM/ผู้ใช้)`: observable user outcomes, no tech jargon
  - `Acceptance Criteria — Developer (มุม dev/QA/AI agent)`: testable specs with SLA/service/pattern; cites B-AC IDs
- **Per-type requirement matrix:** Epic/Story/Bug — both zones required. Task — developer required, business optional (required if user-facing). Subtask — inherit parent (business skip), developer required.
- **`references/templates-epic.md`** — added `Dual-Zone AC Convention` section (G-DZ) with zone definitions, language rules, worked example, ADF structure, and per-type matrix. Updated H2 item 7 description. Updated both CREATE/EDIT ADF JSON blocks to use two H3 zones.
- **`references/templates-story.md`** (new) — Story-specific template with dual-zone AC convention, worked example, and full ADF structure.
- **`references/templates-subtask.md`** (new) — Subtask-specific template: business zone skipped (inherit parent), developer zone required.
- **`references/templates-bug.md`** (new) — Bug-specific template: business zone = symptom + expected behavior; developer zone = repro + fix acceptance + regression guard.
- **`references/templates-task.md`** — added `Dual-Zone AC Convention (v3.16.0)` section with per-type requirement, worked example, and ADF structure for dual-zone Task AC.
- **Validator `S7` — markdown-in-text scan** (`scripts/lib/adf_validator.py`): recursively scans all text nodes (excluding code-marked); flags `\n\n` sequences, `|...|` pipe-table rows, `•`/`-`/`*` bullet prefixes, and `#` markdown headings. Severity: ERROR. Applies to Story, Epic, Task.
- **Validator `S8` — dual-zone AC check** (`scripts/lib/adf_validator.py`): finds AC H2 section; verifies Business and Developer H3 zones present per matrix; checks Business zone for banned jargon tokens (SLA numbers, service names, patterns, method calls, field names). Severity: ERROR for missing required zone (grandfather/warn-only mode by default), WARN for language leaks. Applies to Story, Epic, Task. CLI flag `--dual-zone-strict` (default false) flips missing-zone to FAIL; will become default true in v3.17.0.
- **`agents/story-writer.md`** — added two rule cards: `Dual-Zone AC Emission` (two H3 subsections, language rules, cross-ref pattern, per-type matrix) and `ADF Text Purity` (never emit markdown syntax inside text nodes; always use ADF structural blocks). Updated self-critique checklist with S7 and S8 checks.
- **`agents/adf-surgeon.md`** — added `QUIRK-NEW` (markdown-in-text decomposition): detect raw markdown in text nodes and decompose into proper ADF structural blocks. Added detailed repair rules (para-break split, bullet→bulletList, pipe-table→table, heading→heading node). Updated QG check mapping table.

### Breaking

- Epic/Story AC now requires two H3 zones. **Existing tickets grandfathered** — validator S8 defaults to warn-only mode for 1 sprint. Set `--dual-zone-strict` to enforce errors. Will flip to strict by default in v3.17.0.

### Migration

- No immediate action required. New tickets should use dual-zone structure from templates.
- Run `python validate_adf.py <file> --type epic` to preview S8 warnings on existing epics.
- To opt into strict validation now: `python validate_adf.py <file> --type epic --dual-zone-strict`.

## [3.15.3] - 2026-04-16

### Changed

- **`references/templates-task.md`** — added diagram rule prerequisite note at top. Jira ADF = ASCII code block only; default `sequenceDiagram` for 3+ branch decisions; hand-draw box chars when embedding directly. Mirrors the annotation added to `templates-epic.md` in 3.15.1.

### Rationale

Final audit sweep after 3.15.2. Task-creating skills (`apm-create-task`, `apm-update-task`, `apm-refine-epic`, `apm-vibe-plan`, `apm-spec-to-stories`, `apm-bug-triage`, `apm-create-testplan`) all read `templates-task.md` as their MANDATORY template reference — previously only `templates-epic.md` carried the diagram rule. This closes the last doc gap. All Jira-write paths now propagate the ASCII-only + multi-branch-flowchart-bug convention consistently; Confluence-write paths (`apm-blueprint`, `apm-create-doc`, `apm-update-doc`) are unaffected (Forge Mermaid macro renders natively).

### Migration

- No migration required.

## [3.15.2] - 2026-04-16

### Changed

- **`agents/story-writer.md`** — added explicit diagram rule: Jira ADF = ASCII code block only, default `sequenceDiagram` for 3+ branch decisions (flowchart mashes labels per mermaid-ascii#56), hand-draw box chars when embedding directly. Prevents silent drift when story-writer emits ADF with embedded Mermaid.

### Rationale

Audit found story-writer referenced `templates-core.md` + `templates-task.md` but not `templates-epic.md` (where the diagram convention was documented in 3.15.1). Gap closed by adding the rule directly to story-writer so it applies regardless of which template is loaded.

### Migration

- No migration. Existing generated content unaffected.

## [3.15.1] - 2026-04-16

### Documentation

- **Post-3.15.0 consistency sweep** (`40c498c`) — marketplace.json + README.md badge bumped to 3.15.0 (missed by manual bump); dropped orphaned Theming section from `skills/utilities/apm-pretty-mermaid/references/DIAGRAM_TYPES.md`; fixed `--format` row in Options table; documented `--code` / `-c` inline input flag; softened 3 cross-repo references to private MEMORY.md files; removed dangling "empirical width table" reference in `references/templates-epic.md`.
- **`references/ascii-box-drawing.md`** (new) — dedicated hand-draw palette reference with full Unicode tables (char + U+ codepoint + name) for each category:
  - Single line (U+2500–U+253C)
  - Heavy line full set (U+2501–U+254B): corners, T-junctions, cross
  - Double line (U+2550–U+256C)
  - Mixed single+double junctions (U+255E–U+256B) for mixing detail + architectural boundaries
  - Arc corners (U+256D–U+2570): rounded alternatives for softer UI-style diagrams
  - Dashed / dotted (U+2504–U+250B, U+254C–U+254F) for optional paths, feature-flag edges, pending integrations
  - Shading / blocks (U+2580–U+25A0), arrows (U+25B6/U+2190s/U+21D2)
  - Example patterns (simple box, horizontal connect, tree), stroke-weight rule, drawing tool pointers (MonoSketch, asciiflow.com, monodraw)
- **`references/mermaid-guide.md`** — replaced earlier external gist link with a compact glyph list + pointer to `ascii-box-drawing.md` for the full tables. Self-contained, no external dependency.

### Rationale

Ship-able reference improvements that accumulated after 3.15.0. All docs-only, no behavior change. Inline palette makes the mermaid guide self-contained — gist deletions or URL changes no longer break the reference.

### Migration

- No migration required. Existing diagrams and skill invocations unchanged.

## [3.15.0] - 2026-04-16

### Changed

- **`apm-pretty-mermaid` skill scope narrowed to ASCII-only for Jira.** Confluence rendering path removed from documentation — Confluence uses native Forge Mermaid macro (raw `.mmd` paste), no skill needed. Rationale: team preference for simpler stack; Forge renders Mermaid natively, so the wrapper adds no value for Confluence.
- SKILL.md rewritten: removed `Confluence SVG` Quick Start, `Pattern B` (Confluence SVG), `Pattern C` (cross-platform), `Themes (SVG only)` section, SVG-related options (`--theme`, `--transparent`, `--bg`/`--fg`/`--accent`, `--font`, `--output`), SVG examples, and SVG domain-expert note.
- Downstream SKILL references updated to "raw `.mmd` in Forge Mermaid macro" for Confluence outputs: `apm-close-sprint`, `apm-plan-release`, `apm-map-dependencies`, `apm-scan-tech-debt`.
- `references/mermaid-guide.md`: target matrix now lists Jira ASCII + Confluence Forge Mermaid macro only; Gantt redirected to Forge macro.
- `.claude/rules/mermaid.md`: same matrix update; removed `--theme tokyo-night` reference.
- `references/templates-core.md`: ADF schema takeaways updated — `mediaSingle` no longer documented as SVG path (APM convention does not use attachment-based diagrams).
- `skills/README.md`: `apm-pretty-mermaid` entry now states ASCII-only for Jira.

### Removed

- **`skills/utilities/apm-pretty-mermaid/references/THEMES.md`** — SVG theme catalog, orphaned after SVG path removal.

### Rationale

Back-to-basic simplification. Confluence Forge Mermaid plugin already renders `.mmd` natively with no attachment step, no version drift, and no theme configuration. Maintaining an SVG path in the skill duplicated that capability and added dependencies (beautiful-mermaid theme config, `--transparent`/`--font`/etc.) with no production benefit. The skill's only remaining job — ASCII for Jira ADF code blocks — is its original, uncontested use case.

Script files (`scripts/render.mjs`, `scripts/batch.mjs`, `scripts/themes.mjs`) still support SVG output if invoked directly; only the documentation stops advertising it. Future version may drop SVG-only code paths if no internal users are found.

### Migration

- If you had local scripts invoking `apm-pretty-mermaid` with `--format svg --theme <name>`, replace the step with: paste the raw `.mmd` into a Forge Mermaid macro on the target Confluence page.
- Gantt timelines on Confluence release pages: same replacement — Forge macro renders `gantt` natively.

## [3.14.1] - 2026-04-16

### Documentation

- Documented upstream bug [mermaid-ascii#56](https://github.com/AlexanderGrooff/mermaid-ascii/issues/56): 3+ branch `flowchart` renders broken ASCII (edge labels mash). **Fix: hand-draw ASCII** in Jira code block with box chars (`┌─┐│└┘├┤▶▼`), or convert to `sequenceDiagram`. Sequence/state/ER/class unaffected.
- Updated: `skills/utilities/apm-pretty-mermaid/SKILL.md` (Known Issues), `references/mermaid-guide.md`, `.claude/rules/mermaid.md`, `references/templates-epic.md`, `skills/README.md`.

### Rationale

Empirical testing ({{PROJECT_KEY}}-182, {{PROJECT_KEY}}-183, 2026-04-16) confirmed the bug affects every flowchart with 3+ outgoing edges. Simplest fix = hand-draw ASCII (author controls width, always fits ≤ 80 cols).

### Migration

- No breaking changes — all additive documentation. Existing Mermaid sources continue to work; only ASCII rendering of 3+ branch flowcharts is affected, and only for Jira embedding (Confluence Mermaid macro renders fine).
- Teams with existing 3+ branch flowchart diagrams embedded in Jira descriptions should re-render as `sequenceDiagram` when next updated.

## [3.14.0] - 2026-04-16

### Added

- **`skills/utilities/apm-pretty-mermaid/SKILL.md`** — new skill wrapping `beautiful-mermaid` with APM-aware defaults. ASCII output (default) for Jira ADF code blocks in all issue types (Epic/Task/Bug/Spike/Chore/comment); themed SVG for Confluence attachments. Width discipline ≤ 80 cols. Wraps upstream `beautiful-mermaid` library (15 themes, 5 diagram types).
- **`.claude/rules/mermaid.md`** — added ASCII-first rule, target matrix (Jira → ASCII, Confluence simple → Forge macro, Confluence complex → SVG, Gantt → SVG only), skill pointer to `apm-pretty-mermaid`.
- **`references/mermaid-guide.md`** — new `Jira ASCII` section with render command, ADF codeBlock embed pattern, and width rules. Links to `apm-pretty-mermaid` skill.
- **Discoverability pointers** — `apm-close-sprint`, `apm-plan-release`, `apm-map-dependencies`, `apm-scan-tech-debt` now reference `apm-pretty-mermaid` at their Mermaid generation points.

### Removed

- **`references/workflow-compact.md`** (33 lines) — redundant subset of `workflow-patterns.md`. Four callsites updated in `apm-vibe-plan`, `apm-create-epic`, `templates-epic`.
- **`references/vs-checklist-compact.md`** (42 lines) — redundant subset of `vertical-slice-guide.md`. Callsites updated.

### Rationale

TaThep team convention (2026-04-16, MEMORY.md → "Jira ASCII Diagrams"): default diagram format in Jira = ASCII code block (monospace, zero-dependency, diff-friendly, renders identically in web/mobile/gh-cli). SVG-in-Jira breaks copy-paste + AI-agent parsing. Confluence SVG attachment preserved for high-fidelity architecture docs.

Compact-file deletion eliminates dual-source maintenance debt — every edit previously required updating 2 files.

### Migration

- No breaking changes — all additive.
- Existing Epics/Tasks still validate.
- Skill first-run auto-installs `beautiful-mermaid` (~3 MB); offline environments: `cd skills/utilities/apm-pretty-mermaid && npm install` once.

### Notes

- Upstream library: <https://github.com/imxv/Pretty-mermaid-skills> (641 stars, MIT).
- ASCII renderer does not support Gantt — use SVG on Confluence for release timelines.

## [3.13.0] - 2026-04-16

### Added

- **`skills/task/apm-slice-ship/SKILL.md`** — new skill guiding per-slice ship workflow (pre-ship checklist → deploy → observability smoke → QA verify → PM release approval). 5-phase gate enforces TaThep ship-per-merge convention.
- **`references/templates-epic.md`** — new required `Slicing Plan` section for epics using ship-per-merge (ship strategy, slice order, flag strategy, shared resources, rollback plan per slice).
- **`references/flags-yaml-template.yaml`** — new canonical feature flag registry template. Enforces: flag naming (`feat/{epic-key}/{slice-number}`), TTL ≤ 30 days post-epic-complete, owner + status (`active` → `released` → `scheduled-for-removal`).
- **`references/vertical-slice-guide.md`** — new `Ship Strategy` section documenting ship-per-merge gates (pre-merge → coverage-tiered deploy → canary 5%/25%/100% → QA watch → PM release approval) + carve-outs (AI-agent, video-processing).
- **`references/templates-core.md`** — new `Jira Workflow (TaThep)` section documenting workflow states (Backlog → In Progress → Shipped flag-off → Ready for QA → Released flag-on → Done) + labels (`vs-planned`, `vs-shipped-dark`, `vs-released`, `carve-out-manual-gate`).
- **`scripts/lib/adf_validator.py`** — new check `T16: Slice Flag Discipline` (WARN-level). Slice tickets (`vs-*` label or "Slice" marker) should reference a flag in `.flags.yaml` OR explicit "no flag (hardening)" note.
- **Tests** — 8 new T16 tests in `TestT16SliceFlagDiscipline` class. Total validator tests: 120 → 128.

### Rationale

TaThep team (2026-04-16) established binding convention via 4-role debate (Engineering Lead, QA Lead, DevOps/SRE, Product/Delivery) + Team Lead tiebreak: vertical slices ship to production per merge (flag OFF); release (user exposure) = separate PM-approved flag toggle. This eliminates batch-wait-for-all-tickets bottleneck for market velocity.

**Tier 2 MTTR** (< 4h business hours) current; **Tier 1** (< 1h business + < 4h off-hours) when partner billboard owners onboard. Staging at `{{STAGING_WEB}}` + `{{STAGING_ADMIN}}`. Pilot #1 = Video Playback Phase 1/2/NVR (active `vs-planned` work); Pilot #2 = {{PROJECT_KEY}}-182/{{PROJECT_KEY}}-183 after calibration.

Full binding decision: see `feedback_ship_per_merge_convention.md` (user memory) + `wiki/ship-per-merge-convention.md` (2nd Brain synthesis).

### Migration

- No breaking changes — all additive.
- Existing Epics/Tasks still validate (T16 WARN-only).
- `Slicing Plan` section required only for epics explicitly using ship-per-merge (opt-in via `vs-*` labels or team decision).
- `.flags.yaml` deployment per repo is a Week 0 prerequisite — not enforced by plugin yet.

### Notes

- `apm-slice-ship` skill references external infrastructure (Unleash OSS self-host recommended; fallback PostHog managed).
- Carve-out services (`tathep-ai-agent-python`, `tathep-video-processing`) use manual CI gate — re-audit Day 60 after convention activates.
- T16 Thai label support matches existing TK1-T15 bilingual convention.

## [3.12.2] - 2026-04-16

### Added

- **`scripts/lib/adf_validator.py`** — six new WARN-level checks closing proactive prevention gaps (G7-G12). Unlike v3.12.1 (which closed audit-reactive gaps found in {{PROJECT_KEY}}-183), v3.12.2 closes gaps identified through proactive analysis before they cause future incidents:
  - `T10: Explicit Jira Dependency Links` (Epic + Task) — warns when `{{PROJECT_KEY}}-XXX` appears as plain text without an accompanying `inlineCard` URL. Jira's Issue Links panel only picks up `inlineCard` references; prose-only mentions leave the dependency graph blind. New constant `JIRA_KEY_IN_TEXT_RE`.
  - `T11: Estimate Declaration` (Task-only) — warns when Task description lacks an `Estimate` / `ประมาณการ` section or Story Points mention. Forces explicit size reasoning inline (not only via Jira field that's easy to skip).
  - `T12: Paired-Epic Regression ACs` (Epic + Task) — when description references another TP-key (via `inlineCard` or plain text), AC section must mention that key at least once as a regression marker. Prevents silent cross-boundary behavior between paired epics.
  - `T13: Code Reference Format` (Epic + Task) — warns when inline `code`-marked text is a bare method call (`handle()`, `run()`, `process()`) without a class prefix. Ambiguous across sibling tickets; suggests `ClassName.method()` or full path form. New constant `BARE_METHOD_RE`.
  - `T14: Vague AC Phrase Scan` (Epic + Task) — scans AC / `เงื่อนไขที่ต้องผ่าน` / done-criteria / fix-criteria sections for a dictionary of non-testable phrases (`should work correctly`, `ทำงานได้ดี`, `user-friendly`, `as expected`, etc.). Suggests Given/When/Then rephrase. New constant `VAGUE_AC_PHRASES`.
  - `T15: Out of Scope Required for Slices` (Task-only) — when Task title contains vertical-slice markers (`Slice A/B/C`, `vs1-`, `vs-enabler-`) or labels include `vs*`, requires an `Out of Scope` / `ไม่รวมงานนี้` section. Forces explicit sibling-slice boundary at creation time. New constant `SLICE_MARKER_RE`.
- **`references/templates-epic.md`** — three new subsections under pair/shared guidance:
  - `Regression ACs for Paired Epics` (G9) — documents the mirrored-regression-AC rule matching T12.
  - `AC Quality Rules (INVEST-T: Testable)` (G11) — vague-phrase dictionary + Given/When/Then rewrite examples matching T14.
  - `Explicit Jira Dependency Links` (G7) — `inlineCard` pattern + link-type matrix (`Blocks` / `Is blocked by` / `Relates to` / `Depends on`) matching T10.
- **`references/templates-task.md`** — five new rule sections:
  - `Estimate Declaration` (G8) — `ประมาณการ` H2 pattern with SP + days + confidence table matching T11.
  - `Out of Scope REQUIRED for Vertical Slices` (G12) — explicit boundary declaration for slices matching T15.
  - `Regression ACs for Paired-Epic Slices` (G9) — mirrors Epic-level rule at slice granularity.
  - `AC Quality Rules (INVEST-T: Testable)` (G11) — vague-phrase list matching T14.
  - `Explicit Jira Dependency Links` (G7) — `inlineCard` rule + post-create `acli jira workitem link` command matching T10.
- **`references/templates-core.md`** — new `Code Reference Format` section (G10) — canonical shapes for code references (full path / class.method / bare function) matching T13.
- **`scripts/tests/test_adf_validator.py`** — 29 new tests across six classes (`TestT10ExplicitJiraLinks`, `TestT11Estimate`, `TestT12PairedEpicRegression`, `TestT13CodeReferenceFormat`, `TestT14VagueAcPhrases`, `TestT15OutOfScopeForSlice`) + updated `test_epic_check_count` (13→17) and `test_task_check_count` (12→18).

### Changed

- **`scripts/lib/adf_validator.py`** — class docstring updated; Epic now has 17 checks (T1-T10, T12-T14 + E1-E4), Task now has 18 checks (T1-T8, T10-T15 + TK1-TK4). T10-T15 are WARN-only so existing tickets still pass at 90% threshold.
- **`README.md`** — version badge refreshed from stale `3.10.4` to `3.12.2`.

### Rationale

v3.12.1 closed six gaps surfaced during the {{PROJECT_KEY}}-183 audit (audit-reactive). v3.12.2 closes six gaps identified through proactive analysis — patterns that *could* cause future incidents but haven't broken any specific ticket yet. The distinction matters: reactive fixes close a known wound; proactive fixes prevent a wound from opening.

- **G7 — Jira dependency links visible in UI (T10)** — slices reference siblings via prose ("reuse from {{PROJECT_KEY}}-XXX") instead of `inlineCard`. Dev looking at the slice in Jira UI can't see the dependency because it doesn't appear in the Issue Links panel. Forcing `inlineCard` + an actual Jira link type keeps the dependency graph authoritative.
- **G8 — inline effort declaration (T11)** — Jira Story Points field is easy to skip when creating a ticket. Requiring a `ประมาณการ` section in the description forces explicit size reasoning AND surfaces scope creep when slices grow past 5 SP.
- **G9 — regression ACs for paired epics (T12)** — paired epics ({{PROJECT_KEY}}-182 route-to-review ↔ {{PROJECT_KEY}}-183 auto-decision) rely on each side guarding the other's scope path. Without mirrored regression ACs, a slice can silently absorb sibling scope at implementation time.
- **G10 — canonical code reference format (T13)** — same code path written as `AiMediaAnalysisJob.handle()` in one ticket and `handle()` in a sibling breaks grep-based cross-reference. Bare `handle()` is especially ambiguous (which class?). Canonical shapes keep QA and Dev grep-searches authoritative.
- **G11 — vague AC phrases break INVEST-T (T14)** — phrases like "should work correctly" / "ทำงานได้ดี" are not testable. QA cannot write a pass/fail case from them. A static dictionary scan catches these before creation.
- **G12 — Out of Scope surfaces boundary decisions (T15)** — slices without an explicit `Out of Scope` section implicitly absorb sibling scope at implementation time. Forcing the author to list what's NOT in scope exposes overlap at creation time.

### Migration

- No breaking changes. T10-T15 are WARN-only and do not affect pass/fail at the 90% threshold.
- Existing Epics and Tasks continue to validate. Recommended-with-grace-period:
  - `{{PROJECT_KEY}}-XXX` mentions should migrate from plain text to `inlineCard` during next edit.
  - New vertical slices should include `Out of Scope` + `Estimate` sections from creation.
  - Paired-epic tasks should add regression ACs at next edit.
  - AC sections with vague phrases should rephrase to Given/When/Then during next refinement pass.

### Notes

- Validator test suite grew from 91 → 120 passing tests.
- `scripts/api/validate_adf.py` CLI unchanged; existing `--type epic` / `--type task` invocations automatically pick up T10-T15.
- This release is PROACTIVE (not audit-reactive) — it closes gaps found through analysis before a specific ticket breaks, distinguishing it from v3.12.0 (systemic gaps after {{PROJECT_KEY}}-182 incident) and v3.12.1 ({{PROJECT_KEY}}-183 audit findings).

## [3.12.1] - 2026-04-16

### Added

- **`scripts/lib/adf_validator.py`** — three new WARN-level checks closing prevention gaps from {{PROJECT_KEY}}-183 audit:
  - `T7: Canonical Scope Disambiguation heading` (Epic + Task) — verifies the disambiguation section uses the exact canonical H2 `Scope Disambiguation` (allowing `— subtitle` / `: subtitle`). Catches near-miss variants like `Scope Clarification` that T6 would have silently accepted.
  - `T8: Decision-Path Qualifier` (Epic + Task) — warns when a title contains a decision-path verb (`approve · reject · decide · process` / Thai `อนุมัติ · ปฏิเสธ · ตัดสิน`) without an explicit `auto-` / `manual-` / `admin-` qualifier. An unqualified verb is ambiguous (auto-decision? manual admin action?).
  - `T9: Bilateral Epic Reference` (Epic-only) — when Epic description references another Epic key via `inlineCard`, validator requires a `Coverage Matrix` section with `Related Epic(s)` column. Missing matrix or column → WARN. Forces cross-Epic references to be machine-checkable, not just prose-only.
- **`references/templates-epic.md`** — three new subsections:
  - `Bilateral Epic Reference Rule` — inlineCard to sibling Epic MUST be mirrored in sibling's Coverage Matrix (G6).
  - `Vocabulary Collision Rule` — slice titles under paired Epics MUST use distinct keywords; sibling Epic's keyword must not leak into this Epic's slices (G2).
  - `Shared Resource Declaration` — Epic description MUST list shared components in a `Shared Resources` table when 2+ slices touch the same file (G5, feeds slice-level coordination).
- **`references/templates-task.md`** — two new rules under `Title Discipline`:
  - `Decision-Path Qualifier Rule` (G3) — documents `auto-` / `manual-` / `admin-` prefix requirement matching T8 validator.
  - `Test File Declaration` (G4) — sibling slices under same Epic MUST declare test-file path consistently in `ขอบเขตไฟล์` table (`CREATE` / `MODIFY` / explicit `NONE` with reason).
- **`references/vertical-slice-guide.md`** — new `Shared Resource Coordination` section with the First-Merged-Owns-Upgrade pattern + {{PROJECT_KEY}}-197 ↔ {{PROJECT_KEY}}-200 worked example + anti-pattern `Silent Shared Upgrade` (G5).
- **`scripts/tests/test_adf_validator.py`** — 17 new tests across three classes (`TestT7CanonicalDisambig`, `TestT8DecisionPathQualifier`, `TestT9BilateralEpicRef`) + updated `test_epic_check_count` (10→13) and `test_task_check_count` (10→12).

### Changed

- **`scripts/lib/adf_validator.py`** — class docstring updated; Epic now has 13 checks (T1-T9 + E1-E4), Task now has 12 checks (T1-T8 + TK1-TK4). T7-T9 are WARN-only so existing tickets still pass at 90% threshold.

### Rationale

v3.12.0 introduced 7 prevention fixes (P1-P7) after the {{PROJECT_KEY}}-182 ambiguity incident. A follow-up audit on {{PROJECT_KEY}}-183 and its 6 child slices uncovered 6 more gaps that let inconsistencies slip through even with v3.12.0 in place:

- **G1 (T7)** — {{PROJECT_KEY}}-183 used a near-canonical heading (`Scope Clarification` instead of `Scope Disambiguation`). T6 didn't fire because *some* disambiguation text existed, but readers couldn't grep the canonical anchor across epics.
- **G2 (vocabulary collision)** — a {{PROJECT_KEY}}-183 sibling slice titled `AI ตรวจสอบสื่อ` reused {{PROJECT_KEY}}-182's keyword `ตรวจสอบ`. Reviewers assumed it was a {{PROJECT_KEY}}-182 slice. Paired Epics need distinct keyword spaces.
- **G3 (T8)** — slice titled `AI อนุมัติสื่อ` was ambiguous: auto-approve by AI, or admin-approve with AI assist? An explicit `auto-` / `manual-` / `admin-` qualifier removes the ambiguity.
- **G4 (test-file consistency)** — {{PROJECT_KEY}}-183 sibling slices inconsistently declared test files; some had a `tests/...spec.ts` scope row, others omitted it. QA couldn't tell "no tests needed" from "forgot to declare".
- **G5 (shared resource)** — {{PROJECT_KEY}}-197 (Slice B of {{PROJECT_KEY}}-182) and {{PROJECT_KEY}}-200 (Slice B of {{PROJECT_KEY}}-183) both upgraded `BillboardOwnerLookupService`. No coordination AC existed → merge-conflict risk + duplicated commits. Now each slice mentions the sibling slice and uses First-Merged-Owns-Upgrade pattern.
- **G6 (T9 bilateral ref)** — {{PROJECT_KEY}}-182 Coverage Matrix referenced {{PROJECT_KEY}}-183 but {{PROJECT_KEY}}-183 originally only mentioned {{PROJECT_KEY}}-182 in its Mermaid diagram, not in a machine-checkable Coverage Matrix row. One-way references let readers on the sibling side miss the relationship.

### Migration

- No breaking changes. T7-T9 are WARN-only and do not affect pass/fail at the 90% threshold.
- Existing Epics and Tasks continue to validate. Recommended-with-grace-period:
  - `Scope Disambiguation` heading text should be canonical (fix during next Epic edit).
  - Decision-path slice titles should gain `auto-` / `manual-` / `admin-` qualifiers.
  - Bilateral Epic references should gain mirror entries in both Coverage Matrices.

### Notes

- Validator test suite grew from 74 → 91 passing tests.
- `scripts/api/validate_adf.py` CLI unchanged; existing `--type epic` / `--type task` invocations automatically pick up T7-T9.
- `references/mermaid-guide.md` already covers the all-branches rule (v3.12.0); no change needed for v3.12.1.

## [3.12.0] - 2026-04-16

### Added

- **`references/templates-epic.md`** — new `Scope Disambiguation` H2 section between `สรุปภาพรวม` and `User Flow`; REQUIRED when Epic title contains ambiguous cue words. Captures explicit interpretation + rejected alternatives so QA/PM/Dev see the same scope anchor.
- **`references/templates-epic.md`** — new `Code Paths Covered` H3 subsection in Technical Reference zone (P6): explicit table of every code path with In-Scope status (`✅ / ❌ / partial`). Enumeration gate before drafting scope.
- **`references/templates-epic.md`** — new `Coverage Matrix` H3 subsection (P3): REQUIRED when Epic description references another Epic by key (inlineCard / `TP-YYY`). Cross-references which scenarios belong to this Epic vs related vs out-of-scope.
- **`references/templates-epic.md`** — `User Flow Mermaid — All Branches Rule` (P7): diagrams MUST show all decision branches, each labeled `⭐ {{PROJECT_KEY}}-XXX` (this epic) / `TP-YYY` (related) / `(out of scope)` with color conventions.
- **`references/architect-debate-protocol.md`** — new file codifying the Competing Interpretations → Recommendation → Risk-if-wrong format (P5). Required when any architect-style analysis runs on ambiguous input. Includes {{PROJECT_KEY}}-182 worked example.
- **`references/mermaid-guide.md`** — new `Epic User Flow — All Branches Rule` section with style conventions + 3-way decision template + {{PROJECT_KEY}}-182 anti-pattern.
- **`scripts/lib/adf_validator.py`** — new check `T6: Title Ambiguity Scan` (WARN-level, never FAIL). Scans Epic/Task summary + description for ambiguous cue words (`request · process · handle · manage · review · check · trigger · send · notify · update`). Triggers warning if title has 2+ cues without `Scope Disambiguation` section, or description has cue without explicit `Scope:` / `Trigger:` clarifier. New constant `AMBIGUOUS_CUE_WORDS` exported.
- **`skills/epic/apm-create-epic/SKILL.md`** — new `Phase 0: Intent Clarification Gate` (P1): pre-draft cue-word scan + code path enumeration + interpretation picker. Runs before Phase 1 Discovery.
- **`skills/epic/apm-create-epic/SKILL.md`** — new `Phase 1.5: Stakeholder Confirmation Loop` (P2): explicit pause after first draft, asks user for `confirmed` before generating slices.
- **`skills/epic/apm-update-epic/SKILL.md`** — ambiguity scan added to Phase 2 Impact Analysis and new `Phase 2.5: Stakeholder Confirmation Loop` (P2): pause for `confirmed` before generating update ADF.

### Changed

- **`scripts/lib/adf_validator.py`** — class docstring updated; Epic and Task quality paths now include T6. Check counts: Epic 9 → 10, Task 9 → 10. Threshold still 90%; T6 is WARN-only so existing tickets keep passing.

### Rationale

QA flagged the {{PROJECT_KEY}}-182 scope-ambiguity bug (documented in v3.11.1 case study) as systemic: an ambiguous Epic title (`"Review flow — notification trigger"`) propagated silently through draft → restructure → slices → Mermaid → code review because seven process/tooling gaps never forced the ambiguity to surface. v3.12.0 closes those seven gaps:

- **P1 Intent Clarification Gate** — catch ambiguity at the earliest moment (before draft).
- **P2 Stakeholder Confirmation Loop** — force an explicit checkpoint before slice generation, because that's when ambiguity locks in.
- **P3 Coverage Matrix for Epic Pairs** — make cross-Epic coverage machine-readable.
- **P4 T6 Ambiguity Scan** — static-validator warning so the gap is visible even when humans forget.
- **P5 Architect Debate Protocol** — require Competing Interpretations before any recommendation.
- **P6 Code Paths Covered** — enumerate all decision paths so gaps fall through to a table, not production.
- **P7 All-Branches Mermaid Rule** — every decision node must show every branch with coverage label.

### Migration

- No breaking changes. All new sections are additive.
- Existing Epics still validate at previous scores (T6 is WARN-only).
- `Scope Disambiguation`, `Code Paths Covered`, and `Coverage Matrix` are recommended-with-grace-period: new Epics should include them; existing Epics can add them during the next update.

### Notes

- No architect-specific agent file exists in `agents/` — the debate protocol lives in `references/architect-debate-protocol.md` and is referenced by apm-create-epic / apm-update-epic so any agent doing architect-style reasoning can apply it.
- `scripts/api/validate_adf.py` CLI surface unchanged — existing `--type epic` / `--type task` invocations automatically pick up T6. No new CLI arg needed.

## [3.11.1] - 2026-04-16

### Changed

- **`references/templates-epic.md`** — User Stories section now explicitly forbids layer-split anti-pattern (`[BE] Create X` / `[FE] Update Y`) and requires vertical slices. Links to `vertical-slice-guide.md` + `vs-checklist-compact.md`. Includes ❌/✅ example pair + pre-write checklist.
- **`references/vertical-slice-guide.md`** — added `Component-split` anti-pattern row (splitting by code component where each task has no standalone business value). Added Case Study: {{PROJECT_KEY}}-182/183 restructure 11 technical tasks → 6 vertical slices driven by QA feedback.

### Rationale

Plugin v3.11.0 introduced business-first Epic structure but did not enforce vertical slice decomposition. Agents continued creating layer-split tasks (one task per class/component) under Epics, forcing manual restructure. This release closes the gap by teaching the rule in the Epic template itself, linking to the existing `vertical-slice-guide.md`.

Case study in vertical-slice-guide.md documents the {{PROJECT_KEY}}-182/183 restructure (11 tasks → 6 slices) so agents recognize the pattern.

## [3.11.0] - 2026-04-16

### Added

- **Epic template business-first structure** — new required section `User Flow — ภาพรวมการทำงาน` between Overview and Business Value, expanded `ลูกค้าเห็นอะไร?` with Before/After table + example message copy, optional `📘 Technical Reference (สำหรับ Dev)` H2 separator for epics with heavy technical detail. Rationale: QA feedback — Epic descriptions were too technical, hurting onboarding time for PM/QA/stakeholders.
- **Business Zone language rule** — formal rule that Scope, User Stories, Acceptance Criteria, and Risks sections MUST use user-observable behavior language. No class names, file paths, method signatures, code patterns (e.g. `whereIn`/`findBy`), i18n keys, or SQL queries in Business Zone — these move to Technical Reference Zone. Rationale: agents were mixing technical and business content in Business Zone, making it unreadable for QA/PM/stakeholders.
- **Mermaid flow diagrams** — Epic User Flow section now recommends `codeBlock` with `language: "mermaid"` instead of ASCII text art. Leverages Jira Cloud's native Mermaid rendering for cleaner, readable diagrams.
- **Panel node support** — `panel` with `panelType: info/success/warning/note` moved from Forbidden to Allowed. Previously workarounds (emoji + bold paragraph) were used inconsistently across agents.
- **Emoji allowed in H2 headings** for section zone markers (e.g. `📘 Technical Reference`). Previously banned — agents had no clean way to separate business/technical zones.
- **Business-first ordering rule** — Epic section ordering is now formally specified: Business Zone (User Flow, Business Value, Customer Experience, Scope, User Stories, AC, Risks) always precedes Technical Reference Zone (Current Flow Gap, Technical Design, Edge Cases, Dependencies).

### Changed

- **`references/templates-core.md`** — rewrote ADF Principles + Allowed/Forbidden Node Types tables. Added new `Panel Usage` section documenting when to use each `panelType`.
- **`references/templates-epic.md`** — CREATE/EDIT templates regenerated with User Flow, before/after table, example message copy, warning panel over risks, optional Technical Reference separator.

### Notes

- Agents previously made inconsistent decisions (some used `panel`, others used emoji+bold workaround) because `templates-core.md` forbid panels but `validate_adf.py` did not enforce it. This release aligns documentation with validator reality.
- No breaking changes — existing Epic descriptions still validate at 100%. New structure is additive guidance for future epics.

## [3.10.4] - 2026-04-11

### Fixed

- **`mcp-servers/atlassian-cache/server.py`** — Fixed `AttributeError: 'coroutine' object has no attribute 'invalidate_issue'` (and similar errors for `put_search`, `get_search`, `get_stats`, etc.) caused by missing `await` on `_require_cache()` calls. The helper is `async def` but was being called as if synchronous in 10 locations across the file. All cache MCP tools (`cache_invalidate`, `cache_search`, `cache_sprint_issues`, `cache_stats`, `cache_similar_issues`) were broken — they now work correctly. Also fixed `_log_token_metrics` (sync helper) which was incorrectly trying to `await` from non-async context; switched to using the global `cache` reference directly.

## [3.10.3] - 2026-04-08

### Fixed

- **macOS `timeout` compatibility** — `hooks/run.sh` now detects `gtimeout` (GNU coreutils) on macOS when `timeout` is unavailable, and falls back to running without timeout if neither exists. Fixes all hooks failing with exit 127 on macOS.

## [3.10.2] - 2026-04-08

### Fixed

- **Python type hint compatibility** — Added `from __future__ import annotations` to atlassian-cache MCP server files to fix `TypeError` with `X | None` union syntax on Python < 3.10:
  - `atlassian_cache/embeddings.py`
  - `atlassian_cache/cache.py`
  - `atlassian_cache/confluence_cache.py`
  - `tests/conftest.py`
  - `tests/integration/conftest.py`

## [3.10.1] - 2026-04-08

### Fixed

- **`hooks/plugin/session/start_prerequisite_check.py`** — Corrected atlassian-cache DB path from `CLAUDE_PLUGIN_DATA/atlassian.db` to `~/.cache/atlassian-pm/atlassian.db` (matches actual server path and all other hooks)

### Changed

- **`CLAUDE.md`** — Updated counts: hooks 74→69, references 26→27

## [3.10.0] - 2026-04-08

### Changed

- **`plugin.json`** — Added `"mcpServers": "./.mcp.json"` declaration; `atlassian-cache` MCP now auto-registers for all marketplace users via plugin manifest (OMC pattern)
- **`.mcp.json`** — Updated to use `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` variables; points directly to `run.sh` instead of the `run-mcp.sh` wrapper
- **`setup.sh`** — Removed dynamic `.mcp.json` writing, `run-mcp.sh` copy to data dir, and `~/.claude/CLAUDE.md` Atlassian settings injection; setup now only installs the venv and configures git filters

### Removed

- **`~/.claude/CLAUDE.md` injection** — Setup no longer writes Atlassian settings to the user's global CLAUDE.md; project-level CLAUDE.md handles all context
- **`run-mcp.sh` copy step** — Dead code removed from `setup.sh`; MCP resolves via `${CLAUDE_PLUGIN_ROOT}` directly

## [3.9.5] - 2026-04-08

### Removed

- **project-config-team-detail.json** — Removed optional team-detail config dependency from all 23 files (agents, skills, scripts, docs, hooks); `board_monitor.py` velocity now defaults to `None`; `velocity-tracker` agent deprecated (redirected to `retrospective-analyst`)

### Changed

- **`.mcp.json`** — Emptied (`mcpServers: {}`); MCP registration removed from project config entirely. Plugin system registers `atlassian-cache` via marketplace `.mcp.json` on install; dev mode (`--plugin-dir .`) no longer relies on project-level registration
- **`run-mcp.sh`** — New self-discovering MCP launcher wrapper; uses `find+sort -V` to locate latest plugin version automatically; installed to stable data dir (`$HOME/.claude/plugins/data/atlassian-pm-atlassian-pm/`) by `setup.sh`
- **`apm-doctor` check 10** — Now verifies `run-mcp.sh` launcher instead of team-detail config

### Performance

- **`atlassian-cache` MCP server** — 5 optimizations from 4-agent parallel analysis:
  - `migrations.py` v8: Added missing indexes on `confluence_links(to_page_id)` and `confluence_sprint_links(page_id)` — eliminates full table scans on reverse lookups
  - `server.py`: Fixed double JSON serialization in `cache_get_issue` hit/lazy-hit/miss paths — skips redundant `json.dumps` when `compact=False` (`raw_size = len(result)`)
  - `server.py`: `embeddings.find_similar` now runs via `asyncio.to_thread` — CPU-bound ML inference no longer blocks the event loop
  - `server.py`: Cache enrichment in `handle_cache_similar_issues` parallelized via `asyncio.gather` — N serial SQLite reads → concurrent
  - `server.py`: `_init()` now runs via `asyncio.to_thread` in `_lifespan` — DB migrations + model load no longer block event loop during startup

### Fixed

- **`pyrightconfig.json`** — Added to fix import resolution for `scripts/` and root paths; suppress unused parameter warnings across `monitor/` module

## [3.9.4] - 2026-04-07

### Fixed

- **run.sh** — Added `ATLASSIAN_PM_INTERNAL=true` to Python invocations; without this env var, `parse_stdin()` returned `None` in production, causing all hooks to silently no-op
- **run.sh** — Removed `date +%s.%N` (GNU coreutils only); macOS BSD `date` does not support nanosecond format, causing silent failures in hook duration logging

### Performance

- **Hook aggregator** (`hooks/aggregator.py`) — New framework runs multiple hook scripts in a single Python subprocess, eliminating ~28ms Python startup cost per aggregated hook
- **Aggregated entry points** — 14 sequential subprocess calls consolidated into 6 aggregated calls: `pre_bash.py` (3→1), `pre_jira_create.py` (2→1), `post_jira_create.py` (3→1), `post_jira_get.py` (2→1), `stop.py` (2→1), `subagent_start.py` (2→1); total savings ~224ms per workflow cycle
- Async hooks preserved as separate entries; aggregation applies to sync hooks only

### Tests

- 10 new unit tests for aggregator framework (188 total); covers Pattern A/B hooks, stdin sharing, context merging, blocking, missing files

## [3.9.3] - 2026-04-07

### Performance

- **hooks_state Phase 1A** — Consolidated all 8 `CREATE TABLE IF NOT EXISTS` statements into `_get_connection()` schema init; eliminates 1-2ms DDL overhead on every hot-path call (hr6_pending, cache_checked, qmd_searched, alignment_suggested, risk_assessed, skill_checkpoints, response_sizes, response_totals)
- **hooks_state Phase 1B** — Replaced `@functools.lru_cache(maxsize=128)` with custom `_StateCache` supporting selective per-key eviction; `set_state()` now invalidates only the affected `(session_id, key)` pair instead of clearing all 128 entries, preserving ~90% cache hit rate under write workloads

### Fixed

- **QA markdownlint** — Exclude `.omc/` and `.claude/` directories from markdownlint scan in `qa-check.sh`; add `.markdownlintignore` to prevent false failures from OMC research files

## [3.9.2] - 2026-04-07

### Fixed

- **apm-setup PLUGIN_ROOT resolution** — Use `$CLAUDE_PLUGIN_ROOT` directly per plugin-dev convention; remove fragile `find`-based cache fallback that caused inconsistent behavior between dev and marketplace installs
- **hooks_state backward compat** — Restore `_cache` shim and add `CREATE TABLE IF NOT EXISTS` guards in `cache_is_checked`, `hr6_get_pending`, and `response_size_get_stats` to prevent `OperationalError` on fresh DB sessions (regression from v3.9.0)
- **Hook tests** — Add `conftest.py` with `ATLASSIAN_PM_INTERNAL=true` fixture to fix 39 test failures introduced when internal guard was added in v3.9.0

## [3.9.1] - 2026-04-07

### Performance

- **Stop hooks optimization** — Optimized from 11 minutes to ~30-60ms (20,000x faster)
  - Replaced slow `pgrep -f` subprocess with instant PID file check (1634x faster)
  - Added fast-path exits when no state DB exists
  - Implemented `fast_mode` to skip JSON migration in stop hooks
  - Reduced SQLite timeout for stop hooks (5s → 1s)

### Fixed

- Added PID file creation in `run.sh` for reliable cache server detection
- Fixed stale PID file cleanup on process lookup failure
- Restored `_STATE_STR` for backward compatibility with tests

## [3.8.0] - 2026-04-07

### Fixed

- **Stop hooks hang** — Replaced blocking `fcntl.LOCK_EX` with non-blocking `LOCK_NB` + exponential backoff in `hooks_state.py` to prevent deadlocks during parallel subagent execution
- **Cache performance** — Added B-Tree indexes on `issue_key`, `cached_at`, and `sprint_id` to eliminate full table scans in SQLite

### Performance

- **MCP Cache Server Async Refactor** — Fully transitioned to asynchronous architecture using `asyncio.to_thread()` for all blocking SQLite and REST API I/O, preventing event loop contention and improving concurrency

## [3.7.1] - 2026-04-06

## [3.7.0] - 2026-04-06

### Changed

- **Setup category flattened** — `apm-setup` and `apm-doctor` moved from `skills/setup/` to `skills/` root
- **Hooks cleanup** — Removed 3 unused hooks: `pre_skill_usage_log`, `post_subtask_alignment_suggest`, `post_sprint_capacity_recheck`
- **Sprint alignment** — Documented `sprint-subtask-alignment.py` workflow in CLAUDE.md as instruction instead of hook

## [3.6.0] - 2026-04-06

### Changed

- **Skill namespace standardization** — All 35 skills renamed with `apm-` prefix for consistency and collision avoidance
  - Skills now invoked as `/atlassian-pm:apm-{skill-name}` (e.g., `/atlassian-pm:apm-create-task`)
  - Prevents conflicts with skills from other plugins
  - Updated all documentation, commands, agents, hooks, and references

## [3.5.0] - 2026-04-04

### Added

- **Model selection guide** — `references/model-selection.md` documents when to use haiku vs sonnet for agent tasks
- **Integration test infrastructure** — `tests/integration/` directory for end-to-end workflow testing
- **Hook test coverage** — Added tests for HR2, HR3, HR4, HR6, HR7 guard hooks (coverage ~20% → 80%)

### Changed

- **Agent tool whitelist standardized** — All 20 agents now use `allowed-tools:` field instead of mixed `tools:`/`allowed-tools:`
- **Quality-gate agent deprecated** — Added clear deprecation notice; skills should use `validate_adf.py` directly
- **File permissions hardened** — Cache database, logs, and state files now use `0o600` (owner-only)
- **Exit codes standardized** — All hooks now use: 0=pass, 1=fail/validation, 2=error/exception

### Fixed

- **CRITICAL: MCP lazy-load** — `sentence-transformers` (~500MB) now lazy-loads only when semantic search is used (cold start ~10s → ~100ms)
- **CRITICAL: HR5 state race condition** — Added `STATE_EXPIRY_SECONDS=3600` with `cleanup_stale_state()` to prevent session stalls from partial failures
- **MEDIUM: Import path fragility** — Hook scripts now use `$CLAUDE_PLUGIN_ROOT` env var with fallback to relative paths
- **MEDIUM: State timestamp tracking** — `set_state()` and `get_state()` now include automatic timestamp tracking
- **LOW: Pyright type fixes** — Fixed type annotations in `pre_wip_limit_check.py` and `pre_qmd_auto_search.py`

### Performance

- **Cache hook consolidation** — 4 cache-related hooks consolidated into 1, reducing per-call overhead by ~300ms

## [3.4.0] - 2026-04-03

### Added

- **Token metrics in cache server** — `cache_stats` now returns `tokens_saved`, `tokens_by_tool`, and `avg_response_reduction` for observability
- **Cache-first enforcement hook** — `pre_cache_first_warning.py` warns when base MCP tools used instead of cache equivalents (80-95% token savings)
- **Response size logging** — `post_response_size_log.py` tracks token usage patterns for 15 MCP tools
- **Token estimation utility** — `scripts/api/estimate_tokens.py` estimates token costs before operations (get_issue, search, sprint, confluence)
- **Token efficiency documentation** — `feedback_token_efficiency.md` documents hierarchy, MCP silent failures, and cache-first rules

### Changed

- **13 agents updated** — Added "Cache-First Read Operations" section with tool preference table and fallback guidance
- **tool-selection.md** — Added Token Efficiency Hierarchy table and MCP Silent Failures reference
- **hooks_state.py** — Added `cache_warning_count()`, `cache_warning_increment()`, `response_size_track()`, `response_size_get_stats()`

### Fixed

- **Hook tests** — Added `setUp` to clear test state between runs, fixing intermittent test failures

## [3.3.0] - 2026-04-01

### Changed

- **CLAUDE.md optimized to 100/100** — full command table (11 copy-paste commands), data flow line, categorized docs index, create-task modes reference with Thai headings, 6 common mistakes (added ADF panel + MCP assignee gotchas), compressed Context Management + Efficiency to tables
- Size: 7.8KB → 8.1KB (all additions are high-signal content)

## [3.2.0] - 2026-04-01

### Removed

- **4 deprecated skills deleted** — `create-story`, `analyze-story`, `update-story`, `update-subtask` (replaced by `create-task` and `update-task`)
- Skills count: 39 → 35

## [3.1.0] - 2026-04-01

### Removed

- **4 dead hooks** — `pre_hr10_subtask_sprint_guard`, `pre_hr8_subtask_date_guard`, `pre_story_size_guard`, `post_auto_subtask_suggest` (will never fire in Epic→Task hierarchy)

### Changed

- **vibe-plan** — rewritten from Epic→Story→Subtask to Epic→Task (2-level)
- **blueprint** — Phase 8 backlog_map `stories[]`→`tasks[]`, handoff→`/create-task`
- **12 skills** updated: update-epic, epic-health, refine-epic, sync-artifacts, release-notes, status, create-testplan + terminology fixes across all
- **16 hooks** updated: story→task, subtask→task terminology in messages and type checks
- **pre_adf_structure_validate** — panel check flipped: now warns when panel IS present (forbidden)
- **Tests** — 4 skill redirect tests updated for v3.0.0

### Deprecated

- `update-story`, `update-subtask` — use `update-task` instead

## [3.0.0] - 2026-04-01

### Breaking Changes

- **Epic → Task hierarchy** — 2 levels only (no Story, no Subtask). Task is the value unit with narrative + ACs + file paths.
- **No ADF panel nodes** — All templates use heading + paragraph + bulletList + table only. Panels removed to fix Jira rendering issues (blockquote instead of colored boxes).
- **Thai headings** — สรุปภาพรวม, คุณค่าทางธุรกิจ, ลูกค้าเห็นอะไร?, เงื่อนไขที่ต้องผ่าน, etc. No emoji in headings.
- **Unified Task template** — 5 modes: feature (default), qa, bug, spike, chore. Replaces separate Story + Subtask + Task templates.
- **Deprecated skills** — `create-story` and `analyze-story` replaced by `create-task` (feature mode)

### Removed

- `templates-story.md` — merged into `templates-task.md` (feature mode)
- `templates-subtask.md` — merged into `templates-task.md`
- ADF panel nodes, emoji in headings, horizontal rules, numbered sections
- RICE Score, Domain Model, Progress, Links table from Epic template

### Changed

- Epic template: 9 sections → 6 sections (Thai headings, all required)
- `create-task` skill: added mode selection (--qa, --bug, --spike, --chore) with auto-detect
- `create-testplan`: creates [QA] Task (not Subtask), uses Thai headings
- `create-epic`: updated to Thai headings, references Tasks instead of Stories
- Verification checklist: panel checks → heading checks, Story/Subtask checks → unified Task checks
- HR5/HR8/HR9/HR10: updated from Subtask to Task terminology

## [2.7.0] - 2026-04-01

### Added

- **PRD template for `/create-doc`** — New `prd` template type: Executive Summary, User Stories (P1/P2/P3), Functional Requirements (FR-xxx), Non-Functional Requirements (NFR-xxx), Success Criteria (SC-xxx), Assumptions & Constraints, Edge Cases
- **Performance & Scale section in Blueprint S4** — M/L tier blueprints now require target QPS, latency budget (p95/p99), and data volume projection; new B4a verification check
- **Phase-based task grouping in `/analyze-story`** — Subtasks classified into Setup → Foundational → Feature → Polish phases with `[P]` parallelization markers and dependency summary
- **Ambiguity Check phase in `/create-story`** — Phase 1.5 (--thorough only): surfaces ≤5 clarifying questions on ambiguous ACs before drafting
- **Phase Classification reference** in `templates-subtask.md` for stories with ≥4 subtasks

## [2.6.17] - 2026-04-01

### Fixed

- **create-testplan minimal-first ADF** — AC Coverage matrix (Phase 2) is now internal planning only; Jira ADF output reduced to Test Objective + Test Cases + optional Reference, consistent with v2.6.16 QA template simplification

## [2.6.16] - 2026-04-01

### Changed

- **Improved narrative tone for non-technical audiences** — All templates now write output readable by PMs, designers, and stakeholders (not just engineers)
- **Minimal-first template approach** — Default ADF includes only required sections (Objective + ACs); optional sections (Scope, Reference, Technical Notes) are snippets with clear inclusion conditions
- **Plain language for complex concepts** — Epic Domain Model section rewritten from DDD jargon to plain causality format ("เมื่อ X → Y"); removed unnecessary technical terms from Business Value bullets
- **Updated Content Budget** — Enforces minimal required sections only; optional sections added only when real data exists (no placeholders)
- **Simplified QA template** — Removed AC Coverage table from default; reduced to Test Objective + Test Cases + optional Reference

## [2.6.15] - 2026-03-31

### Fixed

- **Root cause found and fixed**: removed `"mcpServers": "./.mcp.json"` from `plugin.json`. This field caused Claude Code to read `.mcp.json` a second time from the cache dir (installPath) without `${CLAUDE_PLUGIN_ROOT}` expansion, producing the ghost `atlassian-cache: ${CLAUDE_PLUGIN_ROOT}/... ✗ Failed to connect` entry. The standalone `.mcp.json` at plugin root (read once from marketplace dir with full expansion) is sufficient — same pattern used by all other working plugins (e.g. `claude-mem`).

## [2.6.14] - 2026-03-31

### Fixed

- Removed incorrect cache dir `.mcp.json` clearing from `bump-version.sh` and `SessionStart` hook — these were based on a wrong assumption. Correct behavior is full server config in source `.mcp.json` (same as all other working plugins like `claude-mem`); Claude Code handles de-duplication when `${CLAUDE_PLUGIN_ROOT}` expands correctly in cache context.

## [2.6.13] - 2026-03-31

### Fixed

- Reverted incorrect "empty source `.mcp.json`" approach — correct fix is to keep full server config in source `.mcp.json` (same as `claude-mem` and other working plugins). Claude Code de-duplicates cache and marketplace entries when `${CLAUDE_PLUGIN_ROOT}` expands correctly; having full config in both dirs results in exactly one entry. Removed marketplace dir writing from `setup.sh` and `bump-version.sh`.

## [2.6.12] - 2026-03-31

### Fixed

- **Root fix for ghost `atlassian-cache: ${CLAUDE_PLUGIN_ROOT}/... ✗ Failed to connect`** — Claude Code loads `.mcp.json` before SessionStart hooks run, so hook-based clearing was always too late. Solution: source `.mcp.json` is now empty (`{"mcpServers": {}}`), so the cache dir copy is always empty too. `setup.sh` and `bump-version.sh` write the full server config directly to the marketplace dir (the only place `${CLAUDE_PLUGIN_ROOT}` is expanded). No restart dance required after plugin updates.

## [2.6.11] - 2026-03-31

### Fixed

- `SessionStart` hook now auto-clears cache dir `.mcp.json` files on every startup — prevents ghost `atlassian-cache: ${CLAUDE_PLUGIN_ROOT}/... ✗ Failed to connect` entry for all users after `claude plugin update`. No manual action required.

## [2.6.10] - 2026-03-31

### Fixed

- `bump-version.sh`: cache dir `.mcp.json` clearing now polls up to 10s for async download to complete, then clears all cached versions (not just the new one) — prevents ghost `atlassian-cache: ${CLAUDE_PLUGIN_ROOT}/... ✗ Failed to connect` entry after every release.

## [2.6.9] - 2026-03-31

### Fixed

- Duplicate `atlassian-cache: ${CLAUDE_PLUGIN_ROOT}/... ✗ Failed to connect` entry — Claude Code loads `.mcp.json` from **both** marketplace dir (with variable expansion + `plugin:` prefix) and cache dir (no expansion, no prefix). Fixed by clearing cache dir `.mcp.json` after each release in `bump-version.sh`.

## [2.6.8] - 2026-03-31

### Fixed

- `atlassian-cache` MCP server "Failed to connect" — root cause: Claude Code reads `.mcp.json` from the **marketplace dir** only (not cache). Only marketplace-loaded servers get the `plugin:` namespace and `${CLAUDE_PLUGIN_ROOT}` expansion. `bump-version.sh` was incorrectly clearing the marketplace `.mcp.json` after every release, breaking the server for all users.
- `bump-version.sh`: removed marketplace `.mcp.json` clearing step. Cache `.mcp.json` files remain empty to avoid duplicate registration.

## [2.6.7] - 2026-03-31

### Fixed

- `atlassian-cache` MCP registration — restored to official `.mcp.json` plugin pattern using `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` variables (confirmed supported per Claude Code plugin docs). Previous workaround (`setup.sh` writing to `~/.claude.json`) was non-standard and broke for users who installed the plugin without running setup manually.
- Added `mcp-servers/atlassian-cache/run.sh` — portable `uv` locator that checks `PATH` first, then common per-user install locations (`~/.local/bin`, `~/.cargo/bin`, `/opt/homebrew/bin`), fixing "uv not found" in MCP server subprocess environments.
- Removed `~/.claude.json` manipulation from `setup.sh` — venv installation is still performed by setup; MCP registration is now automatic via `.mcp.json`.

## [2.6.6] - 2026-03-31

### Fixed

- `atlassian-cache` MCP server duplicate warning ("skipped — same command/URL") — root cause: Claude Code loads `.mcp.json` from both marketplace and cache dirs. `bump-version.sh` now clears the marketplace `.mcp.json` after each release so only the cache dir copy remains active.

## [2.6.5] - 2026-03-31

### Added

- ci: add GitHub Actions QA workflow (9 gates: shellcheck, markdownlint, plugin.json, SKILL.md frontmatter, agent frontmatter, hooks.json references, Python pytest, CHANGELOG version, required files)

### Fixed

- fix(hooks): run.sh fallback now uses silent exit 0 instead of invalid JSON output

## [Unreleased]

## [2.6.2] - 2026-03-31

### Fixed

- `.mcp.json` — use `cwd: "${CLAUDE_PLUGIN_ROOT}"` with relative paths for `args` so the server resolves correctly in both plugin context (CLAUDE_PLUGIN_ROOT expanded) and project context (cwd defaults to project root). Also add explicit `PATH` to env so `uv` is found regardless of how Claude Code spawns the subprocess.

## [2.6.1] - 2026-03-31

### Fixed

- `.mcp.json` — add `UV_PROJECT_ENVIRONMENT=${CLAUDE_PLUGIN_DATA}/venv` so the atlassian-cache MCP server uses the pre-installed venv from `/atlassian-pm:setup` instead of creating a new one on each restart. Fixes "Failed to connect" on plugin install/update.

## [1.8.0] - 2026-03-25

### Added

- `start-ticket` skill — DLC workflow shortcut: reads ticket AC + transitions to In Progress; tiered status guard (warn for In Progress/Reopened, block for Done/Closed); handles hard WIP gate via `CLAUDE_WIP_CONFIRMED` env var
- `ship-to-qa` skill — DLC workflow shortcut: auto-detects PR via `gh pr view`, constructs CF Pages preview URLs from `environments.preview` config (branch slug, 28-char truncation), posts Jira comment (PR + preview + optional staging BE), transitions to Ready for QA with WIP gate enforcement
- `environments.preview` in `project-config.json.template` — CF Pages project names for branch preview URL construction (`admin`, `web` keys)
- "Ready for QA" added to QA column `statuses` in `project-config.json.template` — ensures `pre_wip_limit_check` WIP gate fires on ship-to-qa transitions

## [1.7.0] - 2026-03-25

### Added

- `flow-check` skill — board health snapshot + Scrumban replenishment (WSJF-approximated pull queue)
- Hard WIP gate hook (`plugin/guards/pre_wip_limit_check.py`) — blocks `jira_transition_issue` until Claude confirms WIP count below limit (DoR/DoD pattern with `CLAUDE_WIP_CONFIRMED=<key>:<col>` env var)
- Auto-trigger hook (`plugin/session/post_done_flow_check.py`) — injects `/flow-check --replenish` imperative on Done transitions
- `workflow` + `board.columns` config in `project-config.json.template` — Scrumban config schema with WIP limits per column and `kanban_board_id`

### Removed

- `hooks/dev/pre_wip_limit_check.py` (soft warn) — replaced by hard gate in `plugin/guards/`

### Fixed

- `scripts/setup.sh` — removed `--extra embeddings` flag (extra was removed from `mcp-servers/atlassian-cache/pyproject.toml`)

### Breaking

- WIP enforcement is now a hard block (was soft warn). Claude must confirm WIP count before transitioning. Set `CLAUDE_WIP_CONFIRMED=<key>:<column>` after verifying count is below limit.

## [1.6.2] - 2026-03-23

### Changed

- **Domain Expert Notes quality audit — all 32 skills** — systematic audit across PM (15 skills), Engineer (11 skills), QA (3 skills), Setup (2 skills), and Utilities (5 skills); 4 Adequate Engineer skills and 15 PM/remaining skills elevated to Strong with specialist-level framework citations, primary author attributions, and causal reasoning
- **Citation integrity fixes** — removed 4 fabricated/unverifiable references: "University of Waterloo Atlassian JQL Best Practices" (search-issues), "32% of agile teams link OKRs" (create-epic), "Infisical Local Development Secrets Guide" (setup), "BetterStack Health Check Guide" (doctor); replaced with NIST SP 800-57 Part 1 Rev 5, Beyer et al. SRE Book Ch.17, 12-Factor App (Wiggins 2011), and real Atlassian Developer Docs
- **Framework attribution completeness** — added primary author + year + venue for: JTBD (Christensen 1997 vs Ulwick ODI 2005 as distinct frameworks), T-shaped skills (Guest 1991 + Tim Brown/IDEO 2010), SMART Goals (Doran 1981 Management Review), Goodhart's Law (1975), 4Ls (Diana Larsen), Walk-the-Board (Scrum.org / Sutherland 2014), Docs as Code (Anne Gentle 2017), CLM (AIIM/Gartner), Keep a Changelog (Olivier Lacan)
- **Numeric threshold disambiguation** — plan-release: 3 distinct buffer concepts separated (10% velocity buffer / 10-15% buffer sprint / 20% carry-over pre-allocation); spec-to-stories: cosine similarity tiers clarified (>0.8 auto-flag vs 0.7–0.8 manual review, <0.7 distinct)
- **P1 escalation consistency** — bug-triage: all 3 triggers (PII/auth bypass, payment failure, database corruption) now share base actions (freeze deployments + Tech Lead escalation) with path-specific follow-on steps
- **Empirical observation labeling** — atlassian-scripts: `~15% MCP parent-drop` statistic marked as "observed empirically — not a documented Atlassian behavior"
- **qa-full Step 0 Guard** — idempotency check added before create-testplan invocation: detects existing `[QA]` sub-tasks and routes to 3 options (A: execute existing / B: update+execute / C: create new); prevents duplicate test plans per sprint
- **README counts corrected** — 31→32 skills, 18→20 agents, 9→10 commands; `test-case-runner` and `bug-evidence-writer` added to agents architecture tree

## [1.6.1] - 2026-03-23

### Added

- **9 orchestration Commands** — end-to-end workflow chains in `.claude/commands/`: `story-full`, `epic-full`, `blueprint-full`, `bug-full`, `story-analyze-full`, `sprint-plan-full`, `sprint-close-full`, `release-full`, `tech-debt-full`; each chains existing skills with confirmation gates
- **Parallel dispatch annotation** — `> **🟢 PARALLEL**` and `> **🟢 AUTO + PARALLEL**` blockquote convention in skill/agent phases marks independent tool calls for single-message dispatch; documented in CLAUDE.md Efficiency section and applied across 11 skill/agent files
- **HR5 Stop hook** (`stop_hr5_pending_check.py`) — session-end guard that flags any subtask creation where parent verification was not confirmed; prevents orphaned subtasks from being silently abandoned
- **Skill usage telemetry hook** (`pre_skill_usage_log.py`) — PreToolUse:Skill hook logs skill invocations with timestamp, model, and session ID for usage analysis
- **Model tracking hook** (`post_event_model_track.py`) — PostToolUse async hook tracks domain model events per session
- **Session artifact cleanup hook** (`start_cleanup_artifacts.py`) — SessionStart hook removes stale task artifacts beyond configurable TTL
- **`<important if>` conditional tags on HR1–HR10** in CLAUDE.md — context-sensitive rule loading; only the relevant rules surface in context based on the current operation
- **Dynamic config injection** — 4 skills now read `project_key` and `board_id` directly from `.claude/project-config.json` at runtime instead of hardcoded placeholders
- **Skill trigger descriptions (P3 pattern)** — all 31 skills now have `Triggers:`, `Use when:`, `Do NOT use for:` in their `description:` block with Thai trigger phrases for bilingual discovery
- **Goal-oriented phase headers (P9 pattern)** — create-story, analyze-story, blueprint, close-sprint, plan-sprint phases now open with `**Goal:**`, `**Required inputs:**`, `**Constraints:**`, `**Output:**`

### Changed

- **README restructured** — 3 distinct sections (Commands → Skills → Agents) ordered by real usage flow; Commands section added with fast-path table; Agents section clarified as internal subagents
- **Workflow diagram updated** — added Commands fast-path node, `spec-to-stories` branch, `/bug-triage → /create-testplan` split from `/create-task`, and `close-sprint → retrospective-analyst` in sprint subgraph
- **`references/` count corrected** — 19 → 24 documents; missing entries (`hr-rules.md`, `hooks-reference.md`, `subtask-design-patterns.md`, `update-workflow.md`) added to skills/README.md shared references table
- **Hook count corrected** — 43 → 46 hooks; 5 previously undocumented session hooks added to hooks/README.md workflow and event tables

### Fixed

- **Hooks library refactor** — replaced inline duplication across 6 hook files with `hooks_lib` helpers (`get_tool_response`, `get_issue_keys_from_text`, `is_in_progress`); fixed `pre_dod_check.py` stdin API and config path
- **Hooks performance** — eliminated redundant `mkdir`/`utime`/`stat` calls per save with path caching; lazy-load QMD collections to avoid config reads on every hook invocation
- **Parallel script output** — `audit_confluence_pages.py` and `sprint_health_record.py` use `ThreadPoolExecutor` with atomic print for deterministic parallel output
- **P1 skill routing fixes** — verify-issue context clarification, blueprint branch logic, retrospective-analyst invocation, release-full and sprint-plan-full gate additions
- **Missing frontmatter fields** — `argument-hint` added to map-dependencies (was the only skill missing it); `x-compatibility: []` added to doctor, setup, atlassian-scripts

## [1.5.2] - 2026-03-22

### Fixed

- `scripts/test-install.sh` — removed `--extra embeddings` flag from `uv sync` call; `embeddings` optional-dependency was removed from `pyproject.toml` causing Phase 2 venv sync to fail (pipeline: 17→18 passed, 0 failed)

## [1.5.1] - 2026-03-22

### Fixed

- `hooks/plugin/session/check_prerequisites.sh` — corrected cache DB default path check to use `atlassian-pm-atlassian-pm` data dir; false-positive warning on fresh session start after clean install

## [1.5.0] - 2026-03-22

### Added

- **`allowed-tools` scope restriction on all 31 skills** — forked context skills now declare minimal MCP tool sets using fully qualified names (`mcp__<server>__<tool>`), preventing tool sprawl in subagent contexts
- **`effort` field on all 31 skills** — overrides session reasoning level per skill: `low` (doctor, setup, assign-issue, search-issues), `high` (create-story, analyze-story, plan-sprint, blueprint, spec-to-stories, sync-artifacts, close-sprint, plan-release, scan-tech-debt), `medium` (all others)
- **`context: fork` on 11 additional skills** — create-epic, update-epic, update-story, create-task, create-testplan, update-subtask, update-task, bug-triage, create-doc, update-doc, release-notes now run in isolated subagent contexts
- **`agent:` field on all 16 existing forked skills** — explicit agent type (`general-purpose` or `Explore`) per skill
- **`disable-model-invocation: true`** on doctor and setup — prevents accidental auto-invocation
- **Domain expert notes** added to all 31 skills — industry frameworks, key metrics, expert decision criteria, and common failure modes per skill
- **`quality-gate` agent** model upgraded from Haiku to Sonnet — higher accuracy QG scoring
- **`atlassian-cache` v1.0.0** — unified Jira + Confluence cache with 21 MCP tools; replaces `jira-cache-server`
  - Confluence tools: `cache_get_confluence_page`, `cache_get_confluence_children`, `cache_get_confluence_section`, `cache_search_confluence`, `cache_find_confluence_related`, `cache_sprint_confluence`, `cache_cross_search`, `cache_refresh_confluence`, `cache_invalidate_confluence`
  - Sprint tools: `cache_similar_sprints` — sprint goal vector search; `cache_sprint_issues` bulk sprint lookup
  - DB renamed: `jira.db` → `atlassian.db`; env vars renamed: `JIRA_CACHE_*` → `ATLASSIAN_CACHE_*`; class renamed: `JiraCache` → `AtlassianCache`
- **Write-invalidation hook** — `cache_write_invalidate.py` auto-clears cache entries after any MCP Atlassian write (HR6 enforcement)
- **Lazy version-check invalidation** — Jira `updated` field triggers cache refresh without explicit `cache_invalidate` call
- **Sprint goal embedding** (`cache_similar_sprints`) — vector search over sprint goals for sprint planning context
- **Confluence page-level embedding** — title + labels embedded for page retrieval via `cache_search_confluence`
- **Section heading in embeddings** — confluence section text now includes heading prefix for richer retrieval

### Changed

- `update-story` skill moved from `task/` → `story/` category (correct grouping)
- Token-optimize: 13 reference files (~1,432 tokens saved), 4 mermaid files (~2,930 tokens saved), 8 agent files (~700 tokens saved)
- `atlassian-cache`: renamed from `jira-cache-server` throughout all references

### Fixed

- `impact_suggester`: correct label extraction using `str.replace` instead of fragile regex; pre-compile regex at module load
- `thai_validator`: remove unused `KEEP_ENGLISH` set (93 dead strings)
- `cache_reindex`: remove dead `jira_api` glob import; update tool description
- `store_batch` calls wrapped in `asyncio.to_thread` — fixes event loop contention in async context
- `cache_sync`: validate `project_key` before sync; wrap blocking I/O in `asyncio.to_thread`
- `adf_validator`: pre-extract all sections once per `validate` call (was re-extracting per field)
- `jira_batch_update`: batch subtask type-check; parallelize updates with `ThreadPoolExecutor`
- `sprint_rank_by_date`: paginate sprint issue fetch to handle sprints with >50 issues
- `clear_sprint_dates`: parallelize Jira updates with `ThreadPoolExecutor`
- `sprint_subtask_alignment`: cache `estimate_oe` result; pre-compute field lookups

### Performance

- 17 performance and correctness fixes across `atlassian-cache`, `scripts/api/`, and `scripts/sprint/`

## [1.4.0] - 2026-03-21

### Added

- **`atlassian-cache` MCP server** (initial integration) — Jira issue cache with vector search, in-session deduplication, and 9 Confluence MCP tools
- `cache_find_related`, `cache_reindex`, `cache_sync` tools
- In-session deduplication and compact list format for 20+ issues
- Resilient hook runner (`hooks/plugin/session/`) — handles stale `CLAUDE_PLUGIN_ROOT` after plugin update mid-session

### Changed

- **12 skills renamed** to verb-noun standard (e.g. `story-analyze` → `analyze-story`) with Good/Bad usage examples added to each SKILL.md
- `bump-version.sh` — removed `claude plugin update` call to prevent session hook errors when bumping version in the active session

### Fixed

- Hook runner stale path warning after plugin update without session restart
- `test-install.sh` — warn when install upgrades plugin but session `CLAUDE_PLUGIN_ROOT` still points to old version

## [1.3.1] - 2026-03-21

### Fixed

- `plugin.json` skills declaration changed from single string `"./skills/"` to explicit array of 7 category paths — required for Claude Code to discover skills in category subdirectories after the v1.3.0 restructure

## [1.3.0] - 2026-03-21

### Added

- `scripts/test-install.sh` — automated install validation pipeline: remove → install → setup simulation → doctor (18 checks, 11 doctor checks); validates config backup/restore and venv recreation
- `scripts/bump-version.sh` fully automated non-interactive mode — no prompts, reads title from latest commit, runs end-to-end

### Changed

- **Skills reorganized into 7 category subdirectories:** `setup/`, `epic/`, `story/`, `task/`, `sprint/`, `confluence/`, `utilities/` — slash-command skills only in `skills/`
- **`references/`** moved from `skills/shared-references/` to project root — shared docs now at `references/` (24 files), skills reference via `../../../references/`
- **Scripts consolidated:** `atlassian-scripts/` and `scripts/` merged into unified `scripts/` with `api/`, `lib/`, `sprint/`, `analysis/`, `docs/` subdirectories
- **Thin SKILL.md wrapper** at `skills/utilities/atlassian-scripts/SKILL.md` — entry point pointing to `scripts/api/` and `scripts/docs/`
- `.mcp.json` PYTHONPATH updated: `skills/atlassian-scripts` → `scripts`
- All internal `sys.path` references in `scripts/sprint/*.py` updated
- Hook paths updated: `hooks/plugin/guards/pre_hr1_quality_gate.py`, `pre_hr4_confluence_macro_guard.py`
- `mcp-servers/atlassian-cache-server/server.py` sys.path updated to use `scripts/`

## [1.1.0] - 2026-03-20

### Added

- **4 new Layer 3 Synthesis agents:**
  - `estimation-calibrator`: SP calibration from historical similar issues via `cache_similar_issues`; HIGH/MEDIUM/LOW confidence; adjustment rules for auth/payment/integration/large-scope stories
  - `risk-forecaster`: 4-dimension delivery risk scoring (Capacity 30%, Complexity 25%, Dependency 25%, Team 20%); named mitigations; adjusted risk scenario after applying mitigations
  - `adf-surgeon`: structural ADF repair with 10 known Jira quirks (QUIRK-1–QUIRK-10); content-safe (never changes text); auto-fixable vs needs-human-judgment classification
  - `team-pattern-advisor`: multi-sprint strategic pattern analysis across 5 dimensions (bottlenecks, estimation accuracy, QA rejections, carry-over culprits, velocity seasonality); only reports patterns with ≥3 data points

- **Skill wiring for new agents:**
  - `create-story` Phase 7b: estimation-calibrator invoked after subtask design before ITERATE gate
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
- Hook matchers updated to use canonical plugin MCP tool names (`mcp__plugin_atlassian-pm_atlassian-cache-server__`)
- `post_subtask_alignment_suggest.py`: fixed SPRINT_TOOLS set comparison with correct tool names
- `setup.sh`: corrected CONFIG_TEMPLATE path (`config/` not `.claude/`)
- `setup.sh`: added dependency checks at top (acli, uv, atlassian-cache-server venv)
- `setup.sh`: skip git filter config when not in a git repository (cache install)
- `sync-skills`: replaced hardcoded dev path with script-relative `SRC_BASE`
- `skills/setup/SKILL.md`: replaced hardcoded version fallback with dynamic `find` for latest cached version
- `hooks/hooks.json`: fixed all `mcp__atlassian-cache-server__` matchers to use full plugin namespace
- `scripts/sprint/*.py` added to `.gitattributes` filter coverage

### Added

- `hooks/config_loader.py`: shared config loader utility for hooks
- `hooks_state.py`: derives `QMD_COLLECTIONS` dynamically from `project-config.json`
- `pre_prompt_issue_prefetch.py`: derives `KEY_RE` and `PROJECT_KEY` from `project-config.json`
- `skills/setup/SKILL.md`: guided first-time setup skill (`/atlassian-pm:setup`)
- `.claude-plugin/marketplace.json`: plugin marketplace catalog
- Legacy cache migration: removes `~/.cache/jira-generator` on setup

### Changed

- MCP atlassian-cache-server DB path now uses `CLAUDE_PLUGIN_DATA` for persistence across plugin updates
- `setup.sh` and `skills/setup/SKILL.md`: venv installed in `CLAUDE_PLUGIN_DATA/venv` when available
- SessionStart hook added for automatic venv reinstall detection on plugin update
- `hooks/hooks.json`: `SubagentStart` event handler added
- `README.md`: added Online Installation section

## [1.0.0] - 2026-03-01

### Added

- Initial release as `atlassian-pm` plugin
- 21 skills: create-story, plan-sprint, verify-issue, analyze-story, update-story, sync-artifacts, and more
- 8 subagents: story-writer, sprint-planner, quality-gate, alignment-checker, and more
- Hook system: 37 hooks enforcing HR1–HR10 guardrails
- atlassian-cache-server MCP: SQLite-backed Jira issue cache with semantic search
- atlassian-scripts: 17 Python scripts for Jira/Confluence REST API operations
- Git smudge/clean filter for placeholder ↔ real value conversion
