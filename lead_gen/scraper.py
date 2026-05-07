#!/usr/bin/env python3
"""
No-Website Business Lead Generator
──────────────────────────────────
Searches Google via Bright Data for local businesses, identifies those
without a website, scores them, and outputs a prioritized lead list.

Usage:
    python scraper.py                          # full sweep, all categories × cities
    python scraper.py --dry-run                # show what will be searched, no API calls
    python scraper.py --category "dentist"     # single category, all cities
    python scraper.py --city "McAllen"         # all categories, single city
    python scraper.py --category "plumber" --city "Mission"
    python scraper.py --limit 5               # limit categories to speed up testing
    python scraper.py --output leads.csv       # custom output filename
"""

import json
import re
import sys
import csv
import time
import html as _html_mod
import base64
import argparse
from pathlib import Path
from datetime import datetime
from urllib import request as _ureq

# ── Encoding fix for Windows ───────────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Import config ───────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from config import (
    CITIES, CATEGORIES, SCORING, QUERY_TEMPLATES,
    OUTPUT_DIR, MAX_RESULTS_PER_SEARCH, BRIGHT_DATA_DELAY,
)

# ── Bright Data setup ───────────────────────────────────────────────────────────
_TOKEN = None

def _load_token() -> str:
    """Load Bright Data key from .env.local (same pattern as keyword_rank_tracker.py)."""
    global _TOKEN
    if _TOKEN:
        return _TOKEN
    env_path = SCRIPT_DIR.parent / ".env.local"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("BRIGHT_DATA_KEY="):
                _TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                return _TOKEN
    # fallback: check os.environ
    import os
    _TOKEN = os.environ.get("BRIGHT_DATA_KEY", "")
    if _TOKEN:
        return _TOKEN
    print("[FATAL] BRIGHT_DATA_KEY not found in .env.local or environment.", file=sys.stderr)
    sys.exit(2)

_BD_URL = "https://api.brightdata.com/request"

def _bd_auth_header(token: str) -> str:
    if ":" in token:
        return f"Basic {base64.b64encode(token.encode('utf-8')).decode('utf-8')}"
    return f"Bearer {token}"

# ── HTML parsing ────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """HTML -> plain text."""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<(?:br|p|div|li|tr|h[1-6])[^>]*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = _html_mod.unescape(text)
    return '\n'.join(l for l in text.split('\n') if l.strip())

SOCIAL_DOMAINS = {
    "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "yelp.com", "tiktok.com", "youtube.com", "pinterest.com",
    "nextdoor.com", "angi.com", "thumbtack.com", "homeadvisor.com",
}

def _is_social_or_directory(url: str) -> bool:
    """Check if a URL is a social media page or directory listing (not a real website)."""
    url_lower = url.lower().replace("www.", "")
    return any(d in url_lower for d in SOCIAL_DOMAINS)

def _parse_review_count(text: str) -> int:
    """Parse review count from various Google formats: '1.3K', '516', '(1.3K)', '1,234'."""
    text = text.strip("() ")
    text = text.replace(",", "")
    if not text:
        return 0
    try:
        if text.upper().endswith("K"):
            return int(float(text[:-1]) * 1000)
        if text.upper().endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        val = int(float(text))
        # Sanity check: no business has 25M+ reviews
        if val > 10_000_000:
            return 0
        return val
    except (ValueError, TypeError):
        return 0


