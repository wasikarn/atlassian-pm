# Task Templates (ADF) — Unified

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules and styling.
>
> **Diagram rule (if embedding one in the Task description):** Jira ADF = ASCII code block only. Default `sequenceDiagram` for interaction/branching flows; `flowchart` OK only for linear or 2-branch (upstream bug mashes 3+ branch labels). See [mermaid-guide.md](mermaid-guide.md) + [ascii-box-drawing.md](ascii-box-drawing.md). Same rule as [templates-epic.md](templates-epic.md).

All task types use Jira `"type": "Task"`. Mode is conveyed via summary prefix and content structure — not issue type.

## Title Discipline (v3.12.1)

### Decision-Path Qualifier Rule (G3)

> **Rule:** Task/slice titles that describe a decision path (approve, reject, decide, process, Thai: อนุมัติ / ปฏิเสธ / ตัดสิน) MUST include an explicit qualifier — `auto-` (system-decided) / `manual-` or `admin-` (human-decided). A bare verb is ambiguous.

**Enforcement:** validator `T8` (WARN-level, Epic + Task) warns when a title contains a decision-path verb without a qualifier.

**Examples:**

- ❌ `"AI อนุมัติสื่อ"` — ambiguous (auto-approve? admin-approve via AI-assist?)
- ✅ `"AI auto-อนุมัติสื่อ"` — explicit: system decides without human
- ✅ `"Admin manual-อนุมัติสื่อ"` — explicit: human decides, AI recommends
- ❌ `"Approve media"` — missing qualifier
- ✅ `"Auto-approve media"` / `"Admin manual-approve media"` — qualified

**Authoring rule:** ถ้า title มี verb ว่า `approve / reject / decide / process` หรือ Thai `อนุมัติ / ปฏิเสธ / ตัดสิน` — ใส่ qualifier ทันที. ถ้าไม่แน่ใจ auto vs manual → scope ยัง ambiguous → ย้อนไปอ่าน Epic's Scope Disambiguation section ก่อน create slice.

### Test File Declaration (G4 — Sibling Consistency)

> **Rule:** Tasks/slices under the same Epic MUST declare test-file path in the `ขอบเขตไฟล์` table. If a sibling task declares a test file, this task MUST also declare one (`CREATE`, `MODIFY`, or explicit `NONE` with reason).

**Why:** {{PROJECT_KEY}}-183 audit found sibling slices inconsistently declared test files — one had `tests/integration/ai-review.spec.ts` in scope, another omitted tests entirely. QA couldn't tell if missing test file meant "no tests needed" or "forgot to declare". Consistency across siblings forces explicit decisions.

**Template pattern (in `ขอบเขตไฟล์` section):**

```markdown
| Action | File |
| --- | --- |
| CREATE | tests/integration/<feature>/<slice-name>.spec.ts |
| MODIFY | app/Services/FooService.ts |
| REF    | app/Models/Billboard.ts |
```

If the slice genuinely needs no new/changed tests (rare — usually only for doc-only or config-only slices):

```markdown
| Action | File |
| --- | --- |
| NONE (tests) | Reason: slice only adds i18n keys; covered by existing `tests/unit/i18n.spec.ts` |
```

**Authoring checklist:**

- [ ] Each sibling slice has an explicit test-file row (CREATE / MODIFY / NONE+reason)
- [ ] Test file path matches the slice's feature scope (e.g. `tests/integration/ai-review/slice-a-single-owner.spec.ts`)
- [ ] If sibling Slice A declares `CREATE tests/...` → Slice B must also declare something; missing = inconsistency warning

### Estimate Declaration (G8 — v3.12.2)

> **Rule:** Every Task/slice MUST declare an effort estimate in the description body (not only in the Jira `Story Points` field, which is easy to skip). Explicit `Estimate` section forces the author to reason about size before creation.

**Template pattern (add as H2 `ประมาณการ` / `Estimate`):**

```markdown
## ประมาณการ (Estimate)

| Story Points | Days | Confidence |
| --- | --- | --- |
| 3 | 1-2 | High |
```

**Anti-pattern:** Slice with `8+ story points` or `> 5 days` → likely needs SPIDR split; reason in description or split before creation. A 13-SP slice signals scope creep almost every time.

