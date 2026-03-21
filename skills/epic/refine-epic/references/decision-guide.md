## When to Use vs Skip

| Situation | Use `/refine-epic`? | Alternative |
|-----------|----------------------|-------------|
| New feature, unclear scope | **Yes** | — |
| Multi-service feature (BE+FE+Admin) | **Yes** | — |
| High-risk or high-visibility | **Yes** | — |
| Simple bug fix / UI tweak | **No** | `/create-task` or `/create-story` directly |
| Requirements already detailed | **No** | `/create-story` directly |
| Single-service, obvious approach | **No** | `/create-story` directly |

**Token budget:** ~60-80K tokens (8 subagent calls + main session). Justify by reduced rework during implementation.
