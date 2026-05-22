#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RGV Rank-5-to-10 SEO Prospector
================================
Finds businesses that rank MID-PAGE (positions 5-10 by default) in Google's
local results for a given industry + city. These are SEO sales prospects:
they already show up on Google but are not in the top 3, so the pitch is
"we'll move you from #7 to #1."

Engine: Google Places API text search. One `textsearch` call per
"{category} in {city} TX" query returns up to 20 places in Google's ranked
order; we slice the configured rank band and enrich each with a `details`
call (phone + website). No scraping, no CAPTCHAs.

This is the SEO-prospect counterpart to lead_gen/scraper.py — that tool finds
NO-WEBSITE businesses in the TOP 3; this one finds rank-5-10 businesses
regardless of website status.

Usage:
    python rank_prospector.py --dry-run
    python rank_prospector.py --category "plumber" --city "McAllen"   # single test
    python rank_prospector.py --city "McAllen"                        # all cats, one city
    python rank_prospector.py                                         # full RGV sweep

Flags:
    --rank-min N     first rank to keep (default 5)
    --rank-max N     last rank to keep  (default 10)
    --limit N        cap categories (testing)
    --output NAME    custom output CSV filename

Output: output/rgv_rank5to10_YYYY-MM-DD_HHMM.csv
Upload to Twenty CRM with: python upload_to_twenty.py
"""

import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
EXECUTION_DIR = SCRIPT_DIR.parent

# ── Reuse the 38 categories x 16 cities from the no-website scraper's config ────
sys.path.insert(0, str(EXECUTION_DIR / "lead_gen"))
from config import CATEGORIES, CITIES  # noqa: E402

# ── Social/directory domains — a link to one of these is NOT a real website ─────
# (mirrors lead_gen/scraper.py so the two tools classify websites the same way)
SOCIAL_DOMAINS = {
    "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "yelp.com", "tiktok.com", "youtube.com", "pinterest.com",
    "nextdoor.com", "angi.com", "thumbtack.com", "homeadvisor.com",
}

TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
DETAILS_FIELDS = "name,formatted_phone_number,formatted_address,website,rating,user_ratings_total,types"

# Places API pricing (approx, USD per 1000 calls) — used only for cost estimates
COST_TEXTSEARCH = 0.032
COST_DETAILS = 0.017

RATE_DELAY = 0.3  # seconds between Places API calls


# ── API key ─────────────────────────────────────────────────────────────────────
def load_api_key() -> str:
    """GOOGLE_PLACES_API_KEY from env, else from execution/.env.local."""
    import os
    key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if key:
        return key.strip()
    env_path = EXECUTION_DIR / ".env.local"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "GOOGLE_PLACES_API_KEY":
                    return v.strip().strip('"').strip("'")
    return ""


# ── HTTP ────────────────────────────────────────────────────────────────────────
def fetch_json(url: str, timeout: int = 25) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        return {"status": "FETCH_ERROR", "error_message": f"{type(e).__name__}: {e}"}


def textsearch(query: str, key: str) -> dict:
    url = f"{TEXTSEARCH_URL}?{urllib.parse.urlencode({'query': query, 'key': key})}"
    return fetch_json(url)


def place_details(place_id: str, key: str) -> dict:
    params = {"place_id": place_id, "fields": DETAILS_FIELDS, "key": key}
    url = f"{DETAILS_URL}?{urllib.parse.urlencode(params)}"
    return fetch_json(url)


# ── Website classification ──────────────────────────────────────────────────────
def classify_website(url: str) -> str:
    """Return 'real', 'social', or 'none'."""
    if not url:
        return "none"
    low = url.lower().replace("www.", "")
    if any(d in low for d in SOCIAL_DOMAINS):
        return "social"
    return "real"


# ── Scoring (SEO-prospect rubric) ───────────────────────────────────────────────
def score_lead(rank: int, reviews: int, rating: float, website_type: str) -> int:
    """Higher = better SEO prospect: established + close to breaking the top 3."""
    score = 0

    # Rank — closer to the top 3 = easier win
    if rank <= 6:
        score += 25
    elif rank <= 8:
        score += 15
    else:
        score += 10

    # Review count — established business that can afford SEO
    if reviews >= 100:
        score += 30
    elif reviews >= 50:
        score += 20
    elif reviews >= 20:
        score += 10

    # Rating — healthy business
    if rating >= 4.5:
        score += 10
    elif rating >= 4.0:
        score += 5

    # Already has a real website — clean SEO upsell
    if website_type == "real":
        score += 10

    return score


def lead_tier(score: int) -> str:
    if score >= 55:
        return "HOT"
    if score >= 35:
        return "WARM"
    return "COLD"


# ── Per-search pipeline ─────────────────────────────────────────────────────────
def prospect_search(category: str, city: str, key: str,
                     rank_min: int, rank_max: int) -> list[dict]:
    """Return the rank-band businesses for one category + city."""
    query = f"{category} in {city} TX"
    data = textsearch(query, key)
    time.sleep(RATE_DELAY)

    status = data.get("status")
    if status != "OK":
        if status == "ZERO_RESULTS":
            print(f"    -> 0 results")
        else:
            print(f"    -> API status: {status} ({data.get('error_message', '')})")
        return []

    results = data.get("results", [])
    leads = []

    for idx in range(rank_min - 1, rank_max):
        if idx >= len(results):
            break
        place = results[idx]
        rank = idx + 1
        place_id = place.get("place_id", "")

        detail = {}
        if place_id:
            dd = place_details(place_id, key)
            time.sleep(RATE_DELAY)
            if dd.get("status") == "OK":
                detail = dd.get("result", {})

        name = detail.get("name") or place.get("name", "")
        rating = detail.get("rating", place.get("rating", 0)) or 0
        reviews = detail.get("user_ratings_total",
                              place.get("user_ratings_total", 0)) or 0
        address = detail.get("formatted_address") or place.get("formatted_address", "")
        phone = detail.get("formatted_phone_number", "")
        website = detail.get("website", "")
        website_type = classify_website(website)

        try:
            rating = float(rating)
        except (ValueError, TypeError):
            rating = 0.0
        try:
            reviews = int(reviews)
        except (ValueError, TypeError):
            reviews = 0

        score = score_lead(rank, reviews, rating, website_type)
        leads.append({
            "tier": lead_tier(score),
            "score": score,
            "rank_pos": rank,
            "name": name,
            "category": category,
            "city": city,
            "rating": rating,
            "reviews": reviews,
            "has_website": website_type != "none",
            "website_type": website_type,
            "website": website,
            "address": address,
            "phone": phone,
            "search_query": query,
        })

    print(f"    -> {len(leads)} leads (ranks {rank_min}-{rank_max})")
    return leads


# ── Dedup ───────────────────────────────────────────────────────────────────────
def dedup_key(lead: dict) -> str:
    name = lead.get("name", "").lower().strip()
    phone = "".join(c for c in lead.get("phone", "") if c.isdigit())
    if phone:
        return f"{name}|{phone}"
    addr = " ".join(lead.get("address", "").lower().split()[:3])
    return f"{name}|{addr}"


# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="RGV Rank-5-to-10 SEO Prospector")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the search plan + cost estimate, no API calls")
    parser.add_argument("--category", type=str, help="Single category")
    parser.add_argument("--city", type=str, help="Single city")
    parser.add_argument("--rank-min", type=int, default=5, help="First rank to keep")
    parser.add_argument("--rank-max", type=int, default=10, help="Last rank to keep")
    parser.add_argument("--limit", type=int, default=0, help="Cap categories (testing)")
    parser.add_argument("--output", type=str, default="", help="Custom output CSV name")
    args = parser.parse_args()

    categories = [args.category] if args.category else list(CATEGORIES)
    cities = [args.city] if args.city else list(CITIES)
    if args.limit:
        categories = categories[:args.limit]

    band = max(0, args.rank_max - args.rank_min + 1)
    searches = len(categories) * len(cities)
    est_cost = searches * COST_TEXTSEARCH + searches * band * COST_DETAILS

    if args.dry_run:
        print("=== DRY RUN ===\n")
        print(f"Categories:      {len(categories)}")
        print(f"Cities:          {len(cities)}")
        print(f"Rank band:       {args.rank_min}-{args.rank_max} ({band} per search)")
        print(f"Text searches:   {searches}")
        print(f"Detail calls:    ~{searches * band} (max)")
        print(f"Est. cost:       ~${est_cost:.2f}")
        print(f"Est. time:       ~{searches * band * RATE_DELAY / 60:.0f} min")
        print(f"\nSample queries:")
        for c in categories[:3]:
            for city in cities[:2]:
                print(f"  -> \"{c} in {city} TX\"")
        return

    key = load_api_key()
    if not key:
        print("[FATAL] GOOGLE_PLACES_API_KEY not found in env or "
              f"{EXECUTION_DIR / '.env.local'}", file=sys.stderr)
        sys.exit(2)

    print("=" * 60)
    print("RGV RANK-5-TO-10 SEO PROSPECTOR")
    print("=" * 60)
    print(f"Categories: {len(categories)}  |  Cities: {len(cities)}  |  "
          f"Searches: {searches}  |  Est: ~${est_cost:.2f}")
    print("=" * 60 + "\n")

    seen = {}
    all_leads = []

    for ci, cat in enumerate(categories):
        print(f"[CAT {ci + 1}/{len(categories)}] {cat}")
        for city in cities:
            print(f"  {city}:")
            for lead in prospect_search(cat, city, key, args.rank_min, args.rank_max):
                k = dedup_key(lead)
                if k not in seen:
                    seen[k] = True
                    all_leads.append(lead)
        print(f"  Running total: {len(all_leads)} unique leads\n")

    all_leads.sort(key=lambda x: x["score"], reverse=True)

    # ── Output ───────────────────────────────────────────────────────────────────
    out_dir = SCRIPT_DIR / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_name = args.output or f"rgv_rank5to10_{ts}.csv"
    out_path = out_dir / out_name

    fields = ["tier", "score", "rank_pos", "name", "category", "city", "rating",
              "reviews", "has_website", "website_type", "website", "address",
              "phone", "search_query"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_leads)

    # ── Summary ──────────────────────────────────────────────────────────────────
    hot = [l for l in all_leads if l["tier"] == "HOT"]
    warm = [l for l in all_leads if l["tier"] == "WARM"]
    with_site = [l for l in all_leads if l["has_website"]]

    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total unique leads:  {len(all_leads)}")
    print(f"HOT  (score 55+):    {len(hot)}")
    print(f"WARM (score 35-54):  {len(warm)}")
    print(f"Have a website:      {len(with_site)} / {len(all_leads)}")
    print(f"\nOutput: {out_path}")

    print("\n" + "-" * 60)
    print("TOP 10 LEADS")
    print("-" * 60)
    for i, l in enumerate(all_leads[:10]):
        site = {"real": "HAS SITE", "social": "SOCIAL ONLY",
                "none": "NO WEBSITE"}[l["website_type"]]
        print(f"  {i + 1}. [{l['tier']}] {l['name']}  (rank #{l['rank_pos']})")
        print(f"     {l['category']} - {l['city']} - {l['rating']}* "
              f"({l['reviews']} reviews) - Score: {l['score']} - {site}")
        if l.get("phone"):
            print(f"     {l['phone']}")

    print(f"\nNext: python upload_to_twenty.py")


if __name__ == "__main__":
    main()
