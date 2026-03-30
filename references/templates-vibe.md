# Vibe Mode Templates & Rules

> **Prerequisite:** Read [templates-subtask.md](templates-subtask.md) for base ADF structure · [templates-core.md](templates-core.md) for panel types

## Purpose

Vibe mode is **speed through less ceremony, NOT less quality.**

When a developer or tech lead runs a skill with `--vibe`, the workflow skips the slow parts (discovery interviews, annotation rounds, RICE scoring) but keeps all the parts that prevent production incidents (codebase exploration, QG gating, HR rules, subtask parent verification).

The core insight: **a subtask IS an AI prompt.** When someone runs `implement TP-123` in Claude Code, Claude reads the Jira ticket via MCP. If the ticket contains rich Implementation Hints, Claude Code produces production-ready code on the first pass. If it doesn't, Claude produces generic scaffolding that the developer still has to rework.

Vibe mode front-loads the codebase exploration that makes those hints accurate.

---

## Vibe Mode Rules

| Aspect | Standard Mode | Vibe Mode |
| --- | --- | --- |
| Discovery interview | Yes — full stakeholder interview | **SKIP** — use existing context |
| ITERATE annotation rounds | Yes — up to 3 rounds | **SKIP** — single pass |
| RICE scoring | Yes | **SKIP** |
| REVIEW gates between phases | Yes | **SKIP** |
| Codebase exploration | Recommended | **MANDATORY** — no hints without it |
| QG ≥ 90% | Yes | **KEEP** — non-negotiable |
| HR1–HR10 hard rules | Yes | **KEEP** — non-negotiable |
| Two-step subtask creation (HR5) | Yes | **KEEP** — MCP create → verify parent → acli edit |
| Section 4 Implementation Hints | Optional | **MANDATORY** — the whole point of vibe mode |

---

## Implementation Hints (Section 4 ADF)

Add this section to every subtask ADF when running in vibe mode. It goes after section 3 (Acceptance Criteria), separated by a `{"type": "rule"}` node.

### How to populate from codebase exploration

Run codebase exploration (QMD search, AST grep, or `analyze-story`) before writing subtasks. Map results to fields:

| Field | How to populate |
| --- | --- |
| **Entry Point** | The primary CREATE or MODIFY file from the Scope table |
| **Pattern to Follow** | The REF file from Scope table — the file whose structure/conventions the new file should mirror |
| **Test Command** | The exact `node ace test`, `pytest`, or `npm test` command scoped to the new file path |
| **Related API** | Only for BE subtasks — the HTTP method + route this code exposes or calls |
| **Dependencies** | Services/repositories injected via constructor — found by reading the REF file's constructor signature |

### ADF JSON

```json
{"type": "rule"},
{"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "4. 🤖 Implementation Hints"}]},
{
  "type": "panel",
  "attrs": {"panelType": "note"},
  "content": [
    {
      "type": "table",
      "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
      "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Key"}]}]},
          {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Value"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Entry Point"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "app/Services/Feature/NewService.ts", "marks": [{"type": "code"}]}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Pattern to Follow"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "app/Services/Existing/ExampleService.ts (REF)", "marks": [{"type": "code"}]}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Test Command"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "node ace test --files \"tests/unit/services/feature*\"", "marks": [{"type": "code"}]}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Related API"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "POST /api/v1/feature"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dependencies"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "FeatureRepository, BaseService"}]}]}
        ]}
      ]
    },
    {"type": "paragraph", "content": [
      {"type": "text", "text": "Claude Code Prompt:", "marks": [{"type": "strong"}]}
    ]},
    {"type": "paragraph", "content": [
      {"type": "text", "text": "Implement [objective] following the pattern in [Pattern to Follow]. Run [Test Command] to verify. All ACs must pass."}
    ]}
  ]
}
```

### Row requirements

| Row | Required | Notes |
| --- | --- | --- |
| Entry Point | **Yes** | Primary file being created or modified |
| Pattern to Follow | **Yes** | REF file from Scope table — structural model |
| Test Command | **Yes** | Scoped to the new file, not the entire suite |
| Related API | Optional | BE subtasks only — HTTP method + route |
| Dependencies | Optional | Constructor-injected services/repos |

---

## Claude Code Prompt Format

The "Claude Code Prompt" line in the note panel is the most important field. It becomes the one-line instruction Claude Code reads when a developer runs `implement TP-123`.

### Template

```
"Implement [objective 1-sentence] following [Pattern file] as the pattern. Key files: [scope CREATE/MODIFY rows]. Run [test command] when done. ACs: [AC1, AC2, AC3]."
```

### Example

```
"Implement LineNotificationChannel that sends push messages via LINE Messaging API following app/Services/Notification/SlackNotificationChannel.ts as the pattern. Key files: CREATE app/Services/Notification/LineNotificationChannel.ts, MODIFY app/Services/Notification/NotificationManager.ts. Run node ace test --files 'tests/unit/services/notification/line*' when done. ACs: channel.notify() sends HTTP POST to LINE API, failed delivery sets status='failed', unsupported message type throws UnsupportedMessageTypeException."
```

### Anti-patterns to avoid

| Anti-pattern | Why | Fix |
| --- | --- | --- |
| `"Implement the notification feature"` | Too vague — Claude invents structure | Reference exact file paths from codebase |
| `"Follow best practices"` | Meaningless — no concrete anchor | Name the specific REF file |
| `"Run the tests"` | Ambiguous — runs 3,000 tests | Scope to file glob matching the new file |
| Omitting ACs in the prompt | Claude may skip edge cases | List all 3 ACs verbatim |
| Listing 6+ files as CREATE | Subtask scope too large | Split into multiple subtasks |

---

## Delegation View Format

Use this table in the vibe-plan **Summary phase** to give the tech lead a scannable delegation view before executing.

```markdown
| Assignee | Subtask | Type | OE | Claude Code Prompt |
|----------|---------|------|----|--------------------|
| dev@email.com | TP-101 [BE] setup service | CREATE | 4h | "Implement X following Y..." |
| dev@email.com | TP-102 [BE] add endpoint | MODIFY | 2h | "Add POST /api/v1/feature to Z following W..." |
| fe@email.com  | TP-103 [FE-Admin] add page | CREATE | 4h | "Implement FeaturePage following AdminPage.tsx..." |
```

**Column notes:**

| Column | Source |
| --- | --- |
| Assignee | From team roster in `project-config.json` — match service tag `[BE]`/`[FE-Admin]` to owner |
| Subtask | Issue key + summary tag + short label (generated after MCP create) |
| Type | Primary Scope action: CREATE or MODIFY |
| OE | Original Estimate from `timetracking` field |
| Claude Code Prompt | Verbatim from the Implementation Hints note panel |
