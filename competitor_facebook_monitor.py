#!/usr/bin/env python3
"""
competitor_facebook_monitor.py — Nightly Facebook page scraper for SPI competitors.

For each competitor with a known fb_url across Yehuda's 4 SPI accounts:
  1. Visits their Facebook page using Yehuda's sniffer profile
  2. Extracts: follower count, last post date, posts in last 7 days, recent post excerpts
  3. Saves dated JSON report to competitor_reports/facebook_YYYY-MM-DD.json
  4. Saves a screenshot per page to competitor_reports/fb_screenshots/

Usage:
  python competitor_facebook_monitor.py                        # all 4 businesses
  python competitor_facebook_monitor.py --business sugar_shack
  python competitor_facebook_monitor.py --business spi_fun_rentals
  python competitor_facebook_monitor.py --headful              # show browser (debug/verify)
  python competitor_facebook_monitor.py --dry-run              # print config, no scraping

Reports saved to:
  competitor_reports/facebook_YYYY-MM-DD.json

Screenshots saved to:
  competitor_reports/fb_screenshots/
"""

import sys
import json
import re
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent
REPORTS_DIR = EXECUTION_DIR / "competitor_reports"
SCREENSHOTS_DIR = REPORTS_DIR / "fb_screenshots"
PROFILE_DIR = EXECUTION_DIR / "facebook_sniffer_profile"  # Yehuda's profile

# ─── Competitor Config — Yehuda's 4 SPI Accounts ─────────────────────────────
# Only competitors WITH fb_url are scraped. None = skip FB check, still in GBP monitor.

