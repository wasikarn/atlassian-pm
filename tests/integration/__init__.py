"""Integration tests for end-to-end Atlassian workflows.

Tests the complete flow: hooks → MCP → acli → Jira/Confluence.

These tests validate:
- Hook execution order and behavior
- MCP tool call correctness
- acli command correctness
- Cache invalidation after writes
"""