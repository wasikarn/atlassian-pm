## Error Handling

| Error | Cause | Solution |
| --- | --- | --- |
| Page not found | Wrong page ID | Search for the page again |
| Version conflict | Someone else updated | Fetch latest version and retry |
| Permission denied | No edit access | Contact admin |
| Code blocks broken | MCP markdown renders `<pre class="highlight">` | Run `fix_confluence_code_blocks.py --page-id` |
