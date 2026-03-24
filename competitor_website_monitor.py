#!/usr/bin/env python3
"""
competitor_website_monitor.py — Daily website change detector for all client competitors.

For each competitor, visits their website, extracts visible text, and diffs it against
yesterday's snapshot. Flags meaningful changes: new prices, offers, hours, promos.

Usage:
  python competitor_website_monitor.py                        # all businesses
  python competitor_website_monitor.py --business sugar_shack
  python competitor_website_monitor.py --business optimum_clinic
  python competitor_website_monitor.py --headful              # show browser
  python competitor_website_monitor.py --dry-run              # print URLs, no scraping

State saved to:
  competitor_reports/website_state.json

Reports appended to the daily competitor_reports/YYYY-MM-DD_website.md
"""

import sys
import json
import re
import time
import hashlib
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
WEBSITE_STATE_FILE = REPORTS_DIR / "website_state.json"

# ─── Competitor Website Config ────────────────────────────────────────────────
# url: competitor's primary website (None = auto-discover via Google on first run)
# pages: list of paths to check beyond homepage (e.g. /menu, /pricing, /specials)
# keywords: extra terms to flag in diffs for this competitor type

COMPETITOR_WEBSITES = {
    "sugar_shack": {
        "our_name": "The Sugar Shack (SPI)",
        "competitors": [
            {
                "name": "Sugar Kingdom",
                "url": None,  # no website — Facebook/Google only
                "google_q": "Sugar Kingdom South Padre Island TX candy store website",
                "pages": ["/"],
                "keywords": ["sale", "special", "deal", "% off", "new arrival", "spring", "summer"],
            },
            {
                "name": "Davey Jones Ice Cream Locker",
                "url": "http://www.daveyjonesicecreamlocker.com",
                "google_q": "Davey Jones Ice Cream Locker South Padre Island TX website",
                "pages": ["/"],
                "keywords": ["special", "new", "flavor", "seasonal"],
            },
            {
                "name": "Turtle Island Souvenir",
                "url": None,  # no website — Facebook/Google only
                "google_q": "Turtle Island Souvenir South Padre Island TX website",
                "pages": ["/"],
                "keywords": ["sale", "special", "new"],
            },
        ],
    },
    "island_arcade": {
        "our_name": "Island Arcade (SPI)",
        "competitors": [
            {
                "name": "Galaxy Arcade",
                "url": "https://www.thegalaxyarcade.com",
                "google_q": "Galaxy Arcade South Padre Island TX website",
                "pages": ["/"],
                "keywords": ["special", "deal", "new", "event", "party", "price", "admission"],
            },
            {
                "name": "Gravity Park",
                "url": "https://gravitypark.com",
                "google_q": "Gravity Park South Padre Island TX website",
                "pages": ["/", "/attractions", "/prices"],
                "keywords": ["price", "admission", "special", "deal", "new", "opening", "closed", "season"],
            },
            {
                "name": "Island Fun Park",
                "url": "https://www.islandfunpark.com",
                "google_q": "Island Fun Park South Padre Island TX go carts website",
                "pages": ["/"],
                "keywords": ["price", "special", "new", "deal", "admission", "hours"],
            },
        ],
    },
    "island_candy": {
        "our_name": "Island Candy (SPI)",
        "competitors": [
            {
                "name": "KIC's Ice Cream",
                "url": "https://www.kicsicecream.com",
                "google_q": "KIC's Ice Cream South Padre Island TX website",
                "pages": ["/"],
                "keywords": ["flavor", "special", "new", "seasonal", "price"],
            },
            {
                "name": "The Baked Bear SPI",
                "url": "https://thebakedbear.com",
                "google_q": "Baked Bear South Padre Island TX website",
                "pages": ["/", "/menu"],
                "keywords": ["flavor", "special", "new", "limited", "seasonal", "price"],
            },
            {
                "name": "Dolce Roma",
                "url": None,  # no website — Facebook/Google only
                "google_q": "Dolce Roma South Padre Island TX gelato website",
                "pages": ["/"],
                "keywords": ["flavor", "special", "new", "seasonal", "price"],
            },
            {
                "name": "Cafe Karma SPI",
                "url": None,  # no website — Facebook only
                "google_q": "Cafe Karma South Padre Island TX ice cream coffee website",
                "pages": ["/"],
                "keywords": ["special", "new", "flavor", "seasonal", "hours", "brunch"],
            },
        ],
    },
    "spi_fun_rentals": {
        "our_name": "SPI Fun Rentals",
        "competitors": [
            {
                "name": "Paradise Fun Rentals",
                "url": "https://www.paradisefunrentals.com",
                "google_q": "Paradise Fun Rentals South Padre Island TX website golf cart slingshot",
                "pages": ["/", "/rates", "/pricing"],
                "keywords": ["price", "rate", "special", "deal", "$", "per day", "per hour"],
            },
            {
                "name": "SPI Sessions Watersports",
                "url": "https://www.spisessionswatersports.com",
                "google_q": "SPI Sessions Watersports South Padre Island TX website jet ski kayak",
                "pages": ["/", "/rates", "/pricing"],
                "keywords": ["price", "rate", "special", "$", "per hour", "deal", "package"],
            },
            {
                "name": "SPI Excursions",
                "url": "https://spiexcursions.com",
                "google_q": "SPI Excursions South Padre Island TX website parasailing tours",
                "pages": ["/", "/tours", "/pricing"],
                "keywords": ["price", "rate", "special", "$", "deal", "package", "season"],
            },
            {
                "name": "Coast to Coast Rentals SPI",
                "url": "https://coasttocoastrental.com",
                "google_q": "Coast to Coast Rental South Padre Island TX website",
                "pages": ["/", "/rates"],
                "keywords": ["price", "rate", "special", "$", "per day", "deal"],
            },
        ],
    },
    "juan": {
        "our_name": "Juan Elizondo RE/MAX Elite",
        "competitors": [
            {
                "name": "Deldi Ortegon Group",
                "url": "https://www.deldiortegon.com",
                "google_q": "Deldi Ortegon Keller Williams RGV website",
                "pages": ["/", "/listings", "/blog"],
                "keywords": ["new listing", "price reduced", "sold", "open house", "market update"],
            },
            {
                "name": "Maggie Harris Team KW",
                "url": "https://www.maggieharristeam.com",
                "google_q": "Maggie Harris Team Keller Williams McAllen TX website real estate",
                "pages": ["/", "/listings"],
                "keywords": ["new listing", "price reduced", "sold", "open house"],
            },
            {
                "name": "Jaime Lee Gonzalez",
                "url": "https://www.jaimeleegonzalez.com",
                "google_q": "Jaime Lee Gonzalez real estate McAllen TX website luxury investment",
                "pages": ["/", "/listings"],
                "keywords": ["new listing", "price reduced", "sold", "commercial", "investment"],
            },
            {
                "name": "Coldwell Banker La Mansion",
                "url": "https://www.cblamansion.com",
                "google_q": "Coldwell Banker La Mansion RGV McAllen TX real estate website",
                "pages": ["/", "/listings"],
                "keywords": ["new listing", "price reduced", "sold", "open house", "market"],
            },
            {
                "name": "CBRE McAllen",
                "url": "https://www.cbre.com/real-estate-services/real-estate-for-locations/united-states/texas/mcallen",
                "google_q": "CBRE McAllen TX commercial real estate website",
                "pages": ["/"],
                "keywords": ["new listing", "for lease", "for sale", "price reduced", "commercial", "industrial", "office"],
            },
            {
                "name": "RGV Realty Commercial",
                "url": "https://www.rgv-realty.com",
                "google_q": "RGV Realty commercial real estate McAllen TX website",
                "pages": ["/", "/listings"],
                "keywords": ["new listing", "for lease", "for sale", "price reduced", "commercial", "warehouse"],
            },
        ],
    },
    "custom_designs_tx": {
        # Services: network cabling, security alarms, cameras, audio/video, outdoor/landscape lighting
        "our_name": "Custom Designs TX (McAllen)",
        "competitors": [
            {
                "name": "D-Tronics Home and Business",
                "url": "https://dtronicshomeandbusiness.com",
                "google_q": "D-Tronics Home Business McAllen TX AV cameras automation website",
                "pages": ["/", "/services"],
                "keywords": ["price", "special", "new", "promotion", "sale", "package", "offer"],
            },
            {
                "name": "ABSOLUTE Services McAllen",
                "url": "https://absolutemcallen.com",
                "google_q": "ABSOLUTE Services security alarms cameras McAllen TX website",
                "pages": ["/", "/services"],
                "keywords": ["price", "special", "new", "promotion", "sale", "package", "offer", "free"],
            },
            {
                "name": "Mach 1 Media RGV",
                "url": "https://m1mtx.com",
                "google_q": "Mach 1 Media AV cameras smart home McAllen Texas website",
                "pages": ["/", "/services", "/pricing"],
                "keywords": ["price", "special", "new", "promotion", "sale", "package"],
            },
            {
                "name": "LexineGroup",
                "url": "https://lexinegroup.com",
                "google_q": "Lexine Group network cabling surveillance alarms McAllen TX website",
                "pages": ["/", "/services"],
                "keywords": ["price", "special", "new", "promotion", "sale", "package", "offer"],
            },
            {
                "name": "Superior Alarms RGV",
                "url": "https://superioralarms.com",
                "google_q": "Superior Alarms McAllen Texas security website",
                "pages": ["/", "/services"],
                "keywords": ["price", "special", "new", "promotion", "sale", "package", "free", "monitor"],
            },
            {
                "name": "RGV Geeks",
                "url": "https://rgvgeeks.com",
                "google_q": "RGV Geeks network cabling cameras McAllen TX website",
                "pages": ["/", "/services"],
                "keywords": ["price", "special", "new", "promotion", "sale", "offer"],
            },
        ],
    },
    "optimum_clinic": {
        "our_name": "Optimum Health & Wellness Clinic (Pharr)",
        "competitors": [
            {
                "name": "DOC-AID Urgent Care Pharr",
                "url": "https://doc-aid.com",
                "google_q": "DOC-AID Urgent Care Pharr TX website",
                "pages": ["/", "/services", "/hours"],
                "keywords": ["hours", "open", "extended", "price", "$", "cash", "special", "new service"],
            },
            {
                "name": "Concentra Urgent Care Pharr",
                "url": "https://www.concentra.com",
                "google_q": "Concentra Urgent Care Pharr TX website",
                "pages": ["/"],
                "keywords": ["hours", "open", "price", "$", "cash", "special", "new location", "extended"],
            },
            {
                "name": "MyCare Medical Pharr",
                "url": "https://www.mycaremedicalgroup.com",
                "google_q": "MyCare Medical Pharr TX urgent care website",
                "pages": ["/", "/services"],
                "keywords": ["hours", "open", "price", "$", "cash", "special", "new service", "weekend"],
            },
            {
                "name": "McAllen Family Urgent Care",
                "url": "https://www.mcallenfamilyurgentcare.com",
                "google_q": "McAllen Family Urgent Care TX walk-in website",
                "pages": ["/", "/services", "/pricing"],
                "keywords": ["hours", "open", "price", "$", "cash", "special", "new location", "new service"],
            },
            {
                "name": "CareNow Urgent Care",
                "url": "https://www.carenow.com",
                "google_q": "CareNow Urgent Care Edinburg McAllen TX website",
                "pages": ["/", "/locations"],
                "keywords": ["hours", "open", "price", "$", "special", "new location", "cash"],
            },
            {
                "name": "DHR Health Urgent Care",
                "url": "https://www.dhr-rgv.com",
                "google_q": "DHR Health Urgent Care McAllen TX website",
                "pages": ["/", "/urgent-care"],
                "keywords": ["hours", "open", "price", "$", "special", "new location", "extended", "cash"],
            },
        ],
    },
    "optimum_foundation": {
        "our_name": "Optimum Health and Wellness Foundation",
        "competitors": [
            {
                "name": "Valley Baptist Legacy Foundation",
                "url": "https://www.vblf.org",
                "google_q": "Valley Baptist Legacy Foundation RGV Texas health grants website",
                "pages": ["/", "/programs", "/events"],
                "keywords": ["new program", "event", "grant", "donation", "fundraiser", "campaign", "scholarship"],
            },
            {
                "name": "DHR Renaissance Cares Foundation",
                "url": "https://www.dhrhealth.com/renaissance-cares-foundation",
                "google_q": "Renaissance Cares Foundation DHR Health RGV Texas website",
                "pages": ["/"],
                "keywords": ["new program", "event", "grant", "donation", "fundraiser", "campaign"],
            },
            {
                "name": "United Way of South Texas",
                "url": "https://unitedwayofsotx.org",
                "google_q": "United Way South Texas Hidalgo Starr County website",
                "pages": ["/", "/programs", "/events"],
                "keywords": ["new program", "event", "campaign", "donation", "fundraiser", "grant", "health"],
            },
            {
                "name": "Nuestra Clinica del Valle",
                "url": "https://nuestraclinica.org",
                "google_q": "Nuestra Clinica del Valle FQHC RGV Texas website",
                "pages": ["/", "/programs", "/services"],
                "keywords": ["new program", "new clinic", "event", "donation", "health", "grant", "expansion"],
            },
            {
                "name": "Hidalgo County Health Human Services",
                "url": "https://www.hidalgocounty.us/health",
                "google_q": "Hidalgo County Health Human Services clinic Texas website",
                "pages": ["/"],
                "keywords": ["new clinic", "new service", "hours", "program", "event", "health"],
            },
        ],
    },
}

