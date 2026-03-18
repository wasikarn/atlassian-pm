# Technical Note Best Practices

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, panel types, styling

## Tech Note vs ADR

| Condition | Use ADR | Use Tech Note |
| --- | --- | --- |
| Architecture/technology decision | ✅ | |
| Implementation guidance | | ✅ |
| Alternatives to document | ✅ | |
| Scope = 1 ticket | | ✅ |
| Scope = multi-ticket / system-wide | ✅ | |
| Needs future review (e.g. 6 months) | ✅ | |

## When to Write

| Situation | Required? | Reason |
| --- | --- | --- |
| Subtask with clear scope, dev knows codebase | No | AC is sufficient |
| Story with new API contract or complex data flow | Yes | Reduces ambiguity for dev |
| Cross-service integration (BE↔FE, external API) | Yes | Prevents miscommunication |
| New pattern/library the team hasn't used | Yes | Reduces learning curve |
| Bug fix with known root cause | No | Put root cause in ticket |

## JBGE Principle (Just Barely Good Enough)

Write only the sections that are necessary — not every section needs to be filled.

**Required:** Objective (1-2 sentences) | Scope (real file paths) | Approach (step-by-step, high-level)

**Recommended (when applicable):** API Contract (new/changed endpoints) | Data Flow (cross-service) | Dependencies (blocked by other tickets) | Alternatives (>1 approach) | Risks | Open Questions

## Size Guide

| Size | Lines | Best For |
| --- | --- | --- |
| Minimal | 5-10 | Single subtask, clear scope |
| Standard | 10-25 | Story with API/integration |
| Extended | 25-50 | Cross-service, new pattern |
| Too Long | > 50 | Should be Tech Spec/ADR instead |

## Writing Rules

**Do:** Use bullet points (not long paragraphs) | Use code marks for file paths, functions, routes | Use real file paths from codebase (always Explore first) | Use arrow notation for data flow: `Client → API → Service → DB` | Link to Jira/Confluence/Figma when referencing

**Don't:** Duplicate AC in tech note (AC = WHAT, tech note = HOW) | Micromanage code line-by-line | Use generic paths ("fix backend files") | Write >1 page (split to Tech Spec/ADR) | Write before story is refined | Never update (review every sprint, archive when done)
