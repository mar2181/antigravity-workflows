#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RGV Rank-5-to-10 SEO Prospector
================================
Finds businesses that rank MID-PAGE (positions 5-10 by default) in Google's
local results for a given industry + city. These are SEO / website-build sales
prospects: they already show up on Google but are not in the top 3.

Engine: Google Places API text search. One `textsearch` call per
"{category} in {city} TX" query returns up to 20 places in Google's ranked
order; we slice the configured rank band and enrich each with a `details`
call (phone + website).

Contact enrichment (default ON): for each rank-band business, the firm's own
website is fetched (home + contact/about pages) to pull email addresses and a
Facebook page link. If no Facebook is found on the site, a Bright Data Google
search is used as a fallback.

This is the SEO-prospect counterpart to lead_gen/scraper.py — that tool finds
NO-WEBSITE businesses in the TOP 3; this one finds rank-5-10 businesses
regardless of website status.

Usage:
    python rank_prospector.py --dry-run
    python rank_prospector.py --category "attorney" --city "McAllen"   # single test
    python rank_prospector.py --category "attorney" --cities "Harlingen,McAllen,Mission" --separate-by-city
    python rank_prospector.py --city "McAllen"                         # all cats, one city
    python rank_prospector.py                                          # full RGV sweep

Flags:
    --category NAME       single category (free text, e.g. "attorney")
    --city NAME           single city
    --cities "A,B,C"      comma-separated list of cities
    --separate-by-city    write one CSV per city instead of one combined file
    --no-enrich           skip the email/Facebook enrichment step
    --rank-min N          first rank to keep (default 5)
    --rank-max N          last rank to keep  (default 10)
    --limit N             cap categories (testing)
    --output NAME         custom output CSV name (combined mode only)

Output: output/<category>_<City>_YYYY-MM-DD_HHMM.csv  (per city)
        output/rgv_rank5to10_YYYY-MM-DD_HHMM.csv       (combined)
