#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
keyword_rank_tracker.py — Google SERP rank tracker for all client businesses.
==============================================================================

For each keyword, searches Google and records:
  - Map Pack position (Local 3-Pack): where our business appears in the top 3
  - Organic position: where our business appears in organic results (1–20)
  - Top 3 results (map pack + organic) with title/URL — shows who we're competing against

Results saved to keyword_rankings_state.json with daily snapshots.
Morning brief reads this file to show rank + deltas.

Usage:
    python keyword_rank_tracker.py                    # all businesses
    python keyword_rank_tracker.py --business sugar_shack
    python keyword_rank_tracker.py --business spi_fun_rentals --keyword "golf cart rental spi"
    python keyword_rank_tracker.py --headful          # show browser (debug)
    python keyword_rank_tracker.py --dry-run          # print config, no scraping

Runs overnight. ~80 searches total, ~5–8 min with throttle.
State: keyword_rankings_state.json
"""

import argparse
import asyncio
import html as _html_mod
import json
import random
import re
import sys
import urllib.parse
import urllib.request as _ureq
from datetime import date
from pathlib import Path

# ── Bright Data Web Unlocker ───────────────────────────────────────────────────
_BD_TOKEN = "7fe773b11b190ba758a122c288438d14deef5356a694ef707a3c847de5af3b5c"
_BD_URL   = "https://api.brightdata.com/request"


async def _fetch_via_brightdata(url: str) -> str | None:
    """
    Fetch a URL via Bright Data Web Unlocker — bypasses Google CAPTCHA.
    Returns plain-text body (HTML tags stripped) or None on failure.
    """
    try:
        payload = json.dumps({
            "zone": "web_unlocker1",
            "url": url,
            "format": "raw",
        }).encode("utf-8")
        req = _ureq.Request(
            _BD_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {_BD_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with _ureq.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", errors="replace")

        # Convert HTML → plain text (mirrors page.inner_text behaviour)
        raw = re.sub(r'<script[^>]*>.*?</script>', ' ', raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r'<style[^>]*>.*?</style>',  ' ', raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r'<(?:br|p|div|li|tr|h[1-6])[^>]*/?>', '\n', raw, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', raw)
        text = _html_mod.unescape(text)
        lines = [l.strip() for l in text.split('\n')]
        text  = '\n'.join(l for l in lines if l)

        if not text or len(text) < 200:
            return None
        if "unusual traffic" in text.lower() or "captcha" in text.lower():
            return None
        return text
    except Exception:
        return None

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
CONFIG_PATH  = SCRIPT_DIR / "keyword_rankings_config.json"
STATE_PATH   = SCRIPT_DIR / "keyword_rankings_state.json"

# ── Load config ────────────────────────────────────────────────────────────────
with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)

BUSINESSES = CONFIG["businesses"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


# ── State helpers ──────────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state: dict):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ── Name matching ──────────────────────────────────────────────────────────────
def _matches(text: str, match_names: list, match_domains: list) -> bool:
    """True if text contains any of our business identifiers (case-insensitive)."""
    t = text.lower()
    for name in match_names:
        if name.lower() in t:
            return True
    for domain in match_domains:
        if domain.lower() in t:
            return True
    return False


# ── Core scraper ───────────────────────────────────────────────────────────────
async def check_keyword(page, keyword: str, match_names: list, match_domains: list) -> dict:
    """
    Search Google for keyword. Returns:
    {
        "map_pack": [{"name", "rating", "address", "is_ours"}, ...],  # top 3
        "organic":  [{"title", "url", "is_ours"}, ...],               # top 10
        "our_map_pack_position":  int or None,   # 1-3 (in the Google 3-pack)
        "our_maps_position":      int or None,   # 1-20 (full extended Maps list)
        "our_organic_position":   int or None,   # 1-10
        "all_maps_entries": [{"name", "rating", "reviews"}, ...],     # up to 20
        "error": str or None
    }
    """
    result = {
        "map_pack": [],
        "organic":  [],
        "our_map_pack_position": None,
        "our_maps_position":     None,
        "our_organic_position":  None,
        "all_maps_entries":      [],
        "error": None,
    }

    try:
        # Single request: tbm=lcl shows full ranked local results list.
        # Top 3 entries = map pack equivalent. Full list = extended position.
        enc     = urllib.parse.quote_plus(keyword)
        lcl_url = f"https://www.google.com/search?q={enc}&tbm=lcl&gl=us&hl=en"

        # Strategy 1: Bright Data (no CAPTCHA, no browser needed)
        body = await _fetch_via_brightdata(lcl_url)

        # Strategy 2: Playwright fallback (if Bright Data fails)
        if not body:
            await page.goto(lcl_url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000 + random.randint(0, 1000))
            body = await page.inner_text("body")

        if "unusual traffic" in body.lower() or "captcha" in body.lower():
            result["error"] = "CAPTCHA — IP rate-limited"
            return result

        all_entries = _parse_local_search_list(body)
        result["all_maps_entries"] = all_entries[:20]

        # Top 3 = map pack
        for i, entry in enumerate(all_entries[:3]):
            entry["is_ours"] = _matches(entry.get("name", ""), match_names, match_domains)
            if entry["is_ours"] and result["our_map_pack_position"] is None:
                result["our_map_pack_position"] = i + 1
        result["map_pack"] = [
            {"name": e.get("name",""), "rating": e.get("rating",""), "is_ours": e.get("is_ours", False)}
            for e in all_entries[:3]
        ]

        # Full list position (1-20)
        for i, entry in enumerate(all_entries[:20]):
            if _matches(entry.get("name", ""), match_names, match_domains):
                result["our_maps_position"] = i + 1
                break

    except Exception as e:
        result["error"] = str(e)

    return result


def _parse_maps_list(body: str) -> list:
    """
    Parse Google Maps search results from inner_text.
    Google Maps format (per line):
      Business Name
      4.9                    ← rating (float, no parens)
      Category · Address     ← contains ·
      Open/Closed status
    Returns list of {"name", "rating"} in rank order.
    """
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    entries = []
    rating_re = re.compile(r'^[1-5]\.[0-9]$')
    ui_skip   = {"rating", "hours", "all filters", "saved", "recents", "get app",
                 "results", "share", "you're seeing", "get the most", "send directions"}

    i = 0
    while i < len(lines) and len(entries) < 25:
        line = lines[i]
        ll   = line.lower()

        # Skip UI chrome, open/closed lines, pure ratings, lines starting with digit
        if (any(sw in ll for sw in ui_skip)
                or rating_re.match(line)
                or re.match(r'^\d', line)
                or re.match(r'^(Open|Closed|Opens|Closes|·)', line)):
            i += 1
            continue

        # Business entry: next line must be a rating float
        if i + 1 < len(lines) and rating_re.match(lines[i + 1]):
            entries.append({"name": line, "rating": lines[i + 1], "reviews": ""})
            i += 4   # skip name + rating + category·addr + open/closed
        else:
            i += 1

    return entries


def _parse_body_text(body: str) -> tuple:
    """Fallback: parse Google's rendered body text for map pack + organic entries."""
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    map_pack = []
    organic  = []

    # Heuristic: lines before "More places" or "See more" are map pack candidates
    # Organic entries follow — lines that look like a title + a URL below them
    in_organic = False
    i = 0
    url_pattern = re.compile(r'^(https?://|www\.)\S+', re.IGNORECASE)
    rating_pattern = re.compile(r'^[1-5](\.[0-9])?\s*(\([\d,]+\))?$')

    while i < len(lines) and len(map_pack) < 3:
        line = lines[i]
        if re.search(r'\bmore places\b|\bsee more\b', line, re.IGNORECASE):
            in_organic = True
            i += 1
            continue
        if not in_organic and len(line) > 5 and not rating_pattern.match(line):
            # Check if next few lines contain a rating → likely a map pack entry
            ahead = lines[i+1:i+4]
            if any(rating_pattern.match(l) for l in ahead):
                map_pack.append({"name": line, "rating": "", "address": ""})
        i += 1

    # Simple organic: find h3-like lines (title-case, not too long) followed by a URL
    for i, line in enumerate(lines):
        if len(organic) >= 10:
            break
        if url_pattern.match(line) and i > 0:
            title = lines[i - 1]
            if 10 < len(title) < 120:
                organic.append({"title": title, "url": line})

    return map_pack, organic


