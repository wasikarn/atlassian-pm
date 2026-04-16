# ADF Core Rules

## Issue Hierarchy

Epic → Task (2 levels only, no Story/Subtask)

## ADF Principles

1. Panel nodes allowed — use sparingly for info/warning/note/success highlights (see Allowed table below)
2. No blockquote — never use `>` markdown syntax or ADF blockquote node
3. Emoji allowed in H2 headings for section markers (e.g. `📘 Technical Reference`) — use sparingly, only for visual zone separators
4. No horizontal rules between sections — headings create separation naturally
5. No numbered section headings — no "1. Context", "2. Scope" style prefixes
6. AC type prefix: ✅ (happy path) / ⚠️ (edge case) / ❌ (error/negative) in bold paragraph text (NOT in heading)
7. Business-first ordering — for Epics: User Flow / Business Value / Customer Experience sections go BEFORE technical detail sections

## Allowed ADF Node Types

| Node | Usage |
| --- | --- |
| `heading` (h2) | Section titles |
| `paragraph` | Content text |
| `bulletList` / `listItem` | Unordered lists |
| `orderedList` / `listItem` | Numbered steps |
| `table` / `tableRow` / `tableHeader` / `tableCell` | Structured data |
| `panel` | Info/warning/note/success highlights — use `attrs.panelType` |
| `codeBlock` | Visual flow diagrams (text art), code examples |
| `inlineCard` | Cross-reference other Jira issues (`url` attr) |
| `text` (marks: `strong`, `em`, `code`, `link`) | Inline formatting |

## Panel Usage

- `panelType: "info"` — context/scope clarification, neutral highlight
- `panelType: "success"` — positive outcome scenario (e.g. auto-approve flow)
- `panelType: "warning"` — high-impact risks, critical constraints
- `panelType: "note"` — side-note, out-of-scope reminders

Panels create visual emphasis beyond plain paragraphs. Use sparingly (1-2 per section max) — overuse reduces impact.

## Forbidden ADF Node Types

| Node | Why |
| --- | --- |
| `blockquote` | No visual hierarchy — use `panel` instead |
| `rule` | Headings create separation naturally |

## CREATE vs EDIT

> **CRITICAL:** Different JSON formats — never interchange!

| Operation | Required | Forbidden |
| --- | --- | --- |
| **CREATE** | `projectKey`, `type`, `summary`, `description` | `issues` |
| **EDIT** | `issues`, `description` | `projectKey`, `type`, `summary`, `parent` |

`unknown field "projectKey"` → CREATE format used on EDIT · `unknown field "issues"` → EDIT format used on CREATE

## Inline Code

Mark file paths, routes, functions: `{"type": "text", "text": "src/file.tsx", "marks": [{"type": "code"}]}`

## Code Reference Format (G10 — v3.12.2)

> **Rule:** When referencing code in `Technical Reference`, `Code Paths Covered`, or any Task/Epic description, use one of these canonical shapes. Bare method names are ambiguous across sibling tickets and break cross-ticket searchability.

| Form | Example | When |
| --- | --- | --- |
| Full path | `app/Jobs/AiMediaAnalysisJob.ts:AiMediaAnalysisJob.handle()` | Preferred — anchors file + class + method |
| Class + method | `AiMediaAnalysisJob.handle()` | When file path already stated in same row/sentence |
| Class only | `AiMediaAnalysisJob` | Referring to the class as an entity, not a specific behavior |
| Function only | `fooHelper()` | Module-level function (no enclosing class) — acceptable |
| Bare method | ❌ `handle()` | Forbidden — too ambiguous across ticket bodies |

**Enforcement:** validator `T13` (WARN-level, Epic + Task) warns when an inline `code`-marked text looks like a bare method call (e.g. `handle()`, `run()`, `process()`) without a class prefix. Either add the class (`AiMediaAnalysisJob.handle()`) or use the full path form.

**Authoring rule:** copy-paste reveals lazy references — ถ้าเห็น bare `handle()` ใน inline code → เติม class name (`AiMediaAnalysisJob.handle()`) หรือ full path. ช่วย QA grep ได้จริงข้าม epic/ticket.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| `projectKey` in EDIT JSON | Use `issues` array only |
| `issues` in CREATE JSON | Use `projectKey`, `type`, `summary` |
| Missing `version: 1` | Always include in doc root |
| Wiki format | Use ADF JSON with acli |
| Nested bulletList | Flatten to single list |
| Missing marks array | `[{"type": "code"}]` not `"code"` |
| `blockquote` node | Replace with `panel` (info/note) |
| Panel overuse (>2 per section) | Convert to plain paragraph + bold |
| Technical sections above business sections (Epic) | Reorder: User Flow / Business Value first, technical reference last |
