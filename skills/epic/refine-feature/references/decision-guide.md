## When to Use vs Skip

| Situation | Use `/refine-feature`? | Alternative |
|-----------|----------------------|-------------|
| New feature, unclear scope | **Yes** | — |
| Multi-service feature (BE+FE+Admin) | **Yes** | — |
| High-risk or high-visibility | **Yes** | — |
| Simple bug fix / UI tweak | **No** | `/create-task` or `/story-full` directly |
| Requirements already detailed | **No** | `/story-full` directly |
| Single-service, obvious approach | **No** | `/story-full` directly |

**Token budget:** ~60-80K tokens (8 subagent calls + main session). Justify by reduced rework during implementation.
