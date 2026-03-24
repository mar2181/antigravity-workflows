#!/usr/bin/env python3
"""
competitor_review_miner.py — Mine Google Review TEXT for all competitors.

Visits Google Maps for each competitor, scrapes the most recent/helpful reviews,
then runs AI analysis to extract:
  - Top complaints (their weakness = your ad angle)
  - Top praise (what customers love — match or beat it)
  - Gaps (what customers never mention = your differentiator opportunity)
  - 2 ready-to-use ad copy angles derived from review sentiment

This is one of the highest-value intel sources: customers tell you exactly
what matters to them, in their own words.

Usage:
    python competitor_review_miner.py                          # all businesses
    python competitor_review_miner.py --business island_candy  # one business
    python competitor_review_miner.py --headful                # show browser
    python competitor_review_miner.py --no-ai                  # scrape only, skip AI
    python competitor_review_miner.py --dry-run                # print config only

Output:
    competitor_reports/reviews_YYYY-MM-DD.json
    competitor_reports/reviews_YYYY-MM-DD.md
"""

import sys
import json
import re
import os
import time
import urllib.request
import urllib.parse
import argparse
from pathlib import Path
from datetime import date, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent
REPORTS_DIR   = EXECUTION_DIR / "competitor_reports"
SCRATCH_DIR   = EXECUTION_DIR.parent.parent / "scratch"
ENV_PATH      = SCRATCH_DIR / "gravity-claw" / ".env"
REPORTS_DIR.mkdir(exist_ok=True)

OPENROUTER_MODEL = "openai/gpt-4o-mini"

# ─── Competitor Config ────────────────────────────────────────────────────────
# Google search terms to find each competitor's Maps listing.
# Uses name + city as search query — more reliable than hardcoded URLs.

