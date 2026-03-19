# Workflow Diagrams + Skill Chaining Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่ม Mermaid workflow diagrams ใน README.md และ skill-orchestration.md พร้อมปรับปรุง skill chaining handoff ใน create-epic และ story-full ให้ consume blueprint_backlog_map อัตโนมัติ

**Architecture:**

- Phase 1 (Diagrams): แก้ไข markdown files 2 ไฟล์ (README.md, skill-orchestration.md) เพิ่ม Mermaid diagrams แทน text-only decision trees
- Phase 2 (Handoff): แก้ไข SKILL.md 2 ไฟล์ (create-epic, story-full) เพิ่ม "Blueprint Handoff Check" section ใน Phase 1 Discovery

**Tech Stack:** Markdown + Mermaid diagram syntax (flowchart TD/LR)

---

## File Map

| Action | File | เปลี่ยนอะไร |
|--------|------|------------|
| Modify | `README.md` | เพิ่ม Diagram A (Master Workflow) ใน section "How It Works" |
| Modify | `skills/shared-references/skill-orchestration.md` | แทน text decision tree ด้วย Diagram B + C (Mermaid) |
| Modify | `skills/create-epic/SKILL.md` | เพิ่ม Blueprint Handoff Check ใน Phase 1 Discovery |
| Modify | `skills/story-full/SKILL.md` | เพิ่ม Blueprint Handoff Check ใน Phase 1 Discovery |

ไม่มีไฟล์ใหม่ — แก้ทุกอย่างใน existing files เท่านั้น

---

## Task 1: Master Workflow Diagram ใน README.md

**Files:**

- Modify: `README.md`

