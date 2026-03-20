# When to Use Scripts vs MCP — scripts/api/

> **CRITICAL:** MCP Confluence tools have TWO limitations that cause macros to fail:
>
> 1. **Storage format** → MCP HTML-escapes `<ac:` tags, macros render as raw text
> 2. **Code blocks** → MCP renders as `<pre>` instead of Confluence macro
>
> **Rule:** If your page contains ANY macros (Jira, expand, info panel, ToC, children) → **ALWAYS use Python scripts**

| Scenario | Tool | Why |
| --- | --- | --- |
| Simple page read | MCP `confluence_get_page` | Fast, no script needed |
| Page create/update (no code, no macros) | MCP `confluence_create_page` / `update_page` | Markdown works fine |
| Page create/update (with code) | MCP + `fix_confluence_code_blocks.py` | MCP renders code as `<pre>`, fix script converts |
| **Page with Jira macros / panels** | **Script** `update_page_storage.py` | MCP escapes XML → macros render as text |
| **Page with expand / ToC / children** | **Script** `update_page_storage.py` | MCP escapes XML → macros render as text |
| Batch text replacement | **Script** `update_confluence_page.py` | More reliable |
| Fix broken code blocks | **Script** `fix_confluence_code_blocks.py` | Post-step after MCP create/update |
| Issue linking (Blocks/Relates) | MCP `jira_create_issue_link` | Bidirectional links between issues |
| Web links (Figma/Confluence) | MCP `jira_create_remote_issue_link` | Add external links to issue Links section |
| Set parent (Epic) on existing issues | **Script** `jira_set_parent.py` | MCP/acli silently ignore parent field |
| Move issues to backlog / sprint mgmt | **Script** via `JiraAPI._request()` | MCP not supported — use Agile REST API + **numeric IDs** |

> **Known Issue (Code Blocks):** MCP `confluence_create_page` / `confluence_update_page` with `content_format: 'markdown'`
> renders code blocks as `<pre class="highlight">` instead of Confluence `<ac:structured-macro>`.
> **You must always run `fix_confluence_code_blocks.py --page-id` after any MCP create/update that contains code blocks.**
>
> **Known Issue (Storage Format/Macros):** MCP with `content_format: 'storage'` HTML-escapes the content.
> `<ac:structured-macro>` becomes `&lt;ac:structured-macro&gt;` and renders as plain text instead of a macro.
> **For ANY page with macros (Jira tables, panels, expand, ToC), use `update_page_storage.py` directly.**