**Enforcement:** validator `T11` (WARN-level, Task) — WARN when Task description lacks an `Estimate` / `ประมาณการ` section OR declares `≥ 8` story points without a `split-justified` note. WARN-only so existing tickets still validate.

**Authoring checklist:**

- [ ] `Estimate` section in description (not only Jira field)?
- [ ] Story points ≤ 5 OR explicit justification for larger size?
- [ ] Days range matches story points (rough rule: 1 SP ≈ half-day)?

### Out of Scope REQUIRED for Vertical Slices (G12 — v3.12.2)

> **Rule:** Tasks that are vertical slices (indicated by `vs{N}-*` label, `Slice [A-Z]` in title, or explicit slice marker) MUST include an `Out of Scope` / `ไม่รวมงานนี้` section. Without it, scope creep + sibling-slice boundary collisions slip past review.

**Template pattern:**

```markdown
## ไม่รวมงานนี้ (Out of Scope)

- Scope belongs to sibling slice (TP-YYY): [what belongs there]
- Scope belongs to paired epic (TP-ZZZ): [what belongs there]
- Deferred to future slice (TP-WWW or undefined): [what + why deferred]
```

**Why:** {{PROJECT_KEY}}-196 / {{PROJECT_KEY}}-197 restructure uncovered that slices without an explicit `Out of Scope` section implicitly absorbed sibling scope at implementation time. Forcing the author to list what's NOT in scope surfaces overlap at creation time — QA and reviewers see the boundary decision instead of inferring it.

**Enforcement:** validator `T15` (WARN-level, Task) — when Task title contains `Slice [A-Z]`, `vs\d+-`, or labels include `vs*`, require `Out of Scope` / `ไม่รวมงานนี้` section. Missing → WARN.

**Authoring checklist:**

- [ ] Slice markers detected (title contains `Slice A/B/C` or `vs1-*` / `vs-enabler-*`)?
- [ ] `ไม่รวมงานนี้` / `Out of Scope` section present with ≥ 1 explicit item?
- [ ] Each out-of-scope item cites a sibling TP-key or a "deferred" marker (no silent omissions)?

### Regression ACs for Paired-Epic Slices (G9 — v3.12.2)

> **Rule:** When this slice's parent Epic is paired with another Epic (declared via parent Epic's Coverage Matrix `Related Epic(s)` column), the slice MUST include at least one regression AC guarding the paired Epic's scope path.

**Template addition (inside `เงื่อนไขที่ต้องผ่าน`):**

```markdown
- ❌ AC_N: regression — [paired-Epic scope path] does NOT trigger this slice's new behavior
  (Paired Epic: TP-ZZZ. Example: "auto-approve case ไม่ trigger review request")
```

**Enforcement:** validator `T12` (WARN-level, Task) — when description references a paired-epic key via inlineCard OR text, validator expects the AC section to contain that key at least once (regression marker). Missing → WARN.

### AC Quality Rules (G11 — INVEST-T: Testable)

> **Rule:** Same as templates-epic — every AC must be testable. Vague phrases break INVEST-T.

**❌ Vague phrases to avoid:**

- `should work correctly` / `works correctly` / `works properly`
- `ทำงานได้ดี` / `ทำงานถูกต้อง` / `ทำงานเหมาะสม`
- `handle properly` / `handles correctly`
- `จัดการได้` / `จัดการถูกต้อง`
- `user-friendly` / `ใช้งานง่าย`
- `perform well` / `ทำงานเร็ว`
- `as expected` / `ตามที่คาดหวัง`

**✅ Testable phrasing:** `Given X, When Y, Then Z` with observable outcome, specific values, time bounds, or visible UI state.

**Enforcement:** validator `T14` (WARN-level, Task) scans AC panels / `เงื่อนไขที่ต้องผ่าน` / `fix criteria` sections for vague phrases → WARN with rephrase hint.

### Explicit Jira Dependency Links (G7 — v3.12.2)

> **Rule:** Any {{PROJECT_KEY}}-XXX mention in Task description MUST use `inlineCard` (not plain text) AND have a corresponding Jira issue link (`Blocks` / `Is blocked by` / `Relates to` / `Depends on`) set via `acli jira workitem link`.

