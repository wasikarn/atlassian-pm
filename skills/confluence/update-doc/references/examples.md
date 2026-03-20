## Common Scenarios

| Scenario | Command | Tool |
| --- | --- | --- |
| Update status | `/update-doc 123456789 --status Published` | MCP |
| Replace text | `/update-doc 123456789 --find "v1" --replace "v2"` | Script |
| Update section | `/update-doc 123456789 --section "API Spec"` | MCP or Script |
| Full rewrite | `/update-doc 123456789` | Script |
| Move page | `/update-doc 123456789 --move 987654321` | Script |
| Batch move | `/update-doc --move 987654321 --pages 123456789,333444555` | Script |
