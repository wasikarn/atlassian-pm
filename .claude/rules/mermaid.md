---
paths:
  - "scripts/confluence/**/*.py"
  - "references/mermaid-guide.md"
  - "docs/mermaid/**/*.md"
---

## Mermaid Diagrams

**APM default:** ASCII in Jira (all issue types) · raw `.mmd` in Confluence Forge Mermaid macro.

**Render via skill:** `/atlassian-pm:apm-pretty-mermaid` — wraps beautiful-mermaid with APM defaults (`--format ascii --use-ascii`). Confluence renders `.mmd` natively via Forge, no skill needed.

| Target | Format | Width |
| --- | --- | --- |
| Jira Epic / Task / Bug / Spike / Chore / comment | **ASCII** code block | ≤ 80 cols |
| Confluence page | Forge Mermaid macro (raw `.mmd`) | any |
| Gantt / release timeline | Forge Mermaid macro on Confluence (ASCII renderer does not support gantt) | any |

If ASCII exceeds 80 cols: simplify OR split into 2 diagrams OR move to Confluence Forge Mermaid macro + Smart Link from Jira.

**⚠️ 3+ branch flowchart broken in ASCII** (upstream bug [mermaid-ascii#56](https://github.com/AlexanderGrooff/mermaid-ascii/issues/56)). Fix: **hand-draw ASCII** with box chars (`┌─┐│└┘├┤▶▼`), or convert to `sequenceDiagram`. Sequence/state/ER/class unaffected.

When creating or editing Mermaid diagrams, read the relevant official docs BEFORE writing diagram code:

- **Flowchart**: `docs/mermaid/flowchart.md` — nodes, edges, subgraphs, styling, curves, ELK renderer
- **State Diagram**: `docs/mermaid/stateDiagram.md` — states, transitions, composite, choice, fork/join, classDef
- **Sequence Diagram**: `docs/mermaid/sequenceDiagram.md` — participants, messages, activations, loops, alt/par
- **Architecture**: `docs/mermaid/architecture.md` — groups, services, edges, junctions, icons (v11.1.0+)
- **Packet**: `docs/mermaid/packet.md` — network packet structure, bit ranges (v11.0.0+)
- **Gantt**: `docs/mermaid/gantt.md` — tasks, sections, milestones, excludes, compact mode, date formats

Project-specific patterns (Confluence + Jira ASCII): `references/mermaid-guide.md`

### Edge Animation (Flowchart only)

Syntax: `e1@-->` assigns edge ID, `e1@{ animation: fast/slow }` sets speed. Only works on flowchart edges — NOT on sequenceDiagram, stateDiagram, or gantt. Confirmed working on Confluence Forge plugin v11.12.2.

Convention: `slow` for cross-system edges (Pusher, API calls), `fast` for interrupt/critical paths. See `mermaid-guide.md` → "Edge Animation" section for full docs.

**Gotcha:** `&` syntax (`D & E e1@--> F`) only assigns edge ID to ONE edge. Must split: `D e1@--> F` + `E e2@--> F`.
