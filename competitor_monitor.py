#!/usr/bin/env python3
"""
competitor_monitor.py — Overnight competitor intelligence scraper.

For each competitor across all 8 client businesses:
  1. Searches Google Business for: rating, review count, hours
  2. Compares to last check — flags any changes (rating drops, review surges)
  3. Generates a dated morning report in competitor_reports/YYYY-MM-DD.md

Usage:
  python competitor_monitor.py                        # all businesses
  python competitor_monitor.py --business sugar_shack
  python competitor_monitor.py --business optimum_clinic
  python competitor_monitor.py --headful              # show browser (debug)
  python competitor_monitor.py --dry-run              # print config, no scraping

Reports saved to:
  C:/Users/mario/.gemini/antigravity/tools/execution/competitor_reports/

State (for change tracking) saved to:
  C:/Users/mario/.gemini/antigravity/tools/execution/competitor_reports/state.json
"""

import sys
import json
import re
import time
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent
REPORTS_DIR = EXECUTION_DIR / "competitor_reports"
STATE_FILE = REPORTS_DIR / "state.json"

# ─── Competitor Config ────────────────────────────────────────────────────────
# google_q: search string that reliably surfaces their Google Business panel
# fb_url: confirmed Facebook page URL — add as discovered, None = not yet confirmed
# note: key intel angle from program.md (shown in report for context)