def _parse_local_search_list(body: str) -> list:
    """
    Parse Google's local search results page (tbm=lcl) from inner_text.
    Format per entry (5 lines):
      Business Name
      4.9(719) · Category          ← rating+reviews+category on ONE line
      Address · Phone
      Open/Closed status
      "Review snippet"
    Returns list of {"name", "rating", "reviews"} in rank order (up to 20).
    """
    lines     = [l.strip() for l in body.split("\n") if l.strip()]
    entries   = []
    # Matches: "4.9(719) · Category" or "4.1(10) · Golf cart dealer"
    rating_re = re.compile(r'^([1-5]\.[0-9])\s*\(?([\d,]*)\)?\s*[·\-]')
    ui_skip   = {"accessibility", "skip to", "sign in", "filters", "ai mode",
                 "images", "forums", "places", "short videos", "more", "tools",
                 "open now", "top rated", "small business", "search results"}

    i = 0
    while i < len(lines) and len(entries) < 25:
        line = lines[i]
        ll   = line.lower()

        # Skip UI chrome
        if any(sw in ll for sw in ui_skip) or ll in {"all", "maps", "more"}:
            i += 1
            continue

        # Skip rating lines, address lines, open/closed lines, review snippets
        if (rating_re.match(line)
                or re.match(r'^(Open|Closed|Opens|Closes|·|")', line)
                or re.match(r'^\d{3,4}\s', line)):   # address starts with street number
            i += 1
            continue

        # Business entry: next line matches rating+category pattern
        if i + 1 < len(lines) and rating_re.match(lines[i + 1]):
            m = rating_re.match(lines[i + 1])
            rating  = m.group(1) if m else ""
            reviews = m.group(2) if m else ""
            entries.append({"name": line, "rating": rating, "reviews": reviews})
            i += 5   # name + rating·category + address + open/closed + review snippet
        else:
            i += 1

    return entries


