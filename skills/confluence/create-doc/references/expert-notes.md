## 🎓 Domain Expert Notes

### Why This Approach

The 3-template system (tech-spec / adr / parent) directly maps to the Diátaxis/Divio documentation framework's principle that each document type serves a distinct cognitive mode — reference (tech-spec), decision record (adr), and navigation (parent). Mixing types in a single page is the most common cause of documentation that exists but cannot be found or trusted.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Diátaxis (Divio) | Template selection in Phase 1 | Forces single-purpose pages; one type = one cognitive job |
| ADR (MADR format) | `adr` template structure | Context → Decision → Consequences captures *why*, not just *what*; prevents decisions being relitigated |
| Docs as Code | Jira link step in Phase 4 output | Traceability from requirement (Jira) to design doc (Confluence) mirrors code→PR→ticket linkage |
| Information Architecture 5–9 rule | `parent` template use | Research shows 5–9 top-level categories is the optimal range for human navigation; creating parent pages is the primary mechanism to stay within that range as a space grows |

### Key Metrics

- **Page findability:** Target ≤ 3 clicks from space root to any page — exceeding this indicates missing parent pages or flat structure
- **ADR completeness:** Every ADR must contain at least one rejected alternative with documented rationale; ADRs without rejected options are opinions, not decisions
- **Jira linkage rate:** 100% of `tech-spec` pages should link back to a Jira epic or story via `jira_create_remote_issue_link` — unlinked specs become orphaned and unmaintained
- **Flesch-Kincaid target:** Technical docs aimed at a developer audience should score Grade 10–12; above Grade 14 signals sentences are too long and should be split

### Expert Decision Criteria

- If the user's request contains "why did we" or "we need to decide" → `adr`, not `tech-spec`
- If the user's request is about how a system *will* work → `tech-spec`
- If the request is to create a space section for a team or service area → `parent` first, then nest `tech-spec`/`adr` beneath it
- If the title contains a version number (e.g. "API v2") → this is a `tech-spec`; version-named ADRs are an anti-pattern because decisions should be immutable once recorded
- ADRs must never be deleted or substantially edited after acceptance — append a superseding ADR instead and link them bidirectionally

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Tech spec becomes a meeting notes dump | No enforced template sections; sections like "Overview" feel optional | Make all sections mandatory in Phase 2; leave section headers with `TBD` if unknown rather than omitting them |
| ADR relitigated 6 months later | Missing "rejected options" section; team doesn't know what was considered | Enforce at least one alternative with "Why not chosen" before approving |
| Confluence space becomes a flat list of 200 pages | Parent pages created too late or not at all | Create parent pages proactively at space setup; use the 5–9 top-level rule as a forcing function |
| Code blocks render as `<pre class="highlight">` | MCP `confluence_create_page` emits raw HTML, not Confluence storage format macros | Always run `fix_confluence_code_blocks.py` post-create (already in Phase 4) — never skip |
| Spec linked to wrong Jira issue | Linked via text copy-paste instead of `jira_create_remote_issue_link` | Use remote link API; it creates a bi-directional "Confluence pages" panel in Jira automatically |

### Authoritative References

- **Diátaxis (Procida, 2017–2025):** "The problem with most documentation is not that it is badly written, but that it tries to do too many things at once." — each page must serve exactly one of the four modes
- **joelparkerhenderson/architecture-decision-record (GitHub):** The most widely adopted ADR template collection; MADR format is recommended for Confluence because its tabular "Considered Options" section renders cleanly
- **Atlassian Confluence Best Practices Guide:** Start with broad categories (5–9 max), become more specific as you go deeper — the taxonomy should reflect how readers search, not how the org chart is drawn
- **Keep a Changelog (keepachangelog.com):** "Changelogs are for humans, not machines" — the same principle applies to ADRs; write for the engineer in 18 months, not the one who wrote it today

---