COMPETITORS = {
    "sugar_shack": {
        "our_name": "The Sugar Shack (SPI)",
        "competitors": [
            {
                "name": "Sugar Kingdom",
                "google_q": "Sugar Kingdom South Padre Island TX candy",
                "phone": "+19569664444",
                "address": "1601 Padre Blvd UNIT-B, South Padre Island, TX 78597",
                "fb_url": None,  # No Facebook page
                "note": "2,500+ candy types, Disney-like decor — biggest direct competitor by volume and reviews (569+)",
            },
            {
                "name": "Sugar Planet",
                "google_q": "Sugar Planet South Padre Island TX candy",
                "fb_url": None,  # No Facebook page found
                "note": "Bulk candy at 1414 Padre Blvd — same strip, watch their pricing and promos",
            },
            {
                "name": "Turtle Island Souvenir",
                "google_q": "Turtle Island Souvenir South Padre Island TX",
                "fb_url": "https://www.facebook.com/p/Turtle-Island-South-Padre-100085620042509/",
                "note": "Souvenir-heavy with candy — we beat with candy-first positioning",
            },
        ],
    },
    "island_arcade": {
        "our_name": "Island Arcade (SPI)",
        "competitors": [
            {
                "name": "Galaxy Arcade",
                "google_q": "Galaxy Arcade South Padre Island TX",
                "fb_url": None,  # No Facebook page found
                "note": "100+ classic/modern games on Padre Blvd — direct head-to-head, watch their pricing + new games",
            },
            {
                "name": "Gravity Park",
                "google_q": "Gravity Park South Padre Island TX",
                "fb_url": "https://www.facebook.com/GravityParkSPI/",
                "note": "Outdoor mega-complex: go-karts, mini-golf, Ferris wheel, arcade, 30yr brand — we beat with indoor all-weather play",
            },
            {
                "name": "Island Fun Park",
                "google_q": "Island Fun Park South Padre Island TX go carts",
                "fb_url": "https://www.facebook.com/spiadventurepark/",  # Verify on first run
                "note": "Go-carts + mini-golf + arcade (outdoor) — we beat with arcade-only indoor focus",
            },
        ],
    },
    "island_candy": {
        "our_name": "Island Candy (SPI)",
        "competitors": [
            {
                "name": "KIC's Ice Cream",
                "google_q": "KIC's Ice Cream South Padre Island TX",
                "fb_url": "https://www.facebook.com/KICsIceCream/",
                "note": "16 Blue Bell flavors + milkshakes, standalone shop — we beat with arcade combo experience",
            },
            {
                "name": "The Baked Bear SPI",
                "google_q": "Baked Bear South Padre Island TX ice cream",
                "fb_url": "https://www.facebook.com/thebakedbearspi/",
                "note": "Custom ice cream sandwiches + baked-from-scratch cookies — we beat with classic scoops + speed",
            },
            {
                "name": "Dolce Roma",
                "google_q": "Dolce Roma South Padre Island TX gelato",
                "fb_url": "https://www.facebook.com/Frozenblue123/",
                "note": "Italian gelato, upscale/European positioning — we beat with beach-casual vibe and homemade story",
            },
            {
                "name": "Cafe Karma SPI",
                "google_q": "Cafe Karma South Padre Island TX ice cream coffee",
                "fb_url": "https://www.facebook.com/cafekarmaSPI/",
                "note": "Ice cream + coffee + breakfast all-day cafe hybrid — we beat with pure dessert/candy focus",
            },
        ],
    },
    "spi_fun_rentals": {
        "our_name": "SPI Fun Rentals",
        "competitors": [
            {
                "name": "Paradise Fun Rentals",
                "google_q": "Paradise Fun Rentals South Padre Island TX golf carts slingshots",
                "fb_url": "https://www.facebook.com/paradisefunrentalsspi/",
                "note": "4 locations, golf carts + slingshots — we beat with water sports breadth",
            },
            {
                "name": "SPI Sessions Watersports",
                "google_q": "SPI Sessions Watersports South Padre Island TX jet ski kayak",
                "fb_url": "https://www.facebook.com/SPISessions/",
                "note": "Jet skis, kayaks, SUP bayfront — we beat with full menu (jeeps + golf carts + water)",
            },
            {
                "name": "SPI Excursions",
                "google_q": "SPI Excursions South Padre Island TX parasailing jet ski tours",
                "fb_url": "https://www.facebook.com/SPIexcursions/",
                "note": "Tour-based: parasailing, banana boats, fishing — different model, watch their pricing",
            },
            {
                "name": "Coast to Coast Rentals SPI",
                "google_q": "Coast to Coast Rental South Padre Island TX golf carts water sports",
                "fb_url": "https://www.facebook.com/p/Coast-to-Coast-South-Padre-TX-100064982529921/",
                "note": "Golf carts + water sports combo — most similar to us, watch their pricing closely",
            },
        ],
    },
    "juan": {
        "our_name": "Juan Elizondo RE/MAX Elite",
        "competitors": [
            {
                "name": "Deldi Ortegon Group",
                "google_q": "Deldi Ortegon Keller Williams RGV McAllen TX real estate",
                "fb_url": "https://www.facebook.com/DeldiOrtegonGroup/",
                "note": "High-profile KW team, luxury + marketing focus, 25+ yrs — we beat with personal touch + commercial expertise",
            },
            {
                "name": "Maggie Harris Team KW",
                "google_q": "Maggie Harris Team Keller Williams McAllen TX real estate",
                "fb_url": "https://www.facebook.com/TeamMaggieHarris/",
                "note": "KW McAllen residential — we beat with Juan's dual commercial/residential expertise",
            },
            {
                "name": "Jaime Lee Gonzalez",
                "google_q": "Jaime Lee Gonzalez real estate agent McAllen TX luxury investment",
                "fb_url": "https://www.facebook.com/jaimeleegonzalez/",
                "note": "Independent luxury + investment, 90+ transactions/yr — highest volume independent in market, monitor their listings",
            },
            {
                "name": "Coldwell Banker La Mansion",
                "google_q": "Coldwell Banker La Mansion RGV McAllen TX real estate",
                "fb_url": "https://www.facebook.com/ColdwellBankerLaMansionRealEstate/",
                "note": "Coldwell Banker full residential RGV — we beat with RE/MAX national network + Juan's personal brand",
            },
            {
                "name": "CBRE McAllen",
                "google_q": "CBRE McAllen TX commercial real estate office industrial",
                "fb_url": None,
                "note": "National commercial heavyweight (office/industrial/retail) — monitor if Juan pushes commercial",
            },
            {
                "name": "RGV Realty Commercial",
                "google_q": "RGV Realty commercial real estate McAllen TX office medical warehouse",
                "fb_url": None,
                "note": "Local commercial specialist: office, medical, retail, warehouses — watch their listings",
            },
        ],
    },
    "custom_designs_tx": {
        # Services: network cabling, security alarms, cameras, audio/video, outdoor/landscape lighting
        "our_name": "Custom Designs TX (McAllen)",
        "competitors": [
            {
                "name": "D-Tronics Home and Business",
                "google_q": "D-Tronics Home Business McAllen TX AV cameras smart home",
                "fb_url": "https://www.facebook.com/DtronicsHomeBusiness/",
                "note": "30yr legacy AV + cameras + automation — we beat with modern brand and full-scope (cabling + lighting)",
            },
            {
                "name": "ABSOLUTE Services McAllen",
                "google_q": "ABSOLUTE Services security alarms cameras access control McAllen TX",
                "fb_url": None,
                "note": "Security alarms + cameras + access control + fire, founded 1998 — we beat with AV + cabling + lighting scope",
            },
            {
                "name": "Mach 1 Media RGV",
                "google_q": "Mach 1 Media AV cameras smart home McAllen Texas",
                "fb_url": "https://www.facebook.com/m1mtx/",
                "note": "AV + cameras + smart home integrator — we beat with full low-voltage scope including outdoor lighting",
            },
            {
                "name": "LexineGroup",
                "google_q": "Lexine Group network cabling surveillance fire alarms McAllen TX",
                "fb_url": None,
                "note": "Network cabling + surveillance + fire alarms — direct overlap on cabling + cameras",
            },
            {
                "name": "Superior Alarms RGV",
                "google_q": "Superior Alarms McAllen Texas security alarms",
                "fb_url": "https://www.facebook.com/superioralarms/",
                "note": "40yr alarm specialist RGV — we beat with full-service scope beyond alarms alone",
            },
            {
                "name": "RGV Geeks",
                "google_q": "RGV Geeks network cabling cameras McAllen TX",
                "fb_url": "https://www.facebook.com/rgvgeeks/",
                "note": "Network cabling + cameras — we beat with complete install ecosystem (alarms + AV + lighting)",
            },
        ],
    },
    "optimum_clinic": {
        "our_name": "Optimum Health & Wellness Clinic (Pharr)",
        "competitors": [
            {
                "name": "DOC-AID Urgent Care Pharr",
                "google_q": "DOC-AID Urgent Care Pharr TX",
                "fb_url": None,
                "note": "TEMPORARILY CLOSED (confirmed 2026-03-14) — their Pharr patients have nowhere local to go. Maximum opportunity window for Optimum Clinic ads RIGHT NOW.",
            },
            {
                "name": "Concentra Urgent Care Pharr",
                "google_q": "Concentra Urgent Care Pharr TX",
                "fb_url": None,
                "note": "Closes 6 PM, occupational health focus — easy win on hours and walk-in availability",
            },
            {
                "name": "MyCare Medical Pharr",
                "google_q": "MyCare Medical Pharr TX urgent care",
                "fb_url": None,
                "note": "Weekday-only, closes 5 PM — we win all evenings AND weekends",
            },
            {
                "name": "McAllen Family Urgent Care",
                "google_q": "McAllen Family Urgent Care TX walk-in",
                "fb_url": None,
                "note": "Open until 11 PM in McAllen — our edge is PHARR location (they have to drive), not hours vs them",
            },
            {
                "name": "CareNow Urgent Care",
                "google_q": "CareNow Urgent Care Edinburg McAllen TX",
                "fb_url": None,
                "note": "Hospital-affiliated chain — we beat with local cash pricing + no insurance bureaucracy",
            },
            {
                "name": "DHR Health Urgent Care",
                "google_q": "DHR Health Urgent Care McAllen TX",
                "fb_url": None,
                "note": "Open late (midnight+ some locations) — our angle is Pharr neighborhood + flat-rate cash pricing, NOT hours vs DHR",
            },
        ],
    },
    "optimum_foundation": {
        "our_name": "Optimum Health and Wellness Foundation (Pharr)",
        "competitors": [
            {
                "name": "Valley Baptist Legacy Foundation",
                "google_q": "Valley Baptist Legacy Foundation RGV Texas health grants scholarships",
                "fb_url": None,
                "note": "Largest grant-maker in 4-county area ($15M+ capacity) — biggest fundraising competitor, same donor pool",
            },
            {
                "name": "DHR Renaissance Cares Foundation",
                "google_q": "Renaissance Cares Foundation DHR Health RGV Texas",
                "fb_url": None,
                "note": "Hospital-backed nonprofit, cancer + general care — we differentiate with independent community-first model",
            },
            {
                "name": "United Way of South Texas",
                "google_q": "United Way South Texas Hidalgo Starr County health",
                "fb_url": None,
                "note": "Federated nonprofit, 21+ partner agencies, Hidalgo + Starr counties — overlapping donor base, watch for competing campaigns",
            },
            {
                "name": "Nuestra Clinica del Valle",
                "google_q": "Nuestra Clinica del Valle FQHC RGV Texas",
                "fb_url": None,
                "note": "FQHC direct care, 11 locations, sliding fee scale, bilingual — different model but competes for health-focused donors",
            },
            {
                "name": "Hidalgo County Health Human Services",
                "google_q": "Hidalgo County Health Human Services clinic Texas",
                "fb_url": None,
                "note": "Government public health programs — we differentiate with bilingual grassroots community approach",
            },
        ],
    },
}

