"""
Pulls Hidalgo CAD records via the official prodigycad.com public API.
Run from execution/ directory; writes hcad_subject.json and hcad_stonecrest.json.
"""
import urllib.request
import urllib.error
import json
import re
import datetime
import sys
from pathlib import Path

OUT_DIR = Path(__file__).parent
BASE = "https://prod-container.trueprodigyapi.com"
ORIGIN_HEADERS = {
    "Origin": "https://hidalgo.prodigycad.com",
    "Referer": "https://hidalgo.prodigycad.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HCAD-fetcher",
}


def get_token():
    req = urllib.request.Request(
        f"{BASE}/trueprodigy/cadpublic/auth/token",
        data=json.dumps({"office": "Hidalgo"}).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **ORIGIN_HEADERS},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["user"]["token"]


def api(path, body=None, method=None, token=None):
    url = f"{BASE}{path}"
    headers = {**ORIGIN_HEADERS}
    if token:
        headers["Authorization"] = token
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if method is None:
        method = "POST" if data else "GET"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    raw = urllib.request.urlopen(req, timeout=45).read()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw.decode("utf-8", "ignore")}


def search_fulltext(token, q, page_size=200):
    return api(
        f"/public/property/searchfulltext?page=1&pageSize={page_size}",
        {
            "pYear": {"operator": "=", "value": "2026"},
            "fullTextSearch": {"operator": "match", "value": q},
        },
        token=token,
    )


def search_pid(token, pid):
    return api(
        "/public/property/search",
        {"pid": {"operator": "=", "value": str(pid)}},
        token=token,
    )


def deeds(token, pid):
    return api(f"/public/property/{pid}/deeds", token=token, method="GET")


def parcel_shape(token, pid):
    try:
        return api(
            "/gama/parcelshapes",
            {"pid": pid, "pYear": "2026"},
            token=token,
        )
    except Exception:
        return None


def normalize(rec, deed_data, shape_data, source_query, fallback_used):
    """Map raw Prodigy record into the schema expected by county_records SQLite + extras."""
    if isinstance(deed_data, dict):
        deed_results = deed_data.get("results") or []
    else:
        deed_results = []
    last_deed = deed_results[0] if deed_results else None
    return {
        "scraper_used": "manual_webfetch_prodigycad_api",
        "scraper_attempted": "county_records_scraper_v4.HidalgoCountyScraper",
        "scraper_outcome": "FAILED — selectors found grid but search returned 'No Rows To Show'; fell back to direct API",
        "fallback_chain": fallback_used,
        "source_query": source_query,
        "scraped_at_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "source_endpoint": f"{BASE}/public/property/search",
        "data_source_site": "https://hidalgo.prodigycad.com (Hidalgo CAD official portal, True Prodigy backend)",
        # Schema fields (matching county_records SQLite columns)
        "county": "Hidalgo",
        "parcel_number": rec.get("pid"),
        "account_number": rec.get("pAccountID"),
        "geo_id": rec.get("geoID"),
        "tax_office_ref": rec.get("taxOfficeRef"),
        "ref_id": rec.get("refID2"),
        "property_address": (rec.get("fullSitus") or "").strip(),
        "city": rec.get("addrCity"),
        "zip_code": rec.get("addrZip"),
        "owner_name": rec.get("name"),
        "owner_address": rec.get("addrDeliveryLine"),
        "owner_city": rec.get("addrCity"),
        "owner_state": rec.get("addrState"),
        "owner_zip": rec.get("addrZip"),
        "legal_description": rec.get("legalDescription"),
        "legal_acreage": rec.get("legalAcreage"),
        "lot_size_sqft": (
            int(round(float(rec["legalAcreage"]) * 43560))
            if rec.get("legalAcreage") and str(rec.get("legalAcreage")).replace(".", "").isdigit()
            else None
        ),
        "block": rec.get("block"),
        "lot": rec.get("lot"),
        "tract": rec.get("tract"),
        "map_id": rec.get("mapID"),
        "zoning": rec.get("zoning"),
        "state_code": rec.get("asCode"),
        "property_type": rec.get("propType"),
        "land_value": rec.get("landValue"),
        "improvement_value": rec.get("improvementValue"),
        "market_value": rec.get("marketValue"),
        "appraised_value": rec.get("appraisedValue"),
        "assessed_value": rec.get("appraisedValue"),  # TX: assessed = appraised pre-cap
        "exemptions": None,  # Not in payload; would require separate /exemptions endpoint (not exposed in public portal)
        "homestead_exemption": 0,
        "tax_year": int(rec.get("pYear")) if rec.get("pYear") else None,
        "active": rec.get("active"),
        "arb_hearing": rec.get("arbHearing"),
        "latitude": float(rec["latitude"]) if rec.get("latitude") else None,
        "longitude": float(rec["longitude"]) if rec.get("longitude") else None,
        # Last sale / acquisition
        "last_sale_price": None,  # Hidalgo CAD does NOT publish sale prices on the public portal (Texas non-disclosure state)
        "last_sale_date": last_deed.get("deedDt") if last_deed else None,
        "last_sale_grantor": last_deed.get("seller") if last_deed else None,
        "last_sale_grantee": last_deed.get("buyer") if last_deed else None,
        "last_sale_instrument": last_deed.get("instrumentNum") if last_deed else None,
        "last_sale_deed_type": last_deed.get("deedDescription") if last_deed else None,
        "deed_book": last_deed.get("book") if last_deed else None,
        "deed_page": last_deed.get("page") if last_deed else None,
        "deed_volume": last_deed.get("volume") if last_deed else None,
        # Full deed history
        "deed_history": deed_results,
        # Special notes for the feasibility study
        "encumbrances_note": (
            "Hidalgo CAD public portal does NOT publish: (a) HCID No. 1 irrigation district "
            "assessment status, (b) liens or special assessments, (c) FEMA flood zone. "
            "These must be pulled from: HCID No. 1 directly (956-787-6471), Hidalgo County "
            "Clerk for liens (956-318-2100), and FEMA Map Service Center for flood zone."
        ),
        "fema_flood_zone": None,
        "hcid_assessment": None,
        "liens_special_assessments": None,
        # Raw payload for full fidelity
        "raw_record": rec,
        "raw_deeds": deed_data,
        "raw_parcel_shape": shape_data,
    }


