## 🎓 Domain Expert Notes

### Why This Approach

Vibe planning trades depth for speed. The 2-interaction maximum (decomposition review + optional annotation) forces rapid convergence, making it ideal when the feature is well-understood and the path to implementation is clear. This contrasts with `/blueprint`, which uses multi-role debate to surface hidden complexity — necessary for features with ambiguous requirements or cross-team dependencies.

The key insight: most features don't need debate. A tech lead can decompose a clear feature in minutes using pattern recognition from similar past work. Vibe planning captures this expertise while `/blueprint` captures the uncertainty resolution process.

### When to Use Vibe vs. Blueprint

| Condition | Use `/vibe-plan` | Use `/blueprint` |
| --- | --- | --- |
| Feature clarity | Clear mental model, minimal ambiguity | Vague idea, multiple interpretations possible |
| Team alignment | Already aligned on approach | Needs stakeholder debate |
| Cross-team impact | Single service or well-defined boundary | 3+ services with unclear ownership |
| Time investment | 5-10 minutes total | 30-60 minutes debate + synthesis |
| Risk profile | Low risk (implementation details only) | High risk (architectural decisions, new domains) |
| Existing patterns | Similar features exist in codebase | No prior art, requires exploration |

**Rule of thumb:** If you can describe the feature in one sentence and a developer would say "I know how to build this," use vibe. If the sentence requires "but we need to decide..." or "depends on whether...", use blueprint.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Vertical Slice Planning | Phase 2 decomposition | Each task is a complete user-facing value increment, not a horizontal layer (backend-only, frontend-only tasks violate this) |
| INVEST Criteria | Phase 2 task sizing | Tasks sized S/M/L with explicit acceptance criteria; vibe mode skips story points but maintains atomicity |
| Pattern Language (Alexander) | Implementation Hints | Reusing proven patterns reduces cognitive load; "follow X pattern" is more valuable than "implement from scratch" |
| Two-Pizza Team (Amazon) | Task assignment | Each task should be completable by 1-2 people within a sprint; larger tasks indicate missing decomposition |
| Definition of Ready | Phase 3 review | The decomposition review gate catches unready tasks before Jira write — not after |

### Key Metrics

- **Time to delegation-ready:** From feature description to delegatable tasks — target <10 minutes for vibe mode
- **Decomposition accuracy:** Tasks created vs. tasks actually needed during implementation — >80% match indicates good decomposition
- **First-attempt success rate:** Tasks implemented without requiring clarification from assignee — >70% indicates clear Implementation Hints
- **Implementation Hint reuse:** Count of "follow X pattern" hints that match actual codebase patterns — low reuse signals missing REF files or exploration gaps
- **Dry-run conversion:** Dry-run plans that proceed to creation — >90% indicates user understands the plan before committing

### Expert Decision Criteria

- **If description <10 words:** Request clarification — too vague for reliable decomposition; suggest `/blueprint` for scope debate
- **If 8+ tasks generated:** The feature is too large — either split into multiple epics or use `/blueprint` for proper scoping
- **If no REF file matches:** Either explore codebase first (Phase 1 missed something) or the feature genuinely has no prior art — use `/blueprint` if novel
- **If all tasks are [BE] or all are [FE]:** Likely a horizontal slice — reject and re-decompose as vertical slices
- **If task estimate >8h:** Task is too large — split into smaller atomic units; implementation hints should guide the split
- **If --dry-run output shows unclear patterns:** User should run `/blueprint` instead — the uncertainty is too high for vibe mode

### Implementation Hint Best Practices

| Hint Type | Good Example | Bad Example |
| --- | --- | --- |
| Entry Point | "Start in `RedeemCouponService.ts` at `processRedemption()` method" | "Start in the service layer" |
| Pattern to Follow | "Follow ApplyCouponService pattern: validate → calculate → apply → audit" | "Follow standard service pattern" |
| Test Command | "Run `npm test -- --grep 'RedeemCoupon'` to verify implementation" | "Run tests" |
| Dependencies | "Requires coupon-schema migration (run first)" | "Depends on other work" |
| File Paths | "CREATE: `app/Services/RedeemCouponService.ts`, MODIFY: `app/Controllers/CouponController.ts`" | "New service, update controller" |

**Anti-pattern:** "Implement from scratch" in Implementation Hints signals missing research — Phase 1 should have found a pattern to follow.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| User rejects decomposition in Phase 3 | Feature description was too vague or ambiguous | Request clarification before re-decomposing; suggest `/blueprint` if ambiguity persists |
| Tasks generated with no file paths | Phase 1 exploration insufficient or no prior art exists | Re-run exploration with broader keywords; consider `/blueprint` for novel features |
| All tasks have L estimates | Feature scope is too large for vibe mode | Split into multiple epics or use `/blueprint` for proper sizing |
| Implementation Hints say "from scratch" | No matching patterns found in codebase | Use `/blueprint` — the feature requires architectural decisions |
| Task requires clarification mid-sprint | Implementation Hints were too generic | Add specific entry points, pattern names, and test commands in future plans |
| User runs vibe-plan on epic with existing tasks | Creates duplicates — didn't use --epic flag | Check for existing epic before planning; use `--epic {{PROJECT_KEY}}-XXX` to extend existing epic |

### Authoritative References

- **Jeff Patton, *User Story Mapping*:** Vertical slices deliver user value, not technical layers — tasks should reflect user-facing outcomes
- **Martin Fowler, *Patterns of Enterprise Application Architecture*:** Named patterns reduce communication overhead — "follow Repository pattern" is clearer than describing data access from scratch
- **Mike Cohn, *User Stories Applied*:** INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable) — vibe tasks should pass INVEST despite minimal ceremony
- **Kent Beck, *Extreme Programming Explained*:** "Do the simplest thing that could possibly work" — vibe mode is XP's YAGNI applied to planning; skip ceremony when clarity exists