COMPETITORS = {
    "sugar_shack": {
        "our_name": "The Sugar Shack",
        "our_edge": "Largest candy selection on South Padre Island, Instagram-worthy, novelty experience",
        "competitors": [
            {"name": "Sugar Kingdom SPI",      "search": "Sugar Kingdom South Padre Island candy"},
            {"name": "Turtle Island Souvenir", "search": "Turtle Island Souvenir South Padre Island"},
        ],
    },
    "island_candy": {
        "our_name": "Island Candy",
        "our_edge": "Ice cream + sweets inside Island Arcade, Dole Whip specialty, unique location",
        "competitors": [
            {"name": "KIC's Ice Cream",      "search": "KIC's Ice Cream South Padre Island"},
            {"name": "The Baked Bear SPI",   "search": "Baked Bear South Padre Island ice cream"},
            {"name": "Dolce Roma SPI",       "search": "Dolce Roma South Padre Island gelato"},
            {"name": "Cafe Karma SPI",       "search": "Cafe Karma South Padre Island"},
        ],
    },
    "spi_fun_rentals": {
        "our_name": "SPI Fun Rentals",
        "our_edge": "Widest menu of water activities (jet skis, kayaks, paddleboards, more) in one place",
        "competitors": [
            {"name": "Paradise Fun Rentals",      "search": "Paradise Fun Rentals South Padre Island"},
            {"name": "Coast to Coast Rentals SPI","search": "Coast to Coast Rentals South Padre Island"},
            {"name": "SPI Excursions",            "search": "SPI Excursions South Padre Island watersports"},
        ],
    },
    "juan": {
        "our_name": "Juan Elizondo RE/MAX Elite",
        "our_edge": "Bilingual, local RGV expertise, residential + commercial + investor network",
        "competitors": [
            {"name": "Deldi Ortegon Group",        "search": "Deldi Ortegon real estate McAllen TX"},
            {"name": "Maggie Harris Team KW",      "search": "Maggie Harris Keller Williams McAllen TX"},
            {"name": "Coldwell Banker La Mansion", "search": "Coldwell Banker La Mansion McAllen TX"},
        ],
    },
    "custom_designs_tx": {
        "our_name": "Custom Designs TX",
        "our_edge": "Full-service installation (security, audio/video, home theater), local B2B + B2C",
        "competitors": [
            {"name": "D-Tronics Home and Business", "search": "D-Tronics security installation McAllen TX"},
            {"name": "Superior Alarms RGV",         "search": "Superior Alarms McAllen TX security"},
            {"name": "RGV Geeks",                   "search": "RGV Geeks McAllen TX tech installation"},
        ],
    },
    "optimum_clinic": {
        "our_name": "Optimum Health & Wellness Clinic",
        "our_edge": "Open evenings, cash-pay, no insurance needed, fast service",
        "competitors": [
            {"name": "Doctors Hospital at Renaissance", "search": "Doctors Hospital Renaissance McAllen TX urgent care"},
            {"name": "Rio Grande Regional Hospital",     "search": "Rio Grande Regional Hospital McAllen TX"},
            {"name": "South Texas Health System",        "search": "South Texas Health System urgent care McAllen"},
        ],
    },
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _load_env(path: Path) -> dict:
    env = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


# ─── Scraping ─────────────────────────────────────────────────────────────────

def scrape_google_reviews(competitor: dict, page) -> dict:
    """
    Search Google Maps for a competitor and scrape their review text.
    Returns: {name, rating, review_count, reviews: [{text, rating, date}], error}
    """
    name   = competitor["name"]
    search = competitor["search"]
    result = {
        "name":         name,
        "search":       search,
        "rating":       None,
        "review_count": None,
        "reviews":      [],
        "error":        None,
    }

    search_url = f"https://www.google.com/maps/search/{urllib.parse.quote(search)}"
    log(f"  Searching: {search}")

    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)

        # Click the first result if we landed on a search results page
        first_result = page.query_selector("a[href*='/maps/place/']")
        if first_result:
            first_result.click()
            time.sleep(2)

        # Extract rating + review count from the place header
        body = page.inner_text("body") or ""

        # Rating pattern: "4.5" followed by "(123)" or "(1,234)"
        rating_m = re.search(r"\b([1-5]\.[0-9])\b", body)
        if rating_m:
            result["rating"] = float(rating_m.group(1))

        count_m = re.search(r"\(([\d,]+)\s*(?:reviews?|reseñas?)\)", body, re.IGNORECASE)
        if count_m:
            result["review_count"] = int(count_m.group(1).replace(",", ""))

        # Click the "Reviews" tab
        review_tab = None
        for selector in [
            "button[aria-label*='Reviews']",
            "button[data-tab-index='1']",
            "[role='tab']:has-text('Reviews')",
            "button:has-text('Reviews')",
        ]:
            try:
                btn = page.query_selector(selector)
                if btn:
                    review_tab = btn
                    break
            except Exception:
                pass

        if review_tab:
            review_tab.click()
            time.sleep(2)
        else:
            log(f"  {name}: Could not find Reviews tab — using page text")

        # Sort by "Newest" for more recent reviews
        try:
            sort_btn = page.query_selector("button[aria-label*='Sort']") or \
                       page.query_selector("button[data-value='Sort']")
            if sort_btn:
                sort_btn.click()
                time.sleep(1)
                newest = page.query_selector("[data-index='1']") or \
                         page.query_selector("[role='menuitem']:has-text('Newest')")
                if newest:
                    newest.click()
                    time.sleep(2)
        except Exception:
            pass

        # Scroll to load more reviews
        for _ in range(4):
            page.evaluate("document.querySelector('.m6QErb') && document.querySelector('.m6QErb').scrollBy(0, 800)")
            time.sleep(1)

        # Extract review text
        reviews = []

        # Strategy A: look for review elements by class/role
        review_elements = page.query_selector_all("[data-review-id]") or \
                          page.query_selector_all(".jftiEf") or \
                          page.query_selector_all("[class*='review']")

        for el in review_elements[:20]:
            try:
                text = el.inner_text().strip()
                if len(text) > 30:
                    # Extract star rating from aria-label if present
                    star_m = re.search(r"(\d)\s*star", text, re.IGNORECASE)
                    star = int(star_m.group(1)) if star_m else None
                    # Clean the text
                    text_clean = re.sub(r"\s+", " ", text).strip()[:500]
                    reviews.append({"text": text_clean, "stars": star})
            except Exception:
                pass

        # Strategy B: grep body text for review-like paragraphs
        if not reviews:
            page_text = page.inner_text("body") or ""
            # Look for paragraphs with 50-400 chars that look like review prose
            paragraphs = [p.strip() for p in page_text.split("\n") if 50 < len(p.strip()) < 400]
            # Filter out navigation/UI text
            skip_phrases = ["google maps", "directions", "website", "call", "save", "nearby",
                            "open now", "closes", "menu", "overview", "photos", "updates"]
            for para in paragraphs[:30]:
                if not any(s in para.lower() for s in skip_phrases):
                    reviews.append({"text": para, "stars": None})

        result["reviews"] = reviews[:25]
        log(f"  {name}: {len(reviews)} reviews scraped (rating: {result['rating']})")

    except PWTimeout:
        result["error"] = "Timeout"
        log(f"  TIMEOUT: {name}")
    except Exception as e:
        result["error"] = str(e)[:200]
        log(f"  ERROR: {name}: {e}")

    return result


# ─── AI Analysis ──────────────────────────────────────────────────────────────

