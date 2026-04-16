---
name: apm-pretty-mermaid
description: |
  Render Mermaid diagrams into ASCII (default, for Jira ADF code blocks) or themed SVG (for Confluence). Wraps beautiful-mermaid with APM-aware defaults: zero-dependency ASCII fits Jira Epic/Task/Bug/Spike descriptions; SVG targets Confluence attachments.

  Trigger phrases:
  - "render mermaid", "pretty mermaid", "beautify diagram"
  - "ascii diagram", "jira diagram", "terminal diagram"
  - "mermaid for jira", "mermaid for confluence"
  - "สร้าง mermaid", "วาด diagram", "diagram ASCII"

  Use this skill when a Jira issue (any type) or Confluence page needs a diagram.
  Default output = ASCII in a code block — zero dependency, renders identically in Jira, gh-cli, terminal.
x-compatibility: []
argument-hint: "[diagram.mmd | --code] [--format ascii|svg] [--theme <name>] [--jira|--confluence]"
effort: low
user-invocable: true
---

# APM Pretty Mermaid

**Role:** Developer / Tech Lead / PM
**Default output:** ASCII (Jira-friendly, zero-dependency)
**Fallback output:** SVG (Confluence attachment, themed)

> **APM convention:** Jira ASCII-first (see `feedback_jira_ascii_diagrams.md`). Width ≤ 80 cols. Complex diagrams → render SVG + attach to Confluence + Smart Link from Jira.

## When to use which format

| Target | Format | Reason |
| --- | --- | --- |
| Jira Epic / Task / Bug / Spike / Chore description | **ASCII** (default) | Code block renders identically · zero plugin dependency · diff-friendly · ≤ 80 cols |
| Jira comment | **ASCII** | Same as above |
| Confluence page (simple, inline) | Mermaid macro (raw `.mmd`) | Forge Mermaid plugin renders natively — see `references/mermaid-guide.md` |
| Confluence page (complex, high-fidelity) | **SVG attachment** | Themed, scalable, presentation-ready |
| Presentation / slide / external share | **SVG** | Theme selection, transparent bg |

## Quick Start

### 1. Jira ASCII (default)

```bash
# From .mmd file
node scripts/render.mjs \
  --input diagram.mmd \
  --format ascii \
  --use-ascii

# Copy output into Jira code block (```) in the ADF description
```

### 2. Confluence SVG

```bash
node scripts/render.mjs \
  --input diagram.mmd \
  --output diagram.svg \
  --format svg \
  --theme tokyo-night \
  --transparent
```

### 3. Batch (multiple Jira issues)

```bash
node scripts/batch.mjs \
  --input-dir ./diagrams \
  --output-dir ./ascii \
  --format ascii \
  --use-ascii \
  --workers 4
