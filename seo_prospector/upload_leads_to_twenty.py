#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload RGV rank-5-to-10 leads for ANY profession to Twenty CRM at localhost:3000.

Profession-driven. Reads the per-city CSVs produced by rank_prospector.py
(output/<profession-slug>_<City>_*.csv -- latest file per city) and creates
one company per firm, named:

    <PROFESSION> LEADS | <City> | R<rank> | <firm name>

e.g.  ATTORNEY LEADS | McAllen | R5 | Patino Law Firm
      DENTIST LEADS | Harlingen | R7 | Valley Smiles

The "<PROFESSION> LEADS |" prefix keeps each batch as its own distinct group,
separate from the general "SEO |" rank-5-10 prospects and the "HS |" no-website
leads. Search / filter that prefix in Twenty to see only that profession.

Field mapping:
  website  -> domainName.primaryLinkUrl
  facebook -> domainName.secondaryLinks  (label "Facebook")
  email    -> domainName.secondaryLinks  (mailto:, label is the address)
  phone    -> phoneNumber
  address  -> address (street / city / state / postcode parsed from CSV)

A firm that ranks 5-10 in more than one city is uploaded once, under its
best (lowest) rank, with every city it ranks in listed in the name.

If the Twenty instance rejects the secondaryLinks composite, the create is
retried with a plain body so the company still lands (email/facebook then
simply absent on that record).

Usage:
    python upload_leads_to_twenty.py --profession "attorney"
    python upload_leads_to_twenty.py --profession "dentist" --dry-run
    python upload_leads_to_twenty.py --profession "attorney" \\
        --csv output/attorney_McAllen_2026-05-21_2237.csv
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
EXECUTION_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = SCRIPT_DIR / "output"

API_URL = "http://localhost:3000/rest/companies"

# Set in main() from --profession. The CRM group name.
PREFIX = ""


def slugify(profession: str) -> str:
    """Match rank_prospector.py's filename slug: spaces -> '-', lowercased."""
    return profession.strip().replace(" ", "-").lower()


def load_env() -> dict:
    env = {}
    env_path = EXECUTION_DIR / ".env.local"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def latest_city_csvs(slug: str) -> list[Path]:
    """Newest <slug>_<City>_*.csv per city."""
    if not OUTPUT_DIR.exists():
        return []
    pat = re.compile(rf"{re.escape(slug)}_(.+?)_\d{{4}}-\d{{2}}-\d{{2}}_\d+\.csv$")
    by_city: dict[str, Path] = {}
    for p in OUTPUT_DIR.glob(f"{slug}_*.csv"):
        m = pat.match(p.name)
        if not m:
            continue
        city = m.group(1)
        if city not in by_city or p.stat().st_mtime > by_city[city].stat().st_mtime:
            by_city[city] = p
    return [by_city[c] for c in sorted(by_city)]


def clean_phone(phone_str: str) -> str:
    digits = "".join(c for c in (phone_str or "") if c.isdigit())
    return digits if len(digits) >= 10 else ""


def parse_address(full: str, fallback_city: str) -> dict:
    """'1802 N 10th St, McAllen, TX 78501, USA' -> address composite."""
    parts = [p.strip() for p in (full or "").split(",") if p.strip()]
    street = parts[0] if len(parts) >= 4 else ""
    city = parts[1] if len(parts) >= 4 else (parts[0] if parts else fallback_city)
    state, postcode = "TX", ""
    for p in parts:
        m = re.match(r"^([A-Z]{2})\s+(\d{5})$", p)
        if m:
            state, postcode = m.group(1), m.group(2)
            break
    return {
        "addressStreet1": street,
        "addressCity": city or fallback_city,
        "addressState": state,
        "addressPostcode": postcode,
        "addressCountry": "US",
    }


def company_name(rec: dict) -> str:
    cities = "+".join(rec["cities"])
    name = rec["name"][:90]
    return f"{PREFIX} {cities} | R{rec['rank']} | {name}"


