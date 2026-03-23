## 🎓 Domain Expert Notes

### Why This Approach

Setup is engineered as an **idempotent provisioning script** — a concept from infrastructure-as-code where running an operation N times produces the same result as running it once. This matters because developer environments are re-provisioned constantly (plugin reinstalls, machine migrations, onboarding). The Phase 0 detection scan + fast-path skip pattern eliminates the most common onboarding fear: "will re-running this break what I already have?"

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| 12-Factor App — Factor III (Config) | Phase 4a: credentials in `~/.config/atlassian/.env`, not code | Config that varies per-deploy belongs in environment, never in source |
| 12-Factor App — Factor X (Dev/Prod Parity) | Phase 1: pinned tool versions (`mcp-atlassian==0.21.0`, Python 3.11+) | Same dependency versions across all developer machines eliminates "works on my machine" |
| Idempotent provisioning (Terraform/Ansible pattern) | Phase 0 detection + per-flag skip guards | Each phase checks current state before acting — re-runs converge, never diverge |
| Least-privilege secret handling (OWASP) | Phase 4a: `chmod 600` on `.env`, `chmod 700` on directory; token passed via `--env-file` not argv | Secrets visible in `ps aux` output if passed as argv; file-based injection keeps them out of process list |
| Backup-restore resilience | Phase 0/3: auto-restore config from `~/.config/atlassian/` on reinstall | Plugin reinstalls wipe the cache dir; a backup that survives outside the plugin directory is standard IaC recovery pattern |

### Key Metrics

- **Time-to-first-green-doctor:** Target ≤5 minutes on a machine with Homebrew installed. If longer, `brew install acli` or `uv sync` is the bottleneck — check network/proxy.
- **Phases skipped on re-run:** All 5 flags true → 0 interactive phases, straight to Phase 5b validation. A good idempotent setup converges to "nothing to do" on the second run.
- **Token rotation frequency:** Atlassian API tokens expire in ≤365 days. Teams without a calendar reminder will hit auth failures silently — setup warns, but enforcement is human.

### Expert Decision Criteria

**Idempotency guards — when each phase runs:**

- Phase 1 (deps): always checks, installs only if missing — `command -v` before `brew install`
- Phase 2 (config): skipped entirely when `SKIP_CONFIG=true` — existing non-placeholder config is authoritative
- Phase 3 (write): overwrite guard prompts before replacing existing valid config — default is `N` (preserve)
- Phase 4a (env): skipped when `.env` already has non-empty `JIRA_API_TOKEN` — no re-prompting for credentials
- Phase 4b (acli auth): skipped when `acli jira auth status` exits 0 — exit code is more stable than string parsing
- Phase 4c (MCP): skipped when `claude mcp get mcp-atlassian` exits 0 — prevents duplicate registrations

**Configuration drift signals to watch for:**

- `ENV_OK=true` but `ACLI_OK=false` → token in `.env` is stale or expired; re-run phases 4a+4b
- `MCP_OK=true` but tools return "not found" → MCP registered in a previous session, not yet activated — restart Claude Code
- `VENV_OK=false` after plugin reinstall → expected; Phase 1 always re-syncs; data dir naming changed (`atlassian-pm-atlassian-pm`)

**Security decisions:**

- Token collected via chat, written with Write tool (not heredoc/echo) — avoids token appearing in bash history
- Credentials dir `chmod 700`, files `chmod 600` — OWASP Secrets Management minimum for local dev
- Token passed to `mcp-atlassian` via `--env-file` (file path in argv), never the token value itself — keeps secret out of `ps aux` process list

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| "Tool not found" immediately after setup | MCP registered but Claude Code not restarted | Restart Claude Code — MCP servers activate only on session start |
| Phase 4b fails with valid credentials | `acli` reading stale token from OS keychain, not `.env` | Run `acli jira auth logout` then retry Phase 4b manually |
| `uv sync` fails with "no project found" | `PLUGIN_ROOT` resolved to wrong path (multiple plugin versions in cache) | Check `ls ~/.claude/plugins/cache/atlassian-pm/atlassian-pm/` — delete stale versions |
| Config restored from backup but has wrong project key | Backup from a previous project setup was restored | Delete `~/.config/atlassian/atlassian-pm-config.json`, re-run setup with correct values |
| board_id stays 0 after setup | User skipped Phase 5b board lookup | Run `/doctor` — it offers board lookup when `board_id=0` is detected |
| mcp-atlassian registered with wrong project filter | `PROJECT_KEY` collected incorrectly in Phase 2 | Remove with `claude mcp remove mcp-atlassian`, fix config, re-run Phase 4c |

### Authoritative References

- **12factor.net — Factor III (Config):** "Store config in the environment. Config varies across deploys, code does not." The `.env` file pattern is the standard local-dev approximation of environment-injected config.
- **OWASP Secrets Management Cheat Sheet:** Secrets must never appear in process argument lists, logs, or version control. File-based injection (`--env-file`) and `chmod 600` are the minimum viable controls for local development secrets.
- **NIST SP 800-57 Part 1 Rev 5 — Key Management Guidelines (NIST, 2020):** Secret rotation creates team-wide drift risk — when one developer rotates an API token, all others' local `.env` files become stale instantly. Setup's backup-restore pattern mitigates this for single-developer reinstalls only; centralized secrets management (vault, secrets manager) is the durable solution for team environments.
