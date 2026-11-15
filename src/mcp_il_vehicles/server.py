"""mcp-il-vehicles — Israeli vehicle registry: plate lookup, open recalls, model specs, new-car prices,
licensed garages and EV charging stations. Live data from data.gov.il (Ministry of Transport)."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import date

from fastmcp import FastMCP

from . import __version__
from .ckan import datastore_search, meta
from .geo import geocode, haversine_km, reverse_city

R_PRIVATE = "053cea08-09bc-40ec-8f7a-156f0677aff3"  # כלי רכב פרטיים ומסחריים (פעילים)
R_PRIVATE_EXTRA = "0866573c-40cd-4ca8-91d2-9dd2d7a492e5"  # המשך: הנעה, עומס/מהירות צמיגים
R_INACTIVE = "f6efe89a-fb3d-43a4-bb61-9bf12a9b9099"  # לא פעילים עם קוד דגם
R_INACTIVE_NO_MODEL = "6f6acd03-f351-4a8f-8ecf-df792f4f573a"  # לא פעילים ללא קוד דגם
R_MOTORCYCLE = "bf9df4e2-d90d-4c0a-a400-19e15af8e95f"  # דו גלגליים
R_PUBLIC = "cf29862d-ca25-4691-84f6-1be60dcb4a1e"  # כלי רכב ציבוריים פעילים
R_RECALL = "36bf1404-0be4-49d2-82dc-2f1ead4a8b93"  # כלי רכב שלא ביצעו ריקול
R_MODELS = "142afde2-6228-49f9-8a29-9b6c3a0cbe40"  # תוצרים ודגמים WLTP
R_PRICES = "39f455bf-6db0-4926-859d-017f34eacbcb"  # יבואנים ומחירוני רכב חדש
R_GARAGES = "bb68386a-a331-4bbc-b668-bba2766d517d"  # מוסכים ומכוני רישוי
R_CHARGERS = "528482f2-d410-4d62-8b17-566ab23a1c52"  # עמדות טעינה לרכב חשמלי
R_PERSONAL_IMPORT = "03adc637-b6fe-402b-9937-7c3d3afc9140"  # כלי רכב ביבוא אישי
R_DISABLED_TAG = "c8b9f9c8-4612-4068-934f-d4acd2e3c06e"  # כלי רכב עם תג חניה לנכה
R_EV_DISTRICT = "07421a4e-5b12-4444-9173-5ca297b31f79"  # כמות כלי רכב חשמליים לפי נפה

DS = {
    "registry": "Ministry of Transport — vehicle registry",
    "recall": "Ministry of Transport — vehicles with open recalls",
    "models": "Ministry of Transport — makes & models (WLTP)",
    "prices": "Ministry of Transport — importers & new-car price lists",
    "garages": "Ministry of Transport — licensed garages & test stations",
    "chargers": "Ministry of Energy — EV charging stations",
    "import": "Ministry of Transport — personally imported vehicles",
    "disabled": "Ministry of Transport — vehicles with disabled-parking permit",
    "ev_district": "Ministry of Transport — electric vehicles by sub-district",
    "osm": "OpenStreetMap Nominatim geocoding (© OpenStreetMap contributors, ODbL)",
}

mcp = FastMCP(
    "mcp-il-vehicles",
    version=__version__,
    instructions=(
        "Israeli vehicle data. Start with vehicle_by_plate (licence plate digits only), then vehicle_recalls and "
        "model_specs_for_plate. Use find_garages for licensed garages by city/specialty. Data is Hebrew."
    ),
)


def _plate(p: str | int) -> int:
    s = "".join(ch for ch in str(p) if ch.isdigit())
    if not 5 <= len(s) <= 8:
        raise ValueError("Plate must have 5-8 digits, e.g. 12-345-67")
    return int(s)


def _registry(r: dict, source: str) -> dict:
    return {
        "registry": source,
        "plate": r.get("mispar_rechev"),
        "make": r.get("tozeret_nm"),
        "make_country": r.get("tozeret_eretz_nm"),
        "model_code": r.get("degem_nm"),
        "commercial_name": r.get("kinuy_mishari"),
        "trim": r.get("ramat_gimur"),
        "year": r.get("shnat_yitzur"),
        "fuel": r.get("sug_delek_nm"),
        "color": r.get("tzeva_rechev"),
        "ownership": r.get("baalut"),
        "vehicle_type": r.get("sug_rechev_nm"),
        "engine_code": r.get("degem_manoa"),
        "engine_cc": r.get("nefach_manoa"),
        "gross_weight_kg": r.get("mishkal_kolel"),
        "first_on_road": r.get("moed_aliya_lakvish"),
        "last_test": r.get("mivchan_acharon_dt"),
        "license_valid_until": r.get("tokef_dt"),
        "vin": r.get("misgeret") or r.get("mispar_shilda"),
        "front_tire": r.get("zmig_kidmi") or r.get("mida_zmig_kidmi"),
        "rear_tire": r.get("zmig_ahori") or r.get("mida_zmig_ahori"),
        "pollution_group": r.get("kvutzat_zihum"),
        "safety_level": r.get("ramat_eivzur_betihuty"),
        "cancellation": r.get("bitul_nm"),
        "cancellation_date": r.get("bitul_dt"),
        "_codes": {"tozeret_cd": r.get("tozeret_cd"), "degem_cd": r.get("degem_cd"), "sug_degem": r.get("sug_degem")},
    }


async def _find_plate(n: int) -> dict | None:
    sources = [
        (R_PRIVATE, "active private/commercial"),
        (R_MOTORCYCLE, "two-wheeler"),
        (R_PUBLIC, "public vehicle"),
        (R_INACTIVE, "inactive (off road)"),
        (R_INACTIVE_NO_MODEL, "inactive, no model code"),
    ]
    res = await asyncio.gather(
        *(datastore_search(rid, filters={"mispar_rechev": n}, limit=1) for rid, _ in sources), return_exceptions=True
    )
    for (rid, label), r in zip(sources, res, strict=True):
        if not isinstance(r, Exception) and r["records"]:
            v = _registry(r["records"][0], label)
            if rid == R_PRIVATE:
                try:
                    extra = await datastore_search(R_PRIVATE_EXTRA, filters={"mispar_rechev": n}, limit=1)
                    if extra["records"]:
                        v["drive"] = extra["records"][0].get("grira_nm")
                except Exception:  # noqa: BLE001
                    pass
            return {k: val for k, val in v.items() if val is not None}
    try:  # personal imports are published in a separate registry
        imp = await datastore_search(R_PERSONAL_IMPORT, filters={"mispar_rechev": n}, limit=1)
    except Exception:  # noqa: BLE001
        imp = {"records": []}
    if imp["records"]:
        r = imp["records"][0]
        v = _registry(r, "personal import")
        v["vin"] = r.get("shilda") or v.get("vin")
        v["import_type"] = r.get("sug_yevu")
        return {k: val for k, val in v.items() if val is not None}
    return None


@mcp.tool
async def vehicle_by_plate(plate: str) -> dict:
    """Look up an Israeli licence plate: make, model, year, fuel, colour, ownership type, last annual test,
    licence expiry, VIN, tyres. Searches active, inactive, two-wheeler and public-vehicle registries."""
    n = _plate(plate)
    v = await _find_plate(n)
    if not v:
        return {"plate": n, "found": False, **meta(DS["registry"])}
    return {"found": True, "vehicle": v, **meta(DS["registry"])}


@mcp.tool
async def vehicle_recalls(plate: str) -> dict:
    """Open (not yet performed) manufacturer recalls for a licence plate."""
    n = _plate(plate)
    res = await datastore_search(R_RECALL, filters={"MISPAR_RECHEV": n}, limit=50)
    recalls = [
        {
            "recall_id": r.get("RECALL_ID"),
            "recall_type": r.get("SUG_RECALL"),
            "fault_category": r.get("SUG_TAKALA"),
            "description": r.get("TEUR_TAKALA"),
            "opened": r.get("TAARICH_PTICHA"),
        }
        for r in res["records"]
    ]
    return {"plate": n, "open_recalls": len(recalls), "recalls": recalls, **meta(DS["recall"])}


def _spec(r: dict) -> dict:
    keys = {
        "make": "tozeret_nm", "manufacturer": "tozar", "country": "tozeret_eretz_nm", "model_code": "degem_nm",
        "commercial_name": "kinuy_mishari", "year": "shnat_yitzur", "body": "merkav", "trim": "ramat_gimur",
        "fuel": "delek_nm", "engine_cc": "nefah_manoa", "horsepower": "koah_sus", "gross_weight_kg": "mishkal_kolel",
        "doors": "mispar_dlatot", "seats": "mispar_moshavim", "drive": "hanaa_nm", "automatic": "automatic_ind",
        "drive_technology": "technologiat_hanaa_nm", "airbags": "mispar_kariot_avir", "abs": "abs_ind",
        "co2_wltp": "CO2_WLTP", "green_index": "madad_yarok", "pollution_group": "kvutzat_zihum",
        "safety_score": "nikud_betihut", "safety_level": "ramat_eivzur_betihuty",
        "lane_departure": "bakarat_stiya_menativ_ind", "adaptive_cruise": "bakarat_shyut_adaptivit_ind",
        "pedestrian_detection": "zihuy_holchey_regel_ind", "auto_emergency_braking": "maarechet_ezer_labalam_ind",
        "reverse_camera": "matzlemat_reverse_ind", "tow_with_brakes_kg": "kosher_grira_im_blamim",
    }
    return {k: r.get(v) for k, v in keys.items() if r.get(v) is not None}


@mcp.tool
async def model_specs_for_plate(plate: str) -> dict:
    """Technical and safety specs (horsepower, engine, drive, airbags, ADAS, CO2, green index) for the
    exact model/year registered to a licence plate."""
    n = _plate(plate)
    v = await _find_plate(n)
    if not v:
        return {"plate": n, "found": False, **meta(DS["registry"])}
    codes = v.get("_codes", {})
    filters = {k: codes[k] for k in ("tozeret_cd", "degem_cd") if codes.get(k) is not None}
    if v.get("year"):
        filters["shnat_yitzur"] = v["year"]
    if len(filters) < 2:
        return {"plate": n, "vehicle": v, "specs": None, "message": "No model code for this vehicle.",
                **meta(DS["registry"])}
    res = await datastore_search(R_MODELS, filters=filters, limit=5)
    return {"plate": n, "vehicle": v, "specs": [_spec(r) for r in res["records"]], **meta([DS["registry"], DS["models"]])}


@mcp.tool
async def search_models(query: str, year: int | None = None, limit: int = 10) -> dict:
    """Search makes/models (Hebrew or Latin, e.g. "טויוטה קורולה" or "COROLLA") and return specs."""
    filters = {"shnat_yitzur": year} if year else None
    res = await datastore_search(R_MODELS, q=query, filters=filters, limit=max(1, min(limit, 50)))
    return {"total": res["total"], "models": [_spec(r) for r in res["records"]], **meta(DS["models"])}


@mcp.tool
async def new_car_prices(query: str, year: int | None = None, limit: int = 20) -> dict:
    """Official importer list prices (₪) for new cars, by make/model text and optional model year.
    Newer models are often listed in Latin letters (e.g. "COROLLA"), older ones in Hebrew — try both."""
    filters = {"shnat_yitzur": year} if year else None
    res = await datastore_search(R_PRICES, q=query, filters=filters, limit=max(1, min(limit, 100)),
                                 sort="shnat_yitzur desc")
    rows = [
        {"importer": r.get("shem_yevuan"), "make": r.get("tozeret_nm"), "model_code": r.get("degem_nm"),
         "commercial_name": r.get("kinuy_mishari"), "year": r.get("shnat_yitzur"), "price_ils": r.get("mehir")}
        for r in res["records"]
    ]
    return {"total": res["total"], "prices": rows, **meta(DS["prices"])}


@mcp.tool
async def find_garages(city: str = "", specialty: str = "", name: str = "", limit: int = 20) -> dict:
    """Licensed garages and test stations (מוסכים ומכוני רישוי) by city (exact Hebrew name, e.g. "בת ים"),
    specialty keyword (e.g. "חשמל", "היברידי", "דיזל", "פחחות") and/or garage name."""
    filters = {"yishuv": city} if city else None
    q = " ".join(x for x in (specialty, name) if x) or None
    res = await datastore_search(R_GARAGES, filters=filters, q=q, limit=max(1, min(limit, 100)))
    rows = [
        {"garage_no": r.get("mispar_mosah"), "name": r.get("shem_mosah"), "type": r.get("sug_mosah"),
         "specialty": r.get("miktzoa"), "professional_manager": r.get("menahel_miktzoa"),
         "address": r.get("ktovet"), "city": r.get("yishuv"), "phone": r.get("telephone"),
         "company_number": r.get("rasham_havarot")}
        for r in res["records"]
    ]
    return {"total": res["total"], "garages": rows, **meta(DS["garages"])}


@mcp.tool
async def ev_charging_stations(query: str, limit: int = 20) -> dict:
    """EV charging sites by place name, address or operator (e.g. "אילת", "Afcon")."""
    res = await datastore_search(R_CHARGERS, q=query, limit=max(1, min(limit, 100)))
    rows = [
        {"name": r.get("name"), "address": r.get("Address"), "operator": r.get("op"),
         "chargers": r.get("count"), "fast": r.get("cnt_fast"), "slow": r.get("cnt_slow")}
        for r in res["records"]
    ]
    return {"total": res["total"], "stations": rows, **meta(DS["chargers"])}


def _yyyymmdd(v) -> str | None:
    s = str(v or "")
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s.isdigit() else (s or None)


@mcp.tool
async def disabled_parking_permit(plate: str) -> dict:
    """Does a licence plate hold a disabled-parking permit (תג חניה לנכה)? Returns issue date and permit type code."""
    n = _plate(plate)
    res = await datastore_search(R_DISABLED_TAG, filters={"MISPAR RECHEV": n}, limit=5)
    permits = [{"issued": _yyyymmdd(r.get("TAARICH HAFAKAT TAG")), "permit_type_code": r.get("SUG TAV")}
               for r in res["records"]]
    return {"plate": n, "has_permit": bool(permits), "permits": permits,
            "note": "permit_type_code is published without a legend by the Ministry of Transport.",
            **meta(DS["disabled"])}


@mcp.tool
async def personal_import_check(plate: str) -> dict:
    """Was this vehicle brought in by personal import (יבוא אישי, new or used) rather than an official importer?
    Personal-import cars can have different warranty, parts and resale considerations."""
    n = _plate(plate)
    res = await datastore_search(R_PERSONAL_IMPORT, filters={"mispar_rechev": n}, limit=1)
    if not res["records"]:
        return {"plate": n, "personal_import": False, **meta(DS["import"])}
    r = res["records"][0]
    return {"plate": n, "personal_import": True, "import_type": r.get("sug_yevu"), "make": r.get("tozeret_nm"),
            "model_code": r.get("degem_nm"), "year": r.get("shnat_yitzur"), "country": r.get("tozeret_eretz_nm"),
            "vin": r.get("shilda"), "fuel": r.get("sug_delek_nm"), "first_on_road": r.get("moed_aliya_lakvish"),
            "last_test": r.get("mivchan_acharon_dt"), "license_valid_until": r.get("tokef_dt"), **meta(DS["import"])}


@mcp.tool
async def ev_adoption_by_year(from_year: int = 2015, to_year: int | None = None) -> dict:
    """Time series of electric (BEV) and plug-in/hybrid share among active private & commercial vehicles,
    grouped by year first on the road — a proxy for EV adoption in new registrations over time."""
    to_year = to_year or date.today().year
    years = list(range(max(1990, from_year), to_year + 1))[-15:]
    sem = asyncio.Semaphore(6)

    async def count(year: int, fuel: list[str] | None) -> int:
        f: dict = {"moed_aliya_lakvish": [f"{year}-{m}" for m in range(1, 13)]}
        if fuel:
            f["sug_delek_nm"] = fuel
        async with sem:
            return (await datastore_search(R_PRIVATE, filters=f, limit=1))["total"]

    jobs = [(y, k, fuel) for y in years for k, fuel in
            (("total", None), ("bev", ["חשמל"]), ("hybrid", ["חשמל/בנזין", "חשמל/דיזל"]))]
    counts = await asyncio.gather(*(count(y, fuel) for y, _, fuel in jobs))
    table: dict[int, dict] = {y: {"year": y} for y in years}
    for (y, k, _), c in zip(jobs, counts, strict=True):
        table[y][k] = c
    rows = []
    for y in years:
        t = table[y]
        tot = t["total"] or 0
        rows.append({**t, "bev_share_pct": round(100 * t["bev"] / tot, 1) if tot else None,
                     "hybrid_share_pct": round(100 * t["hybrid"] / tot, 1) if tot else None})
    return {"series": rows,
            "method": "Counts of vehicles still active today, by year first on the road. Scrapped vehicles are not "
                      "included, so early years are under-counted; recent years approximate new-registration share.",
            **meta(DS["registry"])}


@mcp.tool
async def ev_by_district(ownership: str = "") -> dict:
    """Current number of electric vehicles by district (מחוז) and sub-district (נפה), with each area's share
    of the national EV fleet. Optional ownership filter, e.g. "פרטי", "חברה", "השכרה", "ליסינג"."""
    res = await datastore_search(R_EV_DISTRICT, filters={"baalut": ownership} if ownership else None, limit=500)
    total = sum(r.get("car_num") or 0 for r in res["records"]) or 1
    districts: dict[str, dict] = {}
    subs: dict[tuple, int] = {}
    for r in res["records"]:
        d, nafa, n = r.get("mahoz_nm") or "?", r.get("nafa_nm") or "?", r.get("car_num") or 0
        districts.setdefault(d, {"district": d, "evs": 0})["evs"] += n
        subs[(d, nafa)] = subs.get((d, nafa), 0) + n
    out_d = sorted(districts.values(), key=lambda x: -x["evs"])
    for x in out_d:
        x["share_pct"] = round(100 * x["evs"] / total, 1)
    out_s = sorted(({"district": d, "sub_district": s, "evs": n, "share_pct": round(100 * n / total, 1)}
                    for (d, s), n in subs.items()), key=lambda x: -x["evs"])
    return {"national_evs": total, "ownership_filter": ownership or "all", "by_district": out_d,
            "by_sub_district": out_s,
            "note": "Snapshot as currently published; the ministry does not publish a history for this table. "
                    "See ev_adoption_by_year for a time series.", **meta(DS["ev_district"])}


@mcp.tool
async def find_garages_near(address: str = "", lat: float | None = None, lon: float | None = None,
                            specialty: str = "", radius_km: float = 10.0, max_results: int = 10,
                            extra_cities: list[str] | None = None) -> dict:
    """Licensed garages nearest to an address or GPS point, with distance in km.

    Args:
        address: e.g. "ההסתדרות 50, בת ים" (or give lat/lon instead).
        specialty: keyword such as "חשמל", "היברידי", "מכונאות", "פחחות", "צמיגים".
        radius_km: keep garages within this distance.
        extra_cities: neighbouring cities to include (Hebrew names as in the registry, e.g. ["חולון", "תל אביב -יפו"]).
    Geocoding uses OpenStreetMap (≤1 request/s), so at most 25 garage addresses are located per call.
    """
    if lat is None or lon is None:
        if not address:
            raise ValueError("Provide address or lat/lon")
        origin = await geocode(address)
        if not origin:
            return {"found": False, "message": f"Could not locate '{address}'.", **meta(DS["osm"])}
        lat, lon = origin["lat"], origin["lon"]
    city = await reverse_city(lat, lon)
    cities = [c for c in [city, *(extra_cities or [])] if c]
    if not cities:
        return {"found": False, "message": "Could not determine the city for this point.", **meta(DS["osm"])}
    batches = await asyncio.gather(*(datastore_search(R_GARAGES, filters={"yishuv": c}, q=specialty or None,
                                                      limit=60) for c in cities))
    garages = [r for b in batches for r in b["records"]]
    located, skipped = [], 0
    for r in garages[:25]:
        street, town = (r.get("ktovet") or "").strip(), (r.get("yishuv") or "").strip()
        pt, precision = None, None
        if street and town:
            pt, precision = await geocode(f"{street}, {town}"), "address"
            if not pt:
                bare = re.sub(r"\s*\d+[א-ת]?\s*$", "", street)
                if bare and bare != street:
                    pt, precision = await geocode(f"{bare}, {town}"), "street"
        if not pt and town:
            pt, precision = await geocode(town), "city_centre"
        if not pt:
            skipped += 1
            continue
        dist = haversine_km(lat, lon, pt["lat"], pt["lon"])
        if dist <= radius_km:
            located.append({"name": r.get("shem_mosah"), "garage_no": r.get("mispar_mosah"),
                            "specialty": r.get("miktzoa"), "type": r.get("sug_mosah"),
                            "address": ", ".join(x for x in (street, town) if x), "phone": r.get("telephone"),
                            "distance_km": round(dist, 2), "location_precision": precision,
                            "lat": round(pt["lat"], 5), "lon": round(pt["lon"], 5)})
    located.sort(key=lambda x: (x["location_precision"] == "city_centre", x["distance_km"]))
    return {"origin": {"lat": lat, "lon": lon, "city": city}, "cities_searched": cities,
            "garages_in_registry": len(garages), "geocoded": min(len(garages), 25) - skipped,
            "not_located": skipped + max(0, len(garages) - 25), "results": located[:max(1, min(max_results, 25))],
            "note": "Straight-line distances. location_precision: address = exact, street = street only, "
                    "city_centre = address unknown to OpenStreetMap (distance approximate, listed last).",
            **meta([DS["garages"], DS["osm"]])}


@mcp.tool
async def used_car_report(plate: str) -> dict:
    """One-call pre-purchase check for a used car: registry record, licence/test validity, open recalls,
    personal import, disabled-parking permit, model safety/specs and the model's new list price — with flags."""
    n = _plate(plate)
    v = await _find_plate(n)
    if not v:
        return {"plate": n, "found": False, **meta(DS["registry"])}
    recalls_t = vehicle_recalls(str(n))
    import_t = personal_import_check(str(n))
    tag_t = disabled_parking_permit(str(n))
    specs_t = model_specs_for_plate(str(n))
    recalls, imp, tag, specs = await asyncio.gather(recalls_t, import_t, tag_t, specs_t, return_exceptions=True)
    price = None
    if v.get("commercial_name") and v.get("year"):
        try:
            pr = await datastore_search(R_PRICES, q=str(v["commercial_name"]), filters={"shnat_yitzur": v["year"]}, limit=5)
            price = [{"trim": r.get("degem_nm"), "price_ils": r.get("mehir"), "importer": r.get("shem_yevuan")}
                     for r in pr["records"]] or None
        except Exception:  # noqa: BLE001
            price = None

    flags, ok = [], []
    today = date.today().isoformat()
    if "inactive" in v.get("registry", ""):
        flags.append(f"Vehicle is off the road / cancelled ({v.get('cancellation') or 'inactive registry'})")
    if v.get("license_valid_until") and str(v["license_valid_until"]) < today:
        flags.append(f"Annual licence expired on {v['license_valid_until']}")
    elif v.get("license_valid_until"):
        ok.append(f"Licence valid until {v['license_valid_until']}")
    if isinstance(recalls, dict) and recalls.get("open_recalls"):
        flags.append(f"{recalls['open_recalls']} open manufacturer recall(s) not performed")
    elif isinstance(recalls, dict):
        ok.append("No open recalls")
    own = str(v.get("ownership") or "")
    if any(k in own for k in ("השכרה", "ליסינג", "חברה")):
        flags.append(f"Current ownership type: {own} (ex-rental/lease/company cars often have high mileage)")
    if isinstance(imp, dict) and imp.get("personal_import"):
        flags.append(f"Personal import ({imp.get('import_type')}) — check warranty, parts and insurance")
    if isinstance(tag, dict) and tag.get("has_permit"):
        flags.append("Vehicle holds a disabled-parking permit — it is tied to the holder and will not transfer")
    return {
        "plate": n, "found": True, "vehicle": v, "flags": flags, "positives": ok,
        "recalls": recalls if isinstance(recalls, dict) else None,
        "personal_import": imp if isinstance(imp, dict) else None,
        "disabled_permit": tag if isinstance(tag, dict) else None,
        "model_specs": (specs.get("specs") if isinstance(specs, dict) else None),
        "new_list_price_for_model_year": price,
        "not_covered": ["Liens/pledges (רשם המשכונות) — check before paying",
                        "Ownership history count and mileage — Ministry of Transport vehicle history report",
                        "Accident / insurance claims history — insurer databases",
                        "Physical inspection by an independent test station (מכון בדיקה)"],
        **meta([DS["registry"], DS["recall"], DS["import"], DS["disabled"], DS["models"], DS["prices"]]),
    }