COMPETITORS = {
    "sugar_shack": {
        "our_name": "The Sugar Shack",
        "competitors": [
            {
                "name": "Sugar Kingdom",
                "fb_url": None,  # No Facebook page found
            },
            {
                "name": "Sugar Planet",
                "fb_url": None,  # No Facebook page found
            },
            {
                "name": "Turtle Island Souvenir",
                "fb_url": "https://www.facebook.com/p/Turtle-Island-South-Padre-100085620042509/",
            },
        ],
    },
    "island_arcade": {
        "our_name": "Island Arcade",
        "competitors": [],  # Only arcade on SPI — no direct competitors
    },
    "island_candy": {
        "our_name": "Island Candy",
        "competitors": [
            {
                "name": "KIC's Ice Cream",
                "fb_url": "https://www.facebook.com/KICsIceCream/",
            },
            {
                "name": "The Baked Bear SPI",
                "fb_url": "https://www.facebook.com/thebakedbearspi/",
            },
            {
                "name": "Dolce Roma",
                "fb_url": "https://www.facebook.com/Frozenblue123/",
            },
            {
                "name": "Cafe Karma SPI",
                "fb_url": "https://www.facebook.com/cafekarmaSPI/",
            },
        ],
    },
    "spi_fun_rentals": {
        "our_name": "SPI Fun Rentals",
        "competitors": [
            {
                "name": "Paradise Fun Rentals",
                "fb_url": "https://www.facebook.com/paradisefunrentalsspi/",
                # Golf carts + slingshots, 4 locations on SPI
            },
            {
                "name": "Coast to Coast Rentals SPI",
                "fb_url": "https://www.facebook.com/p/Coast-to-Coast-South-Padre-TX-100064982529921/",
                # Golf carts + water sports — most similar to us
            },
        ],
    },
    "juan": {
        "our_name": "Juan Elizondo RE/MAX Elite",
        "competitors": [
            {
                "name": "Deldi Ortegon Group",
                "fb_url": "https://www.facebook.com/DeldiOrtegonGroup/",
            },
            {
                "name": "Maggie Harris Team KW",
                "fb_url": "https://www.facebook.com/TeamMaggieHarris/",
            },
            {
                "name": "Jaime Lee Gonzalez",
                "fb_url": "https://www.facebook.com/jaimeleegonzalez/",
            },
            {
                "name": "Coldwell Banker La Mansion",
                "fb_url": "https://www.facebook.com/ColdwellBankerLaMansionRealEstate/",
            },
        ],
    },
    "custom_designs_tx": {
        "our_name": "Custom Designs TX",
        "competitors": [
            {
                "name": "D-Tronics Home and Business",
                "fb_url": "https://www.facebook.com/DtronicsHomeBusiness/",
            },
            {
                "name": "Mach 1 Media RGV",
                "fb_url": "https://www.facebook.com/m1mtx/",
            },
            {
                "name": "Superior Alarms RGV",
                "fb_url": "https://www.facebook.com/superioralarms/",
            },
            {
                "name": "RGV Geeks",
                "fb_url": "https://www.facebook.com/rgvgeeks/",
            },
        ],
    },
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[fb_competitor] {msg}", flush=True)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def parse_relative_date(text):
    """Convert Facebook relative dates like '2 days ago', 'a day ago', 'Just now', etc. to YYYY-MM-DD."""
    if not text:
        return None
    text = text.lower().strip()
    # Skip notification-style text entirely
    if text.startswith("unread") or "commented on" in text or "followed you" in text or "top fan" in text:
        return None
    now = datetime.now()
    try:
        if text == "recently":
            return now.strftime("%Y-%m-%d")  # Best guess — post is visible, date unreadable
        if "just now" in text or "few seconds" in text or "moments" in text or "yesterday" in text:
            return (now - timedelta(days=1)).strftime("%Y-%m-%d") if "yesterday" in text else now.strftime("%Y-%m-%d")
        # Handle "a day ago", "a week ago", "an hour ago" (non-numeric)
        if re.search(r"\ba\s+(day|week|month|year)\b", text):
            unit = re.search(r"\ba\s+(day|week|month|year)\b", text).group(1)
            if unit == "day":   return (now - timedelta(days=1)).strftime("%Y-%m-%d")
            if unit == "week":  return (now - timedelta(weeks=1)).strftime("%Y-%m-%d")
            if unit == "month": return (now - timedelta(days=30)).strftime("%Y-%m-%d")
            if unit == "year":  return (now - timedelta(days=365)).strftime("%Y-%m-%d")
        if "an hour" in text or "a minute" in text:
            return now.strftime("%Y-%m-%d")
        m = re.search(r"(\d+)\s*(minute|hour|day|week|month|year)", text)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            if "minute" in unit or "hour" in unit:
                return now.strftime("%Y-%m-%d")
            if "day" in unit:
                return (now - timedelta(days=n)).strftime("%Y-%m-%d")
            if "week" in unit:
                return (now - timedelta(weeks=n)).strftime("%Y-%m-%d")
            if "month" in unit:
                return (now - timedelta(days=n * 30)).strftime("%Y-%m-%d")
            if "year" in unit:
                return (now - timedelta(days=n * 365)).strftime("%Y-%m-%d")
        # Try absolute date patterns like "March 14" or "March 14, 2026"
        for fmt in ("%B %d, %Y", "%B %d"):
            try:
                dt = datetime.strptime(text, fmt)
                if dt.year == 1900:
                    dt = dt.replace(year=now.year)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    except Exception:
        pass
    return text  # Return raw text if we can't parse it


def scrape_page(page, competitor, today_str, screenshots_dir):
    """Visit one Facebook competitor page and extract intel."""
    name = competitor["name"]
    fb_url = competitor["fb_url"]
    result = {
        "name": name,
        "fb_url": fb_url,
        "followers": None,
        "last_post_date": None,
        "posts_last_7d": 0,
        "recent_posts": [],
        "status": "ok",
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    if not fb_url:
        result["status"] = "no_fb_page"
        return result

    try:
        # Navigate to the main page.
        page_url = fb_url.rstrip("/") + "/"
        log(f"  Visiting: {name} → {page_url}")
        page.goto(page_url, wait_until="domcontentloaded", timeout=25000)

        # Scroll into the posts area to trigger Facebook's lazy-loading.
        # Without scrolling (especially in headless), post cards never render.
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, 600)")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, 1200)")
        page.wait_for_timeout(1500)

        # Wait for feed if present, otherwise just settle
        try:
            page.wait_for_selector('[role="feed"]', timeout=6000)
            log(f"  Feed element found")
            page.wait_for_timeout(1000)
        except Exception:
            log(f"  No [role=\"feed\"] — posts loaded via lazy scroll")

        # Screenshot
        ss_path = screenshots_dir / f"{slug(name)}_{today_str}.png"
        page.screenshot(path=str(ss_path))
        log(f"  Screenshot saved: {ss_path.name}")

        # ── Extract follower/like count ──────────────────────────────────────
        followers = page.evaluate("""() => {
            // Look for "X followers" text — return only the count portion, not "• X following"
            const spans = Array.from(document.querySelectorAll('span, div, a'));
            for (const s of spans) {
                const t = (s.innerText || '').trim();
                if (t.length < 80 && /followers/i.test(t) && /[\\d]/.test(t)) {
                    // Extract just the followers number e.g. "508 followers" from "508 followers • 19 following"
                    const m = t.match(/^([\d,\\.]+[KMB]?\\s*followers)/i);
                    if (m) return m[1].trim();
                }
            }
            // Fallback: likes count
            for (const s of spans) {
                const t = (s.innerText || '').trim();
                if (t.length < 60 && /people like this|likes/i.test(t) && /\\d/.test(t)) {
                    return t.split('\\n')[0].trim();
                }
            }
            return null;
        }""")
        result["followers"] = followers

        # ── Extract post timestamps and text (scoped to feed, not notifications) ──
        posts_data = page.evaluate("""() => {
            const posts = [];
            const seen = new Set();
            const NOISE = /^(unread|kelsey|congrats|top fan|followed you|commented on|liked your|replied to|reacted to)/i;
            const UI_CHROME = /^(Like|Comment|Share|See more|Follow|Message|View|All reactions|\\d+\\s*(Comment|Share|Like|Reaction))$/i;

            // ── Strategy 1: [role="feed"] → [role="article"] ─────────────────────
            const feed = document.querySelector('[role="feed"]');
            if (feed) {
                const articles = Array.from(feed.querySelectorAll('[role="article"]'));
                for (const article of articles) {
                    const txt = (article.innerText || '').trim();
                    if (txt.length < 30 || NOISE.test(txt)) continue;

                    const timeEl = article.querySelector(
                        'abbr[data-utime], time, a[aria-label*="ago"], a[aria-label*="hour"], a[aria-label*="day"], a[aria-label*="week"], a[aria-label*="month"]'
                    );
                    const timeText = timeEl
                        ? (timeEl.getAttribute('aria-label') || timeEl.getAttribute('title') || timeEl.textContent || '')
                        : '';

                    const lines = txt.split('\\n')
                        .map(l => l.trim())
                        .filter(l => l.length > 15 && !NOISE.test(l) && !UI_CHROME.test(l));
                    const excerpt = lines.slice(0, 2).join(' ').slice(0, 150);
                    const key = excerpt.slice(0, 60);
                    if (excerpt && !seen.has(key)) {
                        seen.add(key);
                        posts.push({ time: timeText.trim(), excerpt, src: 'article' });
                    }
                    if (posts.length >= 8) break;
                }
            }

            // ── Strategy 2: __cft__ tracking links contain post body text ──────────
            // Facebook post cards use relative href=?__cft__[0]=... links for post content.
            // Absolute https://...?__cft__[0]=... links are page identity/byline links (skip them).
            // The timestamp link has scrambled textContent (no aria-label/title).
            // Other relative __cft__ links carry the readable post body text.
            // Filter: require ≥2 real words (4+ letters) to reject scrambled date text.
            if (posts.length === 0) {
                const cftLinks = Array.from(document.querySelectorAll('a[href*="__cft__"]'))
                    .filter(a => {
                        const h = (a.getAttribute('href') || '');
                        return h.startsWith('?__cft__');  // Relative post-content links only
                    });
                // Group by shared href prefix to cluster links from the same post card
                const postGroups = {};
                for (const a of cftLinks) {
                    const href = (a.getAttribute('href') || '').slice(0, 80);
                    if (!postGroups[href]) postGroups[href] = [];
                    postGroups[href].push(a);
                }
                for (const [, linkGroup] of Object.entries(postGroups)) {
                    let excerpt = '';
                    let timeText = '';
                    for (const a of linkGroup) {
                        const txt = (a.textContent || '').trim();
                        const aria = (a.getAttribute('aria-label') || '').trim();
                        // Check for aria-label with page name (post header link)
                        if (aria && !NOISE.test(aria) && aria.length > 3) {
                            // This is the page-name link in the post header — skip for content
                            continue;
                        }
                        // Require ≥2 real words of 4+ letters to reject scrambled date chars
                        const realWords = (txt.match(/\\b[a-zA-Z]{4,}\\b/g) || []);
                        if (realWords.length < 2) continue;
                        // Skip UI chrome
                        if (UI_CHROME.test(txt) || NOISE.test(txt)) continue;
                        // This is readable post content
                        if (txt.length > 15 && txt.length < 500) {
                            excerpt = txt.slice(0, 150);
                            break;
                        }
                    }
                    // Try to get a date from an aria-label on any link in this group
                    for (const a of linkGroup) {
                        const aria = (a.getAttribute('aria-label') || '').trim();
                        if (aria && /\\b(January|February|March|April|May|June|July|August|September|October|November|December|ago|Yesterday)\\b/i.test(aria)) {
                            timeText = aria;
                            break;
                        }
                    }
                    if (!excerpt) continue;
                    const key = excerpt.slice(0, 60);
                    if (!seen.has(key)) {
                        seen.add(key);
                        posts.push({ time: timeText || 'recently', excerpt, src: 'cft-link' });
                    }
                    if (posts.length >= 5) break;
                }
            }

            // ── Strategy 3: elements with date/time in aria-label OR title ──────
            // Facebook CSS-scrambles date innerText but leaves aria-label/title readable
            if (posts.length === 0) {
                const MONTHS = 'January February March April May June July August September October November December';
                const monthSel = MONTHS.split(' ').map(m =>
                    `[aria-label*="${m}"], [title*="${m}"]`
                ).join(', ');
                const ageSel = '[aria-label*=" ago"], [title*=" ago"], [aria-label*="Yesterday"], [title*="Yesterday"]';
                const timeEls = Array.from(document.querySelectorAll(monthSel + ', ' + ageSel));
                for (const el of timeEls) {
                    const timeText = (el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
                    if (!timeText || NOISE.test(timeText)) continue;
                    let bodyEl = el;
                    for (let i = 0; i < 10; i++) {
                        bodyEl = bodyEl.parentElement;
                        if (!bodyEl) break;
                        const t = (bodyEl.innerText || '').trim();
                        if (t.length > 60 && t.length < 4000 && !NOISE.test(t)) {
                            const lines = t.split('\\n')
                                .map(l => l.trim())
                                .filter(l => l.length > 15 && !NOISE.test(l) && !UI_CHROME.test(l));
                            const excerpt = lines.slice(0, 3).join(' ').slice(0, 150);
                            const key = excerpt.slice(0, 60);
                            if (excerpt && !seen.has(key)) {
                                seen.add(key);
                                posts.push({ time: timeText, excerpt, src: 'aria-time' });
                            }
                            break;
                        }
                    }
                    if (posts.length >= 8) break;
                }
            }

            // ── Strategy 4: page-level innerText scan — relative AND absolute dates ─
            if (posts.length === 0) {
                const body = document.body.innerText || '';
                const datePattern = /(\d+\s*(?:minutes?|hours?|days?|weeks?|months?)\s*ago|Yesterday|Just now|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,?\s*\d{4})?)/gi;
                let m;
                while ((m = datePattern.exec(body)) !== null && posts.length < 4) {
                    const timeText = m[0];
                    if (NOISE.test(timeText)) continue;
                    const around = body.substring(Math.max(0, m.index - 400), m.index + 400);
                    const lines = around.split('\\n')
                        .map(l => l.trim())
                        .filter(l => l.length > 20 && !NOISE.test(l) && !UI_CHROME.test(l));
                    const excerpt = lines.slice(0, 3).join(' ').slice(0, 150);
                    const key = excerpt.slice(0, 60);
                    if (excerpt && !seen.has(key)) {
                        seen.add(key);
                        posts.push({ time: timeText, excerpt, src: 'text-scan' });
                    }
                }
            }

            return posts;
        }""")

        # ── Clean-up pass: strip junk prefixes from __cft__ link excerpts ──────
        # __cft__ link textContent includes patterns like "6FqA0k9.comThe Sugar" before post text.
        # Also filters out excerpts that are just the competitor's own page name.
        clean_posts = []
        for p in posts_data:
            exc = p.get("excerpt", "")
            # Strip obfuscated hash + .com prefix: "6FqA0k9.comThe Sugar" → "The Sugar..."
            exc = re.sub(r'^[A-Za-z0-9+/]{4,}\.(com|net|org)', '', exc).strip()
            # Strip "The Sugar[A-Za-z ]*" if it's a prefix from Yehuda's logged-in context
            exc = re.sub(r'^The\s+Sugar\s*(?:Shack\s*)?', '', exc).strip()
            # Truncate before first scrambled token (15+ char no-space mixed-content like "sopadrepoeorsdnSt6")
            exc = re.sub(r'\s*[A-Za-z0-9]{15,}.*$', '', exc).strip()
            # Strip location-only excerpts and known junk patterns
            if re.match(r'^(South Padre Island|SPI|[A-Z][a-z]+ [A-Z][a-z]+, TX)$', exc):
                continue
            if re.match(r'^Photos from ', exc, re.IGNORECASE):
                continue
            if re.match(r"^This content isn't available", exc, re.IGNORECASE):
                continue
            # Require at least 2 real words (4+ letters) to filter page-name-only results
            if len(re.findall(r'\b[a-zA-Z]{4,}\b', exc)) < 2:
                continue
            if exc and len(exc) > 15:
                p["excerpt"] = exc
                clean_posts.append(p)
        posts_data = clean_posts

        # ── Strategy 5 (Python): separator in page.inner_text() ─────────────────
        # Facebook post cards: page_name → scrambled_date → · → POST BODY → "… See more"
        # A short (1-3 char) non-alphanumeric line reliably marks the start of post text.
        if not posts_data:
            try:
                body_text = page.inner_text("body")
                body_lines = [l.strip() for l in body_text.splitlines() if l.strip()]
                # Debug dump: write body text for inspection
                debug_dump = screenshots_dir / f"{slug(name)}_{today_str}_bodytext.txt"
                with open(debug_dump, "w", encoding="utf-8") as _dbf:
                    for _idx, _ln in enumerate(body_lines, 1):
                        _dbf.write(f"{_idx:5d}→{_ln}\n")
                log(f"  Debug dump: {debug_dump.name} ({len(body_text)} chars total)")
                NOISE_PY = re.compile(
                    r'^(unread|kelsey|congrats|top fan|followed you|commented on'
                    r'|liked your|replied to|reacted to|Number of unread)',
                    re.IGNORECASE,
                )
                UI_CHROME_PY = re.compile(
                    r'^(Like|Comment|Share|See more|Follow|Message|View'
                    r'|All reactions|\d+\s*(Comment|Share|Like|Reaction)s?)$',
                    re.IGNORECASE,
                )
                seen_py: set = set()
                for i, line in enumerate(body_lines):
                    # Match any 1-3 char non-alphanumeric separator line (·  •  ·  — etc.)
                    if (1 <= len(line) <= 3
                            and not any(c.isalnum() for c in line)
                            and i + 1 < len(body_lines)):
                        # Take the next substantive line as the post excerpt
                        for j in range(i + 1, min(i + 4, len(body_lines))):
                            candidate = body_lines[j]
                            if (len(candidate) > 15
                                    and not NOISE_PY.match(candidate)
                                    and not UI_CHROME_PY.match(candidate)):
                                key = candidate[:60]
                                if key not in seen_py:
                                    seen_py.add(key)
                                    posts_data.append({
                                        "time": "recently",
                                        "excerpt": candidate[:150],
                                        "src": "dot-sep",
                                    })
                                break
                    if len(posts_data) >= 5:
                        break
                if posts_data:
                    log(f"  Strategy 5 (dot-sep) found {len(posts_data)} posts")
            except Exception as e_py:
                log(f"  Strategy 5 error: {e_py}")

        # Log extraction result
        if posts_data:
            srcs = {p.get("src", "?") for p in posts_data}
            log(f"  Posts found: {len(posts_data)} via strategies {srcs}")
        else:
            log(f"  ⚠ No posts extracted — all strategies exhausted")

        # ── Engagement extraction ────────────────────────────────────────────
        # Scan page body text for reaction/comment/share counts.
        # Facebook shows these as small spans near the post footer (e.g., "47  💬 3  ↗ 2").
        # We match them in document order — i-th match corresponds to i-th post.
        engagement_data = {"reactions": [], "comments": [], "shares": []}
        try:
            engagement_data = page.evaluate("""() => {
                const body = document.body.innerText || '';

                // Reaction counts via aria-label (most reliable)
                const reactionNums = [];
                const reactEls = Array.from(document.querySelectorAll('[aria-label]'));
                for (const el of reactEls) {
                    const lbl = el.getAttribute('aria-label') || '';
                    const m = lbl.match(/(\\d[\\d,]*)\\s+(?:reaction|people reacted)/i);
                    if (m) reactionNums.push(parseInt(m[1].replace(/,/g, ''), 10));
                }

                // Comment counts: "3 comments" (exclude "Comment as" button text)
                const commentNums = [];
                for (const m of body.matchAll(/(\\d[\\d,]*)\\s+[Cc]omments?(?!\\s+as)/g)) {
                    const n = parseInt(m[1].replace(/,/g, ''), 10);
                    if (!isNaN(n)) commentNums.push(n);
                }

                // Share counts
                const shareNums = [];
                for (const m of body.matchAll(/(\\d[\\d,]*)\\s+[Ss]hares?(?!\\s+with)/g)) {
                    const n = parseInt(m[1].replace(/,/g, ''), 10);
                    if (!isNaN(n)) shareNums.push(n);
                }

                return { reactions: reactionNums, comments: commentNums, shares: shareNums };
            }""")
        except Exception as e_eng:
            log(f"  Engagement extraction skipped: {e_eng}")

        cutoff = datetime.now() - timedelta(days=7)
        posts_in_7d = 0
        recent_posts_detail = []

        for i, p in enumerate(posts_data[:10]):
            date_str = parse_relative_date(p.get("time", "")) or today_str
            excerpt = p.get("excerpt", "").strip()

            if excerpt and len(recent_posts_detail) < 3:
                recent_posts_detail.append({
                    "excerpt": excerpt[:120],
                    "date": date_str,
                    "likes": (engagement_data["reactions"][i]
                              if i < len(engagement_data["reactions"]) else 0),
                    "comments": (engagement_data["comments"][i]
                                 if i < len(engagement_data["comments"]) else 0),
                    "shares": (engagement_data["shares"][i]
                               if i < len(engagement_data["shares"]) else 0),
                })

            if date_str:
                try:
                    post_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if post_date >= cutoff:
                        posts_in_7d += 1
                except (ValueError, TypeError):
                    pass

        # Last post date = first (most recent) post
        if posts_data:
            raw_time = posts_data[0].get("time", "")
            result["last_post_date"] = parse_relative_date(raw_time) if raw_time else today_str
        result["posts_last_7d"] = posts_in_7d
        result["recent_posts"] = recent_posts_detail

        log(f"  ✅ {name}: followers={followers}, last_post={result['last_post_date']}, posts_7d={posts_in_7d}")

    except Exception as e:
        log(f"  ❌ {name}: scrape failed — {e}")
        result["status"] = "scrape_failed"
        result["error"] = str(e)
        try:
            ss_err = screenshots_dir / f"{slug(name)}_{today_str}_error.png"
            page.screenshot(path=str(ss_err))
        except Exception:
            pass

    return result


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Competitor Facebook page monitor")
    parser.add_argument("--business", help="Run for one business only (e.g. sugar_shack)")
    parser.add_argument("--headful", action="store_true", help="Show browser window")
    parser.add_argument("--dry-run", action="store_true", help="Print config, no scraping")
    args = parser.parse_args()

    today_str = datetime.now().strftime("%Y-%m-%d")
    output_file = REPORTS_DIR / f"facebook_{today_str}.json"

    # Filter to requested business
    businesses = COMPETITORS
    if args.business:
        if args.business not in COMPETITORS:
            log(f"Unknown business: {args.business}. Options: {list(COMPETITORS.keys())}")
            sys.exit(1)
        businesses = {args.business: COMPETITORS[args.business]}

    # Dry run — just print config
    if args.dry_run:
        print("\n=== Competitor Facebook Monitor — Config ===\n")
        for biz_key, biz in businesses.items():
            print(f"[{biz_key}] {biz['our_name']}")
            for c in biz["competitors"]:
                fb = c["fb_url"] or "❌ No FB page"
                print(f"  • {c['name']}: {fb}")
            print()
        return

    # Ensure output dirs exist
    REPORTS_DIR.mkdir(exist_ok=True)
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    # Load existing report for today (if partial run)
    if output_file.exists():
        with open(output_file, encoding="utf-8") as f:
            all_results = json.load(f)
    else:
        all_results = {}

    # Count total pages to scrape
    total = sum(
        1 for biz in businesses.values()
        for c in biz["competitors"]
        if c.get("fb_url")
    )
    skipped = sum(
        1 for biz in businesses.values()
        for c in biz["competitors"]
        if not c.get("fb_url")
    )
    log(f"Starting Facebook competitor monitor — {total} pages to scrape, {skipped} skipped (no FB page)")
    log(f"Profile: {PROFILE_DIR}")
    log(f"Output: {output_file}")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=not args.headful,
            args=["--start-maximized"],
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()

        for biz_key, biz in businesses.items():
            log(f"\n── {biz['our_name']} ──")
            biz_results = []

            for competitor in biz["competitors"]:
                if not competitor.get("fb_url"):
                    log(f"  Skipping {competitor['name']} — no Facebook page")
                    biz_results.append({
                        "name": competitor["name"],
                        "fb_url": None,
                        "status": "no_fb_page",
                    })
                    continue

                result = scrape_page(page, competitor, today_str, SCREENSHOTS_DIR)
                biz_results.append(result)
                time.sleep(2)  # Polite delay between pages

            all_results[biz_key] = biz_results

            # Save after each business (progress checkpoint)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            log(f"  Saved checkpoint → {output_file.name}")

        context.close()

    log(f"\n✅ Done. Report: {output_file}")
    log(f"   Screenshots: {SCREENSHOTS_DIR}/")

    # Print summary
    print("\n=== Summary ===")
    for biz_key, results in all_results.items():
        biz_name = COMPETITORS.get(biz_key, {}).get("our_name", biz_key)
        print(f"\n{biz_name}:")
        for r in results:
            if r["status"] == "no_fb_page":
                print(f"  • {r['name']}: no FB page")
            elif r["status"] == "scrape_failed":
                print(f"  • {r['name']}: ❌ scrape failed")
            else:
                last = r.get("last_post_date") or "unknown"
                p7d = r.get("posts_last_7d", 0)
                fol = r.get("followers") or "?"
                print(f"  • {r['name']}: last={last}, posts/7d={p7d}, followers={fol}")


if __name__ == "__main__":
    main()