ตำแหน่ง: แทรกหลัง "How It Works" section (บรรทัดที่มี ````text` → `You (natural language)...`) เพิ่ม Mermaid diagram ต่อท้าย code block เดิม

- [ ] **Step 1: อ่าน README.md ตรวจ context ก่อนแก้**

  อ่านบรรทัด 24-50 ของ README.md เพื่อดู "How It Works" section ที่จะแทรก diagram

- [ ] **Step 2: แทรก Diagram A หลัง "How It Works" code block**

  แทรกหลังบรรทัด `4. A local cache (SQLite + FTS5) stores Jira data...` (ประมาณบรรทัด 33):

  ````markdown

  ### Workflow Overview

  ```mermaid
  flowchart TD
      A([💬 User Intent]) --> B{New or Existing Issue?}

      B -->|New| C["/search-issues\ndedup check"]
      B -->|Existing| D{Single or Cascade?}

      D -->|Single issue| E["/update-{epic,story,\ntask,subtask}"]
      D -->|Story + Subtasks\n± Confluence| F["/sync-alignment"]

      E --> V["/verify-issue"]
      F --> V

      C --> G{Scope?}

      G -->|"Greenfield / Architecture\nNew domain"| H["/feature-blueprint\nConfluence + backlog map"]
      G -->|"Unclear scope\nHigh-risk"| I["/refine-feature\n4-role debate"]
      G -->|"Clear scope\nSingle service"| K["/story-full"]

      H --> J["/create-epic"] --> K
      I --> K

      K --> L["/create-testplan\noptional"]
      L --> V
      K --> V

      V --> M([✅ Jira + Confluence])

      subgraph sprint["Sprint Planning"]
          direction LR
          N["/plan-sprint"] --> O["/dependency-chain"]
      end

      M -.->|"After backlog ready"| sprint

      classDef skill fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
      classDef gate fill:#dcfce7,stroke:#16a34a,color:#14532d
      classDef endpoint fill:#f3f4f6,stroke:#6b7280,color:#111827
      classDef sprint fill:#fef9c3,stroke:#ca8a04,color:#713f12

      class C,E,F,H,I,J,K,L,N,O skill
      class V gate
      class A,M endpoint
  ```
  ````

- [ ] **Step 3: ตรวจสอบ diagram syntax ถูกต้อง**

  อ่านไฟล์หลังแก้ ตรวจว่า:
  - ` ```mermaid ` block ปิดถูกต้อง
  - ไม่มี `end` lowercase ใน node label (Mermaid bug)
  - subgraph มี `end` ที่ถูกต้อง

- [ ] **Step 4: Commit**

  ```bash
  git add README.md
  git commit -m "docs: add master workflow diagram to README How It Works section"
  ```

---

## Task 2: Decision Tree Diagrams ใน skill-orchestration.md

**Files:**

- Modify: `skills/shared-references/skill-orchestration.md`

แทนที่ text-based decision trees ใน section "Decision Trees" ด้วย Mermaid diagrams

- [ ] **Step 1: อ่าน skill-orchestration.md บรรทัด 65-93**

  ดู section "Decision Trees" ที่จะแทน — มี 2 trees: "Create or Update?" และ "story-full vs analyze-story?"

- [ ] **Step 2: แทนที่ "Create or Update?" text tree ด้วย Mermaid**

  แทนที่ code block ของ "Create or Update?" (```text ...```) ด้วย:

  ````markdown
  ```mermaid
  flowchart TD
      A{New Requirement?} -->|Yes| B["/search-issues\ndedup check"]
      A -->|No — Edit existing| C{Single or Cascade?}

      B --> D{Duplicate found?}
      D -->|Yes| E["/update-* or /sync-alignment"]
      D -->|No| F{Scope?}

      F -->|"Greenfield / Architecture\nNew domain"| G["/feature-blueprint\n→ /create-epic → /story-full"]
      F -->|"Unclear scope\nMulti-service / High-risk"| H["/refine-feature\n→ /story-full"]
      F -->|"Clear scope\nSingle service"| I["/story-full ⭐ preferred"]

      C -->|Single issue| J["/update-{type}"]
      C -->|"Story + subtasks\n± Confluence"| K["/sync-alignment"]

      classDef skill fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
      class E,G,H,I,J,K skill
  ```
  ````

- [ ] **Step 3: แทนที่ "story-full vs analyze-story?" text tree ด้วย Mermaid**

  แทนที่ text block ของ section นี้ด้วย:

  ````markdown
  ```mermaid
  flowchart LR
      A{Story exists in Jira?} -->|"No\nCreate from scratch"| B
      A -->|"Yes\nNeed subtasks only"| C

      B["/story-full ⭐ default\nPhases 1–10\nPO + TA combined\nOutput: Story + Sub-tasks"]
      C["/analyze-story\nPhases 5–10\nSkips story creation\nStarts from impact analysis"]

      classDef skill fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
      class B,C skill
  ```
  ````

- [ ] **Step 4: ตรวจสอบ markdown structure ยังถูกต้อง**

  อ่านไฟล์หลังแก้ ตรวจว่า:
  - หัวข้อ `### Create or Update?` และ `### story-full vs analyze-story?` ยังอยู่
  - Mermaid blocks ปิดถูกต้อง
  - ส่วนอื่น (Intent-to-Skill Map, Pre/Post Conditions) ไม่ถูกแตะ

- [ ] **Step 5: Commit**

  ```bash
  git add skills/shared-references/skill-orchestration.md
  git commit -m "docs: replace text decision trees with Mermaid flowcharts in skill-orchestration"
  ```

---

## Task 3: Blueprint Handoff Check ใน create-epic/SKILL.md

**Files:**

- Modify: `skills/create-epic/SKILL.md`

เพิ่ม "Blueprint Handoff Check" ก่อน Phase 1 Discovery เพื่อให้ agent ดึง context จาก blueprint output ที่อยู่ใน conversation history

- [ ] **Step 1: อ่าน create-epic/SKILL.md บรรทัด 33-43**

  ดู Phase 1 Discovery ที่จะแทรก handoff check ก่อน

- [ ] **Step 2: แทรก Blueprint Handoff Check ก่อน "### 1. Discovery"**

  แทรก section ใหม่ก่อนบรรทัด `### 1. Discovery`:

  ```markdown
  ## Blueprint Handoff Check

  > **Check first:** ดู conversation history ว่ามี `/feature-blueprint` output หรือไม่

  **If `blueprint_backlog_map` is present in history:**

  ```text
  Extract from blueprint output:
  - epic.title          → ใช้เป็น epic title (ข้ามการถามจาก user)
  - stories[]           → เก็บเป็น vs_stories[] สำหรับ Phase 3
  - non_goals[]         → เก็บเป็น out-of-scope items
  - blueprint_page_id   → link ใน Epic Doc section "References"
  ```

  Skip the interview questions in Phase 1 for information already documented.
  แสดง summary ให้ user confirm:
  > "พบ blueprint: [Feature Name] — ใช้ข้อมูลจาก blueprint สำหรับ epic นี้ confirm?"

  **⛔ GATE** — รอ user confirm ก่อนดำเนินต่อ

  **If no blueprint in history:** ดำเนิน Phase 1 Discovery ปกติ

  ---

  ```

- [ ] **Step 3: อัปเดต Context Object table — เพิ่ม optional blueprint fields**

  ใน Context Object table เพิ่มแถว:

  ```markdown
  | 0. Blueprint (optional) | `blueprint_page_id`, `blueprint_url`, `blueprint_stories[]` |
  ```

  แทรกก่อนแถว `| 1. Discovery |`

- [ ] **Step 4: ตรวจสอบ**

  อ่านไฟล์หลังแก้ ตรวจว่า:
  - "Blueprint Handoff Check" section อยู่ก่อน Phase 1
  - Context Object table มีแถว `0. Blueprint`
  - Phase 1-5 เดิมไม่ถูกแตะ

- [ ] **Step 5: Commit**

  ```bash
  git add skills/create-epic/SKILL.md
  git commit -m "feat: add blueprint handoff check to create-epic Phase 1 discovery"
  ```

---

## Task 4: Blueprint Handoff Check ใน story-full/SKILL.md

**Files:**

- Modify: `skills/story-full/SKILL.md`

เพิ่ม "Blueprint Handoff Check" ก่อน Phase 1 Discovery เพื่อให้ agent ดึง story context จาก blueprint output

- [ ] **Step 1: อ่าน story-full/SKILL.md บรรทัด 44-55**

  ดู Part A และ Phase 1 Discovery ที่จะแทรก handoff check

- [ ] **Step 2: แทรก Blueprint Handoff Check ก่อน "## Part A: Create Story"**

  แทรก section ใหม่ก่อน `## Part A: Create Story (Phases 1-4)`:

  ```markdown
  ## Blueprint Handoff Check

  > **Check first:** ดู conversation history ว่ามี `/feature-blueprint` output หรือไม่

  **If `blueprint_backlog_map` is present in history:**

  ```text
  Ask user: "ต้องการสร้าง story ไหนจาก blueprint?"
  → User เลือก story index (e.g., "story 1", "first MVP story")

  Extract selected story from blueprint:
  - stories[N].title          → ใช้เป็น story summary draft
  - stories[N].narrative_hint → เริ่ม narrative จาก hint นี้ (ไม่ถาม Who/What/Why ซ้ำ)
  - stories[N].acs_hint[]     → ใช้เป็น starting points สำหรับ ACs
  - stories[N].vs_label       → pre-assign VS label (ข้าม VS assignment)
  - stories[N].sp_estimate    → suggest SP (S/M/L)
  - blueprint_page_id         → link ใน story description section "References"
  ```

  ข้าม "Ask: Who? What? Why?" ใน Phase 1 สำหรับข้อมูลที่มีอยู่แล้ว
  เริ่มที่ Phase 2 Write User Story โดยใช้ blueprint context เป็น draft

  **If no blueprint in history:** ดำเนิน Phase 1 Discovery ปกติ (ถาม Who/What/Why/Constraints)

  ---

  ```

- [ ] **Step 3: อัปเดต Context Object table — เพิ่ม optional blueprint fields**

  ใน Context Object table เพิ่มแถว:

  ```markdown
  | 0. Blueprint (optional) | `blueprint_page_id`, `selected_story_index`, `blueprint_acs_hints[]` |
  ```

  แทรกก่อนแถว `| 1. Discovery |`

- [ ] **Step 4: ตรวจสอบ**

  อ่านไฟล์หลังแก้ ตรวจว่า:
  - "Blueprint Handoff Check" section อยู่ก่อน `## Part A`
  - Context Object table มีแถว `0. Blueprint`
  - Phase 1-11 เดิมไม่ถูกแตะ
  - `context: fork` ใน frontmatter ยังอยู่ (ไม่ควรแตะ frontmatter)

- [ ] **Step 5: Commit**

  ```bash
  git add skills/story-full/SKILL.md
  git commit -m "feat: add blueprint handoff check to story-full Phase 1 discovery"
  ```

---

## Task 5: Verification

ตรวจสอบ consistency ทั้ง 4 ไฟล์หลังแก้เสร็จ

- [ ] **Step 1: ตรวจ README diagram**

  อ่าน README.md ส่วน "How It Works" และ "Workflow Overview" ตรวจว่า:
  - Mermaid block format ถูกต้อง (` ```mermaid ` ... ` ``` `)
  - Node labels ไม่มี lowercase `end`
  - subgraph ปิดด้วย `end`

- [ ] **Step 2: ตรวจ skill-orchestration diagrams**

  อ่าน `skills/shared-references/skill-orchestration.md` บรรทัด 65-95 ตรวจว่า:
  - text decision trees ถูกแทนที่ด้วย Mermaid แล้ว
  - Section headers ยังอยู่ครบ

- [ ] **Step 3: ตรวจ handoff consistency**

  grep ตรวจว่า `blueprint_backlog_map` mention ครบทั้ง 2 skills:

  ```bash
  grep -l "blueprint_backlog_map" skills/create-epic/SKILL.md skills/story-full/SKILL.md
  ```

  Expected: ทั้ง 2 ไฟล์ปรากฏใน output

- [ ] **Step 4: ตรวจว่า feature-blueprint Handoff section ยังสอดคล้อง**

  อ่าน `skills/feature-blueprint/SKILL.md` Phase 10 Handoff ดู `next_skills[]` format
  ตรวจว่า handoff message ยังสอดคล้องกับ check ที่เพิ่มใน create-epic และ story-full

- [ ] **Step 5: Final commit (ถ้ามีการแก้เพิ่มจากการ verify)**

  ```bash
  git add -A
  git commit -m "docs: verify and finalize workflow diagrams + skill chaining handoff"
  ```

---

## สรุป Diagrams ที่จะได้

| Diagram | ตำแหน่ง | จุดประสงค์ |
|---------|---------|------------|
| A: Master Workflow | README.md → How It Works | Onboarding, big picture navigation |
| B: Create vs Update Decision Tree | skill-orchestration.md | Agent navigation: intent → skill |
| C: story-full vs analyze-story | skill-orchestration.md | Agent navigation: which story skill |

## สรุป Handoff ที่จะได้

| Skill | ก่อน | หลัง |
|-------|------|------|
| `/create-epic` Phase 1 | ถามสัมภาษณ์ stakeholder เสมอ | Check blueprint → ถ้ามีให้ข้าม interview ที่ซ้ำกัน |
| `/story-full` Phase 1 | ถาม Who/What/Why/Constraints เสมอ | Check blueprint → ถ้ามีให้ดึง story draft อัตโนมัติ |
