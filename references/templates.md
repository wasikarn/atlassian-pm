# ADF Templates Reference (Index)

> **Split for efficiency** — load only the template section you need

| Template | File | Content |
|----------|------|---------|
| **Core Rules** | [templates-core.md](templates-core.md) | CREATE/EDIT, headings, styling, common mistakes |
| **HR Rules** | [hr-rules.md](hr-rules.md) | Hard Rules canonical reference (HR1-HR10) with examples |
| **Epic** | [templates-epic.md](templates-epic.md) | Epic template + best practices |
| **Task** | [templates-task.md](templates-task.md) | Unified Task template — feature, QA, bug, spike, chore modes |
| **Tech Note** | [templates-technote.md](templates-technote.md) | Tech Note best practices |
| **PRD** | (in create-doc refs) | Product Requirements Document template |
| **Vibe** | [templates-vibe.md](templates-vibe.md) | Implementation Hints ADF, Context Engineering rules, Claude Code Prompt format, Delegation View |

## Loading Guide

**Always load:** `templates-core.md` (CREATE/EDIT rules, heading structure)

**Then load by issue type:**

| Skill | Load |
|-------|------|
| `/create-epic`, `/update-epic` | core + epic |
| `/create-task`, `/update-task` | core + task |
| `/create-doc` | core + technote (+ prd refs for PRD type) |
| `/blueprint` | (uses inline template in SKILL.md) |
| `/verify-issue` | core only |
| `/vibe-plan` | core + task + **vibe** |
