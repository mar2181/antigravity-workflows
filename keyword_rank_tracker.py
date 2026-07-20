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
import os
import random
import re
import sys
import base64
import urllib.parse
import urllib.request as _ureq
from datetime import date
from pathlib import Path

# ── Bright Data credentials ────────────────────────────────────────────────────
def _load_env_value(*keys) -> str | None:
    """Load a value from env vars or .env.local (Windows + WSL paths)."""
    for k in keys:
        v = os.getenv(k)
        if v:
            return v.strip()
    env_path = Path("C:/Users/mario/missioncontrol/dashboard/.env.local")
    if not env_path.exists():
        env_path = Path("/mnt/c/Users/mario/missioncontrol/dashboard/.env.local")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k2, _, v2 = line.partition("=")
            if k2.strip() in keys:
                return v2.strip().strip('"').strip("'")
    return None

# Scraping Browser WS endpoint — full cloud browser, handles CAPTCHAs automatically
_BD_SB_WS = _load_env_value("BRIGHTDATA_SCRAPING_BROWSER_WS")

# Web Unlocker proxy creds (fallback)
_BD_TOKEN = _load_env_value("BRIGHT_DATA_KEY", "BD_TOKEN", "BRIGHTDATA_WEB_UNLOCKER_API")

# ── Serper.dev — PRIMARY SERP provider since 2026-07-19 ───────────────────────
# One JSON call returns organic results AND the local "places" pack. No browser,
# no CAPTCHA surface, prepaid credits (no account-suspension class). Bright Data
# (account hl_b6130486, SUSPENDED 2026-07) stays as the fallback path only.
# Override with SERP_PROVIDER=brightdata to force the old path.
_SERPER_KEY    = _load_env_value("SERPER_API_KEY")
_SERP_PROVIDER = (_load_env_value("SERP_PROVIDER") or ("serper" if _SERPER_KEY else "brightdata")).lower()
_SERPER_CALLS  = 0  # per-run query counter (cost visibility)

if _SERP_PROVIDER != "serper" and not _BD_TOKEN and not _BD_SB_WS:
    print("[FATAL] No SERP provider configured — need SERPER_API_KEY (preferred) or Bright Data creds in env/.env.local.", file=sys.stderr)
    sys.exit(2)

_BD_URL   = "https://api.brightdata.com/request"

def _bd_auth_header(token: str) -> str:
    """
    Bright Data uses Basic auth with the key as 'username:password'.
    The key format is 'brd-customer-...-zone-...:password' — pass as-is.
    If the key has no colon (plain API key), use Bearer as fallback.
    """
    if ":" in token:
        encoded = base64.b64encode(token.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded}"
    return f"Bearer {token}"


