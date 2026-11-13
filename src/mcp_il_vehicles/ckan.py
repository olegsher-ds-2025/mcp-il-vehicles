"""Minimal async client for the data.gov.il CKAN datastore API."""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import httpx

BASE_URL = "https://data.gov.il/api/3/action"
USER_AGENT = "mcp-il/0.1 (+https://github.com/olegsher-ds-2025)"
TIMEOUT = httpx.Timeout(30.0)

_DROP = {"_id", "rank", "_full_text"}


class CkanError(RuntimeError):
    pass


def clean_value(v: Any) -> Any:
    """data.gov.il registries encode a double quote as '~' (e.g. בע~מ -> בע"מ)."""
    if isinstance(v, str):
        v = v.replace("~", '"').strip()
        return v or None
    return v


def clean_record(rec: dict) -> dict:
    return {k: clean_value(v) for k, v in rec.items() if k not in _DROP}


async def datastore_search(
    resource_id: str,
    *,
    filters: dict | None = None,
    q: str | dict | None = None,
    limit: int = 10,
    offset: int = 0,
    fields: list[str] | None = None,
    sort: str | None = None,
    retries: int = 3,
) -> dict:
    """Query one datastore resource. Returns {'total': int, 'records': [cleaned dicts]}."""
    params: dict[str, Any] = {"resource_id": resource_id, "limit": max(1, min(limit, 1000)), "offset": offset}
    if filters:
        params["filters"] = json.dumps(filters, ensure_ascii=False)
    if q:
        params["q"] = json.dumps(q, ensure_ascii=False) if isinstance(q, dict) else q
    if fields:
        params["fields"] = ",".join(fields)
    if sort:
        params["sort"] = sort

    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        for attempt in range(retries):
            try:
                r = await client.get(f"{BASE_URL}/datastore_search", params=params)
                r.raise_for_status()
                body = r.json()
                if not body.get("success"):
                    raise CkanError(str(body.get("error")))
                res = body["result"]
                return {"total": res.get("total", 0), "records": [clean_record(x) for x in res.get("records", [])]}
            except (httpx.HTTPError, CkanError, ValueError) as exc:
                last_exc = exc
                await asyncio.sleep(1.5 * (attempt + 1))
    raise CkanError(f"data.gov.il query failed for {resource_id}: {last_exc}")


def meta(dataset: str | list[str]) -> dict:
    """Standard provenance block added to every tool response."""
    names = [dataset] if isinstance(dataset, str) else dataset
    return {
        "source": "data.gov.il — " + "; ".join(names),
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "attribution": "Israeli government open data (data.gov.il). Not an official service; verify critical facts "
        "with the publishing authority.",
    }
