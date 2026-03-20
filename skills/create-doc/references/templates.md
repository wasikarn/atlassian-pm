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