**Why:** Prose-only references like `"reuse from {{PROJECT_KEY}}-196"` don't appear in Jira's Issue Links panel. Dev looking at the slice in Jira UI misses the dependency. `inlineCard` renders as a preview card and feeds Jira's dependency graph.

**ADF pattern (REQUIRED when {{PROJECT_KEY}}-XXX appears in description):**

```json
{"type": "inlineCard", "attrs": {"url": "https://{{JIRA_SITE}}/browse/TP-XXX"}}
```

**After create, set the actual Jira link:**

```bash
acli jira workitem link --key {{PROJECT_KEY}}-200 --target {{PROJECT_KEY}}-197 --type "Is blocked by"
```

**Enforcement:** validator `T10` (WARN-level, Task) — WARN when `TP-\d+` text appears without a sibling `inlineCard` URL in same section.

**Authoring rule:** ทุก {{PROJECT_KEY}}-XXX ใน description body → ต้องเป็น `inlineCard` + ต้องสร้าง Jira link ตาม semantics (`Is blocked by` ถ้า sibling ต้อง merge ก่อน, `Relates to` ถ้าเป็น paired epic ทั่วไป).

**Jira Fields (set after create via MCP `jira_update_issue`):**

| Field | Jira ID | Value | Required |
| --- | --- | --- | --- |
| Story Points | `customfield_10016` | 1–8 based on effort | Recommended |
| Size | `customfield_10107` | `{"value": "S"}` | Recommended |
| Original Estimate | `timetracking` | `{"originalEstimate": "4h"}` | Recommended |
| Start Date | `{{START_DATE_FIELD}}` | `"YYYY-MM-DD"` | Optional |
| Due Date | `duedate` | `"YYYY-MM-DD"` | Optional |

**EDIT format:** Replace `"projectKey"` with `"issues": ["KEY"]` — all other fields identical.

---

## Mode: feature (default) — replaces Story + Subtask

**Use case:** Any deliverable work — feature, sub-task, or implementation unit.
**Summary:** `[BE/FE-Admin/FE-Web] Task title`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| สิ่งที่ผู้ใช้ต้องการ | Yes | As a / I want / So that, or plain narrative |
| เงื่อนไขที่ต้องผ่าน | Yes | Given/When/Then with ✅/⚠️/❌ prefix per AC |
| ขอบเขตไฟล์ | Optional (AI) | Table: Action \| File path |
| คำแนะนำการพัฒนา | Optional (AI/vibe) | Table: Field \| Value |

**AC naming:** `AC{N}: [Verb] — [Scenario Name]`
**AC prefix:** ✅ happy path · ⚠️ edge case · ❌ error case

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Task",
  "summary": "[BE] Task title",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "สิ่งที่ผู้ใช้ต้องการ"}]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "As a ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[persona],"}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "I want to ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[action],"}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "So that ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[benefit]"}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "เงื่อนไขที่ต้องผ่าน"}]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "✅ AC1: Return data — Happy path", "marks": [{"type": "strong"}]}
      ]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[precondition]"}
        ]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "When: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[action]"}
        ]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Then: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[result]"}
        ]}]}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "⚠️ AC2: Handle empty — Edge case", "marks": [{"type": "strong"}]}
      ]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[precondition]"}
        ]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "When: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[action]"}
        ]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Then: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[result]"}
        ]}]}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "❌ AC3: Reject invalid — Error case", "marks": [{"type": "strong"}]}
      ]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[precondition]"}
        ]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "When: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[action]"}
        ]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Then: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[result]"}
        ]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ขอบเขตไฟล์"}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Action"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "File"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "CREATE"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "app/Services/NewService.ts", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "MODIFY"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "app/Models/User.ts", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "REF"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "app/Services/ExistingService.ts", "marks": [{"type": "code"}]}
          ]}]}
        ]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "คำแนะนำการพัฒนา"}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Field"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Value"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Entry Point"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "[primary file path]", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Pattern"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "[reference file to follow]", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Test Command"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "[test command]", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dependencies"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[key imports]"}]}]}
        ]}
      ]}
    ]
  }
}
```

---

## Mode: qa — replaces create-testplan

**Use case:** QA test plan linked to a story.
**Summary:** `[QA] Story title`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| วัตถุประสงค์ทดสอบ | Yes | 1 sentence — what is being tested and why |
| ชุดทดสอบ | Yes | TC1–TC8, each with Given/When/Then + Priority label |
| อ้างอิง | Optional | Story key, test environment URL |

**Abbreviated ADF structure:**

```
heading(2): วัตถุประสงค์ทดสอบ
paragraph: [1-sentence test objective]

