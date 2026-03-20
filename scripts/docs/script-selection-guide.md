# Script Selection Guide — scripts/api/

```text
What do you need to do?
    │
    ├─ Create a new page
    │     └─ create_confluence_page.py --space --title
    │
    ├─ Update entire content
    │     └─ create_confluence_page.py --page-id --content-file
    │
    ├─ Find/Replace text
    │     └─ update_confluence_page.py --find --replace
    │
    ├─ Move page(s) to new parent
    │     └─ move_confluence_page.py --page-id(s) --parent-id
    │
    ├─ Add macros (ToC, Children, Status)
    │     └─ update_page_storage.py --page-id --content-file
    │
    ├─ Fix broken code blocks
    │     └─ fix_confluence_code_blocks.py --page-id(s)
    │
    ├─ Verify content alignment
    │     └─ audit_confluence_pages.py --config audit.json
    │
    ├─ Fix Jira issue descriptions (ADF)
    │     └─ update_jira_description.py --config fixes.json
    │
    ├─ Validate ADF before Jira write (HR1)
    │     └─ validate_adf.py {{artifacts_dir}}/story.json --type story [--fix]
    │
    ├─ Verify writes took effect (HR3/HR5/HR6)
    │     └─ verify_write.py ABC-1234 --check parent,assignee
    │
    ├─ Create subtask (full pipeline)
    │     └─ jira_write.py create-subtask --parent ABC-1200 --adf {{artifacts_dir}}/sub.json
    │
    ├─ Set parent (Epic) on existing issues
    │     └─ jira_set_parent.py --issues ABC-3331,ABC-3332 --parent ABC-3197
    │
    └─ Track workflow state
          └─ workflow_checkpoint.py start story-full ABC-1200
```
