# Markdown Token Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ลด token consumption ใน skills/, docs/mermaid/, agents/ ประมาณ 30,000–35,000 tokens (16–18%) โดยไม่ทำให้ content ที่จำเป็นหาย

**Architecture:** แบ่งเป็น 3 phases ตาม risk level — Phase 1 (quick wins, ไม่มี dependency), Phase 2 (content restructuring, medium risk), Phase 3 (structural changes, highest risk). แต่ละ phase commit แยก ให้ revert ได้ถ้าพัง

**Tech Stack:** Markdown, Python (สำหรับ token counting), bash (wc -m สำหรับ char counts)

---

## File Map

### Files to MODIFY

- `skills/shared-references/writing-style.md` — remove empty Thai column
- `skills/shared-references/jql-quick-ref.md` — remove ORDER BY warning block
- `skills/atlassian-scripts/script-reference.md` — remove duplicate Script Selection Guide
- `skills/shared-references/mermaid-guide.md` — trim Edge Animation to 1 consolidated example
- `skills/feature-blueprint/SKILL.md` — replace inline B1-B8 table with reference to verification-checklist.md
- `skills/shared-references/sprint-frameworks.md` — remove Sources citation section
- `skills/shared-references/verification-checklist.md` — convert checkbox-in-code-block to compact tables; remove B1-B8 (owned by feature-blueprint)
- `skills/shared-references/team-capacity.md` — remove roster/bus-factor/growth-tracks/cross-training (duplicates project-config.json); keep formulas + multipliers only
- `skills/story-full/SKILL.md` — remove duplicated TL decomposition list (ref analyze-story instead)
- `skills/analyze-story/SKILL.md` — (same TL list — keep canonical here)
- `skills/refine-feature/SKILL.md` — extract 8 inline agent prompts to new reference file
- `docs/mermaid/flowchart.md` — trim edge animation, vendor-specific :::note/:::tip blocks, new shape examples
- `docs/mermaid/sequenceDiagram.md` — trim CSS stylesheet sections, configuration parameter tables
- `docs/mermaid/stateDiagram.md` — trim CSS/style sections
- `docs/mermaid/architecture.md` — trim if bloated
- `docs/mermaid/gantt.md` — trim if bloated
- `docs/mermaid/packet.md` — already small (508 tokens), skip

### Files to CREATE

- `skills/refine-feature/references/agent-prompts.md` — extracted prompts from refine-feature/SKILL.md

### Files NOT to touch (agents/ all well-sized, SKILL.md refs maintained)

- All `agents/*.md` — already optimal
- `.claude/rules/mermaid.md` — maintain existing doc references, just content inside docs improves

---

## Phase 1: Quick Wins (ไม่มี dependency, risk ต่ำ)

### Task 1: writing-style.md — Remove empty Thai column

**Files:**

- Modify: `skills/shared-references/writing-style.md`

- [ ] **Step 1: Read & locate the Thai column**

```bash
grep -n "| - |" skills/shared-references/writing-style.md | head -20
```

ควรเห็น rows ที่มี `| - |` ในคอลัมน์ Thai

- [ ] **Step 2: Remove Thai column from table**

หาตาราง "Commonly Used Transliterations" แล้ว:

- ลบ `| Thai |` column header
- ลบ `| - |` column separator
- ลบ `| - |` content ในทุก row

ใช้ Edit tool แก้ทีละ row หรือ rewrite section นั้น

- [ ] **Step 3: Verify**

```bash
grep -c "| - |" skills/shared-references/writing-style.md
```

Expected: `0`

- [ ] **Step 4: Commit**

```bash
git add skills/shared-references/writing-style.md
git commit -m "docs: remove empty Thai column from writing-style transliteration table"
```

---

### Task 2: jql-quick-ref.md — Remove ORDER BY warning block

**Files:**

- Modify: `skills/shared-references/jql-quick-ref.md`

- [ ] **Step 1: Read & locate ORDER BY warning**

```bash
grep -n "ORDER BY\|❌\|✅" skills/shared-references/jql-quick-ref.md | head -30
```

- [ ] **Step 2: Remove warning block**