def build_body(rec: dict) -> dict:
    secondary = []
    if rec.get("facebook"):
        secondary.append({"url": rec["facebook"], "label": "Facebook"})
    if rec.get("email"):
        secondary.append({"url": f"mailto:{rec['email']}", "label": rec["email"]})

    domain = {"primaryLinkLabel": "Website"}
    if rec.get("website"):
        domain["primaryLinkUrl"] = rec["website"]
    if secondary:
        domain["secondaryLinks"] = secondary

    body = {
        "name": company_name(rec),
        "address": parse_address(rec.get("address", ""), rec["cities"][0]),
    }
    if domain.get("primaryLinkUrl") or domain.get("secondaryLinks"):
        body["domainName"] = domain
    phone = clean_phone(rec.get("phone", ""))
    if phone:
        body["phoneNumber"] = {
            "primaryPhoneNumber": phone,
            "primaryPhoneCountryCode": "US",
            "primaryPhoneCallingCode": "+1",
        }
    return body


def strip_secondary(body: dict) -> dict:
    """Fallback body: drop secondaryLinks if the instance rejects them."""
    out = json.loads(json.dumps(body))
    if "domainName" in out:
        out["domainName"].pop("secondaryLinks", None)
        if not out["domainName"].get("primaryLinkUrl"):
            out.pop("domainName")
    return out


def post_company(body: dict, headers: dict) -> tuple[bool, str]:
    try:
        req = Request(API_URL, data=json.dumps(body).encode(),
                      headers=headers, method="POST")
        resp = urlopen(req, timeout=30)
        data = json.loads(resp.read())
        return True, data["data"]["createCompany"]["id"]
    except HTTPError as e:
        err_body = e.read().decode()[:300] if e.fp else str(e)
        return False, f"HTTP {e.code}: {err_body}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def create_company(rec: dict, headers: dict) -> tuple[bool, str, bool]:
    """Returns (ok, result, dropped_secondary)."""
    body = build_body(rec)
    ok, result = post_company(body, headers)
    if ok or "secondaryLinks" not in result:
        return ok, result, False
    # Instance rejected the secondaryLinks composite -- retry plain.
    ok2, result2 = post_company(strip_secondary(body), headers)
    return ok2, result2, ok2


def fetch_existing_names(headers: dict) -> set:
    """Names already starting with the profession prefix (server-side filter)."""
    existing = set()
    flt = urllib.parse.quote(f"name[ilike]:%{PREFIX}%")
    page = 1
    while True:
        req = Request(f"{API_URL}?limit=100&page={page}&filter={flt}",
                      headers=headers, method="GET")
        try:
            resp = urlopen(req, timeout=30)
            data = json.loads(resp.read())
            companies = data.get("data", {}).get("companies", [])
            if not companies:
                break
            for c in companies:
                nm = c.get("name", "")
                if nm.startswith(PREFIX):
                    existing.add(nm)
            if len(companies) < 100:
                break
            page += 1
            time.sleep(0.6)
        except Exception as e:
            print(f"  Warning: could not fetch existing leads: {e}")
            break
    return existing


def load_records(csv_paths: list[Path]) -> list[dict]:
    """Read every CSV, dedupe a firm across cities into one record."""
    firms: dict[str, dict] = {}
    for path in csv_paths:
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                key = name.lower()
                try:
                    rank = int(row.get("rank_pos") or 99)
                except ValueError:
                    rank = 99
                city = (row.get("city") or "").strip()
                rec = firms.get(key)
                if rec is None:
                    firms[key] = {
                        "name": name,
                        "cities": [city] if city else [],
                        "rank": rank,
                        "tier": row.get("tier", ""),
                        "rating": row.get("rating", ""),
                        "reviews": row.get("reviews", ""),
                        "website": (row.get("website") or "").strip(),
                        "email": (row.get("email") or "").strip(),
                        "facebook": (row.get("facebook") or "").strip(),
                        "address": (row.get("address") or "").strip(),
                        "phone": (row.get("phone") or "").strip(),
                    }
                else:
                    if city and city not in rec["cities"]:
                        rec["cities"].append(city)
                    rec["rank"] = min(rec["rank"], rank)
                    # Keep the richest contact data found in any city.
                    for fld in ("website", "email", "facebook", "phone", "address"):
                        if not rec[fld] and (row.get(fld) or "").strip():
                            rec[fld] = (row.get(fld) or "").strip()
    for rec in firms.values():
        if not rec["cities"]:
            rec["cities"] = ["RGV"]
    return sorted(firms.values(), key=lambda r: (r["cities"][0], r["rank"]))