# Keywords that signal a meaningful change worth flagging
PROMO_KEYWORDS = [
    "sale", "special", "deal", "% off", "discount", "promo", "promotion",
    "limited time", "offer", "coupon", "free", "new", "now open", "extended hours",
    "price", "reduced", "markdown",
]

HOURS_PATTERN = re.compile(
    r'\b(\d{1,2}(?::\d{2})?\s*(?:AM|PM)\s*[-–]\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM))',
    re.IGNORECASE
)

PRICE_PATTERN = re.compile(r'\$\s*\d+(?:\.\d{2})?')


# ─── State ────────────────────────────────────────────────────────────────────

def load_website_state() -> dict:
    if WEBSITE_STATE_FILE.exists():
        try:
            return json.loads(WEBSITE_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_website_state(state: dict):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    WEBSITE_STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ─── URL Discovery ────────────────────────────────────────────────────────────

def discover_website_url(page, google_q: str) -> str | None:
    """Use Google Search to find the competitor's primary website URL."""
    try:
        url = f"https://www.google.com/search?q={quote_plus(google_q)}"
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)

        # Look for the first non-Google result link
        links = page.query_selector_all("a[href]")
        for link in links:
            href = link.get_attribute("href") or ""
            if href.startswith("http") and "google.com" not in href and "youtube.com" not in href:
                # Clean tracking parameters
                clean = href.split("&")[0].split("?utm")[0]
                if any(ext in clean for ext in [".com", ".org", ".net", ".io"]):
                    return clean
    except Exception:
        pass
    return None


