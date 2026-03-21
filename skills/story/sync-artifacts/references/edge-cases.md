# Edge Cases

## Edge Cases

| Case | Handling |
| --- | --- |
| Confluence page does not exist | Flag + recommend `/create-doc` (no auto-create) |
| No sub-tasks exist | Sync only Story <-> Epic/Confluence |
| Multiple Confluence pages match | List all and let user choose |
| Artifact graph > 20 items | Recommend breaking into multiple runs |
| Partial failure | Continue remaining + report failures |
| Issue DONE/CLOSED | Warning but allow sync (doc alignment) |
| No changes detected | Report "already aligned" + skip |
| QA sub-task affected | FLAG for QA review (no auto-rewrite of test plan) |
| Epic Doc affected | Update story status table + summary only |