# ─── State ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

# ─── Scraper ──────────────────────────────────────────────────────────────────

def scrape_google_business(page, google_q: str, debug: bool = False) -> dict:
    """
    Search Google Maps and extract business panel: rating, review count, hours.

    Uses Google Maps search URL + aria-label selectors — proven more stable than
    Google Search HTML regex (which breaks whenever Google updates its SERP layout).
    """
    result = {
        "rating": None,
        "review_count": None,
        "hours_today": None,
        "open_now": None,
        "raw_snippet": "",
    }

    try:
        # ── Strategy 1: Google Maps search (most reliable for ratings) ─────────
        maps_url = f"https://www.google.com/maps/search/{quote_plus(google_q)}/"
        page.goto(maps_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)

        # Dismiss cookie consent if present
        for btn_text in ["Accept all", "Reject all", "I agree"]:
            try:
                page.click(f"button:has-text('{btn_text}')", timeout=1500)
                time.sleep(1)
                break
            except Exception:
                pass

        # ── Rating via aria-label (e.g. aria-label="4.2 stars") ───────────────
        # Maps renders a place card with a span like: aria-label="4.2 stars"
        # Must iterate — first element is often empty (the search bar icon)
        try:
            star_els = page.query_selector_all('[aria-label*="stars"]')
            for el in star_els:
                label = el.get_attribute("aria-label") or ""
                m = re.search(r'([1-5](?:\.\d)?)\s*stars?', label, re.IGNORECASE)
                if m:
                    result["rating"] = m.group(1)
                    break
        except Exception:
            pass

        # ── Review count via aria-label (e.g. aria-label="1,234 reviews") ─────
        try:
            review_els = page.query_selector_all('[aria-label*="review"]')
            for el in review_els:
                label = el.get_attribute("aria-label") or ""
                m = re.search(r'([\d,]+)\s+reviews?', label, re.IGNORECASE)
                if m:
                    result["review_count"] = m.group(1).replace(",", "")
                    break
        except Exception:
            pass

        # ── Fallback: body text for hours + open/closed ───────────────────────
        body_text = page.inner_text("body")
        result["raw_snippet"] = body_text[:2000]

        hours_match = re.search(
            r'(Closes\s+\d+(?::\d+)?\s*(?:AM|PM)|Opens\s+\w+\s*\d+(?::\d+)?\s*(?:AM|PM)|Open\s+24\s+hours|Temporarily\s+closed)',
            body_text, re.IGNORECASE
        )
        if hours_match:
            result["hours_today"] = hours_match.group(0).strip()

        if re.search(r'\bOpen\s+now\b', body_text, re.IGNORECASE):
            result["open_now"] = True
        elif re.search(r'\bClosed\b', body_text, re.IGNORECASE):
            result["open_now"] = False

        # ── Strategy 2 fallback: Google Search if Maps gave nothing ───────────
        if not result["rating"]:
            search_url = f"https://www.google.com/search?q={quote_plus(google_q)}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)
            body_text2 = page.inner_text("body")

            # Try aria-label on search page too
            try:
                star_els2 = page.query_selector_all('[aria-label*="stars"]')
                for el in star_els2:
                    label = el.get_attribute("aria-label") or ""
                    m = re.search(r'([1-5](?:\.\d)?)\s*stars?', label, re.IGNORECASE)
                    if m:
                        result["rating"] = m.group(1)
                        break
            except Exception:
                pass

            # Regex fallback on search body text
            if not result["rating"]:
                rm = re.search(r'\b([1-5]\.[0-9])\s*(?:stars?|out of 5)', body_text2)
                if rm:
                    result["rating"] = rm.group(1)

            if not result["review_count"]:
                rvm = re.search(r'([\d,]+)\s*(?:Google\s*)?reviews?', body_text2, re.IGNORECASE)
                if rvm:
                    result["review_count"] = rvm.group(1).replace(",", "")

        if debug:
            result["raw_snippet"] = result.get("raw_snippet", "")[:3000]

    except Exception as e:
        result["error"] = str(e)

    return result

