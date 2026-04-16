# Epic Template (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, styling

## Epic Best Practices

**Naming:** `[Domain] — [Deliverable]` (never "Phase 1", "v2") · **Size:** 8-15 tasks, 2-6 months — split if >15 tickets, multiple domains, or mixed concerns.

> **Narrative tone:** สรุปภาพรวม และ คุณค่าทางธุรกิจ ต้องเขียนให้ PM, designer, หรือ stakeholder ที่ไม่ใช่ developer อ่านเข้าใจได้ทันที — ห้ามใช้ system term, acronym, หรือ tech jargon ใน 2 section นี้

## Epic Template (ADF) - CREATE

> Used with `acli jira workitem create --from-json`
>
> **Content Budget** → see [writing-style.md](writing-style.md#content-budget-per-section)

**All 7 business sections are required. Technical Reference section is optional (include when Epic has heavy technical detail).**

### Business Zone (ทีมทุกคนอ่าน — QA, PM, Stakeholder)

> **Language rule:** ห้าม class name, file path, method signature, code pattern (เช่น `whereIn` / `findBy`), i18n key, SQL query ใน Business Zone — ทุกอย่างต้องเขียนเป็น user-observable behavior. รายละเอียด technical ไปใส่ใน Technical Reference Zone.

1. **สรุปภาพรวม** — **3 lines max** (Problem → Solution → ใครได้ประโยชน์); ใช้ persona names (billboard owner, advertiser) ห้ามใช้ technical terms
2. **User Flow — ภาพรวมการทำงาน** — step-by-step scenario ภาษา business; ใช้ `orderedList` + `panel` (info/success/warning/note) + Mermaid flow diagram (`codeBlock` with `language: "mermaid"`)
3. **คุณค่าทางธุรกิจ** — **3 bullets max**; ผลลัพธ์เป็นตัวเลข/พฤติกรรม ไม่ใช่ architecture
4. **ลูกค้าเห็นอะไร?** — UX perspective; include Before vs After table + example notification copy (TH/EN titles เท่านั้น — i18n keys ไปที่ Technical Reference)
5. **ขอบเขตงาน** — Included / Excluded bullets, **1 line/item**; user-observable features ("เพิ่มการแจ้งเตือน") ไม่ใช่ "สร้าง `AiFooNotifiable` class"; wrap key scope boundary in `panel` (info)
6. **เงื่อนไขที่ต้องผ่าน** — Epic-level ACs เขียนเป็น observable outcome ("เจ้าของป้ายเห็น notification") ไม่ใช่ implementation detail ("ใช้ `whereIn` pattern")
7. **ความเสี่ยงและวิธีรับมือ** — business impact language ("ป้ายหลายเจ้าของ อาจมีบางคนไม่ได้รับแจ้งเตือน") ไม่ใช่ code-level risk ("`findBy` returns first match"); `panel` (warning) highlighting High-impact + Risk/Impact/Mitigation table

### User Stories = Vertical Slices (NOT Technical Layers)

> **Critical rule — see [vertical-slice-guide.md](vertical-slice-guide.md) / [vs-checklist-compact.md](vs-checklist-compact.md)**

User Stories ใน Epic MUST be **vertical slices** — end-to-end business-deliverable chunks ที่ QA test เป็น user outcome ได้

**❌ Anti-pattern (Layer-split) — อย่าทำ:**

```text
- [BE] Create FooNotifiable class
- [BE] Add i18n keys
- [BE] Hook trigger in FooJob
- [BE] Unit tests
- [FE-Web] Update notification mapping
```

Problem: QA test ทีละ task ไม่ได้ (ไม่มี business value standalone), cycle time ยาว, ต้อง merge ทั้งหมดก่อนเห็น feature

**✅ Correct (Vertical Slice):**

```text
- Slice A (vs1-skeleton): Billboard owner ได้รับ notification เมื่อ AI เริ่ม review (single owner, TH)
- Slice B (vs2-multi-i18n): รองรับ billboard หลาย owner + EN language
- Slice C (vs3-hardening): Retry dedup + failure safety
```

Each slice = minimal E2E working feature, testable in isolation by QA, deployable standalone

**Checklist ก่อนเขียน User Story:**

- [ ] Story = business outcome (user observable)? ไม่ใช่ technical component?
- [ ] Deployable standalone (ไม่ depend story อื่น)?
- [ ] QA test E2E ได้ด้วย business AC?
- [ ] Size ≤ sprint / 1-5 days?
- [ ] มี VS label (`vs1-*`, `vs-enabler-*`)?

### Technical Reference Zone (Dev-only, optional)

Use H2 separator `📘 Technical Reference (สำหรับ Dev)` + info panel explaining "stakeholders/QA สามารถข้ามไปที่ User Stories หรือ Acceptance Criteria ด้านบนได้"

Below the separator use H3 headings:

- Current Flow Gap
- Technical Design — Backend / Frontend / Admin
- Edge Cases
- Dependencies / Estimation / Labels

**Rule:** Technical sections NEVER appear above business sections. If Epic has no technical detail, omit the Technical Reference zone entirely.

**What goes here (moved from Business Zone):**

- Class names, file paths, method signatures, SQL queries
- Code patterns (`whereIn` vs `findBy`, status guards)
- i18n keys (`ADVERTISEMENT.FOO.TITLE`)
- Retry/concurrency implementation details
- Refactor tasks (e.g. "extract `FooService`")

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Epic",
  "summary": "[Domain] — [Deliverable]",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "สรุปภาพรวม"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[Problem: สถานการณ์ปัจจุบัน → ปัญหาที่เกิดขึ้น]"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[Solution: Epic นี้แก้ด้วย...]", "marks": [{"type": "strong"}]}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[ใครได้ประโยชน์: ผู้ใช้/ทีม/ธุรกิจ ได้อะไร]"}]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "User Flow — ภาพรวมการทำงาน"}]},
      {"type": "panel", "attrs": {"panelType": "info"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Flow สรุปสั้น: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[persona] [action] → [system response] → [outcome for user]"}]}
      ]},
      {"type": "paragraph", "content": [{"type": "text", "text": "Scenario แบบละเอียด:", "marks": [{"type": "strong"}]}]},
      {"type": "orderedList", "attrs": {"order": 1}, "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Step 1 — [business action, no tech jargon]", "marks": [{"type": "strong"}]}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Step 2 — [what user sees]", "marks": [{"type": "strong"}]}]}]}
      ]},
      {"type": "panel", "attrs": {"panelType": "success"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Step N (NEW) — [highlight the new behavior from this Epic]", "marks": [{"type": "strong"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "คุณค่าทางธุรกิจ"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 1 — ผลลัพธ์เป็นพฤติกรรมหรือตัวเลขที่เปลี่ยน]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 2]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 3]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ลูกค้าเห็นอะไร?"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[Persona] Journey — Before vs After:", "marks": [{"type": "strong"}]}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "สถานการณ์"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Before (ปัจจุบัน)"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "After (หลังจากงานนี้เสร็จ)"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[scenario description]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[current pain point]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[improved experience]"}]}]}
        ]}
      ]},
      {"type": "paragraph", "content": [{"type": "text", "text": "ตัวอย่างข้อความ (optional — รวม i18n keys ถ้ามี):", "marks": [{"type": "strong"}]}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "TH — Title: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "\"[Thai title]\""}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "EN — Title: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "\"[English title]\""}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ขอบเขตงาน"}]},
      {"type": "panel", "attrs": {"panelType": "info"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "ขอบเขตสำคัญ: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[one-line scope summary — what's in vs out]"}]}
      ]},
      {"type": "paragraph", "content": [{"type": "text", "text": "รวม:", "marks": [{"type": "strong"}]}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Included 1]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Included 2]"}]}]}
      ]},
      {"type": "paragraph", "content": [{"type": "text", "text": "ไม่รวม:", "marks": [{"type": "strong"}]}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Excluded 1]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Excluded 2]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "เงื่อนไขที่ต้องผ่าน"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[AC 1 — high-level outcome, not implementation detail]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[AC 2]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[AC 3]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ความเสี่ยงและวิธีรับมือ"}]},
      {"type": "panel", "attrs": {"panelType": "warning"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "High-impact risks: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[summarize the High rows + mitigation approach]"}]}
      ]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "ความเสี่ยง"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "ผลกระทบ"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "วิธีรับมือ"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[risk description]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[impact — High/Med/Low]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[mitigation plan]"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[risk 2]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[impact]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[mitigation]"}]}]}
        ]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📘 Technical Reference (สำหรับ Dev)"}]},
      {"type": "panel", "attrs": {"panelType": "info"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "section นี้เป็นรายละเอียดเชิงเทคนิคสำหรับทีม Developer — Stakeholders และ QA สามารถข้ามไปที่ User Stories หรือ Acceptance Criteria ด้านบนได้"}]}
      ]},
      {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Technical Design — Backend"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[class/module/file — "}, {"type": "text", "text": "path/to/file.ts", "marks": [{"type": "code"}]}, {"type": "text", "text": "]"}]}]}
      ]},
      {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Edge Cases"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[edge case + handling]"}]}]}
      ]}
    ]
  }
}
```

## Epic Template (ADF) - EDIT

> Used with `acli jira workitem edit --from-json` — preserves existing fields, only replaces description.

```json
{
  "issues": ["{{PROJECT_KEY}}-XXX"],
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "สรุปภาพรวม"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[Problem statement]"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[Solution summary]", "marks": [{"type": "strong"}]}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[Who benefits]"}]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "User Flow — ภาพรวมการทำงาน"}]},
      {"type": "panel", "attrs": {"panelType": "info"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Flow สรุปสั้น: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[one-line flow summary]"}]}
      ]},
      {"type": "orderedList", "attrs": {"order": 1}, "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Step 1 — [action]", "marks": [{"type": "strong"}]}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Step 2 — [outcome]", "marks": [{"type": "strong"}]}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "คุณค่าทางธุรกิจ"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 1]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 2]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 3]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ลูกค้าเห็นอะไร?"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "Before vs After:", "marks": [{"type": "strong"}]}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "สถานการณ์"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Before"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "After"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[scenario]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[pain]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[improved]"}]}]}
        ]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ขอบเขตงาน"}]},
      {"type": "panel", "attrs": {"panelType": "info"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "ขอบเขตสำคัญ: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[scope summary]"}]}
      ]},
      {"type": "paragraph", "content": [{"type": "text", "text": "รวม:", "marks": [{"type": "strong"}]}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Included 1]"}]}]}
      ]},
      {"type": "paragraph", "content": [{"type": "text", "text": "ไม่รวม:", "marks": [{"type": "strong"}]}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Excluded 1]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "เงื่อนไขที่ต้องผ่าน"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[AC 1 — high level]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[AC 2]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ความเสี่ยงและวิธีรับมือ"}]},
      {"type": "panel", "attrs": {"panelType": "warning"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "High-impact risks: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[summary]"}]}
      ]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "ความเสี่ยง"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "ผลกระทบ"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "วิธีรับมือ"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[risk]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[impact]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[mitigation]"}]}]}
        ]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📘 Technical Reference (สำหรับ Dev)"}]},
      {"type": "panel", "attrs": {"panelType": "info"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Section นี้สำหรับ Developer — stakeholders/QA ข้ามได้"}]}
      ]},
      {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Technical Design — Backend"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[technical detail]"}]}]}
      ]}
    ]
  }
}
```
