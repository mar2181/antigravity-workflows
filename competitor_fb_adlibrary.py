#!/usr/bin/env python3
"""
competitor_fb_adlibrary.py — Scrape Facebook Ad Library for all competitors.

For each competitor with a fb_url, checks what PAID ADS they are currently running.
No login required — Ad Library is 100% public data.

What this reveals:
  - Which competitors are spending money on ads RIGHT NOW
  - What message/offer they are paying to promote
  - How long each ad has been running (longer = it's their proven winner)
  - Whether a competitor is running zero ads (opportunity: they've gone dark)

Usage:
    python competitor_fb_adlibrary.py                          # all businesses
    python competitor_fb_adlibrary.py --business island_candy  # one business
    python competitor_fb_adlibrary.py --headful                # show browser
    python competitor_fb_adlibrary.py --dry-run                # print config only

Reports saved to:
    competitor_reports/adlibrary_YYYY-MM-DD.json
    competitor_reports/adlibrary_YYYY-MM-DD.md
"""

import sys
import json
import re
import time
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent
REPORTS_DIR   = EXECUTION_DIR / "competitor_reports"
PROFILE_DIR   = EXECUTION_DIR / "facebook_sniffer_profile"  # Yehuda's saved session
REPORTS_DIR.mkdir(exist_ok=True)

# ─── Competitor Config ────────────────────────────────────────────────────────
# Mirrors competitor_facebook_monitor.py — all businesses with fb_url competitors.

