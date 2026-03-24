#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gbp_morning_check.py — Google Business Profile Daily Monitor
=============================================================
Two-layer approach:
  Layer 1 (always runs): Playwright headless scrape of public Google Maps/Search
           → rating, review count, change detection
  Layer 2 (if Chrome debug is open): CDP-authenticated review fetch
           → unanswered reviews, flags ≤3-star with no reply

Usage:
    python gbp_morning_check.py                    # all 4 accounts
    python gbp_morning_check.py --account sugar_shack
    python gbp_morning_check.py --html             # output HTML for morning_brief

State file: gbp_state.json (auto-created, tracks yesterday's data)
"""

import argparse
import asyncio
import json
import os
import re
import sys
import urllib.parse
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "gbp_config.json"
STATE_PATH  = SCRIPT_DIR / "gbp_state.json"

# ── Load config ────────────────────────────────────────────────────────────────
with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)

ACCESSIBLE = {
    k: v for k, v in CONFIG["accounts"].items() if v.get("access")
}

# Public-scrape-only: access=false but have a places_query (can still get rating/reviews)
PUBLIC_ONLY = {
    k: v for k, v in CONFIG["accounts"].items()
    if not v.get("access") and v.get("places_query")
}


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


# ── Layer 1: Public Google Maps scrape ────────────────────────────────────────
async def scrape_public_maps(account_key: str, account: dict) -> dict:
    """
    Extracts rating + review_count for our business.
    Strategy 1 (fast): Google Places API text search — accurate JSON, no browser.
    Strategy 2 (fallback): Playwright phone-anchored body text extraction.
    """
    from playwright.async_api import async_playwright

    result = {"rating": None, "review_count": None, "error": None}

    # ── Strategy 1: Places API (instant, no browser, accurate) ───────────────
    api_key      = CONFIG.get("places_api_key")
    places_query = account.get("places_query")
    expected     = account.get("expected_name", account.get("name", "")).lower()
    if api_key and places_query:
        try:
            import urllib.request as _req
            q   = urllib.parse.quote_plus(places_query)
            url = (f"https://maps.googleapis.com/maps/api/place/textsearch/json"
                   f"?query={q}&key={api_key}")
            with _req.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
            hits = data.get("results", [])
            if hits:
                top  = hits[0]
                name = top.get("name", "").lower()
                # Verify it's actually our business (at least one key word matches)
                words = [w for w in expected.split() if len(w) > 3]
                if words and any(w in name for w in words):
                    result["rating"]       = top.get("rating")
                    result["review_count"] = top.get("user_ratings_total")
                    return result   # reliable — skip Playwright entirely
        except Exception as e:
            result["error"] = f"Places API: {e}"

    # ── Strategy 2: Playwright phone-anchored scrape (fallback) ──────────────
    query = account["search_query"]
    enc   = urllib.parse.quote_plus(query)
    url   = f"https://www.google.com/maps/search/{enc}/"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx     = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/122.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(4000)

            body_text = ""
            try:
                body_text = await page.inner_text("body")
            except Exception:
                pass

            # ── Phone-anchored extraction (list view) ─────────────────────────
            # Each listing on the search results page has phone below the business
            # name and rating. We anchor on the phone number to read ONLY our entry.
            rating = None
            review_count = None
            phone = account.get("phone", "")
            if phone and body_text:
                phone_digits = re.sub(r'\D', '', phone)[-10:]
                lines = body_text.split('\n')
                anchor_idx = None
                for i, line in enumerate(lines):
                    if phone_digits in re.sub(r'\D', '', line):
                        anchor_idx = i
                        break
                if anchor_idx is not None:
                    window = [l.strip() for l in lines[max(0, anchor_idx - 10):anchor_idx]]
                    # Rating: a standalone float like "3.7" or "4.1"
                    for line in reversed(window):
                        m = re.fullmatch(r'([1-5](?:\.[0-9])?)', line)
                        if m:
                            try:
                                val = float(m.group(1))
                                if 1.0 <= val <= 5.0:
                                    rating = val
                                    break
                            except ValueError:
                                pass
                    # Review count: "X reviews" or explicit "No reviews"
                    no_reviews_flag = False
                    for line in window:
                        if re.search(r'\bno reviews\b', line, re.IGNORECASE):
                            no_reviews_flag = True
                            break
                        m = re.search(r'([\d,]+)\s+reviews?', line, re.IGNORECASE)
                        if m:
                            try:
                                review_count = int(m.group(1).replace(",", ""))
                                break
                            except ValueError:
                                pass
                    # "No reviews" is definitive — do NOT fall through to any other search
                    if no_reviews_flag and review_count is None:
                        review_count = 0

            # ── Click into the correct panel to get review count ──────────────
            # List view often shows rating but not review count. We find the place
            # link whose href contains the business name, click it, then read
            # the review count from the full panel.
            if review_count is None:
                try:
                    biz_name_lower = account.get("name", "").lower()
                    name_words = [w for w in biz_name_lower.split() if len(w) > 3]
                    links = await page.query_selector_all('a[href*="/maps/place/"]')
                    best_link = None
                    best_score = 0
                    for link in links:
                        href = (await link.get_attribute("href") or "").lower()
                        score = sum(1 for w in name_words if w in href)
                        if score > best_score:
                            best_score = score
                            best_link = link
                    if best_link and best_score > 0:
                        await best_link.click()
                        await page.wait_for_timeout(3000)
                        panel_text = await page.inner_text("body")
                        # Look for review count in the panel
                        m = re.search(r'([\d,]+)\s+reviews?', panel_text, re.IGNORECASE)
                        if m:
                            review_count = int(m.group(1).replace(",", ""))
                        elif re.search(r'\bno reviews\b', panel_text, re.IGNORECASE):
                            review_count = 0
                        # Also get rating from panel if we don't have it yet
                        if rating is None:
                            rev_els = await page.query_selector_all('[aria-label*="stars"]')
                            for el in rev_els:
                                lbl = await el.get_attribute("aria-label") or ""
                                m2 = re.search(r'([1-5](?:\.[0-9])?)', lbl)
                                if m2:
                                    val = float(m2.group(1))
                                    if 1.0 <= val <= 5.0:
                                        rating = val
                                        break
                except Exception:
                    pass

            html = await page.content()
            await browser.close()

        # ── HTML JSON-LD fallback (last resort) ───────────────────────────────
        if rating is None:
            star_els_html = re.findall(r'aria-label="([^"]*stars[^"]*)"', html, re.IGNORECASE)
            for lbl in star_els_html:
                m = re.search(r'([1-5](?:\.[0-9])?)', lbl)
                if m:
                    val = float(m.group(1))
                    if 1.0 <= val <= 5.0:
                        rating = val
                        break
        if review_count is None:
            m = re.search(r'"reviewCount"\s*:\s*"?(\d+)"?', html, re.IGNORECASE)
            if m:
                try:
                    review_count = int(m.group(1))
                except ValueError:
                    pass

        result["rating"]       = rating
        result["review_count"] = review_count

    except Exception as e:
        result["error"] = str(e)

    return result


# ── Layer 2: Authenticated CDP review fetch ────────────────────────────────────
async def fetch_authenticated_reviews(account_key: str, account: dict) -> list:
    """
    Connect via CDP to the already-open debug Chrome.
    Fetch reviews using the same batchexecute RPC as gbp_reviews.py.
    Returns list of review dicts, or empty list if Chrome isn't open.
    """
    port        = account["chrome_port"]
    business_id = account["business_id"]

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp(
                    f"http://localhost:{port}", timeout=4000
                )
                print(f"  [2] CDP connected, contexts={len(browser.contexts)}")
            except Exception:
                return []   # Chrome not open — silent skip

            context = browser.contexts[0]
            pages = context.pages
            page    = pages[0] if pages else None
            if not page:
                await browser.close()
                return []

            # Navigate to GBP post page — this embeds valid CSRF tokens
            token_url = (
                f"https://www.google.com/local/business/{business_id}"
                f"/promote/updates/add?knm=0&ih=lu&hl=en"
            )
            await page.goto(token_url)
            await page.wait_for_timeout(4000)

            # Extract tokens
            html = await page.content()
            at_m = re.search(r'"SNlM0e":"([^"]+)"', html)
            fs_m = re.search(r'"FdrFJe":"([^"]+)"', html)
            bl_m = re.search(r'"cfb2h":"([^"]+)"',  html)

            at_token = at_m.group(1) if at_m else None
            fsid     = fs_m.group(1) if fs_m else None
            bl       = bl_m.group(1) if bl_m else None

            if not at_token:
                await browser.close()
                return []

            # Fire review RPC
            inner = json.dumps(
                [business_id, None, 10, None, None, None, [1, 2, 3, 4, 5]],
                separators=(',', ':')
            )
            freq = json.dumps(
                [[["Bfzk6d", inner, None, "generic"]]],
                separators=(',', ':')
            )
            source_path = f"/local/business/{business_id}/promote/updates/add"
            rpc_url = (
                "https://www.google.com/local/business/_/GeoMerchantFrontendEmbeddedUi"
                f"/data/batchexecute?rpcids=Bfzk6d"
                f"&source-path={source_path.replace('/', '%2F')}"
                f"&f.sid={fsid}&bl={bl}"
                f"&hl=en&ih=lu&soc-app=664&soc-platform=1&soc-device=1&_reqid=12345&rt=c"
            )
            body = urllib.parse.urlencode({'f.req': freq, 'at': at_token}) + '&'

            rpc_result = await page.evaluate(f"""async () => {{
                const resp = await fetch('{rpc_url}', {{
                    method: 'POST',
                    headers: {{
                        'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'x-same-domain': '1',
                        'x-goog-ext-266792519-jspb': '["lu"]',
                    }},
                    body: {json.dumps(body)}
                }});
                return {{ status: resp.status, body: await resp.text() }};
            }}""")

            await browser.close()

            if rpc_result["status"] != 200:
                return []

            raw = rpc_result["body"]
            if raw.startswith(")]}'"):
                raw = raw[4:].strip()

            reviews = _parse_reviews(json.loads(raw))
            return reviews

    except Exception:
        return []


def _parse_reviews(data) -> list:
    """Recursively extract review dicts from GBP batchexecute response."""
    reviews = []
    if not isinstance(data, list):
        return reviews

    def walk(lst):
        found = []
        for item in lst:
            if not isinstance(item, list) or len(item) < 3:
                continue
            try:
                if isinstance(item[0], str) and isinstance(item[2], int) and 1 <= item[2] <= 5:
                    found.append({
                        "id":       item[0],
                        "reviewer": item[1] if len(item) > 1 else "Anonymous",
                        "stars":    item[2],
                        "text":     item[3] if len(item) > 3 and isinstance(item[3], str) else "",
                        "reply":    item[5] if len(item) > 5 and isinstance(item[5], str) else None,
                    })
            except Exception:
                pass
            found.extend(walk(item))
        return found

    return walk(data)


# ── Main check logic ───────────────────────────────────────────────────────────
async def check_account(account_key: str, account: dict, state: dict) -> dict:
    print(f"\n[CHECK] {account['name']}")

    prev = state.get(account_key, {})

    # Layer 1 — public scrape
    print(f"  [1] Public scrape...")
    pub = await scrape_public_maps(account_key, account)
    rating       = pub["rating"]
    review_count = pub["review_count"]

    if pub["error"]:
        print(f"  [1] Error: {pub['error']}")
    else:
        print(f"  [1] Rating: {rating}  |  Reviews: {review_count}")

    # Compute deltas
    prev_rating = prev.get("rating")
    prev_count  = prev.get("review_count")
    rating_delta    = round(rating - prev_rating, 1) if (rating and prev_rating) else None
    new_review_count = (review_count - prev_count) if (review_count and prev_count) else None

    # Layer 2 — authenticated review fetch (only for accounts with GBP access)
    reviews = []
    if account.get("access"):
        print(f"  [2] Authenticated review fetch (port {account['chrome_port']})...")
        reviews = await fetch_authenticated_reviews(account_key, account)
        if reviews:
            print(f"  [2] Got {len(reviews)} reviews via CDP")
        else:
            print(f"  [2] Chrome not open or not connected — skipping authenticated check")
    else:
        print(f"  [2] Skipping authenticated check (access=false — public scrape only)")

    # Build alerts
    alerts = []
    if rating_delta is not None and rating_delta < -0.1:
        alerts.append(f"Rating dropped {rating_delta:+.1f} (now {rating})")
    if new_review_count and new_review_count > 0:
        alerts.append(f"{new_review_count} new review(s) since yesterday")

    low_star_unanswered = [
        r for r in reviews
        if r["stars"] <= 3 and not r["reply"]
    ]
    for r in low_star_unanswered:
        stars_str = "⭐" * r["stars"]
        snippet   = r["text"][:80] + "..." if len(r["text"]) > 80 else r["text"]
        alerts.append(f"{stars_str} unanswered — {r['reviewer']}: \"{snippet}\"")

    status = "alert" if alerts else "ok"
    if pub["error"] and not rating:
        status = "error"

    result = {
        "name":          account["name"],
        "rating":        rating,
        "review_count":  review_count,
        "rating_delta":  rating_delta,
        "new_reviews":   new_review_count,
        "alerts":        alerts,
        "status":        status,
        "checked_today": str(date.today()),
    }

    # Update state
    state[account_key] = {
        "rating":        rating       or prev.get("rating"),
        "review_count":  review_count or prev.get("review_count"),
        "last_checked":  str(date.today()),
    }

    return result


async def run_all(account_filter: str | None = None) -> dict:
    state   = load_state()
    results = {}

    # All accounts to process: authenticated + public-only
    all_accounts = {**ACCESSIBLE, **PUBLIC_ONLY}

    if account_filter:
        targets = {account_filter: all_accounts[account_filter]} if account_filter in all_accounts else {}
    else:
        targets = all_accounts

    for key, account in targets.items():
        results[key] = await check_account(key, account, state)

    save_state(state)
    return results


# ── Output formatters ──────────────────────────────────────────────────────────
def print_summary(results: dict):
    print("\n" + "=" * 65)
    print("  GOOGLE BUSINESS PROFILE — MORNING CHECK")
    print("=" * 65)
    for key, r in results.items():
        status_icon = "✅" if r["status"] == "ok" else ("⚠️" if r["status"] == "alert" else "❌")
        rating_str  = f"{r['rating']}" if r["rating"] else "?"
        if r["rating_delta"] is not None:
            rating_str += f" ({r['rating_delta']:+.1f})"
        count_str   = str(r["review_count"]) if r["review_count"] else "?"
        print(f"\n  {status_icon} {r['name']}")
        print(f"     Rating  : {rating_str}  |  Reviews: {count_str}")
        if r["alerts"]:
            for alert in r["alerts"]:
                print(f"     ⚠️  {alert}")
        else:
            print(f"     No alerts")
    print("\n" + "=" * 65)


def render_html_snippet(results: dict) -> str:
    rows = ""
    for key, r in results.items():
        status_icon = "✅" if r["status"] == "ok" else ("⚠️" if r["status"] == "alert" else "❌")
        rating_str  = f"{r['rating']}" if r["rating"] else "?"
        if r["rating_delta"] is not None:
            color = "#e74c3c" if r["rating_delta"] < 0 else "#27ae60"
            rating_str += f' <span style="color:{color};font-size:12px">({r["rating_delta"]:+.1f})</span>'
        count_str    = str(r["review_count"]) if r["review_count"] else "?"
        alerts_html  = "".join(f'<div style="color:#e67e22;font-size:12px">⚠️ {a}</div>' for a in r["alerts"])
        alert_cell   = alerts_html or '<span style="color:#27ae60">None</span>'
        rows += f"""
        <tr>
          <td style="padding:8px 12px;font-weight:600">{status_icon} {r['name']}</td>
          <td style="padding:8px 12px;text-align:center">⭐ {rating_str}</td>
          <td style="padding:8px 12px;text-align:center">{count_str}</td>
          <td style="padding:8px 12px">{alert_cell}</td>
        </tr>"""

    return f"""
<div style="margin:24px 0">
  <h2 style="color:#1a1a2e;margin-bottom:12px">📍 Google Business Profiles</h2>
  <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 8px rgba(0,0,0,.1)">
    <thead>
      <tr style="background:#1a1a2e;color:#fff">
        <th style="padding:10px 12px;text-align:left">Account</th>
        <th style="padding:10px 12px">Rating</th>
        <th style="padding:10px 12px">Reviews</th>
        <th style="padding:10px 12px;text-align:left">Alerts</th>
      </tr>
    </thead>
    <tbody>{rows}
    </tbody>
  </table>
</div>"""


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="GBP Morning Check")
    parser.add_argument("--account", default=None,
                        help="Single account key (e.g. sugar_shack)")
    parser.add_argument("--html", action="store_true",
                        help="Output HTML snippet instead of terminal summary")
    args = parser.parse_args()

    results = asyncio.run(run_all(args.account))

    if args.html:
        print(render_html_snippet(results))
    else:
        print_summary(results)


if __name__ == "__main__":
    main()