ลบ block ที่อธิบาย ORDER BY restriction (ประมาณ 15 บรรทัด) เพราะ HR2 enforce โดย hook อยู่แล้ว
แทนที่ด้วยบรรทัดเดียว: `> **HR2:** Never use ORDER BY with parent= or key in (...) — hook enforced`

- [ ] **Step 3: Verify — content ยังครบ**

```bash
wc -m skills/shared-references/jql-quick-ref.md
```

ควรลดลง ~500 chars

- [ ] **Step 4: Commit**

```bash
git add skills/shared-references/jql-quick-ref.md
git commit -m "docs: replace verbose ORDER BY warning with 1-line HR2 reference (hook-enforced)"
```

---

### Task 3: script-reference.md — Remove duplicate Script Selection Guide

**Files:**

- Modify: `skills/atlassian-scripts/script-reference.md`

- [ ] **Step 1: Read both files — confirm duplication**

```bash
grep -n "Script Selection Guide\|Decision" skills/atlassian-scripts/script-reference.md
grep -n "Script Selection Guide\|Decision" skills/atlassian-scripts/SKILL.md
```

- [ ] **Step 2: Remove duplicate section from script-reference.md**

ลบ "Script Selection Guide" section ออกจาก `script-reference.md` เพราะมีอยู่ใน `SKILL.md` แล้ว
แทนที่ด้วย: `> Script selection guide: see atlassian-scripts/SKILL.md — Decision section`

- [ ] **Step 3: Verify character count dropped**

```bash
wc -m skills/atlassian-scripts/script-reference.md
```

- [ ] **Step 4: Commit**

```bash
git add skills/atlassian-scripts/script-reference.md
git commit -m "docs: remove duplicate Script Selection Guide from script-reference.md (canonical in SKILL.md)"
```

---

### Task 4: sprint-frameworks.md — Remove citation URLs

**Files:**

- Modify: `skills/shared-references/sprint-frameworks.md`

- [ ] **Step 1: Find Sources section**

```bash
grep -n "Source\|http\|reference" skills/shared-references/sprint-frameworks.md | head -20
```

- [ ] **Step 2: Remove Sources section**

ลบ section ที่มี citation URLs ทั้งหมด (ประมาณ 6 URLs, ~80 tokens) — ไม่มีประโยชน์ใน AI context

- [ ] **Step 3: Check for duplicate content with plan-sprint/SKILL.md**

```bash
grep -c "pre-meeting\|checklist\|before sprint" skills/shared-references/sprint-frameworks.md
grep -c "pre-meeting\|checklist\|before sprint" skills/plan-sprint/SKILL.md
```

ถ้ามี overlap ให้ลบ sprint-frameworks.md section ออก

- [ ] **Step 4: Commit**

```bash
git add skills/shared-references/sprint-frameworks.md
git commit -m "docs: remove citation URLs and duplicate checklist from sprint-frameworks.md"
```

---

### Task 5: feature-blueprint/SKILL.md — Replace inline B1-B8 with reference

**Files:**

- Modify: `skills/feature-blueprint/SKILL.md`

- [ ] **Step 1: Read B1-B8 section**

```bash
grep -n "B1\|B2\|B3\|B4\|B5\|B6\|B7\|B8\|Blueprint Quality" skills/feature-blueprint/SKILL.md | head -20
```

- [ ] **Step 2: Replace inline B1-B8 table**

หา section "Blueprint Quality Gate" แล้วแทนที่ table B1-B8 ทั้งหมด ด้วย:

```markdown
Score against `shared-references/verification-checklist.md` — Blueprint Quality (B1-B8).
Load file to see full criteria before scoring.
```

- [ ] **Step 3: Verify references section still exists at bottom**

```bash
grep -n "verification-checklist" skills/feature-blueprint/SKILL.md
```

Expected: ยังมี reference อยู่อย่างน้อย 1 บรรทัด

- [ ] **Step 4: Commit**

```bash
git add skills/feature-blueprint/SKILL.md
git commit -m "docs: replace inline B1-B8 table with reference to verification-checklist.md"
```

---