# ── Single business runner ─────────────────────────────────────────────────────
async def run_business(biz_key: str, biz_cfg: dict, state: dict,
                        target_keyword: str = None) -> dict:
    """Check all keywords for one business. Returns updated state slice."""
    from playwright.async_api import async_playwright

    today_str     = date.today().isoformat()
    match_names   = biz_cfg.get("match_names", [])
    match_domains = biz_cfg.get("match_domains", [])
    keywords      = biz_cfg.get("keywords", [])

    if target_keyword:
        keywords = [k for k in keywords if target_keyword.lower() in k.lower()]
        if not keywords:
            print(f"  Keyword '{target_keyword}' not found in config for {biz_cfg['name']}")
            return state

    biz_state = state.get(biz_key, {})

    async with async_playwright() as p:
        # ── Browser strategy ──────────────────────────────────────────────────
        # Google blocks headless Chromium. Priority:
        #   1. Connect to existing real Chrome via CDP (port 9223 or 9224) if open
        #   2. Launch Chrome via channel="chrome" (user's installed Chrome, looks real)
        #   3. Fall back to headless Chromium with stealth patches
        browser = None
        ctx     = None
        using_cdp = False

        for cdp_port in [9223, 9224]:
            try:
                browser = await p.chromium.connect_over_cdp(f"http://localhost:{cdp_port}")
                using_cdp = True
                print(f"  [CDP connected on port {cdp_port}]")
                break
            except Exception:
                pass

        if not browser:
            # NOTE: Google blocks headless Chrome — always launch visible to bypass anti-bot.
            try:
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=False,      # Always visible — bypasses Google anti-bot
                    args=["--disable-blink-features=AutomationControlled",
                          "--window-position=0,0", "--window-size=1024,768"],
                )
                print("  [Real Chrome — visible window]")
            except Exception:
                browser = await p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                print("  [Chromium — visible window]")

        if using_cdp:
            # In CDP mode, use existing context (do NOT create a new one — it may log you out)
            ctx  = await browser.new_context(locale="en-US")
        else:
            ctx = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale="en-US",
                viewport={"width": 1280, "height": 900},
            )

        page = await ctx.new_page()

        # Stealth: remove navigator.webdriver flag
        await ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        # Block images/fonts to speed up
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf}", lambda r: r.abort())

        for keyword in keywords:
            print(f"    [{biz_cfg['name']}] {keyword} ...", end=" ", flush=True)
            result = await check_keyword(page, keyword, match_names, match_domains)

            map_pos = result["our_map_pack_position"]
            org_pos = result["our_organic_position"]
            maps_pos = result["our_maps_position"]
            if map_pos:
                status = f"3-pack #{map_pos}"
            elif maps_pos:
                status = f"maps #{maps_pos}"
            elif org_pos:
                status = f"organic #{org_pos}"
            else:
                status = "not found"
            print(status)

            if result["error"]:
                print(f"      ERROR: {result['error']}")

            # Build snapshot
            snapshot = {
                "map_pack_position": map_pos,
                "maps_position":     maps_pos,
                "organic_position":  org_pos,
                "top3_map_pack": [
                    {"name": e.get("name", ""), "rating": e.get("rating", ""), "is_ours": e.get("is_ours", False)}
                    for e in result["map_pack"][:3]
                ],
                "top3_maps_entries": [
                    {"name": e.get("name", ""), "rating": e.get("rating", ""), "reviews": e.get("reviews", "")}
                    for e in result["all_maps_entries"][:3]
                ],
                "top3_organic": [
                    {"title": e.get("title", ""), "url": e.get("url", ""), "is_ours": e.get("is_ours", False)}
                    for e in result["organic"][:3]
                ],
                "error": result["error"],
            }

            # Preserve history — store by date
            kw_history = biz_state.get(keyword, {})
            kw_history[today_str] = snapshot
            # Keep only last 30 days
            dates_sorted = sorted(kw_history.keys())
            if len(dates_sorted) > 30:
                for old in dates_sorted[:-30]:
                    del kw_history[old]
            biz_state[keyword] = kw_history

            # Throttle between searches (3–6 seconds)
            await page.wait_for_timeout(random.randint(3000, 6000))

        await page.close()
        if not using_cdp:
            await browser.close()

    state[biz_key] = biz_state
    return state


