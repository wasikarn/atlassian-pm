# Architect Debate Protocol

> **Scope:** ambiguity-prevention protocol for any agent that performs architect-style analysis on ambiguous inputs (Epic titles, user requests, specs, refactor goals). Added in v3.12.0 after {{PROJECT_KEY}}-182 scope-ambiguity root cause analysis.

## When to apply

Invoke this protocol when input contains:

- Ambiguous cue words (see list below)
- Multiple plausible interpretations that lead to different scope
- Terms that have domain-specific meaning in the codebase AND colloquial meaning
- Refactor/"fix" requests without explicit target

## Ambiguous cue words

```text
request · process · handle · manage · review · check · trigger · send · notify · update
```

## The protocol — Competing Interpretations first

When analyzing any ambiguous input, agents MUST produce a **Competing Interpretations** section BEFORE recommending one path forward. Never collapse to a single interpretation silently — that is how {{PROJECT_KEY}}-182 happened (the title "Review flow — notification trigger" was read as AI-review when QA-review was the intended scope).

### Required output structure

```markdown
## Competing Interpretations

### Interpretation A: [short name]

- **Reading:** [what it means in plain words]
- **Evidence for:** [code references, context clues, related tickets]
- **Evidence against:** [counter-evidence]
- **Scope implication:** [what changes / what tasks fall under this reading]

### Interpretation B: [short name]

- **Reading:** [plain-words meaning]
- **Evidence for:** [references]
- **Evidence against:** [counter-evidence]
- **Scope implication:** [scope]

### Interpretation C: [if applicable]

[same structure]

## Recommendation: [A | B | C | ask user]

- **Rationale:** [why this interpretation wins]
- **Risk if wrong:** [impact if we picked the wrong one — scope gap, rework, QA miss]
- **Confirmation needed:** [yes/no — if yes, ask stakeholder before proceeding]
```

## Decision gate

| Confidence | Action |
| --- | --- |
| ≥ 95% one interpretation | Recommend + confirm in-line, proceed |
| 70–94% | Recommend but **PAUSE** and ask user to confirm before drafting |
| < 70% | Do NOT recommend — surface all interpretations, ask user to pick |

## Anti-patterns

| Anti-pattern | Why it fails |
| --- | --- |
| Pick first plausible reading, draft scope | Propagates wrong interpretation through Epic → slices → Mermaid → code review |
| List alternatives in one bullet line each | Not enough detail to compare; user can't see the tradeoff |
| Skip "Risk if wrong" | User can't calibrate how much to verify |
| Ask user without listing the candidates | Wastes a round; user has to do the enumeration work |

## Example — {{PROJECT_KEY}}-182 case

**Input:** `"Review flow — notification trigger for billboard owners"`

### Competing Interpretations

**A. AI-review trigger**

- **Reading:** notification fires when AI starts reviewing a new billboard submission
- **Evidence for:** project has `AiReviewJob`, Slack channel `#ai-review` is mentioned in adjacent epics
- **Evidence against:** current flow already has AI-review notifications via `AiFooNotifiable`
- **Scope implication:** add QA-review hooks only, minimal BE change

**B. QA-review trigger**

- **Reading:** notification fires when QA staff picks up a billboard for manual review
- **Evidence for:** QA dashboard feedback mentions missing notification, `QaReviewService` has no hooks
- **Evidence against:** terminology overlap with AI-review
- **Scope implication:** hook into `QaReviewService.assign()`, update `FooNotifiable` enum, i18n keys

**C. Combined AI + QA**

- **Reading:** single trigger covers both review paths
- **Evidence for:** user said "review flow" (singular)
- **Evidence against:** two very different code paths, hard to test as one slice
- **Scope implication:** 2x effort, 2x risk, needs pair of slices anyway

### Recommendation: ask user

- **Rationale:** evidence for A and B is roughly balanced; silent pick would cost a restructure
- **Risk if wrong:** full Epic restructure (11 tasks → 6 slices as happened in {{PROJECT_KEY}}-182)
- **Confirmation needed:** yes — ask user to confirm A / B / C before drafting

## Integration points

- **Epic template** — output of this protocol feeds `Scope Disambiguation` section in `templates-epic.md`
- **apm-create-epic pre-draft gate** — if title has cue words, architect agent runs protocol, returns interpretation + confirmation requirement
- **apm-update-epic** — if scope change is ambiguous (e.g. "simplify review flow"), run protocol before generating ADF

## Related

- [`templates-epic.md` — Scope Disambiguation section](templates-epic.md#scope-disambiguation-template-markdown-preview-of-adf-output)
- [`templates-epic.md` — Code Paths Covered](templates-epic.md#code-paths-covered-required-subsection)
- CHANGELOG v3.11.1 — {{PROJECT_KEY}}-182/183 restructure case study
- CHANGELOG v3.12.0 — this protocol introduced as P5 of the 7 ambiguity-prevention fixes