"""

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
EXECUTION_DIR = SCRIPT_DIR.parent

# ── Reuse the categories x cities config from the no-website scraper ────────────
sys.path.insert(0, str(EXECUTION_DIR / "lead_gen"))
from config import CATEGORIES, CITIES  # noqa: E402

# ── Social/directory domains — a link to one of these is NOT a real website ─────
SOCIAL_DOMAINS = {
    "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "yelp.com", "tiktok.com", "youtube.com", "pinterest.com",
    "nextdoor.com", "angi.com", "thumbtack.com", "homeadvisor.com",
}

TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
DETAILS_FIELDS = "name,formatted_phone_number,formatted_address,website,rating,user_ratings_total,types"
BRIGHTDATA_URL = "https://api.brightdata.com/request"

# Places API pricing (approx, USD per 1000 calls) — used only for cost estimates
COST_TEXTSEARCH = 0.032
COST_DETAILS = 0.017

RATE_DELAY = 0.3  # seconds between Places API calls

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

# CSV column order — kept in one place so per-city and combined output match.
FIELDS = ["tier", "score", "rank_pos", "name", "category", "city", "rating",
          "reviews", "has_website", "website_type", "website", "email",
          "facebook", "address", "phone", "search_query"]

# Pages checked for contact info, relative to the firm's domain root.
# `/contacto` is included — many RGV firms run bilingual sites.
CONTACT_PATHS = ["", "/contact", "/contact-us", "/contacto", "/about", "/about-us"]


# ── Env ─────────────────────────────────────────────────────────────────────────
def load_env_value(name: str) -> str:
    """Read a value from the environment, else from execution/.env.local."""
    v = os.environ.get(name)
    if v:
        return v.strip()
    env_path = EXECUTION_DIR / ".env.local"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, val = line.split("=", 1)
                if k.strip() == name:
                    return val.strip().strip('"').strip("'")
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


def fetch_page(url: str, timeout: int = 15) -> str:
    """GET a web page as text. Returns '' on any failure or non-HTML response."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": BROWSER_UA,
            "Accept-Encoding": "identity",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "").lower()
            if ctype and "html" not in ctype and "text" not in ctype:
                return ""
            raw = resp.read(3_000_000)  # cap at 3 MB
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def fetch_via_brightdata(url: str, bd_token: str, timeout: int = 35) -> str:
    """Fetch any URL through Bright Data Web Unlocker — bypasses Cloudflare /
    bot blocks that defeat a plain request. '' on failure or empty body."""
    if not bd_token:
        return ""
    auth = (f"Basic {base64.b64encode(bd_token.encode()).decode()}"
            if ":" in bd_token else f"Bearer {bd_token}")
    try:
        payload = json.dumps({"zone": "web_unlocker1", "url": url,
                              "format": "raw"}).encode()
        req = urllib.request.Request(
            BRIGHTDATA_URL, data=payload, method="POST",
            headers={"Authorization": auth, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
        return raw if raw and len(raw) >= 500 else ""
    except Exception:
        return ""


def fetch_serp(query: str, bd_token: str) -> str:
    """Fetch a Google SERP via Bright Data Web Unlocker. '' on failure."""
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&hl=en&gl=us"
    html = fetch_via_brightdata(url, bd_token)
    if html and "captcha" in html[:5000].lower():
        return ""
    return html


# ── Website classification ──────────────────────────────────────────────────────
def classify_website(url: str) -> str:
    """Return 'real', 'social', or 'none'."""
    if not url:
        return "none"
    low = url.lower().replace("www.", "")
    if any(d in low for d in SOCIAL_DOMAINS):
        return "social"
    return "real"


# ── Contact enrichment (email + Facebook) ───────────────────────────────────────
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
# Substrings that mark an "email" match as junk (assets, placeholders, vendors).
EMAIL_JUNK = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js", ".ico",
    "@2x", "@3x", "example.com", "example.org", "yourdomain", "domain.com",
    "email.com", "sentry", "wixpress", "wix.com", "godaddy", "squarespace",
    "schema.org", "w3.org", "googleapis", "gstatic", "cloudflare", "u003e",
    "sentry.io", "core.noscript",
)
# Facebook URL fragments that are share widgets / SDK / chrome / content URLs,
# not the firm's actual page root.
FB_BAD = (
    "sharer", "share.php", "/plugins/", "/tr?", "/tr/", "dialog/", "l.php",
    "/login", "/help", "/policy", "/policies", "/privacy", "/terms",
    "2008/fbml", "home.php", "/legal", "/products/", "/business/help",
    "/posts/", "/photos", "/videos", "/events", "/reel", "/watch",
    "/story", "/marketplace", "/groups/",
)


def extract_emails(html: str) -> list[str]:
    """Pull plausible email addresses from a page (mailto: links + body text)."""
    found = set()
    for m in re.findall(r'mailto:([^"\'<>?\s]+)', html, re.IGNORECASE):
        found.add(m.strip())
    for m in EMAIL_RE.findall(html):
        found.add(m.strip())
    clean = []
    for e in found:
        el = e.lower()
        if el.count("@") != 1 or len(e) > 64:
            continue
        if any(j in el for j in EMAIL_JUNK):
            continue
        local, _, domain = el.partition("@")
        if not local or "." not in domain:
            continue
        clean.append(el)
    return sorted(set(clean))


def extract_facebook(html: str) -> str:
    """Return the first real facebook.com page URL found, or ''."""
    for m in re.finditer(
            r'(?:https?:)?//(?:www\.|m\.|web\.)?facebook\.com/[^\s"\'<>)\\]+',
            html, re.IGNORECASE):
        raw = m.group(0)
        url = raw if raw.lower().startswith("http") else "https:" + raw
        low = url.lower()
        if any(b in low for b in FB_BAD):
            continue
        seg = low.split("facebook.com/", 1)[1].split("/")[0].split("?")[0]
        if seg == "profile.php":
            return url.split("&")[0].rstrip("/")          # keep ?id=...
        if "/pages/" in low:
            return url.split("?")[0].rstrip("/")          # facebook.com/pages/Name/123
        if not seg:
            continue
        return url.split("?")[0].rstrip("/")
    return ""


def enrich_contact(lead: dict, bd_token: str) -> None:
    """Fill lead['email'] and lead['facebook'] by scraping the firm's site.

    Contact pages are built from the site's DOMAIN ROOT — the Places `website`
    field is often a deep landing page, so appending `/contact` to it would
    404. Sites that block a plain request are retried through Bright Data.
    """
    emails: set[str] = set()
    facebook = ""
    website = lead.get("website", "")

    if website and lead.get("website_type") == "real":
        parts = urllib.parse.urlsplit(website)
        root = f"{parts.scheme}://{parts.netloc}"
        # the deep landing page first (its footer usually carries contact info),
        # then the domain root and common contact / about pages
        candidates = [website] + [root + p for p in CONTACT_PATHS]
        tried: set[str] = set()
        for url in candidates:
            key = url.rstrip("/")
            if key in tried:
                continue
            tried.add(key)
            html = fetch_page(url)
            if not html and bd_token:
                html = fetch_via_brightdata(url, bd_token)
            if not html:
                continue
            emails.update(extract_emails(html))
            if not facebook:
                facebook = extract_facebook(html)
            if emails and facebook:
                break
            time.sleep(0.25)

    # Fallback: find the Facebook page via a Google search.
    if not facebook and bd_token:
        serp = fetch_serp(f'"{lead["name"]}" {lead["city"]} TX facebook', bd_token)
        if serp:
            facebook = extract_facebook(urllib.parse.unquote(serp))
        time.sleep(0.3)

    lead["email"] = "; ".join(sorted(emails))
    lead["facebook"] = facebook


# ── Scoring (SEO-prospect rubric) ───────────────────────────────────────────────
def score_lead(rank: int, reviews: int, rating: float, website_type: str) -> int:
    """Higher = better prospect: established + close to breaking the top 3."""
    score = 0
    if rank <= 6:
        score += 25
    elif rank <= 8:
        score += 15
    else:
        score += 10
    if reviews >= 100:
        score += 30
    elif reviews >= 50:
        score += 20
    elif reviews >= 20:
        score += 10
    if rating >= 4.5:
        score += 10
    elif rating >= 4.0:
        score += 5
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
            print("    -> 0 results")
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
            "email": "",
            "facebook": "",
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


# ── Output ──────────────────────────────────────────────────────────────────────
def write_csv(out_path: Path, leads: list[dict]) -> None:
    leads.sort(key=lambda x: x["score"], reverse=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)


def print_summary(label: str, leads: list[dict], out_path: Path) -> None:
    hot = sum(1 for l in leads if l["tier"] == "HOT")
    warm = sum(1 for l in leads if l["tier"] == "WARM")
    site = sum(1 for l in leads if l["has_website"])
    email = sum(1 for l in leads if l.get("email"))
    fb = sum(1 for l in leads if l.get("facebook"))
    print(f"  {label}: {len(leads)} leads  |  HOT {hot}  WARM {warm}  |  "
          f"website {site}  email {email}  facebook {fb}")
    print(f"    -> {out_path}")


# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="RGV Rank-5-to-10 SEO Prospector")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the search plan + cost estimate, no API calls")
    parser.add_argument("--category", type=str, help="Single category (free text)")
    parser.add_argument("--city", type=str, help="Single city")
    parser.add_argument("--cities", type=str, help="Comma-separated list of cities")
    parser.add_argument("--separate-by-city", action="store_true",
                        help="Write one CSV per city instead of one combined file")
    parser.add_argument("--no-enrich", action="store_true",
                        help="Skip the email/Facebook enrichment step")
    parser.add_argument("--rank-min", type=int, default=5, help="First rank to keep")
    parser.add_argument("--rank-max", type=int, default=10, help="Last rank to keep")
    parser.add_argument("--limit", type=int, default=0, help="Cap categories (testing)")
    parser.add_argument("--output", type=str, default="",
                        help="Custom output CSV name (combined mode only)")
    args = parser.parse_args()

    categories = [args.category] if args.category else list(CATEGORIES)
    if args.limit:
        categories = categories[:args.limit]

    if args.cities:
        cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    elif args.city:
        cities = [args.city]
    else:
        cities = list(CITIES)

    enrich = not args.no_enrich
    band = max(0, args.rank_max - args.rank_min + 1)
    searches = len(categories) * len(cities)
    est_cost = searches * COST_TEXTSEARCH + searches * band * COST_DETAILS

    if args.dry_run:
        print("=== DRY RUN ===\n")
        print(f"Categories:      {len(categories)}  {categories if len(categories) <= 6 else ''}")
        print(f"Cities:          {len(cities)}  {cities}")
        print(f"Rank band:       {args.rank_min}-{args.rank_max} ({band} per search)")
        print(f"Text searches:   {searches}")
        print(f"Detail calls:    ~{searches * band} (max)")
        print(f"Contact enrich:  {'ON (website + Facebook fetch per lead)' if enrich else 'OFF'}")
        print(f"Output mode:     {'one CSV per city' if args.separate_by_city else 'one combined CSV'}")
        print(f"Est. Places cost: ~${est_cost:.2f}")
        print("\nSample queries:")
        for c in categories[:3]:
            for city in cities[:3]:
                print(f"  -> \"{c} in {city} TX\"")
        return

    key = load_env_value("GOOGLE_PLACES_API_KEY")
    if not key:
        print("[FATAL] GOOGLE_PLACES_API_KEY not found in env or "
              f"{EXECUTION_DIR / '.env.local'}", file=sys.stderr)
        sys.exit(2)
    bd_token = load_env_value("BRIGHT_DATA_KEY")  # for the Facebook search fallback

    print("=" * 60)
    print("RGV RANK-5-TO-10 SEO PROSPECTOR")
    print("=" * 60)
    print(f"Categories: {len(categories)}  |  Cities: {len(cities)}  |  "
          f"Searches: {searches}  |  Est: ~${est_cost:.2f}  |  "
          f"Enrich: {'on' if enrich else 'off'}")
    print("=" * 60 + "\n")

    # ── Scrape, city by city (dedup is scoped per city) ──────────────────────────
    leads_by_city: dict[str, list[dict]] = {}
    for city in cities:
        print(f"[CITY] {city}")
        seen: dict[str, bool] = {}
        city_leads: list[dict] = []
        for cat in categories:
            print(f"  {cat}:")
            for lead in prospect_search(cat, city, key, args.rank_min, args.rank_max):
                k = dedup_key(lead)
                if k not in seen:
                    seen[k] = True
                    city_leads.append(lead)
        leads_by_city[city] = city_leads
        print(f"  {len(city_leads)} unique leads in {city}\n")

    # ── Enrich (email + Facebook) ────────────────────────────────────────────────
    if enrich:
        total = sum(len(v) for v in leads_by_city.values())
        print(f"Enriching {total} leads — email + Facebook...")
        done = 0
        for city, leads in leads_by_city.items():
            for lead in leads:
                try:
                    enrich_contact(lead, bd_token)
                except Exception as e:
                    print(f"    [enrich error: {lead.get('name', '?')}: {e}]")
                done += 1
                print(f"  [{done}/{total}] {lead['name']}  "
                      f"email:{'Y' if lead.get('email') else '-'}  "
                      f"fb:{'Y' if lead.get('facebook') else '-'}")
        print()

    # ── Output ───────────────────────────────────────────────────────────────────
    out_dir = SCRIPT_DIR / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    cat_slug = (args.category or "leads").replace(" ", "-").lower()

    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    if args.separate_by_city:
        for city, leads in leads_by_city.items():
            fname = f"{cat_slug}_{city.replace(' ', '')}_{ts}.csv"
            out_path = out_dir / fname
            write_csv(out_path, leads)
            print_summary(city, leads, out_path)
    else:
        all_leads = [l for leads in leads_by_city.values() for l in leads]
        fname = args.output or f"rgv_rank5to10_{ts}.csv"
        out_path = out_dir / fname
        write_csv(out_path, all_leads)
        print_summary("All cities", all_leads, out_path)

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


if __name__ == "__main__":
    main()