# ── Delta helper ───────────────────────────────────────────────────────────────
def get_delta(kw_history: dict, field: str, today_str: str) -> int | None:
    """Compare today's value vs the most recent previous day. Returns None if no history."""
    today_val = kw_history.get(today_str, {}).get(field)
    dates = sorted(d for d in kw_history if d != today_str)
    if not dates:
        return None
    prev_val = kw_history[dates[-1]].get(field)
    if today_val is None or prev_val is None:
        return None
    return prev_val - today_val  # positive = improved (moved up in rank)


# ── Public summary builder (called by morning_brief.py) ───────────────────────
def load_rankings_summary(target_date: str = None) -> dict:
    """
    Returns a summary dict keyed by business_key, then keyword.
    Each entry:
    {
        "map_pack_position": int or None,
        "organic_position":  int or None,
        "map_pack_delta":    int or None,   # positive = moved up
        "organic_delta":     int or None,
        "top3_map_pack":     [...],
        "top3_organic":      [...],
    }
    """
    state = load_state()
    if not state:
        return {}

    today_str = target_date or date.today().isoformat()
    summary   = {}

    for biz_key, kw_dict in state.items():
        biz_summary = {}
        for keyword, kw_history in kw_dict.items():
            # Find most recent date (today or most recent available)
            available = sorted(kw_history.keys())
            if not available:
                continue
            use_date = today_str if today_str in kw_history else available[-1]
            snap     = kw_history[use_date]

            biz_summary[keyword] = {
                "map_pack_position": snap.get("map_pack_position"),
                "maps_position":     snap.get("maps_position"),
                "organic_position":  snap.get("organic_position"),
                "map_pack_delta":    get_delta(kw_history, "map_pack_position", use_date),
                "maps_delta":        get_delta(kw_history, "maps_position", use_date),
                "organic_delta":     get_delta(kw_history, "organic_position", use_date),
                "top3_map_pack":     snap.get("top3_map_pack", []),
                "top3_maps_entries": snap.get("top3_maps_entries", []),
                "top3_organic":      snap.get("top3_organic", []),
                "date":              use_date,
            }
        if biz_summary:
            summary[biz_key] = biz_summary

    return summary


# ── Main ───────────────────────────────────────────────────────────────────────
async def main_async(businesses: list, target_keyword: str = None):
    state = load_state()
    for biz_key in businesses:
        if biz_key not in BUSINESSES:
            print(f"  Unknown business: {biz_key} — skipping")
            continue
        biz_cfg = BUSINESSES[biz_key]
        print(f"\n[{biz_cfg['name']}]")
        state = await run_business(biz_key, biz_cfg, state, target_keyword)
        save_state(state)
        print(f"  Saved.")
        # Cool-down between businesses to avoid Google rate-limiting / CAPTCHA
        remaining = [b for b in businesses if b != biz_key]
        if remaining:
            delay = random.randint(45, 60)
            print(f"  Cooling down {delay}s before next business...")
            await asyncio.sleep(delay)

    print(f"\nDone. State: {STATE_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Keyword rank tracker for all client businesses")
    parser.add_argument("--business", choices=list(BUSINESSES.keys()), help="Single business only")
    parser.add_argument("--keyword",  help="Check only keywords containing this string")

    parser.add_argument("--dry-run",  action="store_true", help="Print config, no scraping")
    args = parser.parse_args()

    businesses = [args.business] if args.business else list(BUSINESSES.keys())

    if args.dry_run:
        print(f"Keyword Rank Tracker — dry run")
        for biz in businesses:
            cfg = BUSINESSES[biz]
            print(f"\n  {cfg['name']}  ({len(cfg['keywords'])} keywords)")
            for kw in cfg["keywords"]:
                print(f"    • {kw}")
        return

    asyncio.run(main_async(businesses, args.keyword))


if __name__ == "__main__":
    main()
