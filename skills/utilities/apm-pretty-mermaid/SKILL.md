---
name: apm-pretty-mermaid
description: |
  Render Mermaid diagrams to ASCII for Jira ADF code blocks. Wraps beautiful-mermaid with APM-aware defaults: zero-dependency ASCII fits Jira Epic/Task/Bug/Spike descriptions.

  Trigger phrases:
  - "render mermaid", "pretty mermaid", "beautify diagram"
  - "ascii diagram", "jira diagram", "terminal diagram"
  - "mermaid for jira"
  - "สร้าง mermaid", "วาด diagram", "diagram ASCII"

  Use this skill when a Jira issue (any type) needs a rendered diagram.
  Confluence uses the native Forge Mermaid macro with raw `.mmd` — no skill needed there.
x-compatibility: []
argument-hint: "diagram.mmd [--code <inline mermaid>]"
effort: low
user-invocable: true
---

# APM Pretty Mermaid

**Role:** Developer / Tech Lead / PM
**Output:** ASCII only (Jira ADF code blocks)

> **APM convention:** Jira diagram = ASCII in a code block. Width ≤ 80 cols. Confluence = raw `.mmd` in Forge Mermaid macro — not this skill. See `.claude/rules/mermaid.md` + `references/mermaid-guide.md`.

## When to use

| Target | Format |
| --- | --- |
| Jira Epic / Task / Bug / Spike / Chore description or comment | **ASCII** via this skill, or hand-draw |
| Confluence page | Forge Mermaid macro (raw `.mmd` paste) — see `references/mermaid-guide.md` |

## Quick Start

```bash
# From .mmd file → ASCII to stdout
node scripts/render.mjs \
  --input diagram.mmd \
  --format ascii \
  --use-ascii

# Copy output into a Jira code block in the ADF description.
```

Batch (multiple diagrams):

```bash
node scripts/batch.mjs \
  --input-dir ./diagrams \
  --output-dir ./ascii \
  --format ascii \
  --use-ascii \
  --workers 4
```

## APM Workflow

1. Decide diagram type (`sequenceDiagram` / `erDiagram` / `classDiagram` / `stateDiagram-v2` / linear `flowchart`).
2. Write `.mmd` (templates in `assets/example_diagrams/`).
3. Render ASCII:

   ```bash
   node skills/utilities/apm-pretty-mermaid/scripts/render.mjs \
     --input /tmp/diagram.mmd \
     --format ascii --use-ascii > /tmp/diagram.txt
   ```

4. Embed in ADF description as a code block:

   ```json
   {
     "type": "codeBlock",
     "attrs": { "language": "text" },
     "content": [{ "type": "text", "text": "<paste ASCII here>" }]
   }
   ```

5. Run QG: `uv run scripts/api/validate_adf.py <file> --type task --json` (≥ 90).
6. Create/update via `acli --from-json` or MCP.

## Diagram Types

See [references/DIAGRAM_TYPES.md](references/DIAGRAM_TYPES.md). Quick pick:

| Use case | Type | ASCII status |
| --- | --- | --- |
| API call / service interaction | `sequenceDiagram` | ✅ **best** — no width/label issues |
| Data model / DB schema | `erDiagram` | ✅ |
| Class / object relationship | `classDiagram` | ✅ |
| State machine | `stateDiagram-v2` | ✅ (2-branch), ⚠️ (3+) |
| Linear workflow / 2-branch decision | `flowchart` | ✅ |
| **3+ branch decision flow** | `flowchart` | ❌ **broken** — see Known Issues |
| Sprint dependency graph | `flowchart LR` with subgraphs | ⚠️ width blow-up |
| Gantt / release timeline | `gantt` | ❌ not supported in ASCII — render in Confluence Forge Mermaid macro instead |

## Known Issues