async def _fetch_via_brightdata(url: str, return_html: bool = False) -> str | None:
    """
    Fetch a URL via Bright Data Web Unlocker — bypasses Google CAPTCHA.
    Default: returns plain-text body (HTML tags stripped, mirrors inner_text).
    return_html=True: returns raw HTML for class-based parsing.
    Returns None on failure.

    NOTE: Bright Data's web_unlocker1 zone returns 502 on Google `tbm=lcl`
    URLs (selector "#main" not found) and on `/maps/search/...` URLs
    (endpoint disabled). Always pass plain `/search?q=...` URLs and parse
    the inline local pack from the returned HTML.
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
                "Authorization": _bd_auth_header(_BD_TOKEN),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with _ureq.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", errors="replace")

        if not raw or len(raw) < 500:
            print(f"      [BD: empty/short body, len={len(raw) if raw else 0}]")
            return None

        if return_html:
            return raw

        # Convert HTML → plain text (mirrors page.inner_text behaviour)
        stripped = re.sub(r'<script[^>]*>.*?</script>', ' ', raw, flags=re.DOTALL | re.IGNORECASE)
        stripped = re.sub(r'<style[^>]*>.*?</style>',  ' ', stripped, flags=re.DOTALL | re.IGNORECASE)
        stripped = re.sub(r'<(?:br|p|div|li|tr|h[1-6])[^>]*/?>', '\n', stripped, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', stripped)
        text = _html_mod.unescape(text)
        lines = [l.strip() for l in text.split('\n')]
        text  = '\n'.join(l for l in lines if l)

        if not text or len(text) < 200:
            print(f"      [BD: stripped body too short, len={len(text) if text else 0}]")
            return None
        if "unusual traffic" in text.lower() or "captcha" in text.lower():
            print(f"      [BD: CAPTCHA in response]")
            return None
        return text
    except Exception as _bd_err:
        print(f"      [BD failed: {type(_bd_err).__name__}: {_bd_err}]")
        return None


def _strip_html_to_text(raw: str) -> str:
    """HTML → plain text (matches what _fetch_via_brightdata returns by default)."""
    raw = re.sub(r'<script[^>]*>.*?</script>', ' ', raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r'<style[^>]*>.*?</style>',  ' ', raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r'<(?:br|p|div|li|tr|h[1-6])[^>]*/?>', '\n', raw, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', raw)
    text = _html_mod.unescape(text)
    lines = [l.strip() for l in text.split('\n')]
    return '\n'.join(l for l in lines if l)


def _parse_local_pack_html(html: str) -> list:
    """
    Parse Google's inline local 3-pack from regular SERP HTML using the
    stable `VkpGBb` container class. Each container holds one local result.

    Selector map (verified 2026-05-02):
      Container ........ class="VkpGBb"
      Business name .... class="OSrXXb"
      Rating + reviews . aria-label="Rated 4.9 out of 5, 228 user reviews"

    Returns list of {"name", "rating", "reviews", "address"} for up to ~10
    entries (Google occasionally shows expanded packs).
    """
    containers = re.findall(
        r'<div class="VkpGBb".{0,8000}?</div></div></div>',
        html,
        flags=re.DOTALL,
    )
    entries = []
    for c in containers:
        name = ""
        rating = ""
        reviews = ""
        address = ""

        m_name = re.search(r'class="OSrXXb[^"]*"[^>]*>([^<]+)<', c)
        if m_name:
            name = _html_mod.unescape(m_name.group(1)).strip()

        for aria in re.findall(r'aria-label="([^"]+)"', c):
            m = re.search(r'Rated\s+(\d\.\d)\s+out of 5', aria, re.IGNORECASE)
            if m and not rating:
                rating = m.group(1)
            m = re.search(r'(\d[\d,]*)\s*user reviews?', aria, re.IGNORECASE)
            if m and not reviews:
                reviews = m.group(1).replace(",", "")

        # Fallback: visible text scan (handles future layout shifts)
        if not name:
            text = _strip_html_to_text(c)
            for l in [x.strip() for x in text.split('\n') if x.strip()]:
                if re.match(r'^[1-5]\.\d', l):
                    continue
                if 3 < len(l) < 120 and not l.startswith('('):
                    name = l
                    break

        text_for_addr = _strip_html_to_text(c)
        addr_match = re.search(
            r'(\d{1,6}\s+[A-Z][\w\s\.,]{3,60}(?:TX|Texas|McAllen|Edinburg|Mission|Pharr|Brownsville|Harlingen))',
            text_for_addr,
        )
        if addr_match:
            address = addr_match.group(1).strip()

        if name:
            entries.append({
                "name": name,
                "rating": rating,
                "reviews": reviews,
                "address": address,
            })

    return entries

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
    """Parallel-safe: lock, re-read disk, merge our updates per-business, atomic rename."""
    import time, tempfile
    try:
        import msvcrt
        _LOCK_WIN = True
    except ImportError:
        import fcntl
        _LOCK_WIN = False

    lock_path = str(STATE_PATH) + ".lock"
    lock_f = open(lock_path, "a+")
    try:
        # Acquire exclusive lock (retry up to 30 sec)
        acquired = False
        for _ in range(60):
            try:
                if _LOCK_WIN:
                    msvcrt.locking(lock_f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except Exception:
                time.sleep(0.5)
        # Re-read disk state and merge per-business
        disk_state = {}
        if STATE_PATH.exists():
            try:
                with open(STATE_PATH, encoding="utf-8") as f:
                    disk_state = json.load(f)
            except Exception:
                disk_state = {}
        for biz_key, biz_data in state.items():
            disk_state[biz_key] = biz_data
        # Atomic write via temp + replace
        tmp_path = str(STATE_PATH) + f".tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(disk_state, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, str(STATE_PATH))
    finally:
        if acquired:
            try:
                if _LOCK_WIN:
                    lock_f.seek(0)
                    msvcrt.locking(lock_f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        lock_f.close()


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


# ── Serper.dev provider ────────────────────────────────────────────────────────
def _check_keyword_serper(keyword: str, match_names: list, match_domains: list, result: dict) -> dict:
    """
    One Serper.dev call fills the same result dict the Bright Data path builds:
    `places[]` → local pack (map_pack / all_maps_entries), `organic[]` → organic.
    Errors are recorded in result["error"] with the provider named, so the
    fail-loud gate's Telegram alert says exactly which provider died.
    """
    global _SERPER_CALLS
    try:
        payload = json.dumps({"q": keyword, "gl": "us", "hl": "en", "num": 20}).encode("utf-8")
        req = _ureq.Request(
            "https://google.serper.dev/search",
            data=payload,
            headers={"X-API-KEY": _SERPER_KEY, "Content-Type": "application/json"},
            method="POST",
        )
        with _ureq.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        _SERPER_CALLS += 1
    except Exception as e:
        code = getattr(e, "code", None)
        result["error"] = f"serper HTTP {code}" if code else f"serper: {e}"
        return result

    # ── Local pack (serper "places") ──
    local_entries = [
        {
            "name":    pl.get("title", ""),
            "rating":  str(pl.get("rating", "") or ""),
            "reviews": str(pl.get("ratingCount", "") or ""),
        }
        for pl in (data.get("places") or [])
    ]
    result["all_maps_entries"] = local_entries[:20]
    for i, entry in enumerate(local_entries[:3]):
        entry["is_ours"] = _matches(entry.get("name", ""), match_names, match_domains)
        if entry["is_ours"] and result["our_map_pack_position"] is None:
            result["our_map_pack_position"] = i + 1
    result["map_pack"] = [
        {"name": e.get("name", ""), "rating": e.get("rating", ""),
         "is_ours": e.get("is_ours", False)}
        for e in local_entries[:3]
    ]
    for i, entry in enumerate(local_entries[:20]):
        if _matches(entry.get("name", ""), match_names, match_domains):
            result["our_maps_position"] = i + 1
            break

    # ── Organic ──
    organic_entries = []
    for o in (data.get("organic") or []):
        link = o.get("link", "")
        organic_entries.append({
            "title":  o.get("title", ""),
            "url":    link,
            "domain": urllib.parse.urlparse(link).netloc if link else "",
        })
    for i, entry in enumerate(organic_entries):
        check_text = f"{entry['title']} {entry['domain']} {entry['url']}"
        if _matches(check_text, match_names, match_domains):
            result["our_organic_position"] = i + 1
            break
    result["organic"] = [
        {"title": e["title"], "url": e["url"],
         "is_ours": _matches(f"{e['title']} {e['domain']}", match_names, match_domains)}
        for e in organic_entries[:10]
    ]
    return result


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

    if _SERP_PROVIDER == "serper":
        return _check_keyword_serper(keyword, match_names, match_domains, result)

    try:
        # ── Single Bright Data call: plain Google SERP, raw HTML ──
        # Google embeds the local 3-pack inline in the regular SERP via
        # `class="VkpGBb"` containers. The standalone `tbm=lcl` URL has been
        # broken on Bright Data since spring 2026 (web_unlocker1 → expect_element,
        # serp_api1 → expect_body). One call to plain `/search?q=...` gives us
        # both the local pack AND organic results.
        enc        = urllib.parse.quote_plus(keyword)
        search_url = f"https://www.google.com/search?q={enc}&gl=us&hl=en&pws=0"

        html = await _fetch_via_brightdata(search_url, return_html=True)

        # Playwright fallback (rare — only if Bright Data itself fails)
        if not html:
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(2000 + random.randint(0, 1000))
                html = await page.content()
            except Exception:
                html = None

        if not html:
            result["error"] = "no SERP body"
            return result

        if ("unusual traffic" in html.lower()) or ("captcha-form" in html.lower()):
            result["error"] = "CAPTCHA — IP rate-limited"
            return result

        # ── Local pack: parse from VkpGBb HTML containers ──
        local_entries = _parse_local_pack_html(html)
        result["all_maps_entries"] = local_entries[:20]

        for i, entry in enumerate(local_entries[:3]):
            entry["is_ours"] = _matches(entry.get("name", ""), match_names, match_domains)
            if entry["is_ours"] and result["our_map_pack_position"] is None:
                result["our_map_pack_position"] = i + 1

        result["map_pack"] = [
            {"name": e.get("name", ""), "rating": e.get("rating", ""),
             "is_ours": e.get("is_ours", False)}
            for e in local_entries[:3]
        ]

        for i, entry in enumerate(local_entries[:20]):
            if _matches(entry.get("name", ""), match_names, match_domains):
                result["our_maps_position"] = i + 1
                break

        # ── Organic: parse from same HTML (stripped to text) ──
        organic_text    = _strip_html_to_text(html)
        organic_entries = _parse_organic_serp(organic_text)

        for i, entry in enumerate(organic_entries):
            check_text = (
                f"{entry.get('title', '')} "
                f"{entry.get('domain', '')} "
                f"{entry.get('url', '')}"
            )
            if _matches(check_text, match_names, match_domains):
                result["our_organic_position"] = i + 1
                break

        result["organic"] = [
            {"title": e.get("title", ""), "url": e.get("url", ""),
             "is_ours": _matches(
                 f"{e.get('title', '')} {e.get('domain', '')}",
                 match_names, match_domains)}
            for e in organic_entries[:10]
        ]

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
    Parse Google local search results (tbm=lcl) from inner_text.
    Handles BOTH layouts Google has shipped:
      OLD: Name / "4.9(719) · Category" / Address · Phone / Open/Closed / Review snippet
      NEW: Name / "4.9" / "(719)" / Category / Address / Open/Closed / ...
    Returns list of {"name", "rating", "reviews"} in rank order (up to 25).
    """
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    entries = []
    rating_inline_re = re.compile(r'^([1-5]\.[0-9])\s*\(?([\d,]*)\)?\s*[·\-]')
    rating_only_re   = re.compile(r'^[1-5]\.[0-9]$')
    reviews_re       = re.compile(r'^\(([\d,]+)\)$')
    ui_skip = {"accessibility", "skip to", "sign in", "filters", "ai mode",
               "images", "forums", "places", "short videos", "more", "tools",
               "open now", "top rated", "small business", "search results",
               "delete", "see more", "report inappropriate", "press",
               "google search", "send feedback"}

    i = 0
    while i < len(lines) and len(entries) < 25:
        line = lines[i]
        ll   = line.lower()

        if (any(sw in ll for sw in ui_skip)
                or ll in {"all", "maps", "more", "(", ")"}
                or rating_inline_re.match(line)
                or rating_only_re.match(line)
                or reviews_re.match(line)
                or re.match(r'^(Open|Closed|Opens|Closes|·|")', line)
                or re.match(r'^\d{3,4}\s', line)):
            i += 1
            continue

        # OLD layout: name then "X.X(NN) · Cat"
        if i + 1 < len(lines) and rating_inline_re.match(lines[i + 1]):
            m = rating_inline_re.match(lines[i + 1])
            entries.append({"name": line, "rating": m.group(1), "reviews": m.group(2)})
            i += 5
            continue

        # NEW layout: name, then bare "X.X", optionally followed by "(NN)"
        if i + 1 < len(lines) and rating_only_re.match(lines[i + 1]):
            rating  = lines[i + 1]
            reviews = ""
            advance = 2
            if i + 2 < len(lines):
                rm = reviews_re.match(lines[i + 2])
                if rm:
                    reviews = rm.group(1)
                    advance = 3
            entries.append({"name": line, "rating": rating, "reviews": reviews})
            i += advance + 2
            continue

        i += 1

    return entries