```

## APM Workflow

### Pattern A — Jira issue (any type)

1. Decide diagram type (flowchart / sequence / state / class / ER).
2. Write `.mmd` file (templates in `assets/example_diagrams/`).
3. Render ASCII:

   ```bash
   node skills/utilities/apm-pretty-mermaid/scripts/render.mjs \
     --input /tmp/diagram.mmd \
     --format ascii --use-ascii > /tmp/diagram.txt
   ```

4. Embed in ADF description as code block:

   ```json
   {
     "type": "codeBlock",
     "attrs": { "language": "text" },
     "content": [{ "type": "text", "text": "<paste ASCII here>" }]
   }
   ```

5. Run QG: `uv run scripts/api/validate_adf.py <file> --type task --json` (≥ 90).
6. Create/update via `acli --from-json` or MCP.

### Pattern B — Confluence page

1. Write `.mmd`.
2. Render SVG with theme:

   ```bash
   node skills/utilities/apm-pretty-mermaid/scripts/render.mjs \
     --input /tmp/diagram.mmd \
     --output /tmp/diagram.svg \
     --theme tokyo-night --transparent
   ```

3. Upload via `confluence_upload_attachment` → embed `<ac:image>` in storage format.
4. For raw Mermaid macro (Forge plugin): see `references/mermaid-guide.md`.

### Pattern C — Complex diagram spanning Jira + Confluence

1. Render SVG → attach to Confluence.
2. Render ASCII preview (simplified) → embed in Jira.
3. Add Smart Link in Jira pointing to Confluence page.

## Diagram Types

See [references/DIAGRAM_TYPES.md](references/DIAGRAM_TYPES.md). Quick pick:

| Use case | Type | ASCII status |
| --- | --- | --- |
| API call / service interaction | `sequenceDiagram` | ✅ **best** — no width/label issues |
| Data model / DB schema | `erDiagram` | ✅ |
| Class / object relationship | `classDiagram` | ✅ |
| State machine | `stateDiagram-v2` | ✅ (2-branch), ⚠️ (3+) |
| Linear workflow / 2-branch decision | `flowchart` | ✅ |
| **3+ branch decision flow** | `flowchart` | ❌ **broken** — use `sequenceDiagram` or graph-easy (see Known Issues) |
| Sprint dependency graph | `flowchart LR` with subgraphs | ⚠️ width blow-up |
| Release timeline | `gantt` | SVG only — ASCII renderer does not support gantt |

## Known Issues

### ❌ Multi-branch flowchart label overlap (beautiful-mermaid / mermaid-ascii bug)

**Symptom:** flowchart with 3+ outgoing edges from one decision node → edge labels mash into gibberish (e.g., `Branch-C:auncertainw/crequires-reviewhigh`). Upstream bug [mermaid-ascii#56](https://github.com/AlexanderGrooff/mermaid-ascii/issues/56), unpatched, no forks fix.

**Verified workarounds:**

1. **Convert to `sequenceDiagram`** (preferred) — linear time axis, no collision. Typical width: **85–100 cols**. Example: actor → actor interactions with `alt / else` blocks for branches.
2. **Switch renderer to `graph-easy`** (Perl) — pipe DOT input → `graph-easy --as=boxart`. Labels render correctly but width typically **150–200 cols** for 3-branch (exceeds 80-col rule). Install: `cpanm Graph::Easy`.
3. **Ultra-short labels + legend** — node labels ≤ 4 chars (e.g., `AP`, `RJ`), edge labels ≤ 3 chars, full names in a legend table below. Fits ≤ 80 cols but sacrifices readability.

**Empirical width table** (3-branch decision, 8-node flow):

| Approach | Width | Readable |
| --- | --- | --- |
| `sequenceDiagram` | 85–100 | ✅ |
| `graph-easy` medium labels | 164–190 | ✅ |
| `graph-easy` short labels + legend | 71–73 | ⚠️ cryptic |
| `graph-easy` LR direction | 220–295 | ✅ but too wide |
| `beautiful-mermaid` flowchart | 200+ | ❌ labels mash |

**Decision rule:**

```
diagram is interaction / has branches?
├── yes → sequenceDiagram (default for Jira)
└── no  → flowchart OK (linear or 2-branch only)
```

## Themes (SVG only)

```bash
node scripts/themes.mjs
```

Recommended for Confluence:

- **Dark pages:** `tokyo-night` (default), `github-dark`, `dracula`
- **Light pages:** `github-light`, `zinc-light`, `catppuccin-latte`
- **Print / export:** `zinc-light`, `solarized-light`

Full theme reference: [references/THEMES.md](references/THEMES.md)

## Options

| Flag | Purpose | Default |
| --- | --- | --- |
| `--input` | Source `.mmd` file | required |
| `--output` | Destination file (SVG) | stdout (ASCII) |
| `--format` | `svg` \| `ascii` | `svg` |
| `--theme` | Theme name | none |
| `--use-ascii` | Pure ASCII (no Unicode box chars) | false |
| `--padding-x` / `--padding-y` | ASCII spacing | auto |
| `--transparent` | Transparent SVG bg | false |
| `--bg` / `--fg` / `--accent` | Override theme colors | theme |
| `--font` | SVG font family | Inter |
| `--workers` | Batch parallelism | 4 |

## Examples

### ✅ Good

```bash
# Jira Epic {{PROJECT_KEY}}-182 architecture diagram (ASCII)
node skills/utilities/apm-pretty-mermaid/scripts/render.mjs \
  --input /tmp/tp-182-arch.mmd --format ascii --use-ascii

