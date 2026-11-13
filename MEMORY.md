# mcp-il-vehicles — MEMORY.md

## Status (2026-11-13)
- v0.1.0 built and tested against live data.gov.il; repo https://github.com/olegsher-ds-2025/mcp-il-vehicles
- PyPI + MCP Registry publishing via GitHub Actions on tag v*; Horizon free tier is private-only (public needs paid plan) → self-host on laptop 10.0.0.100 via Cloudflare Tunnel (mcp-il-deploy)

## Next tasks
1. Deploy to Prefect Horizon; add hosted URL to README
2. List on MCP Registry, Glama, Smithery, agentskills.co.il
3. Roadmap items in README

## Facts
- data.gov.il CKAN reachable from Claude cloud workspace and cloud hosts (unlike cbs.gov.il)
- Registry text encodes `"` as `~` — cleaned in ckan.clean_value
