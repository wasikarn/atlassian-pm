## When to Use vs Skip

| Situation | Use `/blueprint`? | Alternative |
|-----------|--------------------------|-------------|
| New feature, unclear scope, greenfield | **Yes** | — |
| Multi-service feature needing architecture review | **Yes** | — |
| Need cross-role alignment before sprint planning | **Yes** | — |
| Feature already has clear stories, needs refinement | **No** | `/refine-epic` |
| Simple bug fix / UI tweak | **No** | `/create-task` or `/create-story` |
| Requirements already detailed, ready to create | **No** | `/create-story` directly |
| Single-service, obvious approach | **No** | `/create-story` directly |

### `/blueprint` vs `/refine-epic`

| | `/blueprint` | `/refine-epic` |
|---|---|---|
| **When** | Before any Jira artifacts (greenfield) | Refining existing/draft stories |
| **Input** | Feature idea / concept | Jira key / draft stories |
| **Output** | Confluence doc + backlog map | Refined stories → `/create-story` |
| **Roles** | 5 (+ Domain Expert) | 4 (no Domain Expert) |
| **Scope** | Architecture-level (Epic-sized) | Story-level |
| **Downstream** | → `/create-epic` → `/create-story` | → `/create-story` |

**Token budget:** S ~40K, M ~80K, L ~120K. Justified by reduced rework + cross-role alignment before implementation.
