# Vibe Mode Templates & Rules

> **Prerequisite:** → see [templates-core.md](templates-core.md) for panel types · [templates-subtask.md](templates-subtask.md) for base ADF

## Purpose

Vibe mode is **speed through less ceremony, NOT less quality.** Skips: discovery interviews, annotation rounds, RICE scoring. Keeps: codebase exploration, QG≥90%, HR1–HR10. Use `--thorough` for full ceremony.

**Core insight:** A subtask IS an AI prompt. Rich Implementation Hints → Claude Code produces production-ready code on first pass. No hints → generic scaffolding. Vibe mode front-loads codebase exploration to make hints accurate.

---

## Context Engineering Rules

1. **Verification-first** — Explore codebase (QMD, AST grep, file reads) before writing any ADF. Guessing paths produces hints that mislead Claude Code.
2. **Point to pattern files** — Every subtask must reference a concrete REF file. "Follow best practices" gives Claude Code nothing to anchor on.
3. **Separate explore from implement** — Finish exploring before writing ADF. Never interleave.
4. **Just-in-time context** — Load references only when the current phase needs them.
5. **Canonical examples over descriptions** — Point to a working file in the codebase, not prose.
6. **Single concern per subtask** — One file or one tightly-coupled pair (service + test). 4+ CREATE files = split it.
7. **Lean descriptions, rich hints** — Keep summary/objective short. Detail goes in Section 4.

---

## Vibe Mode Rules

| Aspect | Vibe Mode |
| --- | --- |
| Discovery interview | **SKIP** — use existing context |
| ITERATE annotation rounds | **SKIP** — single pass |
| RICE scoring | **SKIP** |
| REVIEW gates between phases | **SKIP** |
| Codebase exploration | **MANDATORY** — no hints without it |
| QG ≥ 90% | **KEEP** — non-negotiable |
| HR1–HR10 hard rules | **KEEP** — non-negotiable |
| Two-step subtask creation (HR5) | **KEEP** — MCP create → verify parent → acli edit |
| Section 4 Implementation Hints | **MANDATORY** — the whole point of vibe mode |

---

## Implementation Hints (Section 4 ADF)

Add after Section 3, preceded by `{"type": "rule"}`. Field mapping from codebase exploration:

| Field | Source | Required |
| --- | --- | --- |
| Entry Point | Primary CREATE/MODIFY file from Scope table | Yes |
| Pattern to Follow | REF file from Scope table — structural model | Yes |
| Test Command | Exact command scoped to new file path | Yes |
| Related API | BE only — HTTP method + route | Optional |
| Dependencies | Constructor-injected services/repos from REF | Optional |

### ADF JSON (Section 4 note panel)

Shorthand: `cell(text)` = `{"type":"tableCell","content":[{"type":"paragraph","content":[{"type":"text","text":"TEXT"}]}]}` · `cell(text, code)` = same with `"marks":[{"type":"code"}]` · `hdr(text)` = tableHeader with `"background":"#eae6ff"`

```json
{"type":"rule"},
{"type":"heading","attrs":{"level":2},"content":[{"type":"text","text":"4. 🤖 Implementation Hints"}]},
{"type":"panel","attrs":{"panelType":"note"},"content":[
  {"type":"table","attrs":{"isNumberColumnEnabled":false,"layout":"default"},"content":[
    {"type":"tableRow","content":[hdr("Key"), hdr("Value")]},
    {"type":"tableRow","content":[cell("Entry Point"), cell("app/Services/Feature/NewService.ts", code)]},
    {"type":"tableRow","content":[cell("Pattern to Follow"), cell("app/Services/Existing/ExampleService.ts (REF)", code)]},
    {"type":"tableRow","content":[cell("Test Command"), cell("node ace test --files \"tests/unit/services/feature*\"", code)]},
    {"type":"tableRow","content":[cell("Related API"), cell("POST /api/v1/feature")]},
    {"type":"tableRow","content":[cell("Dependencies"), cell("FeatureRepository, BaseService")]}
  ]},
  {"type":"paragraph","content":[{"type":"text","text":"Claude Code Prompt:","marks":[{"type":"strong"}]}]},
  {"type":"paragraph","content":[{"type":"text","text":"Implement [objective] following the pattern in [Pattern to Follow]. Run [Test Command] to verify. All ACs must pass."}]}
]}
```

---

## Claude Code Prompt Format

One-line instruction Claude reads when developer runs `implement {{PROJECT_KEY}}-123`.

**Template:** `"Implement [objective] following [Pattern file] as the pattern. Key files: [scope CREATE/MODIFY rows]. Run [test command] when done. ACs: [AC1, AC2, AC3]."`

**Example:** `"Implement LineNotificationChannel following app/Services/Notification/SlackNotificationChannel.ts as the pattern. Key files: CREATE app/Services/Notification/LineNotificationChannel.ts, MODIFY NotificationManager.ts. Run node ace test --files 'tests/unit/services/notification/line*' when done. ACs: channel.notify() sends HTTP POST, failed delivery sets status='failed', unsupported type throws UnsupportedMessageTypeException."`

### Anti-patterns

| Anti-pattern | Fix |
| --- | --- |
| `"Implement the notification feature"` | Reference exact file paths from codebase |
| `"Follow best practices"` | Name the specific REF file |
| `"Run the tests"` | Scope to file glob matching the new file |
| Omitting ACs in the prompt | List all ACs verbatim |
| 6+ files as CREATE | Split into multiple subtasks |

---

## Delegation View Format

Use in vibe-plan Summary phase for scannable tech lead overview.

```markdown
| Assignee | Subtask | Type | OE | Claude Code Prompt |
|----------|---------|------|----|--------------------|
| dev@email.com | {{PROJECT_KEY}}-101 [BE] setup service | CREATE | 4h | "Implement X following Y..." |
| dev@email.com | {{PROJECT_KEY}}-102 [BE] add endpoint | MODIFY | 2h | "Add POST /api/v1/feature to Z following W..." |
| fe@email.com  | {{PROJECT_KEY}}-103 [FE-Admin] add page | CREATE | 4h | "Implement FeaturePage following AdminPage.tsx..." |
```

| Column | Source |
| --- | --- |
| Assignee | Team roster in `project-config.json` — match service tag to owner |
| Type | Primary Scope action: CREATE or MODIFY |
| OE | `timetracking` field |
| Claude Code Prompt | Verbatim from Implementation Hints note panel |
