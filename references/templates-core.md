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

## Jira Workflow (TaThep — ship-per-merge)

Binding convention (2026-04-16, rules C1-C13 + verdicts D1-D8). Ship = flag-OFF deploy to prod; Release = PM-approved flag-on.

Workflow states (preferred order):

```text
Backlog → In Progress → Shipped (flag-off) → Ready for QA → Released (flag-on) → Done
```

OR reinterpret the existing `Done` state = `Released` and add a `Shipped (flag-off)` intermediate state. The key invariant: **deploy and release are two events, not one**.

### Labels (convention)

| Label | When applied | Phase |
| --- | --- | --- |
| `vs-planned` | Slice planned in Epic, not started | pre-P0 |
| `vs-shipped-dark` | Shipped to prod, flag OFF | Phase 1 complete |
| `vs-released` | Flag ON, user-visible | Phase 4 complete |
| `carve-out-manual-gate` | Service in AI-agent / video carve-out (D5) | tagged at ticket creation |

### Phases (see skill `apm-slice-ship` for the full walkthrough)

1. Phase 0 — pre-ship checklist (flag registered, coverage ≥80%, rollback runbook, contract tests green)
2. Phase 1 — deploy to prod (flag OFF) — auto if eligible, staging + QA sign-off if not
3. Phase 2 — observability smoke (30-min post-deploy watch)
4. Phase 3 — QA verify on prod with flag OFF (dark)
5. Phase 4 — PM approves flag-on toggle → Release
6. Phase 5 — ticket → `Released` / `Done`; flag → 30-day TTL cleanup

### See also

- [vertical-slice-guide.md — Ship Strategy](vertical-slice-guide.md#ship-strategy-ship-per-merge-default)
- [flags-yaml-template.yaml](flags-yaml-template.yaml)
- Skill: `apm-slice-ship`

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

## External References

- **ADF JSON Schema (authoritative)** — <http://go.atlassian.com/adf-json-schema> — short link redirects to the versioned `@atlaskit/adf-schema` JSON schema on unpkg. Use when validating ADF structure, debugging `acli --from-json` payloads, or adding new node types.
- **ADF overview + examples** — <https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/>
- **ADF node reference** — <https://developer.atlassian.com/cloud/jira/platform/apis/document/nodes/>
- **ADF mark reference** — <https://developer.atlassian.com/cloud/jira/platform/apis/document/marks/>

### Key schema takeaways (from v52.5.0, 2026-04-16)

- `codeBlock` — free-string `language` attr (no `mermaid` enum), plain text content only, `marks: maxItems 0`. What APM uses for ASCII diagrams.
- `extension` / `bodiedExtension` — ADF's official diagram-rendering path (Mermaid, draw.io). Requires a marketplace app to render; parameters object is schema-free.
- `mediaSingle` with `type: "external"` — allows external image URL (SVG possible), subject to Jira CSP / trusted-domain policy.
- `panel` — 7 `panelType` values (`info`, `note`, `tip`, `warning`, `error`, `success`, `custom`); may contain `codeBlock`, `media`, `extension`.
- `expand` / `nestedExpand` — collapsible block; useful for hiding long diagrams or appendices.
- No native `diagram`, `mermaid`, `flowchart`, `chart`, `drawio`, or `excalidraw` node — all delegated to `extension`.