COMPETITORS = {
    "sugar_shack": {
        "our_name": "The Sugar Shack",
        "competitors": [
            {"name": "Turtle Island Souvenir",
             "fb_url": "https://www.facebook.com/p/Turtle-Island-South-Padre-100085620042509/"},
        ],
    },
    "island_candy": {
        "our_name": "Island Candy",
        "competitors": [
            {"name": "KIC's Ice Cream",          "fb_url": "https://www.facebook.com/KICsIceCream/"},
            {"name": "The Baked Bear SPI",        "fb_url": "https://www.facebook.com/thebakedbearspi/"},
            {"name": "Dolce Roma",                "fb_url": "https://www.facebook.com/Frozenblue123/"},
            {"name": "Cafe Karma SPI",            "fb_url": "https://www.facebook.com/cafekarmaSPI/"},
        ],
    },
    "spi_fun_rentals": {
        "our_name": "SPI Fun Rentals",
        "competitors": [
            {"name": "Paradise Fun Rentals",     "fb_url": "https://www.facebook.com/paradisefunrentalsspi/"},
            {"name": "Coast to Coast Rentals",   "fb_url": "https://www.facebook.com/p/Coast-to-Coast-South-Padre-TX-100064982529921/"},
        ],
    },
    "juan": {
        "our_name": "Juan Elizondo RE/MAX Elite",
        "competitors": [
            {"name": "Deldi Ortegon Group",         "fb_url": "https://www.facebook.com/DeldiOrtegonGroup/"},
            {"name": "Maggie Harris Team KW",       "fb_url": "https://www.facebook.com/TeamMaggieHarris/"},
            {"name": "Jaime Lee Gonzalez",          "fb_url": "https://www.facebook.com/jaimeleegonzalez/"},
            {"name": "Coldwell Banker La Mansion",  "fb_url": "https://www.facebook.com/ColdwellBankerLaMansionRealEstate/"},
        ],
    },
    "custom_designs_tx": {
        "our_name": "Custom Designs TX",
        "competitors": [
            {"name": "D-Tronics Home and Business", "fb_url": "https://www.facebook.com/DtronicsHomeBusiness/"},
            {"name": "Mach 1 Media RGV",            "fb_url": "https://www.facebook.com/m1mtx/"},
            {"name": "Superior Alarms RGV",         "fb_url": "https://www.facebook.com/superioralarms/"},
            {"name": "RGV Geeks",                   "fb_url": "https://www.facebook.com/rgvgeeks/"},
        ],
    },
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def extract_page_id_from_url(fb_url: str) -> str | None:
    """Extract numeric page ID from profile.php?id= URLs. Returns None for slug URLs."""
    m = re.search(r"profile\.php\?id=(\d+)", fb_url)
    return m.group(1) if m else None


def extract_slug_from_url(fb_url: str) -> str | None:
    """Extract the username/slug from a Facebook URL like /KICsIceCream/ or /p/NAME-ID/"""
    # Handle /p/Name-Slug-ID/ format
    m = re.search(r"/p/[^/]+-(\d+)/?$", fb_url)
    if m:
        return m.group(1)  # numeric ID embedded in /p/ path
    # Handle /slug/ format
    m = re.search(r"facebook\.com/([^/?]+)/?$", fb_url)
    if m and m.group(1) not in ("profile.php", "p"):
        return m.group(1)
    return None


def resolve_page_id(fb_url: str, page) -> str | None:
    """
    Get the numeric Facebook page ID needed for the Ad Library URL.

    Strategy:
      1. If profile.php?id= URL → extract directly (instant)
      2. If /p/Name-12345/ URL  → extract trailing digits
      3. Otherwise → visit the page, grep HTML for numeric page ID patterns
    """
    # Strategy 1: profile.php direct
    direct = extract_page_id_from_url(fb_url)
    if direct:
        return direct

    # Strategy 2: /p/ format with trailing digits
    m = re.search(r"/p/[^/]+-(\d{10,})/?", fb_url)
    if m:
        return m.group(1)

    # Strategy 3: visit the page and grep source
    slug = extract_slug_from_url(fb_url)
    if not slug:
        return None

    try:
        page.goto(fb_url, wait_until="domcontentloaded", timeout=20000)
        content = page.content()
        # Try multiple patterns — Facebook obfuscates class names but JSON keys are stable
        for pattern in [
            # Most reliable: profile_owner block names the page being viewed
            r'"profile_owner"\s*:\s*\{"id"\s*:\s*"(\d{10,})"',
            # Fallbacks
            r'"pageID"\s*:\s*"(\d{10,})"',
            r'"entity_id"\s*:\s*"(\d{10,})"',
            r'fb://page/(\d{10,})',
            r'"page_id"\s*:\s*"(\d{10,})"',
            r'/ads/library/\?.*?page_id=(\d{10,})',
        ]:
            m = re.search(pattern, content)
            if m:
                return m.group(1)
        log(f"  Could not extract page ID from {fb_url}")
        return None
    except Exception as e:
        log(f"  Error resolving page ID for {fb_url}: {e}")
        return None


def scrape_ad_library(competitor: dict, page) -> dict:
    """
    Visit the Facebook Ad Library for one competitor and extract all active ads.
    Returns a dict with: name, fb_url, page_id, active_ad_count, ads[], no_ads, error
    """
    name   = competitor["name"]
    fb_url = competitor["fb_url"]
    result = {
        "name":            name,
        "fb_url":          fb_url,
        "page_id":         None,
        "active_ad_count": 0,
        "ads":             [],
        "no_ads":          False,
        "error":           None,
    }

    log(f"  Resolving page ID for {name}...")
    page_id = resolve_page_id(fb_url, page)
    if not page_id:
        result["error"] = "Could not resolve numeric page ID"
        log(f"  SKIP {name}: no page ID")
        return result

    result["page_id"] = page_id
    ad_lib_url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=ALL&view_all_page_id={page_id}"
    )
    log(f"  Scraping Ad Library → {ad_lib_url}")

    try:
        page.goto(ad_lib_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)  # let React render

        # Scroll to trigger lazy-load (up to 5 scrolls = ~50 ads max)
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 1200)")
            time.sleep(1.2)

        body_text = page.inner_text("body") or ""
        page_html = page.content()

        # ── No-ads detection ──────────────────────────────────────────────────
        no_ads_signals = [
            "no results found",
            "there are no ads",
            "no ads match",
            "hasn't run any ads",
            "not currently running",
            "0 ads",
        ]
        if any(s in body_text.lower() for s in no_ads_signals):
            result["no_ads"] = True
            log(f"  {name}: NO ACTIVE ADS")
            return result

        # ── Extract ads from page ─────────────────────────────────────────────
        ads = []

        # Strategy A: Look for "Started running on" text blocks in body
        # Find all "Started running on DATE" markers and work backwards
        started_pattern = re.compile(
            r"started running on\s+((?:january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\s+\d{1,2},\s+\d{4})",
            re.IGNORECASE
        )

        # Also find date ranges like "March 5, 2026"
        found_dates = [(m.start(), m.group(1)) for m in started_pattern.finditer(body_text)]

        if found_dates:
            log(f"  {name}: found {len(found_dates)} date markers in body text")
            # Split body text into ad segments using date positions
            segments = []
            for i, (pos, date_str) in enumerate(found_dates):
                # Take text from 600 chars before this date marker as the ad copy
                start = max(0, pos - 600)
                segment_text = body_text[start:pos + len(date_str) + 20]
                segments.append((segment_text, date_str))

            for seg_text, start_date in segments:
                ad = _parse_ad_segment(seg_text, start_date)
                if ad:
                    ads.append(ad)
        else:
            # Strategy B: Parse from HTML — look for ad card elements
            log(f"  {name}: no date markers in text, trying HTML selectors...")
            ads = _extract_ads_from_html(page_html)

        result["ads"]             = ads[:20]  # cap at 20 ads
        result["active_ad_count"] = len(ads)
        log(f"  {name}: {len(ads)} active ads found")

    except PWTimeout:
        result["error"] = "Timeout loading Ad Library page"
        log(f"  TIMEOUT: {name}")
    except Exception as e:
        result["error"] = str(e)[:200]
        log(f"  ERROR: {name}: {e}")

    return result