def find_subject():
    """Subject parcel — Turquesa Construction LLC owner, ROGERS RD."""
    token = get_token()
    fallback_chain = []

    # Strategy 1: owner search
    fallback_chain.append("owner_search:Turquesa Construction")
    res = search_fulltext(token, "Turquesa Construction")
    rogers = [r for r in res["results"] if "ROGERS" in (r.get("streetName") or "").upper()
              and "TEX-MEX" in (r.get("legalDescription") or "").upper()
              and r.get("block") == "244"]
    if rogers:
        rec = rogers[0]
        fallback_chain.append(f"hit_pid:{rec['pid']}")
    else:
        # Strategy 2: address search
        fallback_chain.append("address_search:Rogers Rd Edinburg")
        res2 = search_fulltext(token, "Rogers Rd Edinburg")
        rogers = [r for r in res2["results"]
                  if (r.get("name") or "").upper() == "TURQUESA CONSTRUCTION LLC"]
        if not rogers:
            raise SystemExit("Subject parcel not found by owner OR address")
        rec = rogers[0]
        fallback_chain.append(f"hit_pid:{rec['pid']}")

    pid = rec["pid"]
    full = search_pid(token, pid)
    rec_2026 = next((r for r in full["results"] if r.get("pYear") == "2026"), full["results"][0])
    deed_data = deeds(token, pid)
    shape = parcel_shape(token, pid)
    return normalize(rec_2026, deed_data, shape, "owner=Turquesa Construction (LOT 8 BLK 244 ROGERS RD)", fallback_chain), full

