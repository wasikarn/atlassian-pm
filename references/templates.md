# ADF Templates Reference (Index)

> **Split for efficiency** — load only the template section you need

| Template | File | Content |
|----------|------|---------|
| **Core Rules** | [templates-core.md](templates-core.md) | CREATE/EDIT, panels, styling, common mistakes |
| **HR Rules** | [hr-rules.md](hr-rules.md) | Hard Rules canonical reference (HR1-HR10) with examples |
| **Epic** | [templates-epic.md](templates-epic.md) | Epic template + best practices |
| **Story** | [templates-story.md](templates-story.md) | Story template + AC naming |
| **Subtask & QA** | [templates-subtask.md](templates-subtask.md) | Subtask + QA templates |
| **Task** | [templates-task.md](templates-task.md) | Tech-debt, bug, chore, spike |
| **Tech Note** | [templates-technote.md](templates-technote.md) | Tech Note best practices |
| **Blueprint** | (inline in SKILL.md) | Blueprint Confluence page structure (8 sections) |

## Loading Guide

**Always load:** `templates-core.md` (CREATE/EDIT rules, panel types)

**Then load by issue type:**

| Skill | Load |
|-------|------|
| `/create-epic`, `/update-epic` | core + epic |
| `/update-story` | core + story |
| `/analyze-story`, `/update-subtask` | core + subtask |
| `/story-full`, `/sync-alignment` | core + story + subtask |
| `/create-testplan` | core + subtask (QA section) |
| `/create-task`, `/update-task` | core + task |
| `/create-doc` | core + technote |
| `/feature-blueprint` | (uses inline template in SKILL.md) |
| `/verify-issue` | core only |
