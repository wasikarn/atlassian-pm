# Model Selection Guide

This guide helps choose the right Claude model for agents and skills.

## Model Tiers

| Model | Best For | Cost | Speed |
|-------|----------|------|-------|
| haiku | L1: Fast, simple tasks | Low | Fast |
| sonnet | L2/L3: Complex reasoning | Medium | Medium |

## Task Type → Model Mapping

| Task Type | Model | Reason |
|-----------|-------|--------|
| Search/lookup | haiku | Fast, simple pattern matching |
| QG validation | haiku | Structured output, deterministic |
| SP calibration | haiku | Historical comparison, math |
| Duplicate detection | haiku | Similarity scoring |
| Issue bootstrap | haiku | Context fetching, formatting |
| Epic creation | sonnet | Complex reasoning, RICE scoring |
| Blueprint debate | sonnet | Multi-role creative thinking |
| Subtask design | sonnet | File path discovery, AC mapping |
| Story writing | sonnet | ADF composition, service-aware |
| Risk forecasting | sonnet | Multi-factor analysis |

## Rules

1. **Default to haiku** for L1 tasks (search, validate, format)
2. **Use sonnet** for L2/L3 tasks requiring reasoning
3. **Document exceptions** in agent frontmatter if model differs from guidelines

## Agent Architecture

- **Layer 1 (Foundation)**: haiku - code-explorer, issue-bootstrap, jira-search, quality-gate
- **Layer 2 (Analysis)**: sonnet - story-writer, alignment-checker, backlog-groomer
- **Layer 3 (Synthesis)**: sonnet - estimation-calibrator, risk-forecaster, team-pattern-advisor

## Enforcement

Skills should specify `model: sonnet` or `model: haiku` in their frontmatter.
The skill loader validates model matches documented tier.