@mcp.prompt
def used_car_checklist(plate: str) -> str:
    """Guided pre-purchase review of a used car in Israel, using all vehicle tools."""
    return f"""You are helping me decide whether to buy the used car with Israeli licence plate {plate}.

1. Call `used_car_report` with plate {plate}. Summarise the car in two lines (make, model, trim, year, fuel,
   ownership type, first on road) and list every flag first, in plain language.
2. If the report shows open recalls, explain what each fault is and that the seller/importer should fix it
   before sale at no cost.
3. Compare the model's safety equipment and safety score from `model_specs` with what a buyer should expect.
4. Use `new_list_price_for_model_year` as context for depreciation (never present it as the market price).
5. Call `find_garages_near` for my area (ask me for my address) to suggest a licensed test station or garage
   for an independent inspection.
6. Finish with a checklist of what the open data cannot confirm: liens (רשם המשכונות), number of previous
   owners and mileage (vehicle history report), accident history, service book, test drive.
Answer in the language I write in. Be factual and cite the data source for each claim."""


@mcp.tool
async def health() -> dict:
    """Check that the server can reach data.gov.il."""
    try:
        res = await datastore_search(R_PRIVATE, limit=1)
        return {"status": "ok", "active_vehicles": res["total"], **meta(DS["registry"])}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}


def main() -> None:
    if os.environ.get("MCP_TRANSPORT", "stdio") == "stdio":
        mcp.run()
    else:
        mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