**Flowchart with 3+ branches from one decision node renders broken ASCII** (upstream bug [mermaid-ascii#56](https://github.com/AlexanderGrooff/mermaid-ascii/issues/56), unpatched) — edge labels mash into gibberish. Sequence/state/ER/class diagrams unaffected.

**Fix:** hand-draw ASCII in the Jira code block using box chars (`┌─┐│└┘├┤▶▼`). Author-controlled layout always fits ≤ 80 cols. Alternatively convert to `sequenceDiagram` and render via this skill.

## Options

| Flag | Purpose | Default |
| --- | --- | --- |
| `--input` | Source `.mmd` file | required unless `--code` |
| `--code` / `-c` | Inline Mermaid source (string) instead of a file | — |
| `--format ascii` | Output format (only ASCII is part of the documented surface) | `ascii` |
| `--use-ascii` | Pure ASCII (no Unicode box chars) | false |
| `--padding-x` / `--padding-y` | ASCII spacing | auto |
| `--workers` | Batch parallelism (batch.mjs only) | 4 |

## Examples

### ✅ Good

```bash
# Jira Epic {{PROJECT_KEY}}-182 architecture diagram (ASCII)
node skills/utilities/apm-pretty-mermaid/scripts/render.mjs \
  --input /tmp/tp-182-arch.mmd --format ascii --use-ascii

# Batch-render 12 sprint dependency diagrams as ASCII
node skills/utilities/apm-pretty-mermaid/scripts/batch.mjs \
  --input-dir .scratch/sprint-deps --output-dir .scratch/ascii \
  --format ascii --use-ascii --workers 8
```

### ❌ Bad

```bash
# ASCII wider than 80 cols in Jira code block — horizontal scroll hell
# Fix: simplify graph OR hand-draw OR move to Confluence Forge Mermaid macro

# Using this skill for Confluence pages
# Fix: paste raw .mmd into the Forge Mermaid macro — Confluence renders natively
```

## Common Mistakes

- ASCII > 80 cols — breaks code block on narrow screens; either simplify or move to Confluence.
- Forgetting `--use-ascii` — default ASCII uses Unicode box characters, which some Jira fonts render poorly; `--use-ascii` forces pure `+-|` style.
- Running without `node_modules/beautiful-mermaid` — first run auto-installs; CI/sandbox should pre-run `npm install` in the skill dir.
- Trying to render Gantt as ASCII — unsupported; use Forge Mermaid macro on a Confluence page.

## Prerequisites

- `node` 18+ (for `beautiful-mermaid` ESM)
- First run auto-installs `beautiful-mermaid` in `skills/utilities/apm-pretty-mermaid/`; offline environments: `cd skills/utilities/apm-pretty-mermaid && npm install` once.

## References

- [references/DIAGRAM_TYPES.md](references/DIAGRAM_TYPES.md) — syntax guide
- `assets/example_diagrams/` — starter templates (flowchart, sequence, state, class, er)
- Project rule: `.claude/rules/mermaid.md`
- Jira + Confluence patterns: `references/mermaid-guide.md`
- Team convention lives in the user's project memory (APM instance-specific)

## 🎓 Domain Expert Notes

**Why ASCII for Jira:** Jira ADF code blocks render in monospace across web, mobile, and gh-cli. ASCII survives copy-paste, search, grep, and AI-agent parsing. Attachment-based images break the agent-readable ticket convention.

**Why Forge Mermaid macro for Confluence:** Confluence renders Mermaid natively via the Forge plugin. Pasting raw `.mmd` into the macro keeps the page source clean and re-rendering is free — no attachment upload step, no version drift between source and rendered output.

**Width discipline:** 80 cols ≈ iPhone 14 Pro landscape width in Jira mobile. Going wider hides half the diagram behind horizontal scroll. If the graph doesn't fit, it's a signal to split into 2 diagrams or promote to a Confluence page.

**Failure modes:**

- Node.js missing in CI → batch script silently produces 0 files; gate with `node --version` precheck.
- Mermaid syntax error → `beautiful-mermaid` throws on parse; run on <https://mermaid.live/> to debug before re-running.
