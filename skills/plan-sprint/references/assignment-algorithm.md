# Assignment Algorithm

## Assignment Algorithm

1. For each item, determine required skill area (from service tag: [BE]→backend, [FE-Admin]→frontend_admin, etc.)
2. Score each team member: `Match Score = skill_level × (1 + context_bonus)`
   - expert=1.0, intermediate=0.8, basic=0.6
   - context_bonus=0.2 if member has related carry-over items
3. Check hours capacity: `Available Hours ≥ Estimated Hours` for the item (read from `timetracking.originalEstimate` if set, else estimate from ADF panel)
4. Assign to highest score member with available capacity

## Rules

- Related items → same person (reduce context switching)
- Blockers → prioritize (unblock others)
- Critical path → expert-level skill match required
- Never exceed productive hours ceiling
- Track cumulative assigned hours vs available hours (not just item count)
