"""mcp-il-vehicles — Israeli vehicle registry: plate lookup, open recalls, model specs, new-car prices,
licensed garages and EV charging stations. Live data from data.gov.il (Ministry of Transport)."""
from __future__ import annotations

import asyncio
import os

from fastmcp import FastMCP

from .ckan import datastore_search, meta

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

DS = {
    "registry": "Ministry of Transport — vehicle registry",
    "recall": "Ministry of Transport — vehicles with open recalls",
    "models": "Ministry of Transport — makes & models (WLTP)",
    "prices": "Ministry of Transport — importers & new-car price lists",
    "garages": "Ministry of Transport — licensed garages & test stations",
    "chargers": "Ministry of Energy — EV charging stations",
}

mcp = FastMCP(
    "mcp-il-vehicles",
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