def _detect_website_info(html: str, container_start: int, container_end: int) -> dict:
    """
    Detect website link for a local pack result.
    Google places the website <a> tag as a SIBLING after the VkpGBb container div,
    with class 'yYlJEf'. We also check within the container for inline links.

    Returns {"has_website": bool, "website_url": str|None, "website_type": str}
    website_type: "real", "social", "none"
    """
    # Strategy 1: Look for the yYlJEf class <a> tag after the container
    # Pattern: <a class="yYlJEf Q7PwXb L48Cpd brKmxb" href="https://..." ...>...Website...</a>
    post_container = html[container_end:container_end + 3000]
    m = re.search(r'<a\b[^>]*\bclass="[^"]*\byYlJEf\b[^"]*"[^>]*href="([^"]+)"', post_container)
    if m:
        href = m.group(1)
        if _is_social_or_directory(href):
            return {"has_website": True, "website_url": href, "website_type": "social"}
        return {"has_website": True, "website_url": href, "website_type": "real"}

    # Strategy 2: Check inside the container for external links (fallback for layout changes)
    container_html = html[container_start:container_end]
    links = re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', container_html, re.DOTALL)

    for href, inner_html in links:
        if any(x in href.lower() for x in ["google.com/maps", "google.com/search",
                                              "google.com/travel", "data:",
                                              "maps.google.", "support.google",
                                              "/maps/place/", "/maps/dir/"]):
            continue
        if href.startswith(("tel:", "mailto:", "javascript:", "#")):
            continue
        if "direction" in inner_html.lower():
            continue

        visible = re.sub(r'<[^>]+>', '', inner_html).strip()
        if not visible or len(visible) < 2:
            continue

        if _is_social_or_directory(href):
            return {"has_website": True, "website_url": href, "website_type": "social"}
        return {"has_website": True, "website_url": href, "website_type": "real"}

    # Strategy 3: Look for <cite> elements containing domain URLs (organic-style results)
    cite_matches = re.findall(
        r'<cite[^>]*>https?://([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:/[^\s<>"\']*)?)',
        html[container_start:container_end + 3000]
    )
    for domain in cite_matches:
        domain_clean = domain.strip().rstrip(".)")
        if domain_clean and not any(s in domain_clean.lower() for s in ["google.com", "w3.org"]):
            if _is_social_or_directory(domain_clean):
                return {"has_website": True, "website_url": f"https://{domain_clean}", "website_type": "social"}
            return {"has_website": True, "website_url": f"https://{domain_clean}", "website_type": "real"}
    domain_pattern = re.findall(
        r'(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:/[^\s<>"\']*)?)',
        container_html
    )
    for d in domain_pattern:
        d_clean = d.strip().rstrip(".)")
        if d_clean and not any(s in d_clean.lower() for s in ["google.com", "w3.org"]):
            if _is_social_or_directory(d_clean):
                return {"has_website": True, "website_url": d_clean, "website_type": "social"}
            return {"has_website": True, "website_url": d_clean, "website_type": "real"}

    return {"has_website": False, "website_url": None, "website_type": "none"}


def _parse_local_pack(html: str) -> list[dict]:
    """
    Parse Google SERP local pack (3-pack) with accurate website detection.

    Google's HTML structure per result:
      <div class="VkpGBb">...business info (name, rating, address)...</div>
      <a class="yYlJEf..." href="https://www.business.com">Website</a>   ← sibling!
      <a href="/maps/dir/...">Directions</a>

    Returns list of business dicts.
    """
    # Find all VkpGBb container start positions
    container_starts = [m.start() for m in re.finditer(r'<div class="VkpGBb"', html)]

    entries = []
    for idx, start in enumerate(container_starts):
        # Find the end of this container (closing </div> tags)
        # The VkpGBb div ends, then an inner wrapper div ends (/div></div></div>)
        end_match = re.search(r'</div></div></div>', html[start:start + 12000])
        if not end_match:
            continue
        end = start + end_match.end()
        container_html = html[start:end]

        name = ""
        rating = ""
        reviews = 0
        address = ""
        phone = ""

        # Business name: <span class="OSrXXb">Business Name</span>
        m_name = re.search(r'class="OSrXXb[^"]*"[^>]*>([^<]+)<', container_html)
        if m_name:
            name = _html_mod.unescape(m_name.group(1)).strip()

        # Rating and reviews from aria-label
        for aria in re.findall(r'aria-label="([^"]+)"', container_html):
            m = re.search(r'Rated\s+(\d\.\d)\s+out of 5', aria, re.IGNORECASE)
            if m and not rating:
                rating = m.group(1)
            # e.g. "1.3K user reviews" or "516 user reviews"
            m = re.search(r'([\d.,]+K?)\s*user reviews?', aria, re.IGNORECASE)
            if m and not reviews:
                reviews = _parse_review_count(m.group(1))

        # Review count in visible text: <span>(1.3K)</span> or <span>(516)</span>
        if not reviews:
            rv_match = re.search(r'\((\d[\d.,]*K?)\)', container_html)
            if rv_match:
                reviews = _parse_review_count(rv_match.group(1))

        # Phone: visible text with phone pattern
        plain = _strip_html(container_html)
        phone_match = re.search(r'(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', plain)
        if phone_match:
            phone = phone_match.group(0)

        # Address: extract from container text
        # Google format: "930 E Expressway 83 · (956) 540-7825" or similar
        for line in plain.split('\n'):
            line = line.strip()
            if re.search(r'\d{1,6}\s+[A-Z]', line) and len(line) > 10:
                # Remove phone from address line
                addr_clean = re.sub(r'\s*·?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', '', line)
                addr_clean = re.sub(r'\s*·\s*.*$', '', addr_clean)  # remove category suffix
                if len(addr_clean) > 5:
                    address = addr_clean.strip()
                    break

        # Fallback: scan for address pattern in full text
        if not address:
            addr_match = re.search(
                r'(\d{1,6}\s+[A-Z][\w\s\.,]{5,60}(?:TX|Texas|McAllen|Edinburg|Mission|Pharr|Brownsville|Harlingen|Weslaco))',
                plain,
            )
            if addr_match:
                address = addr_match.group(1).strip()

        # Website detection (uses end position for sibling link scan)
        web_info = _detect_website_info(html, start, end)

        if name:
            entries.append({
                "name": name,
                "rating": rating,
                "reviews": reviews,
                "address": address,
                "phone": phone,
                "has_website": web_info["has_website"],
                "website_url": web_info["website_url"],
                "website_type": web_info["website_type"],
                "rank_pos": idx + 1,
            })

    return entries