### Task 6: mermaid-guide.md — Trim Edge Animation examples

**Files:**

- Modify: `skills/shared-references/mermaid-guide.md`

- [ ] **Step 1: Locate Edge Animation section**

```bash
grep -n "Edge Animation\|animation\|slow\|fast" skills/shared-references/mermaid-guide.md | head -30
```

- [ ] **Step 2: Read the section**

Read from start of "Edge Animation" section to end — identify how many progressive examples there are (expected: 5 incremental variants)

- [ ] **Step 3: Collapse to 1 consolidated example**

เหลือแค่ 1 example ที่สมบูรณ์ที่สุด (แบบที่มี `slow` + `fast` annotation ครบ) แล้วลบ 4 intermediate examples

- [ ] **Step 4: Verify Known Limitations table**

```bash
grep -n "Known Limitation\|Limitation" skills/shared-references/mermaid-guide.md
```

ถ้า rows มี verbose multi-sentence descriptions → trim ให้เหลือ 1 sentence per row

- [ ] **Step 5: Commit**

```bash
git add skills/shared-references/mermaid-guide.md
git commit -m "docs: collapse Edge Animation examples to 1 consolidated example in mermaid-guide.md"
```

---

## Phase 2: Content Restructuring (medium risk)

### Task 7: verification-checklist.md — Convert format + remove B1-B8

**Context:** ไฟล์นี้ referenced โดย 10+ skills และ quality-gate agent
**Rule:** ต้องไม่ลบ check items ใด ๆ — แค่เปลี่ยน format และลบ B1-B8 (ย้าย canonical ไปที่ feature-blueprint)

**Files:**

- Modify: `skills/shared-references/verification-checklist.md`

- [ ] **Step 1: Read entire file & map structure**

อ่าน verification-checklist.md ทั้งหมด และจดโครงสร้าง:

- กี่ sections?
- แต่ละ section มีกี่ check items?
- B1-B8 อยู่ที่ section ไหน?
- Format ปัจจุบันเป็นยังไง (checkpoint-in-code-block หรือ mixed)?

- [ ] **Step 2: Convert checkbox-in-code-block sections to compact tables**

สำหรับ sections ที่ใช้ pattern:

```
**Check: Something**
□ item one
□ item two
```

แปลงเป็น table:

```markdown
| Check | Criteria |
|-------|----------|
| Something | item one; item two |
```

หรือถ้า items หลาย ๆ แบบ ใช้ inline list: `- item one · item two · item three`

**สำคัญ:** ห้ามลบ check item ใด ๆ — แค่เปลี่ยน format

- [ ] **Step 3: Remove B1-B8 section**

ลบ Blueprint Quality (B1-B8) section ออก เพราะ feature-blueprint/SKILL.md เป็น owner แล้ว reference กลับมา แทนที่ด้วยบรรทัดเดียว:

```
Blueprint Quality (B1-B8): see feature-blueprint/SKILL.md — "Blueprint Quality Gate" section.
```

- [ ] **Step 4: Verify quality-gate agent ยังใช้ได้**

```bash
grep -n "verification-checklist\|B1\|B2\|B3" agents/quality-gate.md
```

ถ้า quality-gate.md reference B1-B8 โดยตรง → update ให้ point ไปที่ feature-blueprint/SKILL.md แทน

- [ ] **Step 5: Count token reduction**

```bash
wc -m skills/shared-references/verification-checklist.md
```

ควรลดจาก ~27,280 chars เหลือ ~18,000-20,000

- [ ] **Step 6: Commit**

```bash
git add skills/shared-references/verification-checklist.md agents/quality-gate.md
git commit -m "docs: convert verification-checklist to compact table format, move B1-B8 to feature-blueprint"
```

---

### Task 8: team-capacity.md — Remove project-config.json duplications

**Context:** Referenced by `agents/sprint-planner.md`, `skills/dependency-chain/SKILL.md`, `skills/plan-sprint/SKILL.md`, `context-packs.json`
**Rule:** ห้ามลบ capacity formulas, focus factor definitions, skill multipliers — ลบเฉพาะ data ที่ซ้ำกับ project-config.json

