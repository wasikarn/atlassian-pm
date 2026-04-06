## Error Handling Reference

| Phase | Error | Action |
| --- | --- | --- |
| 0 | Not macOS | Hard stop: `ERROR: requires macOS` |
| 0 | Python < 3.11 | Hard stop: show `brew install python@3.11` command |
| 0 | Plugin not found | Hard stop: `Error: plugin not found` |
| 1 | acli install fail | Hard stop: show brew command |
| 1 | uv install fail | Hard stop: show brew command |
| 1 | uv sync fail | Warn + continue: note cache degraded |
| 2 | Invalid project key | Re-ask with format reminder |
| 3 | Write permission denied | Hard stop: check directory permissions |
| 4b | acli auth fail | Hard stop: show retry command |
| 5 | setup.sh fail | Show error output, suggest manual run |
