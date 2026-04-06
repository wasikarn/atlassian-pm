## 🎓 Domain Expert Notes

### Why This Approach

Health checks should be non-blocking and comprehensive. Unlike setup which must succeed for the plugin to work, doctor runs after installation and after updates to confirm everything is working — it should never block the user, but should show the complete picture of what's working and what isn't.

### System Check Philosophy

1. **Dependencies First**: Check acli, uv, MCP before Jira config — early failures indicate environment issues
2. **Configuration Second**: Project config, team config, board monitor — these are project-specific
3. **Integration Last**: Git filters, CLAUDE.md — these enable advanced features

### Key Metrics

| Check | Healthy Threshold | Warning |
| --- | --- | --- |
| acli install | `acli version` exits 0 | Command not found |
| uv install | `uv --version` exits 0 | Command not found |
| MCP config | `atlassian-cache` MCP server running | Connection refused |
| Project config | `project-config.json` valid JSON | Parse error |
| Board ID | Board ID > 0 | Board ID = 0 or missing |
| Git filters | `git config --get filter...` returns value | Empty or missing |

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| acli not found | Not in PATH | Add to PATH or reinstall |
| MCP connection refused | Server not started | Check `.mcp.json` and restart Claude Code |
| Board ID = 0 | New project, not configured | Run `/atlassian-pm:setup` or set manually |
| Git filters missing | Setup not run | Run `./scripts/setup.sh` |
| CLAUDE.md blocked | Already has CLAUDE.md | Manual merge required |

### Expert Decision Criteria

- **If 1-2 checks fail**: Show warning, continue — plugin can still work
- **If 3+ checks fail**: Show error, suggest `/atlassian-pm:setup` — fundamental issues
- **If all pass**: Show green — ready for use

### Authoritative References

- **acli Documentation**: <https://github.com/atlassian/atlassian-cli> — CLI for Jira/Confluence operations
- **MCP Specification**: Model Context Protocol — tool calling standard for AI agents
- **Git Filters**: Custom clean/smudge filters for sensitive data protection