heading(2): ชุดทดสอบ
paragraph(strong): TC1: [Verb] — [Scenario] · Priority: High
bulletList:
  listItem → paragraph: Given(strong) + [precondition]
  listItem → paragraph: When(strong) + [action]
  listItem → paragraph: Then(strong) + [expected result]
paragraph(strong): TC2: [Verb] — [Scenario] · Priority: Medium
bulletList: ...

heading(2): อ้างอิง
bulletList:
  listItem → paragraph: Story: {{PROJECT_KEY}}-XXX
  listItem → paragraph: Test env: [URL]
```

---

## Mode: bug — replaces bug-triage

**Use case:** Bug report from QA or production.
**Summary:** `[Bug] Title — affected area`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| รายละเอียดปัญหา | Yes | What is broken, who is affected, severity |
| ขั้นตอนทำซ้ำ | Yes | Numbered steps to reproduce |
| คาดหวัง vs เกิดจริง | Yes | Table: Expected \| Actual |
| เงื่อนไขที่ต้องผ่าน | Yes | Fix criteria — what must be true after fix |

**Abbreviated ADF structure:**

```
heading(2): รายละเอียดปัญหา
paragraph: [description of what is broken + who is affected]

heading(2): ขั้นตอนทำซ้ำ
orderedList:
  listItem → paragraph: [step 1]
  listItem → paragraph: [step 2]
  listItem → paragraph: [step 3]

heading(2): คาดหวัง vs เกิดจริง
table(layout:default):
  tableRow: tableHeader[คาดหวัง] | tableHeader[เกิดจริง]
  tableRow: tableCell[expected behavior] | tableCell[actual behavior]

heading(2): เงื่อนไขที่ต้องผ่าน
bulletList:
  listItem → paragraph: ✅ AC1: [fix criterion — happy path]
  listItem → paragraph: ❌ AC2: [regression guard — error case]
```

---

## Mode: spike

**Use case:** Research, investigation, proof of concept.
**Summary:** `[Spike] Title`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| คำถามวิจัย | Yes | Main research question — 1 sentence |
| บริบท | Yes | Why this spike is needed, what decision it unblocks |
| พื้นที่สำรวจ | Yes | Bullet list of areas/topics to investigate |
| ผลการค้นหา | Optional | Populate only after spike is done — omit if no data yet |
| ข้อเสนอแนะ | Optional | Recommendations — populate only after spike is done |

**Abbreviated ADF structure:**

```
heading(2): คำถามวิจัย
paragraph: [main research question]

heading(2): บริบท
paragraph: [background — why this spike, what decision it informs]

heading(2): พื้นที่สำรวจ
bulletList:
  listItem → paragraph: [area 1]
  listItem → paragraph: [area 2]
  listItem → paragraph: [area 3]

heading(2): ผลการค้นหา          ← add after research, omit at creation
paragraph: [findings]

heading(2): ข้อเสนอแนะ           ← add after research, omit at creation
bulletList:
  listItem → paragraph: [recommendation]
```

---

## Mode: chore

**Use case:** Maintenance, dependency updates, configuration changes, CI/CD tasks.
**Summary:** `[Chore] Title`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| วัตถุประสงค์ | Yes | 1 sentence — what this chore achieves |
| รายการงาน | Yes | Bullet checklist with ⬜ prefix |
| เงื่อนไขที่ต้องผ่าน | Yes | Definition of done — what must be true when complete |

**Abbreviated ADF structure:**

```
heading(2): วัตถุประสงค์
paragraph: [1-sentence objective]

heading(2): รายการงาน
bulletList:
  listItem → paragraph: ⬜ [task item 1]
  listItem → paragraph: ⬜ [task item 2]
  listItem → paragraph: ⬜ [task item 3]

heading(2): เงื่อนไขที่ต้องผ่าน
bulletList:
  listItem → paragraph: ✅ [done criterion 1]
  listItem → paragraph: ✅ [done criterion 2]
```
