#!/usr/bin/env python3
"""Upload lead CSV to Supabase hs_solutions_leads table."""

import csv
import os
from pathlib import Path
from supabase import create_client

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
SUPABASE_URL = "https://svgsbaahxiaeljmfykzp.supabase.co"
SUPABASE_KEY = _env.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Read {len(rows)} leads from CSV")

    # Batch insert in chunks of 50
    batch_size = 50
    inserted = 0
    errors = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        records = []
        for r in batch:
            records.append({
                "tier": r.get("tier", "COLD"),
                "score": int(r.get("score", 0)),
                "name": r.get("name", "Unknown")[:255],
                "category": r.get("category", "Unknown"),
                "city": r.get("city", "Unknown"),
                "rating": float(r["rating"]) if r.get("rating") and r["rating"] != "" else None,
                "reviews": int(r.get("reviews", 0)),
                "has_website": r.get("has_website", "False").lower() == "true",
                "website_type": r.get("website_type") or None,
                "website_url": r.get("website_url") or None,
                "address": r.get("address") or None,
                "phone": r.get("phone") or None,
                "rank_pos": int(r["rank_pos"]) if r.get("rank_pos") and r["rank_pos"] != "" else None,
                "search_query": r.get("search_query") or None,
            })

        try:
            result = supabase.table("hs_solutions_leads").insert(records).execute()
            inserted += len(result.data)
            print(f"  Batch {i//batch_size + 1}: {len(result.data)} rows inserted ({inserted}/{len(rows)})")
        except Exception as e:
            print(f"  Batch {i//batch_size + 1} ERROR: {e}")
            errors += len(records)

    print(f"\nDone! {inserted} inserted, {errors} errors")

    # Verify
    count = supabase.table("hs_solutions_leads").select("*", count="exact").execute()
    print(f"Total rows in table: {count.count}")

if __name__ == "__main__":
    main()
