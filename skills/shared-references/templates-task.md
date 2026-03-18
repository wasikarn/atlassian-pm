# Task Templates (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, panel types, styling

**Jira Fields (set after create via MCP `jira_update_issue`):**

| Field | Jira ID | Value | Required |
| --- | --- | --- | --- |
| Story Points | `customfield_10016` | 1-8 based on effort | Recommended |
| Size | `customfield_10107` | `{"value": "S"}` | Recommended |
| Original Estimate | `timetracking` | `{"originalEstimate": "4h"}` | Recommended |
| Start Date | `{{START_DATE_FIELD}}` | `"YYYY-MM-DD"` | Optional |
| Due Date | `duedate` | `"YYYY-MM-DD"` | Optional |

## tech-debt Template

**Use case:** PR review issues, code improvements, refactoring
**Summary:** `[BE] [Title] - [Context]`

> Used with `acli jira workitem create --from-json`
> **Section format:** `N. Emoji Title` — see [writing-style.md](writing-style.md#numbered-section-pattern)

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Task",
  "summary": "[BE] [Title] - [Context]",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "1. 📋 Context"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "info"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "[Origin of this task - e.g., found during PR review, code smell, etc.]"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "2. 🔴 HIGH Priority"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "error"},
        "content": [
          {"type": "paragraph", "content": [{"type": "text", "text": "1. [Issue title]", "marks": [{"type": "strong"}]}]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "File: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "path/to/file.ts", "marks": [{"type": "code"}]}
          ]},
          {"type": "paragraph", "content": [{"type": "text", "text": "[Description of issue]"}]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Fix: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[How to fix]"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "3. 🟡 MEDIUM Priority"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "warning"},
        "content": [
          {"type": "paragraph", "content": [{"type": "text", "text": "2. [Issue title]", "marks": [{"type": "strong"}]}]},
          {"type": "paragraph", "content": [{"type": "text", "text": "[Description and fix]"}]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "4. 🟣 LOW Priority"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "note"},
        "content": [
          {"type": "paragraph", "content": [{"type": "text", "text": "3. [Issue title]", "marks": [{"type": "strong"}]}]},
          {"type": "paragraph", "content": [{"type": "text", "text": "[Description and fix]"}]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "5. ✅ Acceptance Criteria"}]},
      {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
        "content": [
          {"type": "tableRow", "content": [
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "#"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Priority"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Criteria"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "1", "marks": [{"type": "strong"}]}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "🔴 HIGH"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Criteria description]"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "⬜"}]}]}
          ]}
        ]
      },
      {
        "type": "panel",
        "attrs": {"panelType": "warning"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "⛔ Out of Scope: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[สิ่งที่ไม่ต้องทำในรอบนี้] (จะ implement ใน [TICKET-XXX])"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "7. 🔗 Reference"}]},
      {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
        "content": [
          {"type": "tableRow", "content": [
            {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Type"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Link"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Related Issue"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "ABC-XXX", "marks": [{"type": "link", "attrs": {"href": "https://{{JIRA_SITE}}/browse/ABC-XXX"}}]}
            ]}]}
          ]}
        ]
      }
    ]
  }
}
```

## bug Template

**Use case:** Bug fixes from QA or production
**Summary:** `[Bug] [Title]`

**Sections:** (numbered `N. Emoji Title`)

1. `1. 🐛 Bug Description` — panel(error): describe symptoms + impact
2. `2. 🔄 Reproduction Steps` — orderedList: step-by-step
3. `3. 📊 Expected vs Actual` — table with green/red headers
4. `4. 🔍 Root Cause` — panel(note): root cause or TBD
5. `5. ✅ Fix Criteria` — panel(success): bulletList of criteria
6. `6. 🔗 Reference` — purple table

## chore Template

**Use case:** Maintenance, dependency updates, configs
**Summary:** `[Chore] [Title]`

**Sections:** (numbered `N. Emoji Title`)

1. `1. 🎯 Objective` — panel(info): task objective
2. `2. 📋 Tasks` — panel(note): bulletList with ⬜ checkboxes
3. `3. ⚡ Out of Scope` — panel(warning): optional, เพิ่มเมื่อ task มี adjacent scope ที่อาจสับสน
4. `4. 🔗 Reference` — purple table

## spike Template

**Use case:** Research, investigation, POC
**Summary:** `[Spike] [Title]`

**Sections:** (numbered `N. Emoji Title`)

1. `1. ❓ Research Question` — panel(info): main question
2. `2. 📋 Context` — paragraph: background/rationale
3. `3. 🔍 Investigation Areas` — bulletList: topics to study
4. `4. 📝 Findings` — panel(note): *[To be filled after research]*
5. `5. 💡 Recommendations` — panel(success): *[To be filled after research]*
6. `6. ⚡ Out of Scope` — panel(warning): optional, เพิ่มเมื่อ spike มี adjacent area ที่ชัดเจนว่าไม่ investigate
7. `7. 🔗 Reference` — purple table