# Confluence release page (SVG, dark theme, transparent)
node skills/utilities/apm-pretty-mermaid/scripts/render.mjs \
  --input /tmp/release-flow.mmd --output /tmp/release-flow.svg \
  --theme tokyo-night --transparent

# Batch-render 12 sprint dependency diagrams as ASCII
node skills/utilities/apm-pretty-mermaid/scripts/batch.mjs \
  --input-dir .scratch/sprint-deps --output-dir .scratch/ascii \
  --format ascii --use-ascii --workers 8
```

### ❌ Bad

```bash
# SVG in Jira ADF description — not rendered, waste of bytes
# Fix: use --format ascii

# ASCII wider than 80 cols in Jira code block — horizontal scroll hell
# Fix: simplify graph OR render SVG + attach to Confluence + Smart Link

# Using pretty-mermaid for Confluence Forge Mermaid macro
# Fix: write raw .mmd into the macro — Forge renders natively
```

## Common Mistakes

- Embedding SVG in Jira — Jira ADF does not render SVG inline; use ASCII or attach as file.
- ASCII > 80 cols — breaks code block on narrow screens; either simplify or move to Confluence.
- Forgetting `--use-ascii` — default ASCII uses Unicode box characters, which some Jira fonts render poorly; `--use-ascii` forces pure `+-|` style.
- Running without `node_modules/beautiful-mermaid` — first run auto-installs; CI/sandbox should pre-run `npm install` in the skill dir.

## Prerequisites

- `node` 18+ (for `beautiful-mermaid` ESM)
- First run auto-installs `beautiful-mermaid` in `skills/utilities/apm-pretty-mermaid/`; offline environments: `cd skills/utilities/apm-pretty-mermaid && npm install` once.

## References

- [references/DIAGRAM_TYPES.md](references/DIAGRAM_TYPES.md) — syntax guide
- [references/THEMES.md](references/THEMES.md) — theme catalog
- `assets/example_diagrams/` — 5 starter templates (flowchart, sequence, state, class, er)
- Project rule: `.claude/rules/mermaid.md` — when to consult official Mermaid docs
- Confluence + Jira ASCII patterns: `references/mermaid-guide.md`
- Jira convention: `MEMORY.md` → "Jira ASCII Diagrams"

## 🎓 Domain Expert Notes

**Why ASCII-first for Jira:** Jira ADF code blocks render in monospace across web, mobile, and gh-cli. SVG requires attachment + inline image, which breaks copy-paste, search, and AI-agent parsing. ASCII survives compaction, grep, and the agent-readable ticket convention (see MEMORY.md → "AI-Agent-Readable Tickets").

**Why themed SVG for Confluence:** Confluence pages are read for review and presentation; visual density and theme consistency matter. Attachment-based SVG keeps the page source clean and allows re-render without touching page storage.

**Width discipline:** 80 cols ≈ iPhone 14 Pro landscape width in Jira mobile. Going wider hides half the diagram behind horizontal scroll. If the graph doesn't fit, it's a signal to split into 2 diagrams (zoom out + zoom in) or promote to Confluence SVG.

**Failure modes:**

- Node.js missing in CI → batch script silently produces 0 files; gate with `node --version` precheck.
- Mermaid syntax error → `beautiful-mermaid` throws on parse; run on <https://mermaid.live/> to debug before re-running.
- Theme name typo → script falls back to default palette with no warning; validate against `node scripts/themes.mjs` output.
