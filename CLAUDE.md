# mcp-il-vehicles — CLAUDE.md

Israeli vehicle registry for AI agents: plate lookup, open recalls, model specs, new-car prices, licensed garages, EV chargers — live from data.gov.il.

## Stack
Python 3.11 · FastMCP · httpx · pytest. No database: every tool queries data.gov.il CKAN `datastore_search` live.

## Layout
- server.py — Prefect Horizon entrypoint (`server.py:mcp`); check with `fastmcp inspect server.py:mcp`
- src/mcp_il_vehicles/server.py — tools + resource IDs (constants `R_*` at top)
- src/mcp_il_vehicles/ckan.py — shared CKAN client (retries, User-Agent, `~`→`"` cleanup, `meta()` provenance). Keep identical across mcp-il-* repos.
- tests/ — offline tests (monkeypatched `datastore_search`); `pytest -m live` for real calls

## Rules
- Every tool response includes `source`, `retrieved_at`, `attribution` via `meta()`.
- Resource IDs can change when a ministry republishes — if a tool returns 404/empty, re-resolve with
  `package_search` and update the `R_*` constant.
- Exact matches via `filters` (numbers must be int unless the dataset stores strings); free text via `q`.
- Never store or log personal queries. Data is public registry data only.
- Update MEMORY.md at the end of every session.

## Model routing
Architect/Advisor: Fable (else Opus) · Orchestrator: Opus · Executor: Sonnet · Explorer/tests: Haiku · tiny text jobs: Jetson llama.cpp · graphics: Gemini/ChatGPT.

## Deployment
Prefect Horizon free tier (public HTTP), entrypoint `server.py:mcp`. data.gov.il is reachable from cloud hosts.
