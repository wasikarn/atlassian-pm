# Epic Template (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, styling

## Epic Best Practices

**Naming:** `[Domain] — [Deliverable]` (never "Phase 1", "v2") · **Size:** 8-15 tasks, 2-6 months — split if >15 tickets, multiple domains, or mixed concerns.

> **Narrative tone:** สรุปภาพรวม และ คุณค่าทางธุรกิจ ต้องเขียนให้ PM, designer, หรือ stakeholder ที่ไม่ใช่ developer อ่านเข้าใจได้ทันที — ห้ามใช้ system term, acronym, หรือ tech jargon ใน 2 section นี้

## Epic Template (ADF) - CREATE

> Used with `acli jira workitem create --from-json`
>
> **Content Budget** → see [writing-style.md](writing-style.md#content-budget-per-section)

**All 6 sections are required.**

- สรุปภาพรวม — **3 lines max** (Problem → Solution → ใครได้ประโยชน์)
- คุณค่าทางธุรกิจ — **3 bullets max**
- ลูกค้าเห็นอะไร? — UX perspective, what changes for the customer
- ขอบเขตงาน — Included / Excluded bullets, **1 line/item**
- เงื่อนไขที่ต้องผ่าน — Epic-level ACs (high-level)
- ความเสี่ยงและวิธีรับมือ — Risk + mitigation table

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

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "คุณค่าทางธุรกิจ"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 1 — ผลลัพธ์เป็นพฤติกรรมหรือตัวเลขที่เปลี่ยน]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 2]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 3]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ลูกค้าเห็นอะไร?"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[UX change 1 — สิ่งที่ผู้ใช้สัมผัสได้โดยตรง]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[UX change 2]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ขอบเขตงาน"}]},
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

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "คุณค่าทางธุรกิจ"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 1]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 2]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Value 3]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ลูกค้าเห็นอะไร?"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[UX change 1]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[UX change 2]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ขอบเขตงาน"}]},
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
      ]}
    ]
  }
}
```
