# Epic Template (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, panel types, styling

## Epic Best Practices

**Naming:** `[Domain] — [Deliverable]` (never "Phase 1", "v2") · **Size:** 8-15 stories, 2-6 months — split if >15 tickets, multiple domains, or mixed concerns.

> **Narrative tone:** Epic Overview and Business Value ต้องเขียนให้ PM, designer, หรือ stakeholder ที่ไม่ใช่ developer อ่านเข้าใจได้ทันที — ห้ามใช้ system term, acronym, หรือ tech jargon ใน 2 section นี้ (ย้ายไปใส่ Technical Notes ของ Story แทน)

## Epic Template (ADF) - CREATE

> Used with `acli jira workitem create --from-json`
>
> **Content Budget** → see [writing-style.md](writing-style.md#content-budget-per-section)

**Structure:** (⚡ = optional, include only when real data exists)

- 🎯 Epic Overview (info) — **3 lines max** (Problem → Summary → Supports)
- 💰 Business Value (success) — **3 bullets max**
- 📦 Scope (info) — **1 line/item, no description needed**
- 🔄 Domain Model (info) — ⚡ optional, include for complex domains with multiple aggregates/events
- 📊 RICE Score (table) — ⚡ skip if priority is already clear
- 🎯 Success Metrics (table) — ⚡ skip if metrics not yet defined
- 📋 User Stories (panels) — **list + link only**
- 📈 Progress (note) — auto counts
- 🔗 Links (table)

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Epic",
  "summary": "[Epic Name] Phase X",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🎯 Epic Overview"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "info"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Problem: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[สถานการณ์ปัจจุบัน] → [ปัญหาที่เกิดขึ้น] → [Epic นี้แก้ด้วย...]  ← เขียนให้คนทั่วไปอ่านเข้าใจ ไม่ใช้ tech term"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "[ทำให้ผู้ใช้ทำ X ได้ / ช่วยให้ทีม Y ทำงานง่ายขึ้น]", "marks": [{"type": "strong"}]}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "[รองรับ: feature1, feature2, feature3]"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "💰 Business Value"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "success"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Revenue: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[ผลลัพธ์เป็นตัวเลขหรือพฤติกรรมที่เปลี่ยน — เช่น เพิ่ม conversion 15%, ผู้ใช้ซื้อซ้ำมากขึ้น]"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Retention: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[ผู้ใช้อยู่นานขึ้น / กลับมาใช้บ่อยขึ้น เพราะ...]"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Operations: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[ทีมทำงานเร็วขึ้น / ลด manual work / ลด error — ไม่ใช่ tech feature]"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📦 Scope"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "info"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "1. [Feature/Module 1]", "marks": [{"type": "strong"}]},
            {"type": "text", "text": " - [description]"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "2. [Feature/Module 2]", "marks": [{"type": "strong"}]},
            {"type": "text", "text": " - [description]"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🔄 เมื่อ X เกิดขึ้น ⚡"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "info"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "⚡ Developer-only section — include only for complex epics with cross-domain side effects. Write in plain language, not DDD jargon.", "marks": [{"type": "em"}]}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "เมื่อ ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[ผู้ใช้ทำ X] → ระบบ [ทำ Y ให้อัตโนมัติ]"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "เมื่อ ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[event ที่ 2] → [side effect ที่ 2]"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📊 RICE Score"}]},
      {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
        "content": [
          {"type": "tableRow", "content": [
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Factor"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Score"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Rationale"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Reach"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[number]"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[rationale]"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Impact"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[1-3]"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[rationale]"}]}]}
          ]}
          // ... repeat pattern for Confidence ([%], [rationale]), Effort ([weeks], [stories count]),
          // and RICE Score (bold, [score], "(R × I × C) / E") rows
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🎯 Success Metrics"}]},
      {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
        "content": [
          {"type": "tableRow", "content": [
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Metric"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Target"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Measurement"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Metric 1]"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[target]"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[how to measure]"}]}]}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📋 User Stories"}]},
      {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "🔨 [Group 1]"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "info"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "ABC-XXX", "marks": [{"type": "strong"}]},
            {"type": "text", "text": " - [Story title]"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📈 Progress"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "note"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "✅ Done: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "X (Y%)"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "🟡 In Progress: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "X (Y%)"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "⚪ To Do: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "X (Y%)"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Total: X stories", "marks": [{"type": "strong"}]}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🔗 Links"}]},
      {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
        "content": [
          {"type": "tableRow", "content": [
            {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Type"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Link"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Epic Doc"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "Confluence", "marks": [{"type": "link", "attrs": {"href": "[URL]"}}]}
            ]}]}
          ]}
        ]
      }
    ]
  }
}
```

**Panels:** Overview/Scope/Domain Model=`info`, Business Value=`success`, Progress=`note`, Canceled=`warning`