def _parse_ad_segment(text: str, start_date: str) -> dict | None:
    """Parse a single ad segment into structured data."""
    # Clean up the text
    text = re.sub(r"\s+", " ", text).strip()

    # Remove common UI chrome: page name, "Sponsored", "Like Page", button labels
    chrome = ["Like Page", "Follow", "Sponsored", "See ad details", "About", "Contact",
              "Learn More", "Shop Now", "Get Quote", "Call Now", "Book Now", "Sign Up",
              "Download", "Watch More", "Apply Now", "Contact Us", "Send Message"]
    for c in chrome:
        text = text.replace(c, " ").strip()

    text = re.sub(r"\s+", " ", text).strip()

    # Skip if remaining text is too short to be real ad copy
    if len(text) < 20:
        return None

    # Estimate days running
    days_running = _days_since(start_date)

    return {
        "copy":         text[:500],  # first 500 chars of ad copy
        "started":      start_date,
        "days_running": days_running,
        "long_runner":  days_running is not None and days_running >= 14,
    }


def _days_since(date_str: str) -> int | None:
    """Convert 'March 5, 2026' → integer days since then."""
    try:
        dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
        return (datetime.now() - dt).days
    except Exception:
        return None


def _extract_ads_from_html(html: str) -> list:
    """Fallback: try to extract any ad copy from page using HTML patterns."""
    ads = []
    # Look for spans/divs with substantial text that aren't navigation
    # Find all text blocks between 50-500 chars that look like ad copy
    text_blocks = re.findall(r'(?<=>)([A-Z][^<]{50,400})(?=<)', html)
    for block in text_blocks[:10]:
        block = re.sub(r"\s+", " ", block).strip()
        if any(skip in block for skip in ["Started running", "Ad Library", "Meta ", "About Meta"]):
            continue
        if len(block) > 50:
            ads.append({
                "copy":         block[:400],
                "started":      "unknown",
                "days_running": None,
                "long_runner":  False,
            })
    return ads


# ─── Report Generation ────────────────────────────────────────────────────────