def main():
    global PREFIX
    parser = argparse.ArgumentParser(
        description="Upload rank-5-10 leads for any profession to Twenty CRM")
    parser.add_argument("--profession", required=True,
                        help='Trade to upload, e.g. "attorney", "dentist". '
                             "Drives the CSV glob and the CRM group name.")
    parser.add_argument("--csv", action="append", default=[],
                        help="Specific CSV(s); repeatable. Default: latest per city.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would upload, no writes")
    args = parser.parse_args()

    slug = slugify(args.profession)
    PREFIX = f"{args.profession.strip().upper()} LEADS |"

    if args.csv:
        csv_paths = [Path(c) for c in args.csv]
    else:
        csv_paths = latest_city_csvs(slug)
    csv_paths = [p for p in csv_paths if p.exists()]
    if not csv_paths:
        print(f"[FATAL] No '{slug}_*.csv' files found in output/. Run "
              f'rank_prospector.py --category "{args.profession}" '
              "--separate-by-city first.", file=sys.stderr)
        sys.exit(2)

    records = load_records(csv_paths)
    print("Source CSVs:")
    for p in csv_paths:
        print(f"  {p.name}")
    print(f"\nUnique firms after cross-city dedupe: {len(records)}")
    print(f"List name in Twenty: '{PREFIX}' (search this prefix to see the group)")
    print("=" * 64)

    if args.dry_run:
        for r in records:
            extras = []
            if r["email"]:
                extras.append(f"email:{r['email']}")
            if r["facebook"]:
                extras.append("facebook")
            if not r["website"]:
                extras.append("NO website")
            tag = ("  [" + ", ".join(extras) + "]") if extras else ""
            print(f"  {company_name(r)}{tag}")
        with_email = sum(1 for r in records if r["email"])
        with_fb = sum(1 for r in records if r["facebook"])
        with_site = sum(1 for r in records if r["website"])
        print(f"\n[DRY RUN] {len(records)} companies would be created.")
        print(f"  website: {with_site}/{len(records)}  "
              f"email: {with_email}/{len(records)}  "
              f"facebook: {with_fb}/{len(records)}")
        return

    env = load_env()
    api_key = env.get("TWENTY_API_KEY", os.environ.get("TWENTY_API_KEY", ""))
    if not api_key:
        print(f"[FATAL] TWENTY_API_KEY not found in {EXECUTION_DIR / '.env.local'}",
              file=sys.stderr)
        sys.exit(2)
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {api_key}"}

    print(f"Checking for existing '{PREFIX}' leads in Twenty...")
    existing = fetch_existing_names(headers)
    print(f"  Found {len(existing)} existing '{PREFIX}' companies")

    new_records = [r for r in records if company_name(r) not in existing]
    print(f"  {len(records) - len(new_records)} already in Twenty, "
          f"{len(new_records)} new to upload\n")

    success = errors = dupes = stripped = 0
    for i, r in enumerate(new_records):
        ok, result, dropped = create_company(r, headers)
        if ok:
            success += 1
            if dropped:
                stripped += 1
        elif "already" in str(result).lower() or "duplicate" in str(result).lower():
            dupes += 1
        else:
            errors += 1
            if errors <= 5:
                print(f"  ERROR [{r['name']}]: {result[:200]}")
        time.sleep(0.6)
        if (i + 1) % 30 == 0:
            time.sleep(2.0)

    print("\n" + "=" * 64)
    print(f"DONE: {success} new + {len(existing)} existing = "
          f"{success + len(existing)} total '{PREFIX}' leads in Twenty")
    print(f"Errors: {errors}  |  Dupes: {dupes}")
    if stripped:
        print(f"Note: {stripped} record(s) created without email/facebook "
              f"(instance rejected secondaryLinks).")
    print(f"Open: http://localhost:3000/objects/companies "
          f"- search '{PREFIX}'")


if __name__ == "__main__":
    main()