def find_stonecrest():
    """Stonecrest unnumbered lot east of lots 8-17.

    NOTE: The public full-text search API only returns ~12 STONECREST records
    (numbered residential lots indexed by streetName). The unnumbered tract is
    only retrievable by querying the entire subdivision via asCode=S644700 (the
    official Hidalgo CAD subdivision code for STONECREST R/S LTS 11 & 12).
    """
    token = get_token()
    fallback_chain = []

    # Strategy 1: full-text "STONECREST" (returns only numbered residential lots — won't find target)
    fallback_chain.append("attempt_1:fulltext_STONECREST -> only returns 12 numbered residential lots, target NOT in result set")
    res_full = search_fulltext(token, "STONECREST", page_size=500)
    fallback_chain.append(f"  fulltext_count={res_full['totalProperty']['propertyCount']}")

    # Strategy 2: search by asCode for the entire STONECREST subdivision
    fallback_chain.append("attempt_2:asCode=S644700 (STONECREST subdivision)")
    res = api(
        "/public/property/search",
        {"asCode": {"operator": "=", "value": "S644700"}, "pYear": {"operator": "=", "value": "2026"}},
        token=token,
    )
    fallback_chain.append(f"  asCode_count={res['totalProperty']['propertyCount']}")

    # Filter for target: legal description == "STONECREST (R/S LTS 11 & 12) AN UNNUMBERED LOT EAST LOTS 8-17"
    candidates = []
    for r in res["results"]:
        legal = (r.get("legalDescription") or "").upper()
        if "STONECREST" in legal and "UNNUMBERED" in legal and "EAST LOTS 8-17" in legal:
            candidates.append(r)

    fallback_chain.append(f"  exact_match_candidates={len(candidates)}")

    if not candidates:
        # Broaden: any STONECREST record with UNNUMBERED in legal
        for r in res["results"]:
            legal = (r.get("legalDescription") or "").upper()
            if "STONECREST" in legal and "UNNUMBERED" in legal:
                candidates.append(r)
        fallback_chain.append(f"  unnumbered_only_candidates={len(candidates)}")

    if not candidates:
        return None, fallback_chain, res

    # Pick best match: prefer "UNNUMBERED" wording + "EAST LOTS 8-17"
    def score(r):
        legal = (r.get("legalDescription") or "").upper()
        s = 0
        if "UNNUMBERED" in legal:
            s += 10
        if "EAST LOTS 8-17" in legal or "EAST LOTS 8 - 17" in legal:
            s += 10
        if "R/S LTS 11" in legal:
            s += 5
        return s

    candidates.sort(key=score, reverse=True)
    rec = candidates[0]
    fallback_chain.append(f"chosen_pid:{rec['pid']} legal:{rec.get('legalDescription')[:80]} acres:{rec.get('legalAcreage')}")

    pid = rec["pid"]
    full = search_pid(token, pid)
    rec_2026 = next((r for r in full["results"] if r.get("pYear") == "2026"), full["results"][0])
    deed_data = deeds(token, pid)
    shape = parcel_shape(token, pid)
    norm = normalize(rec_2026, deed_data, shape, "legal=STONECREST UNNUMBERED EAST LOTS 8-17", fallback_chain)
    norm["search_candidates_considered"] = [
        {"pid": c["pid"], "legal": c.get("legalDescription"), "acres": c.get("legalAcreage"), "owner": c.get("name")}
        for c in candidates[:8]
    ]
    return norm, fallback_chain, res


def main():
    print("[1/2] Fetching SUBJECT parcel (Turquesa Construction LLC, Rogers Rd)...", flush=True)
    subj, full_subj = find_subject()
    out1 = OUT_DIR / "hcad_subject.json"
    out1.write_text(json.dumps(subj, indent=2, default=str))
    print(f"    -> wrote {out1} (pid={subj['parcel_number']}, owner={subj['owner_name']})")

    print("[2/2] Fetching STONECREST adjacent tract (legal: STONECREST UNNUMBERED EAST LOTS 8-17)...", flush=True)
    stone, chain, raw_search = find_stonecrest()
    out2 = OUT_DIR / "hcad_stonecrest.json"
    if stone is None:
        # Save a diagnostic JSON
        diag = {
            "scraper_used": "manual_webfetch_prodigycad_api",
            "scraper_outcome": "PARTIAL — could not pinpoint Stonecrest UNNUMBERED tract via legal-description full-text search",
            "fallback_chain": chain,
            "search_query": "STONECREST",
            "candidates_examined": [
                {"pid": r.get("pid"), "legal": r.get("legalDescription"), "acres": r.get("legalAcreage"), "owner": r.get("name")}
                for r in raw_search.get("results", [])[:25]
            ],
            "next_steps": [
                "Manual lookup at hidalgo.prodigycad.com/property-search",
                "Search by 'STONECREST UNNUMBERED' or by adjacent owner name (likely original developer)",
                "Pull plat from Hidalgo County Clerk Vol. 34 Pg. 164A H.C.M.R. — check accompanying parcel list",
                "Field visit to confirm parcel-pin from county GIS",
            ],
            "scraped_at_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "owner_name": None,
            "parcel_number": None,
            "last_sale_date": None,
            "last_sale_price": None,
            "assessed_value": None,
            "market_value": None,
        }
        out2.write_text(json.dumps(diag, indent=2, default=str))
        print(f"    -> wrote DIAGNOSTIC {out2} (no definitive match found)")
    else:
        out2.write_text(json.dumps(stone, indent=2, default=str))
        print(f"    -> wrote {out2} (pid={stone['parcel_number']}, owner={stone['owner_name']})")

    print()
    print("DONE.")
    return subj, stone


if __name__ == "__main__":
    main()
