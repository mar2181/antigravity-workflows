#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload RGV rank-5-to-10 SEO prospects to Twenty CRM at localhost:3000.

Reads the latest rank_prospector.py CSV from output/ (or --csv PATH) and
creates one company per lead, named:

    SEO | R{rank} | {category} | {business name}

The "SEO |" prefix keeps these distinct from the no-website leads, which
the lead_gen uploader files under "HS |".

Usage:
    python upload_to_twenty.py                 # latest CSV in output/
    python upload_to_twenty.py --csv output/rgv_rank5to10_2026-05-21_1430.csv
    python upload_to_twenty.py --dry-run        # show what would upload, no writes
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
EXECUTION_DIR = SCRIPT_DIR.parent

API_URL = "http://localhost:3000/rest/companies"


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


def latest_csv() -> Path | None:
    out_dir = SCRIPT_DIR / "output"
    if not out_dir.exists():
        return None
    csvs = sorted(out_dir.glob("rgv_rank5to10_*.csv"), key=lambda p: p.stat().st_mtime)
    return csvs[-1] if csvs else None


def clean_phone(phone_str: str) -> str:
    digits = "".join(c for c in (phone_str or "") if c.isdigit())
    return digits if len(digits) >= 10 else ""


def company_name(row: dict) -> str:
    rank = row.get("rank_pos", "?")
    category = row.get("category", "Unknown")
    name = row.get("name", "Unknown")[:120]
    return f"SEO | R{rank} | {category} | {name}"


def create_company(name: str, phone: str, city: str, website: str,
                    headers: dict) -> tuple[bool, str]:
    body = {
        "name": name,
        "domainName": {"primaryLinkUrl": website or ""},
        "address": {
            "addressCity": city,
            "addressState": "TX",
            "addressCountry": "US",
        },
        "phoneNumber": {
            "primaryPhoneNumber": clean_phone(phone),
            "primaryPhoneCountryCode": "US",
            "primaryPhoneCallingCode": "+1",
        },
    }
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


def fetch_existing_seo_names(headers: dict) -> set:
    """Collect names already starting with 'SEO |'.

    Uses a server-side `ilike` filter so only the handful of SEO companies
    come back — paginating the whole CRM would burn Twenty's rate limit
    (100 tokens / 60s) before any uploads start.
    """
    existing = set()
    flt = urllib.parse.quote("name[ilike]:%SEO |%")
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
                if nm.startswith("SEO |"):
                    existing.add(nm)
            if len(companies) < 100:
                break
            page += 1
            time.sleep(0.6)
        except Exception as e:
            print(f"  Warning: could not fetch existing SEO leads: {e}")
            break
    return existing


def main():
    parser = argparse.ArgumentParser(description="Upload SEO prospects to Twenty CRM")
    parser.add_argument("--csv", type=str, default="", help="CSV path (default: latest)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would upload, no writes")
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else latest_csv()
    if not csv_path or not csv_path.exists():
        print(f"[FATAL] No CSV found. Run rank_prospector.py first, or pass --csv.",
              file=sys.stderr)
        sys.exit(2)

    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"CSV: {csv_path}")
    print(f"Leads in file: {len(rows)}")
    print(f"Name format: SEO | R<rank> | <category> | <business name>")
    print("=" * 60)

    if args.dry_run:
        for r in rows[:20]:
            print(f"  {company_name(r)}")
        if len(rows) > 20:
            print(f"  ... +{len(rows) - 20} more")
        print(f"\n[DRY RUN] {len(rows)} companies would be created.")
        return

    env = load_env()
    api_key = env.get("TWENTY_API_KEY", os.environ.get("TWENTY_API_KEY", ""))
    if not api_key:
        print(f"[FATAL] TWENTY_API_KEY not found in {EXECUTION_DIR / '.env.local'}",
              file=sys.stderr)
        sys.exit(2)
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {api_key}"}

    print("Checking for existing SEO leads in Twenty...")
    existing = fetch_existing_seo_names(headers)
    print(f"  Found {len(existing)} existing 'SEO |' companies")

    new_rows = [r for r in rows if company_name(r) not in existing]
    print(f"  {len(rows) - len(new_rows)} already in Twenty, "
          f"{len(new_rows)} new to upload\n")

    success = errors = dupes = 0
    for i, r in enumerate(new_rows):
        ok, result = create_company(
            company_name(r), r.get("phone", ""), r.get("city", "Unknown"),
            r.get("website", ""), headers)
        if ok:
            success += 1
        elif "already" in str(result).lower() or "duplicate" in str(result).lower():
            dupes += 1
        else:
            errors += 1
            if errors <= 3:
                print(f"  ERROR: {result[:200]}")

        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(new_rows)} - {success} ok, "
                  f"{errors} errors, {dupes} dupes")

        # Rate limit: 0.6s = ~1.7 req/s, well under Twenty's 100 tokens/sec.
        time.sleep(0.6)
        if (i + 1) % 30 == 0:
            time.sleep(2.0)

    print("\n" + "=" * 60)
    print(f"DONE: {success} new + {len(existing)} existing = "
          f"{success + len(existing)} total 'SEO |' leads in Twenty")
    print(f"Errors: {errors}  |  Dupes: {dupes}")
    print(f"Open: http://localhost:3000/objects/companies - search 'SEO |'")


if __name__ == "__main__":
    main()
