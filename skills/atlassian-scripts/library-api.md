# Library API Reference

> Python library API for developers who need to create custom scripts.
>
> For overview, see [SKILL.md](SKILL.md)

---

## Library API (for developers)

### Using ConfluenceAPI

```python
from lib import (
    ConfluenceAPI,
    create_ssl_context,
    load_credentials,
    get_auth_header,
)

creds = load_credentials()
api = ConfluenceAPI(
    base_url=creds["CONFLUENCE_URL"],
    auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
    ssl_context=create_ssl_context(),
)

# Get page
page = api.get_page("123456")
print(page["title"])

# Create page
result = api.create_page("BEP", "My Page", "<p>Content</p>", parent_id="123")

# Update page
result = api.update_page("123456", "Title", "<p>New content</p>", version=2)

# Move page
result = api.move_page("123456", "789012")
```

### Using Converters

```python
from lib import markdown_to_storage, create_code_macro, fix_code_blocks

# Convert markdown to storage format
storage_html = markdown_to_storage("# Hello\\n**Bold** text")

# Create code macro
macro = create_code_macro("python", "print('hello')")

# Fix broken code blocks in HTML
fixed_html = fix_code_blocks(broken_html)
```

### Using JiraAPI

```python
from lib import (
    JiraAPI,
    create_ssl_context,
    load_credentials,
    get_auth_header,
    derive_jira_url,
    walk_and_replace,
)

creds = load_credentials()
jira_url = derive_jira_url(creds["CONFLUENCE_URL"])  # strips /wiki
api = JiraAPI(
    base_url=jira_url,
    auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
    ssl_context=create_ssl_context(),
)

# High-level: fix description with find/replace
had_changes, count = api.fix_description(
    "BEP-2819",
    [("billboard_ids", "billboard_codes")],
    dry_run=False,
)

# Low-level: get ADF, modify, update
issue = api.get_issue("BEP-2819")
description = issue["fields"]["description"]  # ADF dict
# ... modify ADF ...
api.update_description("BEP-2819", description)
```

### Custom Exceptions

```python
from lib import (
    ConfluenceError, CredentialsError, PageNotFoundError, APIError,
    JiraError, IssueNotFoundError,
)

# Confluence
try:
    page = api.get_page("invalid")
except PageNotFoundError as e:
    print(f"Page not found: {e.page_id}")

# Jira
try:
    issue = jira_api.get_issue("BEP-9999")
except IssueNotFoundError as e:
    print(f"Issue not found: {e.issue_key}")

# Common
except APIError as e:
    print(f"API error {e.status_code}: {e.reason}")
except CredentialsError as e:
    print(f"Credentials error: {e}")
```