# ─── Report ───────────────────────────────────────────────────────────────────

def rating_change_emoji(old_rating, new_rating):
    if old_rating is None or new_rating is None:
        return ""
    try:
        delta = float(new_rating) - float(old_rating)
        if delta <= -0.2:
            return f" [DOWN {delta:+.1f} vs last check]"
        elif delta >= 0.2:
            return f" [UP {delta:+.1f} vs last check]"
    except Exception:
        pass
    return ""


def review_change_label(old_count, new_count):
    if old_count is None or new_count is None:
        return ""
    try:
        delta = int(new_count) - int(old_count)
        if delta > 0:
            return f" (+{delta} new)"
        elif delta < 0:
            return f" ({delta})"
    except Exception:
        pass
    return ""


def generate_report(all_results: dict, state: dict, businesses_run: list) -> str:
    now = datetime.now()
    lines = [
        f"# Competitor Intelligence Report",
        f"Date: {now.strftime('%Y-%m-%d')} | Generated: {now.strftime('%I:%M %p')}",
        "",
        "---",
        "",
    ]

    # ── Alerts section (notable changes) ──────────────────────────────────────
    alerts = []
    for biz_key, biz_results in all_results.items():
        biz_config = COMPETITORS[biz_key]
        for comp_result in biz_results:
            name = comp_result["name"]
            state_key = f"{biz_key}__{name}"
            old = state.get(state_key, {})

            new_rating = comp_result.get("rating")
            old_rating = old.get("rating")
            if new_rating and old_rating:
                try:
                    delta = float(new_rating) - float(old_rating)
                    if delta <= -0.3:
                        alerts.append(
                            f"- **{name}** ({biz_config['our_name']}): Rating dropped "
                            f"{old_rating} -> {new_rating} ({delta:+.1f}) — positioning opportunity"
                        )
                    elif delta >= 0.3:
                        alerts.append(
                            f"- **{name}** ({biz_config['our_name']}): Rating improved "
                            f"{old_rating} -> {new_rating} ({delta:+.1f}) — they may be improving"
                        )
                except Exception:
                    pass

            new_count = comp_result.get("review_count")
            old_count = old.get("review_count")
            if new_count and old_count:
                try:
                    delta = int(new_count) - int(old_count)
                    if delta >= 10:
                        alerts.append(
                            f"- **{name}**: +{delta} new reviews since last check — active customer base"
                        )
                except Exception:
                    pass

            if comp_result.get("error"):
                alerts.append(f"- **{name}**: Scrape failed — check manually")

    if alerts:
        lines.append("## Alerts (Review First)")
        lines.extend(alerts)
        lines.append("")
        lines.append("---")
        lines.append("")
    else:
        lines.append("## Alerts")
        lines.append("- No significant changes detected since last check.")
        lines.append("")
        lines.append("---")
        lines.append("")

    # ── Per-business sections ──────────────────────────────────────────────────
    for biz_key in businesses_run:
        if biz_key not in all_results:
            continue
        biz_config = COMPETITORS[biz_key]
        lines.append(f"## {biz_config['our_name']}")
        lines.append("")

        for comp_result in all_results[biz_key]:
            name = comp_result["name"]
            state_key = f"{biz_key}__{name}"
            old = state.get(state_key, {})

            # Find matching competitor config for note
            comp_config = next((c for c in biz_config["competitors"] if c["name"] == name), {})
            note = comp_config.get("note", "")

            lines.append(f"### {name}")

            if comp_result.get("error"):
                lines.append(f"- Status: Scrape failed — {comp_result['error']}")
                lines.append(f"- Note: {note}")
                lines.append("")
                continue

            rating = comp_result.get("rating", "n/a")
            review_count = comp_result.get("review_count", "n/a")
            hours_today = comp_result.get("hours_today", "n/a")

            r_change = rating_change_emoji(old.get("rating"), rating)
            rv_change = review_change_label(old.get("review_count"), review_count)

            lines.append(f"- Google Rating: {rating} stars{r_change}")
            lines.append(f"- Reviews: {review_count}{rv_change}")
            lines.append(f"- Hours today: {hours_today}")
            if comp_result.get("open_now") is True:
                lines.append(f"- Status: Open now")
            elif comp_result.get("open_now") is False:
                lines.append(f"- Status: Closed")
            lines.append(f"- Angle: {note}")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append(f"*Report generated by competitor_monitor.py — run nightly before posting sessions.*")
    return "\n".join(lines)