**Files:**

- Modify: `skills/shared-references/team-capacity.md`

- [ ] **Step 1: Read team-capacity.md + project-config.json side by side**

```bash
# Check what's in project-config.json that team-capacity.md duplicates
grep -n "bus_factor\|growth_track\|cross_training\|members\|throughput" skills/shared-references/team-capacity.md | head -40
```

- [ ] **Step 2: Identify sections to remove**

Sections ที่ exist ใน project-config.json ด้วย (remove from team-capacity.md):

- Full member roster with throughput numbers
- Bus Factor analysis
- Growth Tracks per person
- Cross-Training schedule

Sections ที่ KEEP (unique value ไม่มีใน project-config.json):

- Capacity calculation formulas (available_hours × focus_factor × complexity_multiplier)
- Focus Factor definition table (Tech Lead: 0.4-0.5, Senior: 0.7-0.8, etc.)
- Skill matrix multiplier definitions (expert: 1.0x, intermediate: 0.8x, basic: 0.6x)
- Sprint capacity model explanation

- [ ] **Step 3: Rewrite team-capacity.md**

เปลี่ยนเนื้อหาเป็น:

1. **Header** - one sentence what this file is for
2. **Capacity Calculation** - formulas only
3. **Focus Factor** - definition table (already in project-config.json as _note, keep here as formula context)
4. **Skill Multipliers** - table
5. **Data Reference** - "For roster, throughput history, bus factor, growth tracks: see `.claude/project-config.json`"

- [ ] **Step 4: Verify skills that READ team-capacity.md still work**

```bash
grep -n "team-capacity\|capacity" skills/plan-sprint/SKILL.md | head -20
grep -n "team-capacity\|capacity" skills/dependency-chain/SKILL.md | head -20
```

Plan-sprint อ่าน team-capacity สำหรับ member list + throughput — เพิ่ม note ว่า "Load project-config.json สำหรับ member data"

- [ ] **Step 5: Update plan-sprint/SKILL.md + dependency-chain/SKILL.md read instructions**

ใน Phase X ที่ read team-capacity เพิ่ม:

```
Read: .claude/skills/shared-references/team-capacity.md (formulas)
Read: .claude/project-config.json (team roster, throughput, capacity data)
```

- [ ] **Step 6: Commit**

```bash
git add skills/shared-references/team-capacity.md skills/plan-sprint/SKILL.md skills/dependency-chain/SKILL.md
git commit -m "docs: trim team-capacity.md to formulas only, reference project-config.json for roster data"
```

---

### Task 9: story-full + analyze-story — Remove TL decomposition list duplication

**Files:**

- Modify: `skills/story-full/SKILL.md`
- Modify: `skills/analyze-story/SKILL.md` (keep canonical here)

- [ ] **Step 1: Find duplicated TL decomposition list in both files**

```bash
grep -n "decomposition\|vertical\|Tech Lead\|ordering" skills/story-full/SKILL.md | head -20
grep -n "decomposition\|vertical\|Tech Lead\|ordering" skills/analyze-story/SKILL.md | head -20
```

- [ ] **Step 2: Read duplicated section in story-full/SKILL.md**

อ่าน section ที่ duplicate และ confirm เนื้อหาเหมือนกัน (copy-paste ชัดเจน)

- [ ] **Step 3: Remove duplication from story-full/SKILL.md**

ลบ duplicated list จาก story-full แล้วแทนที่ด้วย:

```
TL decomposition ordering: see analyze-story/SKILL.md — Phase X
```

- [ ] **Step 4: Review phases 6-10 ของ story-full vs phases 3-7 ของ analyze-story**

อ่าน phases เหล่านั้นและ assess:

- ถ้า structural overlap มาก → ลบ story-full phase ที่ซ้ำ + point ไปที่ analyze-story
- ถ้าต่างกัน (story-full มีรายละเอียด implementation เพิ่ม) → leave as-is

**Conservative approach:** ลบแค่ส่วนที่ copy-paste verbatim ก่อน อย่า over-optimize

- [ ] **Step 5: Commit**

