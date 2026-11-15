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

## 2026-11-15 — v0.2.0
- Added: disabled_parking_permit, personal_import_check, ev_adoption_by_year, ev_by_district, find_garages_near, used_car_report, prompt used_car_checklist (14 tools)
- Personal-import cars live in a separate registry — _find_plate falls back to it
- data.gov.il has no datastore_search_sql (404); time series built with list filters on moed_aliya_lakvish ('YYYY-M', not zero-padded)
- EV-by-district table is a current snapshot only
- Nominatim misses some industrial-zone streets → city-centre fallback flagged as location_precision=city_centre
- Next: publish v0.2.0 via GitHub release tag v0.2.0
