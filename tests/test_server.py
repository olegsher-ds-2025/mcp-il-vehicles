import asyncio

import pytest
from fastmcp import Client

from mcp_il_vehicles import server

FAKE = {"total": 1, "records": [{"dummy": "value"}]}


async def _fake_search(resource_id, **kwargs):
    return FAKE


def _call(tool, args):
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(tool, args)

    return asyncio.run(run())


def test_tools_registered():
    async def run():
        async with Client(server.mcp) as client:
            return {t.name for t in await client.list_tools()}

    names = asyncio.run(run())
    assert {'vehicle_by_plate', 'search_models', 'new_car_prices', 'health', 'vehicle_recalls', 'ev_charging_stations', 'model_specs_for_plate', 'find_garages'} <= names


def test_offline_call_has_provenance(monkeypatch):
    monkeypatch.setattr(server, "datastore_search", _fake_search)
    result = _call('vehicle_recalls', {'plate': '1000632'})
    data = result.data if hasattr(result, "data") else result
    assert "source" in data and "data.gov.il" in data["source"]


def test_clean_value():
    from mcp_il_vehicles.ckan import clean_value

    assert clean_value("בע~מ") == 'בע"מ'
    assert clean_value("  ") is None


@pytest.mark.live
def test_live_smoke():
    result = _call('vehicle_by_plate', {'plate': '22216501'})
    data = result.data if hasattr(result, "data") else result
    assert "retrieved_at" in data


def test_haversine_bat_yam_to_tel_aviv():
    from mcp_il_vehicles.geo import haversine_km

    d = haversine_km(32.0209, 34.7518, 32.0853, 34.7818)  # Bat Yam -> Tel Aviv centre
    assert 7 < d < 9


def test_disabled_permit_offline(monkeypatch):
    async def fake(resource_id, **kwargs):
        return {"total": 1, "records": [{"MISPAR RECHEV": 50096, "TAARICH HAFAKAT TAG": 20230419, "SUG TAV": 1}]}

    monkeypatch.setattr(server, "datastore_search", fake)
    data = _call("disabled_parking_permit", {"plate": "50096"})
    data = data.data if hasattr(data, "data") else data
    assert data["has_permit"] and data["permits"][0]["issued"] == "2023-04-19"


def test_ev_by_district_offline(monkeypatch):
    async def fake(resource_id, **kwargs):
        return {"total": 3, "records": [
            {"baalut": "פרטי", "mahoz_nm": "המרכז", "nafa_nm": "רחובות", "car_num": 60},
            {"baalut": "חברה", "mahoz_nm": "המרכז", "nafa_nm": "רחובות", "car_num": 15},
            {"baalut": "פרטי", "mahoz_nm": "הצפון", "nafa_nm": "עכו", "car_num": 25}]}

    monkeypatch.setattr(server, "datastore_search", fake)
    data = _call("ev_by_district", {})
    data = data.data if hasattr(data, "data") else data
    assert data["national_evs"] == 100 and data["by_district"][0] == {"district": "המרכז", "evs": 75, "share_pct": 75.0}


def test_used_car_prompt_registered():
    async def run():
        async with Client(server.mcp) as client:
            return [p.name for p in await client.list_prompts()]

    assert "used_car_checklist" in asyncio.run(run())