# ─── Main ─────────────────────────────────────────────────────────────────────

def run_monitor(businesses_to_run: list, headful: bool = False, dry_run: bool = False, debug: bool = False):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    all_results = {}

    if dry_run:
        print("\n[DRY RUN — printing config, no scraping]\n")
        for biz_key in businesses_to_run:
            biz = COMPETITORS[biz_key]
            print(f"\n{biz['our_name']}:")
            for c in biz["competitors"]:
                print(f"  - {c['name']}")
                print(f"    Google: {c['google_q']}")
        return

    print(f"\n=== Competitor Monitor ===")
    print(f"Businesses: {', '.join(businesses_to_run)}")
    print(f"Mode: {'headful' if headful else 'headless'}")
    print(f"Report dir: {REPORTS_DIR}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        for biz_key in businesses_to_run:
            biz_config = COMPETITORS[biz_key]
            print(f"\n[{biz_config['our_name']}]")
            biz_results = []

            for comp in biz_config["competitors"]:
                name = comp["name"]
                print(f"  Checking {name}...", end=" ", flush=True)

                result = scrape_google_business(page, comp["google_q"], debug=debug)
                result["name"] = name

                # Save raw snippet to debug file if --debug flag set
                if debug and result.get("raw_snippet"):
                    debug_dir = REPORTS_DIR / "debug"
                    debug_dir.mkdir(exist_ok=True)
                    safe_name = re.sub(r'[^\w]', '_', name)
                    (debug_dir / f"{safe_name}.txt").write_text(result["raw_snippet"], encoding="utf-8")

                # Update state
                state_key = f"{biz_key}__{name}"
                old = state.get(state_key, {})
                if result.get("rating"):
                    state[state_key] = {
                        "rating": result["rating"],
                        "review_count": result.get("review_count"),
                        "hours_today": result.get("hours_today"),
                        "open_now": result.get("open_now"),
                        "last_checked": datetime.now().isoformat(),
                    }

                # Log result
                if result.get("error"):
                    print(f"FAILED — {result['error']}")
                else:
                    rating = result.get("rating", "?")
                    reviews = result.get("review_count", "?")
                    hours = result.get("hours_today", "?")
                    old_rating = old.get("rating", "new")
                    change = f" [{old_rating} -> {rating}]" if old_rating != "new" and old_rating != rating else ""
                    print(f"{rating} stars ({reviews} reviews) | {hours}{change}")

                biz_results.append(result)
                time.sleep(1.5)  # be polite between requests

            all_results[biz_key] = biz_results

        browser.close()

    # Save state
    save_state(state)

    # Generate report
    report_md = generate_report(all_results, state, businesses_to_run)
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{date_str}.md"
    report_path.write_text(report_md, encoding="utf-8")

    print(f"\n=== Report saved ===")
    print(f"[{report_path}]")
    print()
    print(report_md[:1000])  # Preview first 1000 chars

# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Overnight competitor intelligence scraper — generates morning report"
    )
    parser.add_argument(
        "--business",
        choices=list(COMPETITORS.keys()),
        help="Run for one business only (default: all)",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Show browser window (useful for debugging)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print competitor config only, no scraping",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save raw page text to competitor_reports/debug/ for selector troubleshooting",
    )
    args = parser.parse_args()

    if args.business:
        businesses_to_run = [args.business]
    else:
        businesses_to_run = list(COMPETITORS.keys())

    run_monitor(businesses_to_run, headful=args.headful, dry_run=args.dry_run, debug=getattr(args, 'debug', False))


if __name__ == "__main__":
    main()
