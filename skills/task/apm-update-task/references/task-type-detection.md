# update-task: Task Type Detection

## Task Type Detection

**Auto-detect from content:**

| Pattern | Detected Type |
| --- | --- |
| Priority sections (HIGH/MEDIUM/LOW) | `tech-debt` |
| Repro steps, Expected/Actual | `bug` |
| Task checklist, simple objective | `chore` |
| Research question, Investigation | `spike` |
| No clear pattern | `generic` |

**Type impacts which template structure is used**