```bash
git add skills/story-full/SKILL.md skills/analyze-story/SKILL.md
git commit -m "docs: remove duplicate TL decomposition list from story-full (canonical in analyze-story)"
```

---

## Phase 3: Structural Changes (highest risk)

### Task 10: refine-feature/SKILL.md — Extract agent prompts to reference file

**Context:** feature-blueprint ทำแบบนี้อยู่แล้ว (references/agent-prompts.md) — ทำ refine-feature ให้ consistent
**Risk:** ถ้า extract แล้วลืม update path → skill พัง

**Files:**

- Modify: `skills/refine-feature/SKILL.md`
- Create: `skills/refine-feature/references/agent-prompts.md`

- [ ] **Step 1: Read refine-feature/SKILL.md — map all 8 agent prompts**

```bash
grep -n "Agent\|prompt\|Round\|PO\|TL\|Engineer\|QA\|<<<\|>>>" skills/refine-feature/SKILL.md | head -40
```

อ่าน SKILL.md ทั้งหมด สังเกตว่า prompts อยู่ที่ line ไหนและมี structure ยังไง (PO R1/R2, TL R1/R2, Eng R1/R2, QA R1/R2)

- [ ] **Step 2: Read feature-blueprint/references/agent-prompts.md เพื่อดู format**

```bash
cat skills/feature-blueprint/references/agent-prompts.md
```

ดูว่า section headers, naming convention เป็นยังไง

- [ ] **Step 3: Create skills/refine-feature/references/ directory + agent-prompts.md**

```bash
mkdir -p skills/refine-feature/references
```

สร้าง `skills/refine-feature/references/agent-prompts.md` โดย:

- ย้าย 8 prompts จาก SKILL.md ทั้งหมดมาไว้ที่นี่
- Section headers: `## PO Agent — Round 1`, `## PO Agent — Round 2`, etc.
- Frontmatter: `# Refine Feature — Agent Prompts`

- [ ] **Step 4: Replace inline prompts ใน SKILL.md ด้วย reference**

ในแต่ละ Phase ที่เคย embed prompt ตรง ๆ แทนที่ด้วย:

```
**Agent prompt:** See [references/agent-prompts.md](references/agent-prompts.md) — **PO Round 1** section. Substitute all `{...}` placeholders before launching.
```

Pattern เดียวกับที่ feature-blueprint/SKILL.md ใช้ (lines 144, 162)

- [ ] **Step 5: Verify SKILL.md ยังอ่านได้และ complete**

อ่าน refine-feature/SKILL.md ตั้งแต่ต้นจนจบ — check ว่า flow ยังครบ และมี reference ถูกต้องทุก Phase

- [ ] **Step 6: Commit**

```bash
git add skills/refine-feature/SKILL.md skills/refine-feature/references/agent-prompts.md
git commit -m "refactor: extract refine-feature agent prompts to references/agent-prompts.md (consistent with feature-blueprint)"
```

---

### Task 11: docs/mermaid/ — Trim vendor-specific syntax and noise

**Context:** `.claude/rules/mermaid.md` references ทั้ง 6 files โดยตรง — ไม่เปลี่ยน references, แค่ปรับ content
**Rule:** ห้ามลบ Mermaid syntax ที่ใช้จริง — ลบแค่ vendor site syntax, CSS sections, ที่ไม่ render ใน Claude context
**Priority:** flowchart.md (9,803 tokens), sequenceDiagram.md (6,905 tokens), stateDiagram.md (3,369 tokens)

**Files:**

- Modify: `docs/mermaid/flowchart.md`
- Modify: `docs/mermaid/sequenceDiagram.md`
- Modify: `docs/mermaid/stateDiagram.md`
- Read-only (assess): `docs/mermaid/architecture.md`, `docs/mermaid/gantt.md`

**What to remove (safe to delete — Claude cannot use these):**

