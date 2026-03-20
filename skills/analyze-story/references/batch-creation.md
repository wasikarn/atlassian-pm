# Batch Sub-task Creation

> When creating ≥3 sub-tasks, use batch pattern to save tokens:
>
> 1. Create all shells with MCP (parallel calls)
> 2. Write all ADF JSON as files in `{{artifacts_dir}}/`
> 3. Run `acli edit --from-json` sequentially (or Python script for batch >5)
