# mcp-il-vehicles — MEMORY.md

## Status (2026-11-13)
- v0.1.0 built and tested against live data.gov.il; repo https://github.com/olegsher-ds-2025/mcp-il-vehicles
- Not yet deployed to Horizon, not yet listed in registries

## Next tasks
1. Deploy to Prefect Horizon; add hosted URL to README
2. List on MCP Registry, Glama, Smithery, agentskills.co.il
3. Roadmap items in README

## Facts
- data.gov.il CKAN reachable from Claude cloud workspace and cloud hosts (unlike cbs.gov.il)
- Registry text encodes `"` as `~` — cleaned in ckan.clean_value