def _parse_organic_serp(body: str) -> list:
    """
    Parse Google organic SERP results from inner_text body.
    Identifies each result by its URL/breadcrumb line (e.g. "example.com › path").
    Returns list of {"title", "url", "domain"} in rank order, max 100.

    Tolerant to Google layout variants — looks for any line that opens with a
    valid domain.tld pattern, then takes the previous non-URL line as the title.
    Dedupes by domain so sitelinks of the same result don't inflate the count.
    """
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    results = []
    seen_domains = set()

    # URL/breadcrumb line patterns:
    #   "spifunrentals.com"
    #   "spifunrentals.com › about › services"
    #   "https://www.spifunrentals.com/path"
    #   "www.spifunrentals.com › about"
    url_re = re.compile(
        r'^(https?://)?(www\.)?([a-z0-9-]+\.)+[a-z]{2,12}(/[^\s]*)?(\s*[›>].*)?$',
        re.IGNORECASE,
    )
    domain_re = re.compile(
        r'^(?:https?://)?(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)+)',
        re.IGNORECASE,
    )
    # Skip Google internal links and the usual Google product noise
    skip_substrings = (
        "google.com/search", "google.com/maps", "google.com/url",
        "support.google", "accounts.google", "policies.google",
        "myactivity.google", "translate.google",
    )

    for i, line in enumerate(lines):
        if not url_re.match(line):
            continue
        ll = line.lower()
        if any(s in ll for s in skip_substrings):
            continue
        if ll in ("google.com", "www.google.com"):
            continue

        m = domain_re.match(line)
        if not m:
            continue
        domain = m.group(1).lower()

        # Skip Google's own properties — these are UI, not organic results
        if domain in ("google.com", "youtube.com", "maps.google.com"):
            # NOTE: youtube.com IS a legitimate organic result; only skip if it
            # appears as a sitelink/UI nav. Keep it for now.
            if domain == "google.com":
                continue

        # Dedupe — Google often shows same domain twice for sitelinks
        if domain in seen_domains:
            continue
        seen_domains.add(domain)

        # Title = the previous non-URL, non-rating line
        title = ""
        for j in range(i - 1, max(-1, i - 4), -1):
            prev = lines[j]
            if url_re.match(prev):
                continue
            if re.match(r'^[\d.]+\s*\(?[\d,]*\)?\s*$', prev):
                continue  # rating line
            if len(prev) < 5 or len(prev) > 200:
                continue
            title = prev
            break

        results.append({"title": title, "url": line, "domain": domain})
        if len(results) >= 100:
            break

    return results