def generate_report(all_results: dict, date_str: str):
    """Write JSON + markdown reports."""
    json_path = REPORTS_DIR / f"adlibrary_{date_str}.json"
    md_path   = REPORTS_DIR / f"adlibrary_{date_str}.md"

    # JSON raw data
    json_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"JSON saved → {json_path}")

    # Markdown report
    lines = [
        f"# Facebook Ad Library Report — {date_str}",
        "",
        "> Which competitors are running PAID ADS right now, what they say, and how long they've been running.",
        "> Long-running ads (14+ days) = proven winners — their best-performing creative.",
        "",
    ]

    # ── Headline alerts ────────────────────────────────────────────────────────
    active_advertisers = []
    dark_competitors   = []
    long_runners       = []

    for business, biz_data in all_results.items():
        for comp in biz_data["competitors"]:
            if comp.get("no_ads"):
                dark_competitors.append(f"{comp['name']} ({business})")
            elif comp.get("active_ad_count", 0) > 0:
                active_advertisers.append(f"{comp['name']} ({comp['active_ad_count']} ads)")
                for ad in comp.get("ads", []):
                    if ad.get("long_runner"):
                        long_runners.append({
                            "competitor": comp["name"],
                            "business":   business,
                            "days":       ad["days_running"],
                            "copy":       ad["copy"][:200],
                        })

    if active_advertisers:
        lines += ["## 🔴 Active Advertisers Right Now", ""]
        for a in active_advertisers:
            lines.append(f"- {a}")
        lines.append("")

    if dark_competitors:
        lines += ["## 💤 Competitors Running Zero Ads (Opportunity)", ""]
        for d in dark_competitors:
            lines.append(f"- {d} — **they've gone dark. Outspend them now.**")
        lines.append("")

    if long_runners:
        lines += ["## ⭐ Long-Running Ads (14+ Days = Proven Winners)", ""]
        for lr in long_runners:
            lines += [
                f"### {lr['competitor']} — {lr['days']} days running",
                f"> {lr['copy']}",
                "",
            ]

    # ── Per-business breakdown ─────────────────────────────────────────────────
    for business, biz_data in all_results.items():
        lines += [
            f"---",
            f"## {biz_data['our_name']}",
            "",
        ]
        for comp in biz_data["competitors"]:
            lines.append(f"### {comp['name']}")
            if comp.get("error"):
                lines.append(f"- ⚠️ Error: {comp['error']}")
            elif comp.get("no_ads"):
                lines.append("- ✅ No active paid ads — not currently spending")
            elif comp.get("active_ad_count", 0) == 0:
                lines.append("- ❓ No ads found (may be private or scrape issue)")
            else:
                lines.append(f"- **{comp['active_ad_count']} active ads** | Page ID: `{comp.get('page_id', 'unknown')}`")
                for i, ad in enumerate(comp.get("ads", [])[:5], 1):
                    days = f"{ad['days_running']} days" if ad.get("days_running") is not None else "date unknown"
                    flag = " ⭐ LONG RUNNER" if ad.get("long_runner") else ""
                    lines += [
                        f"",
                        f"**Ad #{i}** — Started {ad['started']} ({days}){flag}",
                        f"> {ad['copy'][:300]}",
                    ]
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"Report saved → {md_path}")
    return md_path


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape Facebook Ad Library for competitor paid ads")
    parser.add_argument("--business", help="Run for one business only")
    parser.add_argument("--headful",  action="store_true", help="Show browser window")
    parser.add_argument("--dry-run",  action="store_true", help="Print config, no scraping")
    args = parser.parse_args()

    businesses = (
        {args.business: COMPETITORS[args.business]}
        if args.business and args.business in COMPETITORS
        else COMPETITORS
    )

    if args.dry_run:
        total = sum(len(v["competitors"]) for v in businesses.values())
        print(f"Dry run — {len(businesses)} businesses, {total} competitors to check:")
        for biz, data in businesses.items():
            print(f"  {biz}: {[c['name'] for c in data['competitors']]}")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    headless  = not args.headful

    log(f"Facebook Ad Library scan — {date_str}")
    log(f"Businesses: {list(businesses.keys())}")

    all_results = {}

    with sync_playwright() as pw:
        # Use Yehuda's sniffer profile — needed to resolve page IDs from slug URLs.
        # The Ad Library itself is public, but visiting facebook.com/SLUG without
        # a session hits the login wall and hides the page ID in the HTML.
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.set_default_timeout(30000)

        for business, biz_data in businesses.items():
            log(f"\n{'='*50}")
            log(f"Business: {biz_data['our_name']} ({len(biz_data['competitors'])} competitors)")
            log(f"{'='*50}")

            biz_results = {
                "our_name":    biz_data["our_name"],
                "competitors": [],
            }

            for competitor in biz_data["competitors"]:
                log(f"\nChecking: {competitor['name']}")
                result = scrape_ad_library(competitor, page)
                biz_results["competitors"].append(result)
                time.sleep(2)  # polite delay between pages

            all_results[business] = biz_results

        ctx.close()

    md_path = generate_report(all_results, date_str)

    # ── Summary to console ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    total_ads     = 0
    total_dark    = 0
    total_checked = 0
    for biz, data in all_results.items():
        for c in data["competitors"]:
            total_checked += 1
            if c.get("no_ads"):
                total_dark += 1
            else:
                total_ads += c.get("active_ad_count", 0)

    print(f"Competitors checked : {total_checked}")
    print(f"Running paid ads    : {total_checked - total_dark}")
    print(f"Gone dark (0 ads)   : {total_dark}")
    print(f"Total active ads    : {total_ads}")
    print(f"\nReport: {md_path}")


if __name__ == "__main__":
    main()
