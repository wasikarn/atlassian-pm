## When to Use vs Skip

| Situation | Use `/feature-blueprint`? | Alternative |
|-----------|--------------------------|-------------|
| New feature, unclear scope, greenfield | **Yes** | — |
| Multi-service feature needing architecture review | **Yes** | — |
| Need cross-role alignment before sprint planning | **Yes** | — |
| Feature already has clear stories, needs refinement | **No** | `/refine-feature` |
| Simple bug fix / UI tweak | **No** | `/create-task` or `/story-full` |
| Requirements already detailed, ready to create | **No** | `/story-full` directly |
| Single-service, obvious approach | **No** | `/story-full` directly |

### `/feature-blueprint` vs `/refine-feature`

| | `/feature-blueprint` | `/refine-feature` |
|---|---|---|
| **When** | Before any Jira artifacts (greenfield) | Refining existing/draft stories |
| **Input** | Feature idea / concept | Jira key / draft stories |
| **Output** | Confluence doc + backlog map | Refined stories → `/story-full` |
| **Roles** | 5 (+ Domain Expert) | 4 (no Domain Expert) |
| **Scope** | Architecture-level (Epic-sized) | Story-level |
| **Downstream** | → `/create-epic` → `/story-full` | → `/story-full` |

**Token budget:** S ~40K, M ~80K, L ~120K. Justified by reduced rework + cross-role alignment before implementation.