# ── Single business runner ─────────────────────────────────────────────────────
async def run_business(biz_key: str, biz_cfg: dict, state: dict,
                        target_keyword: str = None) -> dict:
    """Check all keywords for one business. Returns updated state slice."""
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
    # Merge in any biz-specific today file (from incremental saves of prior crashed runs)
    _biz_today_path = str(STATE_PATH).replace('.json', f'_{biz_key}_today.json')
    if __import__('pathlib').Path(_biz_today_path).exists():
        try:
            with open(_biz_today_path, encoding='utf-8') as _tf:
                _today_data = __import__('json').load(_tf)
            biz_state = biz_state.copy()
            for _kw, _hist in _today_data.get(biz_key, {}).items():
                biz_state.setdefault(_kw, {}).update(_hist)
        except Exception:
            pass

    async def _sweep(page):
        """Run every keyword through check_keyword — shared by both providers."""
        for keyword in keywords:
            # Skip keywords already checked today (incremental resume) — but
            # RETRY ones whose today-snapshot is an error, so a same-day rerun
            # after fixing the provider (key added / account restored) recovers.
            _prior = biz_state.get(keyword, {}).get(today_str)
            if _prior and not _prior.get("error"):
                print(f"    [{biz_cfg['name']}] {keyword} ... (already done today, skipping)")
                continue
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
            # Incremental save to biz-specific file (avoids race with other trackers)
            try:
                state[biz_key] = biz_state
                _biz_path = str(STATE_PATH).replace('.json', f'_{biz_key}_today.json')
                with open(_biz_path, 'w', encoding='utf-8') as _f:
                    import json as _json
                    _json.dump({biz_key: biz_state}, _f, indent=2, ensure_ascii=False)
            except Exception as _e:
                pass  # non-fatal, main save happens at end

            # Throttle: serper = polite 0.5s (no Google exposure); browser = 0.8-1.5s
            if page is None:
                await asyncio.sleep(0.5)
            else:
                await page.wait_for_timeout(random.randint(800, 1500))

    # ── Serper path: pure JSON API, no browser needed ──
    if _SERP_PROVIDER == "serper":
        print(f"  [Serper.dev SERP API — no browser]")
        await _sweep(None)
        state[biz_key] = biz_state
        return state

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        # ── Browser strategy ──────────────────────────────────────────────────
        # Priority:
        #   1. Bright Data Scraping Browser (cloud browser — no CAPTCHA, residential IP)
        #   2. Local Chrome via CDP (port 9223 or 9224) if open
        #   3. Local Chrome with Bright Data proxy
        #   4. Plain local Chrome (last resort — will CAPTCHA on heavy scraping)
        browser = None
        ctx     = None
        using_cdp = False

        # Strategy 1: Bright Data Scraping Browser (best — Bright Data runs the browser)
        if _BD_SB_WS and not browser:
            try:
                browser = await p.chromium.connect_over_cdp(_BD_SB_WS)
                using_cdp = True
                print(f"  [Bright Data Scraping Browser — cloud residential IP]")
            except Exception as _sb_err:
                print(f"  [BD Scraping Browser failed: {_sb_err}]")

        # Strategy 2: Local CDP (already-open Chrome)
        if not browser:
            for cdp_port in [9223, 9224]:
                try:
                    browser = await p.chromium.connect_over_cdp(f"http://localhost:{cdp_port}")
                    using_cdp = True
                    print(f"  [CDP connected on port {cdp_port}]")
                    break
                except Exception:
                    pass

        # Strategy 3 & 4: Launch local Chrome, with or without Bright Data proxy
        if not browser:
            is_headless = os.environ.get("HEADLESS", "false").lower() == "true"

            bd_proxy = None
            if _BD_TOKEN and ":" in _BD_TOKEN:
                _bd_user, _bd_pass = _BD_TOKEN.split(":", 1)
                bd_proxy = {
                    "server": "http://brd.superproxy.io:22225",
                    "username": _bd_user,
                    "password": _bd_pass,
                }
                print(f"  [Local Chrome + Bright Data proxy — residential IP]")
            else:
                print(f"  [Real Chrome — headless={is_headless}] (no proxy — CAPTCHA risk)")

            try:
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=is_headless,
                    proxy=bd_proxy,
                    args=["--disable-blink-features=AutomationControlled",
                          "--window-position=0,0", "--window-size=1024,768"],
                )
            except Exception:
                browser = await p.chromium.launch(
                    headless=is_headless,
                    proxy=bd_proxy,
                    args=["--disable-blink-features=AutomationControlled"],
                )

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

        await _sweep(page)

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
async def main_async(businesses: list, target_keyword: str = None, limit: int = None):
    state = load_state()
    for biz_key in businesses:
        if biz_key not in BUSINESSES:
            print(f"  Unknown business: {biz_key} — skipping")
            continue
        biz_cfg = BUSINESSES[biz_key]
        if limit:
            biz_cfg = dict(biz_cfg)
            biz_cfg["keywords"] = biz_cfg["keywords"][:limit]
        print(f"\n[{biz_cfg['name']}]")
        state = await run_business(biz_key, biz_cfg, state, target_keyword)
        save_state(state)
        print(f"  Saved.")
        # Cool-down between businesses to avoid Google rate-limiting / CAPTCHA
        # (serper = JSON API, no Google exposure — token pause only)
        remaining = [b for b in businesses if b != biz_key]
        if remaining:
            delay = 2 if _SERP_PROVIDER == "serper" else random.randint(45, 60)
            print(f"  Cooling down {delay}s before next business...")
            await asyncio.sleep(delay)

    print(f"\nDone. State: {STATE_PATH}")
    if _SERP_PROVIDER == "serper":
        print(f"[serper] {_SERPER_CALLS} queries this run (~${_SERPER_CALLS * 0.0003:.2f}-${_SERPER_CALLS * 0.001:.2f} at $0.30-1.00/1k)")

    # ── Fail-loud gate: a run whose snapshots are mostly errors is a FAILED run ──
    # 2026-07-19: Bright Data account suspension made every scrape return empty →
    # every snapshot errored ("CAPTCHA — IP rate-limited") for 3+ days, yet this
    # script exited 0 and the push step upserted null rows and reported success.
    # Never again: if ≥50% of today's snapshots errored, exit 3 + Telegram Mario.
    today = date.today().isoformat()
    total = errs = 0
    for biz_key in businesses:
        for kw_hist in state.get(biz_key, {}).values():
            snap = kw_hist.get(today)
            if isinstance(snap, dict):
                total += 1
                if snap.get("error"):
                    errs += 1
    if total and errs / total >= 0.5:
        print("\n" + "!" * 70)
        print(f"!! SCRAPE FAILED: {errs}/{total} snapshots errored today.")
        print("!! Likely Bright Data account/zone problem. Check:")
        print("!!   curl -H 'Authorization: Bearer <BD key>' https://api.brightdata.com/status")
        print("!!   ('suspended' = billing — only Mario can fix at brightdata.com)")
        print("!! NOT pushing this as a healthy run. Exit code 3.")
        print("!" * 70)
        try:
            import urllib.parse
            env = {}
            for line in Path("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env").read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
            tok, chat = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_USER_ID", "")
            if tok and chat:
                msg = (f"🚨 Rank tracker FAILED: {errs}/{total} keyword scrapes errored "
                       f"({today}). Bright Data likely suspended/out of credit — "
                       f"check brightdata.com billing. Rankings are NOT updating.")
                data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
                _ureq.urlopen(_ureq.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data), timeout=10)
                print("[alert] Telegram sent to Mario")
        except Exception as e:
            print(f"[alert] Telegram notify failed: {e}")
        return 3
    return 0


def main():
    parser = argparse.ArgumentParser(description="Keyword rank tracker for all client businesses")
    parser.add_argument("--business", choices=list(BUSINESSES.keys()), help="Single business only")
    parser.add_argument("--keyword",  help="Check only keywords containing this string")
    parser.add_argument("--limit", type=int, help="Cap each business at N keywords (testing)")

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

    rc = asyncio.run(main_async(businesses, args.keyword, limit=args.limit))
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
