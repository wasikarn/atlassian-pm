---
paths:
  - "scripts/confluence/**/*.py"
  - "skills/shared-references/mermaid-guide.md"
  - "docs/mermaid/**/*.md"
---

## Mermaid Diagrams

When creating or editing Mermaid diagrams, read the relevant official docs BEFORE writing diagram code:

- **Flowchart**: `docs/mermaid/flowchart.md` — nodes, edges, subgraphs, styling, curves, ELK renderer
- **State Diagram**: `docs/mermaid/stateDiagram.md` — states, transitions, composite, choice, fork/join, classDef
- **Sequence Diagram**: `docs/mermaid/sequenceDiagram.md` — participants, messages, activations, loops, alt/par
- **Architecture**: `docs/mermaid/architecture.md` — groups, services, edges, junctions, icons (v11.1.0+)
- **Packet**: `docs/mermaid/packet.md` — network packet structure, bit ranges (v11.0.0+)
- **Gantt**: `docs/mermaid/gantt.md` — tasks, sections, milestones, excludes, compact mode, date formats

Project-specific patterns and Confluence constraints: `skills/shared-references/mermaid-guide.md`

### Edge Animation (Flowchart only)

Syntax: `e1@-->` assigns edge ID, `e1@{ animation: fast/slow }` sets speed. Only works on flowchart edges — NOT on sequenceDiagram, stateDiagram, or gantt. Confirmed working on Confluence Forge plugin v11.12.2.

Convention: `slow` for cross-system edges (Pusher, API calls), `fast` for interrupt/critical paths. See `mermaid-guide.md` → "Edge Animation" section for full docs.

**Gotcha:** `&` syntax (`D & E e1@--> F`) only assigns edge ID to ONE edge. Must split: `D e1@--> F` + `E e2@--> F`.
