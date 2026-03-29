## 🎓 Domain Expert Notes

### Why This Approach

Specification by Example (Gojko Adzic) establishes that requirements only become unambiguous when expressed as concrete, testable examples — not prose paragraphs. This skill operationalises that principle: the spec-parser-agent extracts structured requirements and immediately maps them to Given-When-Then scenarios, forcing the spec author's intent to surface as verifiable behaviors rather than interpretable statements.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Specification by Example (Gojko Adzic, 2011) | Phase 2 Extract → Phase 3 Map | Requirements expressed as examples (scenarios) are unambiguous and directly drive test automation; prose requirements require an extra translation step that introduces drift |
| User Story Mapping (Jeff Patton) | Phase 3 grouping by persona + feature area | Patton's backbone → activities → tasks hierarchy maps to: Persona → Feature Area → Story cluster; this grouping prevents persona-crossing stories |
| Feature Injection (Chris Matts) | Phase 2 persona + constraint extraction | "In order to [goal], As a [persona], I want [feature]" — Feature Injection starts from goals, not from system features; ensures extracted stories anchor to real user needs |
| BDD Given-When-Then (Dan North) | Phase 3 AC format per requirement | Minimum 1 happy path + 1 error case per requirement cluster; this satisfies the "Testable" criterion without requiring full test case design at story-creation time |
| Semantic dedup (cosine similarity thresholds) | Phase 4 Dedup Check | Two-tier threshold for English+Thai mixed-language backlogs: similarity **> 0.8** = likely duplicate → auto-flag, require confirmation before creating; similarity **0.7–0.8** = borderline → show candidate to user for manual decision, do not auto-flag or auto-skip. Below 0.7 = distinct enough to proceed without review |

### Key Metrics

- **Extraction yield:** Target 1 story per 3-5 requirements; lower ratio suggests over-granular stories; higher ratio suggests under-specified requirements needing `/blueprint` first
- **Dedup flag rate:** > 30% of stories flagged as duplicates indicates the spec page overlaps significantly with existing backlog — consolidate or update existing stories instead
- **QG batch pass rate:** < 70% of stories passing QG on first attempt indicates the spec lacks sufficient persona and scenario detail for automatic extraction to work well
- **Coverage map completeness:** Every spec section must appear in the coverage map output; unmapped sections indicate requirements that were dropped during extraction and need manual review

### Expert Decision Criteria

- If the spec page contains more than one persona and they have conflicting workflows → create separate story clusters per persona rather than merging them; mixed-persona stories fail INVEST Independent
- If a requirement group yields more than 7 ACs → split into two stories along the happy-path vs. edge-case boundary; one story for the primary flow, one for error/boundary handling
- If dedup similarity is between 0.7-0.8 (borderline) → show the candidate duplicate to the user before proceeding; do not auto-flag or auto-skip
- If `--dry-run` QG scores average below 70% → do not proceed to Phase 7 batch create; return to the spec page and enrich persona/scenario detail or run `/blueprint` to rewrite the spec
- Non-functional requirements (performance, security, accessibility) extracted from the spec → convert to explicit ACs on the relevant functional story, not separate stories, unless they require independent implementation work

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Stories created as orphans (no epic) | `--epic` omitted or epic key typo | Run `jira_set_parent.py --issues KEY1,KEY2 --parent EPIC`; verify with `jira_get_issue(fields="parent")` per story |
| spec-parser-agent produces low-quality requirements | Source page is meeting notes or brainstorm, not a structured spec | Run `/blueprint <confluence-page-id>` first to produce a spec with explicit personas, requirements, and constraints sections |
| Duplicate stories created despite dedup flag | User approved flagged story without reviewing the existing issue | Before approving flagged stories, use `cache_get_issue` to read the candidate duplicate; update the existing story instead if scope overlaps |
| Story narrative reads as a feature description ("The system will support X") | Feature Injection not applied — spec written from system-out rather than user-in | Rewrite narrative using the persona identified in Phase 2: "As a [persona], I want [goal] so that [value]" |
| Coverage map has unmapped spec sections | spec-parser-agent skipped sections with no persona signal | Manually review unmapped sections; add a catch-all story or annotate the spec page to indicate intentionally deferred scope |

### Authoritative References

- **Gojko Adzic, "Specification by Example" (2011):** "Key examples are not test cases — they are a communication tool that becomes the acceptance test"; the spec-parser-agent extracts these key examples from prose requirements
- **Jeff Patton, "User Story Mapping" (2014):** "Don't just break down stories — map the whole journey first"; the persona + feature area grouping in Phase 3 is the lightweight version of Patton's backbone construction
- **Chris Matts (Feature Injection):** Goals before features — if the spec doesn't state a user goal for a requirement, the extracted story will lack the "Valuable" INVEST criterion
- **Dan North (BDD, 2006):** "The scenario title should describe a role and an action"; Phase 3's `AC{N}: [Verb] — [Scenario Name]` format directly implements this naming convention

---
