# mcp-il-vehicles

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
| `health` | Connectivity check |

## Try asking

- “What car is plate 22-216-501 and when is its licence due?”
- “Does my car have any open recalls?”
- “Find licensed auto-electric garages in Bat Yam.”
- “Compare list prices of the 2026 Toyota Corolla trims.”

## Install

```bash
pip install git+https://github.com/olegsher-ds-2025/mcp-il-vehicles
```

Claude Desktop / Claude Code (`.mcp.json`):

```json
{ "mcpServers": { "il-vehicles": { "command": "mcp-il-vehicles" } } }
```

Run over HTTP (for remote hosting):

```bash
MCP_TRANSPORT=http PORT=8000 mcp-il-vehicles   # → http://localhost:8000/mcp
```

Prefect Horizon entrypoint: `server.py:mcp`.

## Data sources

- Vehicle registry — active, inactive, two-wheelers, public vehicles
- Vehicles with open recalls
- Makes & models (WLTP)
- Importers & new-car price lists
- Licensed garages & test stations
- EV charging stations

All data © the publishing Israeli government authority, via data.gov.il. This project is independent and not
affiliated with the Government of Israel. Registry data can lag; verify critical facts with the authority.

## Development

```bash
pip install -e ".[dev]"
pytest            # offline tests
pytest -m live    # hits data.gov.il
```

## Roadmap

- [ ] Disabled-parking permit & personal import datasets
- [ ] EV share by district (time series)
- [ ] Garage lookup by GPS (geocode addresses)
- [ ] Used-car checklist prompt combining all tools

## Related

Part of a family of Israeli public-data MCP servers by [Oleg Sher](https://linkedin.com/in/sheroleg):
mcp-il-companies · mcp-il-vehicles · mcp-il-health · mcp-cbs-places · mcp-mavat.

## License

MIT