# ── Bright Data fetch ───────────────────────────────────────────────────────────

def _fetch_serp(query: str) -> str | None:
    """Fetch Google SERP HTML for a query via Bright Data Web Unlocker."""
    token = _load_token()
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}&hl=en&gl=us"

    try:
        payload = json.dumps({
            "zone": "web_unlocker1",
            "url": url,
            "format": "raw",
        }).encode("utf-8")
        req = _ureq.Request(
            _BD_URL, data=payload,
            headers={
                "Authorization": _bd_auth_header(token),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with _ureq.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", errors="replace")

        if not raw or len(raw) < 500:
            return None
        if "unusual traffic" in raw.lower() or "captcha" in raw.lower():
            return None
        return raw
    except Exception as e:
        print(f"    [BD error: {type(e).__name__}: {e}]")
        return None

# ── Scoring ─────────────────────────────────────────────────────────────────────

def _score_lead(business: dict) -> int:
    """Score a business as a lead. Higher = better prospect."""
    score = 0

    # Rank position score (only for top 3 in a given search)
    pos = business.get("rank_pos", 10)
    score += SCORING["rank_score"].get(pos, max(0, 20 - pos * 2))

    # Review count bonus (established business)
    reviews = business.get("reviews", 0) or 0
    for threshold, bonus in SCORING["reviews_bonus"]:
        if reviews >= threshold:
            score += bonus

    # No website = primary target -> big bonus
    if not business.get("has_website"):
        score += 40

    # Social media "website" = still a lead but less urgent
    if business.get("website_type") == "social":
        score += 15

    # Has rating boost
    try:
        r = float(business.get("rating", 0) or 0)
        if r >= 4.5:
            score += 10
        elif r >= 4.0:
            score += 5
    except (ValueError, TypeError):
        pass

    return score

def _lead_tier(score: int) -> str:
    if score >= 75:
        return "HOT"
    if score >= 55:
        return "WARM"
    if score >= 35:
        return "COLD"
    return "LOW"

# ── Deduplication ───────────────────────────────────────────────────────────────

def _dedup_key(business: dict) -> str:
    """Create a stable dedup key from name + phone (or name + address)."""
    name = business.get("name", "").lower().strip()
    phone = business.get("phone", "").strip()
    if phone:
        return f"{name}|{phone}"
    addr = business.get("address", "").lower().strip()
    addr_short = " ".join(addr.split()[:3]) if addr else ""
    return f"{name}|{addr_short}"

# ── Main pipeline ───────────────────────────────────────────────────────────────

def run_search(category: str, city: str, queries: list[str] = None) -> list[dict]:
    """Run all queries for a category+city, return deduped business list."""
    if queries is None:
        queries = [t.format(category, city) for t in QUERY_TEMPLATES]

    seen = {}
    all_businesses = []

    for qi, query in enumerate(queries):
        print(f"    [{qi+1}/{len(queries)}] \"{query}\"", end=" ", flush=True)
        html = _fetch_serp(query)
        if not html:
            print("-> NO RESULT")
            continue

        results = _parse_local_pack(html)
        print(f"-> {len(results)} results")

        for b in results:
            key = _dedup_key(b)
            if key not in seen:
                seen[key] = True
                b["search_query"] = query
                b["category"] = category
                b["city"] = city
                all_businesses.append(b)

        time.sleep(BRIGHT_DATA_DELAY)

    return all_businesses


def main():
    parser = argparse.ArgumentParser(description="No-Website Business Lead Generator")
    parser.add_argument("--dry-run", action="store_true", help="Print search plan, no API calls")
    parser.add_argument("--category", type=str, help="Single category to search")
    parser.add_argument("--city", type=str, help="Single city to search")
    parser.add_argument("--limit", type=int, default=0, help="Limit categories (for testing)")
    parser.add_argument("--output", type=str, default="", help="Custom output CSV filename")
    parser.add_argument("--min-score", type=int, default=SCORING["min_score"],
                        help=f"Minimum lead score (default: {SCORING['min_score']})")
    parser.add_argument("--no-website-only", action="store_true",
                        help="Only show businesses with no website")
    parser.add_argument("--debug", action="store_true",
                        help="Save raw HTML responses for inspection")
    args = parser.parse_args()

    categories = [args.category] if args.category else CATEGORIES
    cities = [args.city] if args.city else CITIES
    if args.limit:
        categories = categories[:args.limit]

    total_searches = len(categories) * len(cities) * len(QUERY_TEMPLATES)

    if args.dry_run:
        print(f"=== DRY RUN ===\n")
        print(f"Categories: {len(categories)}")
        print(f"Cities:     {len(cities)}")
        print(f"Templates:  {len(QUERY_TEMPLATES)}")
        print(f"Total API calls: {total_searches}")
        print(f"Est. time:       {total_searches * BRIGHT_DATA_DELAY / 60:.0f} min")
        print(f"\nSample searches:")
        for c in categories[:3]:
            for city in cities[:2]:
                for t in QUERY_TEMPLATES[:1]:
                    print(f"  -> \"{t.format(c, city)}\"")
        return

    print(f"{'='*60}")
    print(f"NO-WEBSITE BUSINESS LEAD GENERATOR")
    print(f"{'='*60}")
    print(f"Categories: {len(categories)}  |  Cities: {len(cities)}  |  "
          f"Searches: {total_searches}  |  Est: ~{total_searches * BRIGHT_DATA_DELAY / 60:.0f} min")
    print(f"{'='*60}\n")

    all_leads = []

    for ci, cat in enumerate(categories):
        print(f"[CAT {ci+1}/{len(categories)}] {cat}")
        for city in cities:
            print(f"  {city}:", end="")
            results = run_search(cat, city)
            print(f"    -> {len(results)} unique businesses found")

            for b in results:
                b["score"] = _score_lead(b)
                b["tier"] = _lead_tier(b["score"])
                all_leads.append(b)

        # Progress marker
        print(f"  Running total: {len(all_leads)} leads collected\n")

    # ── Filter & sort ────────────────────────────────────────────────────────────
    if args.no_website_only:
        all_leads = [l for l in all_leads if not l["has_website"]]

    all_leads = [l for l in all_leads if l["score"] >= args.min_score]
    all_leads.sort(key=lambda x: x["score"], reverse=True)

    # ── Output ───────────────────────────────────────────────────────────────────
    out_dir = SCRIPT_DIR / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_name = args.output or f"rgv_no_website_leads_{ts}.csv"
    out_path = out_dir / out_name

    fields = ["tier", "score", "name", "category", "city", "rating", "reviews",
              "has_website", "website_type", "website_url", "address", "phone",
              "rank_pos", "search_query"]

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_leads)

    # ── Summary ──────────────────────────────────────────────────────────────────
    no_site = [l for l in all_leads if not l["has_website"]]
    social = [l for l in all_leads if l.get("website_type") == "social"]
    hot = [l for l in all_leads if l["tier"] == "HOT"]
    warm = [l for l in all_leads if l["tier"] == "WARM"]

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Total leads found:      {len(all_leads)}")
    print(f"No website at all:      {len(no_site)}  ← PRIMARY TARGETS")
    print(f"Social media only:      {len(social)}  ← upgrade to real site")
    print(f"HOT leads (score 75+):  {len(hot)}")
    print(f"WARM leads (score 55+): {len(warm)}")
    print(f"\nOutput: {out_path}")

    # Top 10 preview
    print(f"\n{'-'*60}")
    print(f"TOP 10 LEADS")
    print(f"{'-'*60}")
    for i, l in enumerate(all_leads[:10]):
        web = "NO WEBSITE" if not l["has_website"] else ("SOCIAL ONLY" if l.get("website_type") == "social" else "HAS SITE")
        print(f"  {i+1}. [{l['tier']}] {l['name']}")
        print(f"     {l['category']} • {l['city']} • {l['rating']}* ({l['reviews']} reviews) • Score: {l['score']} • {web}")
        if l.get("phone"):
            print(f"     Phone: {l['phone']}")
        if l.get("address"):
            print(f"     {l['address']}")

    print(f"\nDone. Full list -> {out_path}")


if __name__ == "__main__":
    main()
