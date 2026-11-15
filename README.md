# mcp-il-vehicles

<!-- mcp-name: io.github.olegsher-ds-2025/mcp-il-vehicles -->

Israeli vehicle registry for AI agents: plate lookup, open recalls, model specs, new-car prices, licensed garages, EV chargers — live from data.gov.il.

**מאגרי רכב: מספר רישוי, ריקולים, מפרט דגם, מחירון, מוסכים מורשים, עמדות טעינה**

An [MCP](https://modelcontextprotocol.io) server that lets Claude and other AI assistants query official Israeli
government open data in plain language. No API key, no scraping — every call goes to the public
[data.gov.il](https://data.gov.il) CKAN API and returns the source with each answer.

## Tools

| Tool | What it does |
|---|---|
| `vehicle_by_plate` | Make, model, year, fuel, colour, ownership, last test, licence expiry, VIN, tyres |
| `vehicle_recalls` | Open manufacturer recalls not yet performed |
| `model_specs_for_plate` | Horsepower, engine, drive, airbags, ADAS, CO2, green index for the registered model |
| `search_models` | Search makes/models and specs |
| `new_car_prices` | Importer list prices (₪) |
| `find_garages` | Licensed garages / test stations by city and specialty |
| `ev_charging_stations` | EV charging sites by place or operator |
| `find_garages_near` | Licensed garages nearest to an address or GPS point, with distance (OpenStreetMap geocoding) |
| `disabled_parking_permit` | Does the plate hold a disabled-parking permit (תג נכה) |
| `personal_import_check` | Personal import (יבוא אישי) — new or used |
| `ev_adoption_by_year` | EV and hybrid share by year first on road — adoption time series |
| `ev_by_district` | Current EV count and national share by district / sub-district |
| `used_car_report` | One-call pre-purchase check with red flags |
| `health` | Connectivity check |

## Prompts

| Prompt | What it does |
|---|---|
| `used_car_checklist(plate)` | Guided used-car review combining all tools, ending with what open data cannot confirm (liens, mileage, accidents) |

## Try asking

- “What car is plate 22-216-501 and when is its licence due?”
- “Does my car have any open recalls?”
- “Find licensed auto-electric garages in Bat Yam.”
- “Compare list prices of the 2026 Toyota Corolla trims.”
- “I'm about to buy car 22-216-501 — run the used-car checklist.”
- “Find hybrid-specialist garages within 5 km of Herzl 20, Rishon LeZion.”
- “How has the EV share of new cars changed since 2019, and which district has the most EVs?”

## Install

No install needed with [uv](https://docs.astral.sh/uv/):

```bash
uvx mcp-il-vehicles
```

Claude Desktop / Claude Code (`.mcp.json`):

```json
{ "mcpServers": { "il-vehicles": { "command": "uvx", "args": ["mcp-il-vehicles"] } } }
```

Or `pip install mcp-il-vehicles`, or from source: `pip install git+https://github.com/olegsher-ds-2025/mcp-il-vehicles`.

Also listed in the official MCP Registry as `io.github.olegsher-ds-2025/mcp-il-vehicles`.

Run over HTTP (for remote hosting):

```bash
MCP_TRANSPORT=http PORT=8000 mcp-il-vehicles   # → http://localhost:8000/mcp
```

Docker: `docker build -t mcp-il-vehicles . && docker run -p 8000:8000 mcp-il-vehicles`.

Prefect Horizon entrypoint: `server.py:mcp`.

## Data sources

- Vehicle registry — active, inactive, two-wheelers, public vehicles
- Vehicles with open recalls
- Makes & models (WLTP)
- Importers & new-car price lists
- Licensed garages & test stations
- EV charging stations
- Vehicles with disabled-parking permit · Personally imported vehicles · Electric vehicles by sub-district
- Geocoding: [OpenStreetMap Nominatim](https://nominatim.org) (© OpenStreetMap contributors, ODbL) — max 1 request/s, results cached

All data © the publishing Israeli government authority, via data.gov.il. This project is independent and not
affiliated with the Government of Israel. Registry data can lag; verify critical facts with the authority.

## Development

```bash
pip install -e ".[dev]"
pytest            # offline tests
pytest -m live    # hits data.gov.il
```

## Roadmap

- [x] Disabled-parking permit & personal import datasets (v0.2.0)
- [x] EV adoption time series + EV by district (v0.2.0)
- [x] Garage lookup by GPS / address (v0.2.0)
- [x] Used-car checklist prompt combining all tools (v0.2.0)
- [ ] Self-hosted geocoder (Nominatim/Photon on the laptop) to lift the 1 req/s limit
- [ ] Vehicle ownership-history count (if the ministry opens it)

## Related

Part of a family of Israeli public-data MCP servers by [Oleg Sher](https://linkedin.com/in/sheroleg):
mcp-il-companies · mcp-il-vehicles · mcp-il-health · mcp-il-professionals · mcp-cbs-places · mcp-mavat.

## License

MIT