# ─── Page Scraper ─────────────────────────────────────────────────────────────

def clean_page_text(raw: str) -> str:
    """Strip excess whitespace and boilerplate noise from extracted page text."""
    lines = raw.splitlines()
    seen = set()
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if line in seen:
            continue
        # Skip common nav/footer boilerplate
        if re.match(r'^(home|about|contact|menu|privacy|terms|cookie|©|\|)$', line, re.IGNORECASE):
            continue
        seen.add(line)
        cleaned.append(line)
    return "\n".join(cleaned)


def scrape_page(page, url: str) -> str | None:
    """Visit a URL and return cleaned visible text. Returns None on failure."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)

        # Dismiss cookie banners
        for btn_text in ["Accept all", "Accept", "I agree", "Got it", "OK"]:
            try:
                page.click(f"button:has-text('{btn_text}')", timeout=1000)
                time.sleep(0.5)
                break
            except Exception:
                pass

        raw = page.inner_text("body")
        return clean_page_text(raw)
    except Exception as e:
        return None


# ─── Change Detection ─────────────────────────────────────────────────────────

def content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def extract_meaningful_changes(old_text: str, new_text: str, keywords: list) -> list[str]:
    """
    Diff old vs new page text. Return lines that are new AND contain
    price/promo/hours signals. Limits output to 10 most relevant lines.
    """
    old_lines = set(old_text.splitlines())
    new_lines = new_text.splitlines()

    added = [line for line in new_lines if line not in old_lines and len(line) > 8]

    flagged = []
    all_keywords = PROMO_KEYWORDS + [k.lower() for k in keywords]

    for line in added:
        line_lower = line.lower()
        has_keyword = any(kw in line_lower for kw in all_keywords)
        has_price = bool(PRICE_PATTERN.search(line))
        has_hours = bool(HOURS_PATTERN.search(line))
        if has_keyword or has_price or has_hours:
            flagged.append(line[:200])  # cap line length

    return flagged[:10]


# ─── Main Scrape Loop ─────────────────────────────────────────────────────────

def run_website_monitor(businesses_to_run: list, headful: bool = False, dry_run: bool = False) -> dict:
    """
    Returns dict: { biz_key: [ { name, url, status, changes, is_first_run } ] }
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    state = load_website_state()
    all_results = {}

    if dry_run:
        print("\n[DRY RUN — website monitor config]\n")
        for biz_key in businesses_to_run:
            biz = COMPETITOR_WEBSITES[biz_key]
            print(f"\n{biz['our_name']}:")
            for c in biz["competitors"]:
                url = state.get(f"{biz_key}__{c['name']}", {}).get("url") or c.get("url") or "(discover on first run)"
                print(f"  - {c['name']}: {url}")
        return {}

    print(f"\n=== Website Change Monitor ===")
    print(f"Businesses: {', '.join(businesses_to_run)}")
    print(f"Mode: {'headful' if headful else 'headless'}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        for biz_key in businesses_to_run:
            biz_config = COMPETITOR_WEBSITES[biz_key]
            print(f"\n[{biz_config['our_name']}]")
            biz_results = []

            for comp in biz_config["competitors"]:
                name = comp["name"]
                state_key = f"{biz_key}__{name}"
                saved = state.get(state_key, {})

                # Resolve URL: saved → config → discover
                url = saved.get("url") or comp.get("url")
                if not url:
                    print(f"  {name}: discovering URL...", end=" ", flush=True)
                    url = discover_website_url(page, comp["google_q"])
                    if url:
                        print(f"found {url[:60]}")
                    else:
                        print("not found — skipping")
                        biz_results.append({"name": name, "url": None, "status": "url_not_found", "changes": []})
                        continue

                print(f"  {name} [{url[:50]}]...", end=" ", flush=True)

                # Scrape all configured pages, combine text
                combined_text = ""
                for path in comp.get("pages", ["/"]):
                    page_url = url.rstrip("/") + path if path != "/" else url
                    text = scrape_page(page, page_url)
                    if text:
                        combined_text += f"\n--- {path} ---\n{text}"
                    time.sleep(1)

                if not combined_text.strip():
                    print("scrape failed")
                    biz_results.append({"name": name, "url": url, "status": "scrape_failed", "changes": []})
                    continue

                new_hash = content_hash(combined_text)
                old_hash = saved.get("hash")
                old_text = saved.get("text", "")
                is_first_run = not old_hash

                if is_first_run:
                    print("first run — baseline saved")
                    status = "baseline"
                    changes = []
                elif new_hash == old_hash:
                    print("no change")
                    status = "no_change"
                    changes = []
                else:
                    changes = extract_meaningful_changes(old_text, combined_text, comp.get("keywords", []))
                    if changes:
                        print(f"CHANGED — {len(changes)} flagged lines")
                        status = "changed"
                    else:
                        print("minor change (no promo signals)")
                        status = "minor_change"

                # Save updated state
                state[state_key] = {
                    "url": url,
                    "hash": new_hash,
                    "text": combined_text[:50000],  # cap stored text at 50k chars
                    "last_checked": datetime.now().isoformat(),
                    "last_status": status,
                }

                biz_results.append({
                    "name": name,
                    "url": url,
                    "status": status,
                    "changes": changes,
                    "is_first_run": is_first_run,
                })

                time.sleep(2)

            all_results[biz_key] = biz_results

        browser.close()

    save_website_state(state)
    return all_results


# ─── Report ───────────────────────────────────────────────────────────────────

def generate_website_report(all_results: dict, businesses_run: list) -> str:
    now = datetime.now()
    lines = [
        f"# Website Change Report",
        f"Date: {now.strftime('%Y-%m-%d')} | Generated: {now.strftime('%I:%M %p')}",
        "",
        "---",
        "",
    ]

    # Alerts first
    alerts = []
    for biz_key, biz_results in all_results.items():
        for r in biz_results:
            if r["status"] == "changed" and r["changes"]:
                biz_name = COMPETITOR_WEBSITES[biz_key]["our_name"]
                alerts.append(f"- **{r['name']}** ({biz_name}): {len(r['changes'])} new promo/price lines detected")

    if alerts:
        lines.append("## Website Alerts")
        lines.extend(alerts)
    else:
        lines.append("## Website Alerts")
        lines.append("- No significant website changes detected.")
    lines += ["", "---", ""]

    # Per-business
    for biz_key in businesses_run:
        if biz_key not in all_results:
            continue
        biz_config = COMPETITOR_WEBSITES[biz_key]
        lines.append(f"## {biz_config['our_name']}")
        lines.append("")

        for r in all_results[biz_key]:
            name = r["name"]
            url = r.get("url", "unknown")
            status = r.get("status", "unknown")

            status_icon = {
                "changed": "⚠️ CHANGED",
                "minor_change": "🔄 Minor change",
                "no_change": "✅ No change",
                "baseline": "📋 Baseline saved",
                "scrape_failed": "❌ Scrape failed",
                "url_not_found": "❓ URL not found",
            }.get(status, status)

            lines.append(f"### {name}")
            lines.append(f"- Site: {url}")
            lines.append(f"- Status: {status_icon}")

            if r.get("changes"):
                lines.append(f"- New lines detected:")
                for change in r["changes"]:
                    lines.append(f'  > "{change}"')

            lines.append("")

        lines += ["---", ""]

    lines.append("*Report generated by competitor_website_monitor.py*")
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Daily competitor website change detector"
    )
    parser.add_argument(
        "--business",
        choices=list(COMPETITOR_WEBSITES.keys()),
        help="Run for one business only (default: all)",
    )
    parser.add_argument("--headful", action="store_true", help="Show browser window")
    parser.add_argument("--dry-run", action="store_true", help="Print config only, no scraping")
    args = parser.parse_args()

    businesses_to_run = [args.business] if args.business else list(COMPETITOR_WEBSITES.keys())

    all_results = run_website_monitor(businesses_to_run, headful=args.headful, dry_run=args.dry_run)

    if not all_results:
        return

    report_md = generate_website_report(all_results, businesses_to_run)
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{date_str}_website.md"
    report_path.write_text(report_md, encoding="utf-8")

    print(f"\n=== Website Report saved ===")
    print(f"Path: {report_path}")
    print()
    print(report_md[:1200])


if __name__ == "__main__":
    main()