- Fenced blocks: ` ```mermaid-example `, ` ```note `, ` ```tip `, ` ```warning ` — site-specific renderers
- `<!--@include: virtual:shapesTable -->` include directives
- CSS stylesheet sections (`.node rect`, `.label`, etc.)
- `%%{init: ...}%%` configuration parameter tables (Claude doesn't run these as-is)

**What to KEEP:**

- Actual Mermaid syntax examples (` ```mermaid ` blocks)
- Section headers explaining concepts
- Parameter/option tables describing syntax

- [ ] **Step 1: Read flowchart.md — identify bloat**

```bash
wc -m docs/mermaid/flowchart.md
grep -n "mermaid-example\|:::note\|:::tip\|@include\|classDef\|style " docs/mermaid/flowchart.md | wc -l
```

- [ ] **Step 2: Trim flowchart.md**

ลบ:

- ` ```mermaid-example` blocks (แทนด้วย ` ```mermaid `)
- ` ```note `, ` ```tip ` blocks ทั้งหมด
- `@include` virtual directives
- "New shapes" section ถ้า exhaustive (30+ shapes with individual examples) → เหลือแค่ grouped reference table
- Edge animation progressive examples → เหลือ 1 final complete example

- [ ] **Step 3: Trim sequenceDiagram.md**

```bash
grep -n "classDef\|style\|%%{init\|stylesheet\|mermaid-example\|:::note" docs/mermaid/sequenceDiagram.md | head -20
```

ลบ CSS sections + configuration parameter tables (ถ้ามี)

- [ ] **Step 4: Trim stateDiagram.md**

```bash
grep -n "classDef\|style\|%%{init\|stylesheet\|mermaid-example\|:::note" docs/mermaid/stateDiagram.md | head -20
```

ลบ CSS/style sections

- [ ] **Step 5: Assess architecture.md + gantt.md**

```bash
wc -m docs/mermaid/architecture.md docs/mermaid/gantt.md
```

architecture.md (~1,458 tokens) + gantt.md (~2,235 tokens) — ถ้าไม่มี vendor syntax ชัดเจน ให้ skip

- [ ] **Step 6: Verify after trimming — syntax blocks still intact**

```bash
grep -c '```mermaid' docs/mermaid/flowchart.md
grep -c '```mermaid' docs/mermaid/sequenceDiagram.md
grep -c '```mermaid' docs/mermaid/stateDiagram.md
```

ควรยังมี mermaid blocks อยู่ (ไม่ลบ examples จริง)

- [ ] **Step 7: Count savings**

```bash
wc -m docs/mermaid/flowchart.md docs/mermaid/sequenceDiagram.md docs/mermaid/stateDiagram.md
```

Target: flowchart.md จาก ~39,000 chars → <20,000 / sequenceDiagram จาก ~27,600 → <15,000

- [ ] **Step 8: Commit**

```bash
git add docs/mermaid/
git commit -m "docs: trim vendor site-specific syntax from mermaid docs (note/tip blocks, CSS, @include directives)"
```

---

## Final: Token Count Summary

- [ ] **Count total savings**

```bash
# Before counts (from analysis):
# skills/: ~163,360 tokens
# agents/: ~1,955 tokens
# docs/mermaid/: ~24,278 tokens
# Total: ~189,593 tokens

# After — run this to get new totals:
find skills/ agents/ docs/mermaid/ -name "*.md" | xargs wc -m | tail -1
```

- [ ] **Final commit — update README if it has token counts**

```bash
grep -n "token\|189\|163" README.md
git commit -m "docs: markdown token optimization — 30k+ token reduction across skills/docs/agents"
```

---

## Risk Notes

| Task | Risk | Mitigation |
|------|------|-----------|
| T7 verification-checklist format | **Medium** — 10+ skills depend on content | ห้ามลบ check items — format only |
| T8 team-capacity trim | **Medium** — plan-sprint reads this for roster | เพิ่ม project-config.json read instruction |
| T10 refine-feature extract | **High** — skill พังถ้า reference path ผิด | Test ทุก phase reference หลัง edit |
| T11 mermaid docs trim | **Medium** — `.claude/rules/mermaid.md` points here | ห้ามลบ actual mermaid blocks |

## Rollback

```bash
# ถ้าพัง revert ทั้ง phase:
git log --oneline -15  # ดู commits
git revert <commit-hash>  # revert specific commit
```
