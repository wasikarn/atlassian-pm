## tech-spec Template

```markdown
# [Title] - Technical Specification

## Overview
[Brief description of what this spec covers]

## Related Issues
- [ABC-XXX](https://{{JIRA_SITE}}/browse/ABC-XXX)

---

## Requirements

### Functional Requirements
- FR-1: [Requirement]
- FR-2: [Requirement]

### Non-Functional Requirements
- NFR-1: [Performance/Security/etc.]

---

## Design

### Architecture
[High-level architecture description]

### Data Model
[Database changes if any]

### Sequence Diagram
[Flow description or diagram]

---

## API Specification

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/resource | Create resource |
| GET | /api/v1/resource/:id | Get resource |

### Request/Response Examples
[Code examples]

---

## Testing Strategy

### Unit Tests
- [Test case 1]

### Integration Tests
- [Test case 1]

### Manual Testing
- [Test scenario 1]

---

## Rollout Plan
1. Deploy to staging
2. QA verification
3. Deploy to production

## Rollback Plan
[How to rollback if issues arise]
```

## adr Template

```markdown
# ADR-XXX: [Title]

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
[What is the issue that we're seeing that is motivating this decision?]

## Decision
[What is the change that we're proposing and/or doing?]

## Options Considered

### Option 1: [Name]
**Pros:**
- [Pro 1]

**Cons:**
- [Con 1]

### Option 2: [Name]
**Pros:**
- [Pro 1]

**Cons:**
- [Con 1]

## Consequences

### Positive
- [Positive consequence 1]

### Negative
- [Negative consequence 1]

## Related
- [Link to related ADRs or issues]
```

## parent Template

```markdown
# [Title]

[Brief description of what this category contains]

{toc:maxLevel=2}

---

## 📄 Sub-pages

{children:all=true|sort=title}

---

## 🏷️ Topics Covered

| Topic | Description |
| --- | --- |
| [Topic 1] | [Description] |
| [Topic 2] | [Description] |

---

## 🔗 Related

- [Link to related pages or issues]

---

*Last updated: [date]*
```

## prd Template

```markdown
# [Title] — Product Requirements Document

**Status:** Draft | Under Review | Approved
**Author:** [name]
**Stakeholders:** [list]
**Related Issues:** [ABC-XXX](https://{{JIRA_SITE}}/browse/ABC-XXX)

---

## Executive Summary

[1 paragraph: what problem this solves, who it's for, expected outcome]

---

## User Stories

### US-1: [Title] (Priority: P1)

[Plain language description of this user journey]

**Acceptance Scenarios:**
1. **Given** [state], **When** [action], **Then** [outcome]
2. **Given** [state], **When** [action], **Then** [outcome]

### US-2: [Title] (Priority: P2)

[Description]

**Acceptance Scenarios:**
1. **Given** [state], **When** [action], **Then** [outcome]

---

## Functional Requirements

- **FR-001:** [Requirement — system MUST...]
- **FR-002:** [Requirement]
- **FR-003:** [Requirement]

## Non-Functional Requirements

- **NFR-001:** [Performance/Security/Accessibility requirement]
- **NFR-002:** [Requirement]

---

## Success Criteria

- **SC-001:** [Measurable outcome tied to FR-001]
- **SC-002:** [Measurable outcome]
- **SC-003:** [Measurable outcome]

---

## Assumptions & Constraints

### Assumptions
- [Assumption about scope, users, or environment]

### Constraints
- [Timeline, budget, technical, or compliance constraint]

---

## Edge Cases

- What happens when [boundary condition]?
- How does the system handle [error scenario]?

---

*Created: [date] · Last updated: [date]*
```
