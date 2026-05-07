#!/usr/bin/env python3
"""Upload RGV no-website leads to Twenty CRM at localhost:3000."""

import csv
import json
import os
import time
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SCRIPT_DIR = Path(__file__).parent

def _load_env() -> dict:
    """Load key=value pairs from the parent .env.local file."""
    env = {}
    env_path = SCRIPT_DIR.parent / ".env.local"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_env = _load_env()

CSV_PATH = SCRIPT_DIR / "output" / "rgv_no_website_only_2026-05-06.csv"
API_URL = "http://localhost:3000/rest/companies"
API_KEY = _env.get("TWENTY_API_KEY", os.environ.get("TWENTY_API_KEY", ""))

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}


def clean_phone(phone_str: str) -> str:
    """Return just digits, or empty if no valid phone."""
    if not phone_str:
        return ""
    digits = "".join(c for c in phone_str if c.isdigit())
    return digits if len(digits) >= 10 else ""


def create_company(name: str, phone: str, city: str, website_url: str = "") -> tuple[bool, str]:
    """Create a company in Twenty CRM. Returns (success, id_or_error)."""
    body = {
        "name": name,
        "domainName": {"primaryLinkUrl": website_url or ""},
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
        req = Request(API_URL, data=json.dumps(body).encode(), headers=HEADERS, method="POST")
        resp = urlopen(req, timeout=30)
        data = json.loads(resp.read())
        cid = data["data"]["createCompany"]["id"]
        return True, cid
    except HTTPError as e:
        err_body = e.read().decode()[:300] if e.fp else str(e)
        return False, f"HTTP {e.code}: {err_body}"


def main():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Uploading {len(rows)} leads to Twenty CRM...")
    print(f"Format: HS | [TIER] | [Category] | [Business Name]")
    print(f"{'='*60}")

    success = 0
    errors = 0
    already = 0

    # ── Skip already-uploaded leads ──────────────────────────────────────────
    print("Checking for existing HS leads...")
    existing_names = set()
    page = 1
    while True:
        req = Request(f"http://localhost:3000/rest/companies?limit=100&page={page}",
                      headers=HEADERS, method="GET")
        try:
            resp = urlopen(req, timeout=30)
            data = json.loads(resp.read())
            companies = data.get("data", {}).get("companies", [])
            if not companies:
                break
            for c in companies:
                name = c.get("name", "")
                if name.startswith("HS |"):
                    existing_names.add(name)
            page += 1
        except Exception as e:
            print(f"  Warning: could not fetch page {page}: {e}")
            break
    print(f"  Found {len(existing_names)} existing HS leads in Twenty")

    new_rows = [r for r in rows if f"HS | {r.get('tier', 'COLD')} | {r.get('category', 'Unknown')} | {r.get('name', 'Unknown')[:120]}" not in existing_names]
    print(f"  {len(rows) - len(new_rows)} already in Twenty, {len(new_rows)} new to upload\n")

    for i, r in enumerate(new_rows):
        tier = r.get("tier", "COLD")
        name_raw = r.get("name", "Unknown")[:120]
        category = r.get("category", "Unknown")
        city = r.get("city", "Unknown")
        phone = r.get("phone", "")
        website = r.get("website_url", "")

        company_name = f"HS | {tier} | {category} | {name_raw}"

        ok, result = create_company(company_name, phone, city, website)
        if ok:
            success += 1
        elif "already" in str(result).lower() or "duplicate" in str(result).lower():
            already += 1
        else:
            errors += 1
            if errors <= 3:
                print(f"  ERROR: {result[:200]}")

        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(new_rows)} — {success} ok, {errors} errors, {already} dupes")

        # Rate limit: 100 tokens per 1000ms. Each create seems to cost ~2 tokens.
        # 0.6s delay = ~1.7 req/s, well under the limit.
        time.sleep(0.6)
        # Extra cooldown every 30 requests to let token bucket refill
        if (i + 1) % 30 == 0:
            time.sleep(2.0)

    total_in_crm = len(existing_names) + success
    print(f"\n{'='*60}")
    print(f"DONE: {success} new + {len(existing_names)} existing = {total_in_crm} total in Twenty")
    print(f"Errors: {errors}  |  Dupes: {already}")
    print(f"Open: http://localhost:3000/objects/companies — search 'HS |' to see all leads")


if __name__ == "__main__":
    main()