def analyze_reviews_with_ai(business_key: str, our_name: str, our_edge: str,
                             scraped: list, api_key: str) -> str:
    """Send all competitor reviews for a business to AI for sentiment analysis."""

    # Build review digest
    sections = []
    for comp_data in scraped:
        name    = comp_data["name"]
        rating  = comp_data.get("rating")
        reviews = comp_data.get("reviews", [])
        if not reviews:
            continue
        section = [f"### {name} (rating: {rating or 'unknown'})"]
        for r in reviews[:12]:  # max 12 reviews per competitor
            section.append(f"  - {r['text'][:200]}")
        sections.append("\n".join(section))

    if not sections:
        return "No review text available for AI analysis."

    prompt = f"""You are a marketing strategist analyzing competitor Google reviews for a local business.

OUR BUSINESS: {our_name}
OUR EDGE: {our_edge}

COMPETITOR GOOGLE REVIEWS:
{chr(10).join(sections)}

Analyze the reviews and respond with ONLY these sections:

**TOP COMPLAINTS ABOUT COMPETITORS**
(What do customers consistently complain about? These are their weaknesses — and our opportunity.)
-
-
-

**WHAT CUSTOMERS LOVE ABOUT COMPETITORS**
(What do they praise? We need to match or exceed this.)
-
-
-

**WHAT'S NEVER MENTIONED**
(What topics, features, or qualities are absent from the reviews? This is the gap in the market.)
-
-

**2 AD ANGLES THAT WEAPONIZE THIS DATA**
(Specific headline/hook ideas for {our_name} that directly address competitor weaknesses.)
1.
2.

Keep each bullet to one clear sentence. Under 300 words total. Be direct."""

    payload = json.dumps({
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a sharp, concise marketing analyst. No fluff."},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 700,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://antigravity.local",
            "X-Title":       "Antigravity Review Miner",
        },
        method="POST",
    )
    try:
        resp   = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        return f"[API ERROR {e.code}: {e.read().decode()[:200]}]"
    except Exception as e:
        return f"[ERROR: {e}]"


# ─── Report ───────────────────────────────────────────────────────────────────

def generate_report(all_results: dict, date_str: str) -> Path:
    md_path   = REPORTS_DIR / f"reviews_{date_str}.md"
    json_path = REPORTS_DIR / f"reviews_{date_str}.json"

    lines = [
        f"# Competitor Google Review Analysis — {date_str}",
        "",
        "> Customer voice data: what people love, hate, and never mention about your competitors.",
        "> The complaints section = your ad angles. Run these directly as ad copy.",
        "",
        "---",
        "",
    ]

    for biz_key, biz_data in all_results.items():
        our_name = biz_data["our_name"]
        lines += [f"## {our_name}", ""]

        # Raw review summary
        for comp in biz_data["scraped"]:
            rating = comp.get("rating", "?")
            count  = comp.get("review_count", "?")
            n_text = len(comp.get("reviews", []))
            lines.append(f"**{comp['name']}** — {rating}★ ({count} reviews) — {n_text} review texts scraped")

        lines += ["", "### AI Analysis", ""]
        lines.append(biz_data.get("ai_analysis", "_No AI analysis available._"))
        lines += ["", "---", ""]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Report saved → {md_path}")
    return md_path


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Mine Google Reviews for competitor sentiment")
    parser.add_argument("--business", help="Run for one business only")
    parser.add_argument("--headful",  action="store_true", help="Show browser")
    parser.add_argument("--no-ai",    action="store_true", help="Scrape only, skip AI analysis")
    parser.add_argument("--dry-run",  action="store_true", help="Print config only")
    args = parser.parse_args()

    businesses = (
        {args.business: COMPETITORS[args.business]}
        if args.business and args.business in COMPETITORS
        else COMPETITORS
    )

    if args.dry_run:
        total = sum(len(v["competitors"]) for v in businesses.values())
        print(f"Dry run — {len(businesses)} businesses, {total} competitors:")
        for biz, data in businesses.items():
            print(f"  {biz}: {[c['name'] for c in data['competitors']]}")
        return

    # Load API key
    env     = _load_env(ENV_PATH)
    api_key = env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not args.no_ai:
        print("WARNING: No OPENROUTER_API_KEY — running without AI analysis (use --no-ai to suppress)")

    date_str = date.today().strftime("%Y-%m-%d")
    headless = not args.headful
    all_results = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx  = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.set_default_timeout(25000)

        for business, biz_data in businesses.items():
            log(f"\n{'='*50}")
            log(f"{biz_data['our_name']} — {len(biz_data['competitors'])} competitors")
            log(f"{'='*50}")

            scraped = []
            for comp in biz_data["competitors"]:
                result = scrape_google_reviews(comp, page)
                scraped.append(result)
                time.sleep(2)

            # AI analysis
            ai_text = ""
            if not args.no_ai and api_key:
                log(f"  Running AI review analysis for {biz_data['our_name']}...")
                ai_text = analyze_reviews_with_ai(
                    business_key=business,
                    our_name=biz_data["our_name"],
                    our_edge=biz_data["our_edge"],
                    scraped=scraped,
                    api_key=api_key,
                )
                log(f"  AI done ({len(ai_text)} chars)")
                print(f"\n--- {biz_data['our_name']} ---")
                print(ai_text)

            all_results[business] = {
                "our_name":   biz_data["our_name"],
                "scraped":    scraped,
                "ai_analysis": ai_text,
            }

        ctx.close()
        browser.close()

    md_path = generate_report(all_results, date_str)

    total_reviews = sum(
        len(c.get("reviews", []))
        for b in all_results.values()
        for c in b["scraped"]
    )
    print(f"\n{'='*60}")
    print(f"Total review texts scraped : {total_reviews}")
    print(f"Report: {md_path}")


if __name__ == "__main__":
    main()
