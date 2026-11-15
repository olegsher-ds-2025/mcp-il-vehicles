"""Tiny geocoding helper on OpenStreetMap Nominatim (free; usage policy: <=1 request/second, identify the app,
cache results). See https://operations.osmfoundation.org/policies/nominatim/"""
from __future__ import annotations

import asyncio
import math
import os
import time
from functools import lru_cache

import httpx

NOMINATIM = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
USER_AGENT = os.environ.get("GEOCODER_USER_AGENT", "mcp-il-vehicles/0.2 (+https://github.com/olegsher-ds-2025/mcp-il-vehicles)")
_lock = asyncio.Lock()
_last = 0.0
_cache: dict[tuple, dict | None] = {}


async def _get(path: str, params: dict) -> object:
    global _last
    key = (path, tuple(sorted(params.items())))
    if key in _cache:
        return _cache[key]
    async with _lock:  # serialize + rate limit to 1 req/s
        wait = 1.05 - (time.monotonic() - _last)
        if wait > 0:
            await asyncio.sleep(wait)
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT, "Accept-Language": "he,en"}) as c:
            r = await c.get(f"{NOMINATIM}/{path}", params={**params, "format": "jsonv2"})
        _last = time.monotonic()
    r.raise_for_status()
    data = r.json()
    if len(_cache) > 5000:
        _cache.clear()
    _cache[key] = data
    return data


async def geocode(address: str) -> dict | None:
    """Address (Hebrew or English) in Israel -> {'lat','lon','display_name'} or None."""
    res = await _get("search", {"q": address, "countrycodes": "il", "limit": 1})
    if not res:
        return None
    top = res[0]
    return {"lat": float(top["lat"]), "lon": float(top["lon"]), "display_name": top.get("display_name")}


async def reverse_city(lat: float, lon: float) -> str | None:
    """Coordinates -> Hebrew city/town name, or None."""
    res = await _get("reverse", {"lat": round(lat, 5), "lon": round(lon, 5), "zoom": 10})
    addr = (res or {}).get("address", {})
    return addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")


@lru_cache(maxsize=1)
def _r() -> float:
    return 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _r() * math.asin(math.sqrt(a))
