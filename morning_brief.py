#!/usr/bin/env python3
"""
morning_brief.py — Daily synthesis report for all 8 client businesses.

Reads from:
  - {business}/program.md          (posting log, current priorities, what's working)
  - {business}/engagement_history.json  (angle performance scores)
  - competitor_reports/YYYY-MM-DD.md    (overnight competitor intel)
  - competitor_reports/state.json       (competitor rating changes)

Generates:
  - morning_briefs/YYYY-MM-DD.md   (markdown)
  - morning_briefs/YYYY-MM-DD.html (dark-themed browser view)

Google Calendar + Gmail via GWS helper scripts. Screenpipe attention via local REST API.

Usage:
  python morning_brief.py                        # all businesses, MD + HTML
  python morning_brief.py --open                 # auto-opens HTML in browser
  python morning_brief.py --text-only            # markdown only, no HTML
  python morning_brief.py --business sugar_shack # single business
"""

import sys
import json
import re
import argparse
import webbrowser
from pathlib import Path
from datetime import date, datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _run_fb_health_check_silent() -> list:
    """Run fb_health_check.py in headless mode and return results as a list of dicts.
    Each dict: {page, profile, status: OK|WARN|FAIL, detail}
    Runs silently — no browser window opens."""
    import json as _json
    import time as _time
    from playwright.sync_api import sync_playwright as _swp

    config_path = EXECUTION_DIR / "fb_pages_config.json"
    with open(config_path) as f:
        config = _json.load(f)

    pages = config["pages"]
    default_profile = config.get("auth_profile", "facebook_sniffer_profile")

    # Group pages by profile to open each browser only once
    profile_groups: dict = {}
    for key, info in pages.items():
        profile = info.get("auth_profile", default_profile)
        profile_groups.setdefault(profile, []).append((key, info))

    results = []
    with _swp() as p:
        for profile, page_list in profile_groups.items():
            full_profile = str(EXECUTION_DIR / profile)
            try:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=full_profile,
                    headless=True,
                    args=["--no-sandbox"],
                    viewport={"width": 1280, "height": 900}
                )
                pg = ctx.new_page()
                pg.goto("https://www.facebook.com/pages/?category=your_pages", timeout=15000)
                _time.sleep(3)

                session_ok = "login" not in pg.url.lower()
                heading_el = pg.locator("h1, h2").first
                account_name = heading_el.inner_text(timeout=3000) if heading_el.count() > 0 else "unknown"

                for page_key, page_info in page_list:
                    page_id = str(page_info.get("page_id", ""))
                    if not session_ok:
                        results.append({"page": page_key, "profile": profile,
                                        "status": "FAIL", "detail": "Session expired — run reauth"})
                        continue
                    link_count = pg.locator(f'a[href*="{page_id}"]').count() if page_id else 0
                    if link_count == 0:
                        results.append({"page": page_key, "profile": profile,
                                        "status": "FAIL",
                                        "detail": f"Page not on this account (got: {account_name})"})
                        continue
                    try:
                        btn = pg.locator(f'div:has(a[href*="{page_id}"]) [aria-label="Create post"]').first
                        btn.wait_for(state="visible", timeout=4000)
                        results.append({"page": page_key, "profile": profile,
                                        "status": "OK", "detail": account_name})
                    except Exception:
                        results.append({"page": page_key, "profile": profile,
                                        "status": "WARN",
                                        "detail": f"Page found, composer button not visible ({account_name})"})
                ctx.close()
            except Exception as e:
                for page_key, _ in page_list:
                    results.append({"page": page_key, "profile": profile,
                                    "status": "FAIL", "detail": str(e)[:100]})
    return results

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent
BRIEFS_DIR = EXECUTION_DIR / "morning_briefs"
COMPETITOR_REPORTS_DIR = EXECUTION_DIR / "competitor_reports"
COMPETITOR_STATE = COMPETITOR_REPORTS_DIR / "state.json"

BUSINESS_DIRS = {
    "sugar_shack":      EXECUTION_DIR / "sugar_shack",
    "island_arcade":    EXECUTION_DIR / "island_arcade",
    "island_candy":     EXECUTION_DIR / "island_candy",
    "juan":             EXECUTION_DIR / "juan",
    "spi_fun_rentals":  EXECUTION_DIR / "spi_fun_rentals",
    "custom_designs_tx": EXECUTION_DIR / "custom_designs_tx",
    "optimum_clinic":   EXECUTION_DIR / "optimum_clinic",
    "optimum_foundation": EXECUTION_DIR / "optimum_foundation",
}

BUSINESS_NAMES = {
    "sugar_shack":       "The Sugar Shack",
    "island_arcade":     "Island Arcade",
    "island_candy":      "Island Candy",
    "juan":              "Juan Elizondo RE/MAX Elite",
    "spi_fun_rentals":   "SPI Fun Rentals",
    "custom_designs_tx": "Custom Designs TX",
    "optimum_clinic":    "Optimum Health & Wellness Clinic",
    "optimum_foundation":"Optimum Health and Wellness Foundation",
}

BUSINESS_ICONS = {
    "sugar_shack":       "🍬",
    "island_arcade":     "🕹️",
    "island_candy":      "🍦",
    "juan":              "🏠",
    "spi_fun_rentals":   "🏖️",
    "custom_designs_tx": "📺",
    "optimum_clinic":    "🏥",
    "optimum_foundation":"❤️",
}

# Days without a post before flagging as overdue
OVERDUE_THRESHOLD = 4

# ─── Seasonal Hooks ───────────────────────────────────────────────────────────

SEASONAL_HOOKS = [
    {"name": "Spring Break peak", "start": "03-08", "end": "03-28",
     "businesses": ["sugar_shack", "island_arcade", "island_candy", "spi_fun_rentals"],
     "tip": "High-traffic window — post every 2-3 days minimum"},
    {"name": "Easter weekend", "start": "04-18", "end": "04-20",
     "businesses": ["all"],
     "tip": "Family travel spike — lead with family-friendly angles"},
    {"name": "Cinco de Mayo", "start": "05-04", "end": "05-05",
     "businesses": ["sugar_shack", "island_arcade", "island_candy", "spi_fun_rentals", "juan"],
     "tip": "RGV/SPI bilingual celebration — post in Spanish"},
    {"name": "Memorial Day weekend", "start": "05-23", "end": "05-26",
     "businesses": ["all"],
     "tip": "Major SPI travel weekend — start promotions 5 days early"},
    {"name": "Summer peak", "start": "06-01", "end": "08-15",
     "businesses": ["sugar_shack", "island_arcade", "island_candy", "spi_fun_rentals"],
     "tip": "Max posting frequency — heat/relief angles work for SPI businesses"},
    {"name": "4th of July", "start": "07-03", "end": "07-05",
     "businesses": ["all"],
     "tip": "SPI fireworks weekend — one of the biggest traffic weekends of year"},
    {"name": "Back to school", "start": "08-10", "end": "08-25",
     "businesses": ["optimum_clinic", "optimum_foundation"],
     "tip": "Kids need physicals and screenings — strong angle for clinic and foundation"},
    {"name": "Labor Day weekend", "start": "08-29", "end": "09-01",
     "businesses": ["all"],
     "tip": "Last big summer weekend — use urgency/end-of-season angles"},
    {"name": "Flu season", "start": "10-01", "end": "02-28",
     "businesses": ["optimum_clinic"],
     "tip": "Rapid test angle, walk-in convenience — highest ROI season for clinic"},
    {"name": "Holiday shopping", "start": "11-25", "end": "12-24",
     "businesses": ["sugar_shack", "island_arcade", "island_candy", "custom_designs_tx"],
     "tip": "Gift ideas and home theater installs — strong angle for Custom Designs"},
    {"name": "New Year / Resolution season", "start": "01-01", "end": "01-15",
     "businesses": ["optimum_clinic", "optimum_foundation"],
     "tip": "Health resolutions — diabetes/hypertension awareness for foundation"},
    {"name": "Valentine's Day", "start": "02-10", "end": "02-14",
     "businesses": ["island_candy", "island_arcade", "spi_fun_rentals"],
     "tip": "Couples angle — date night, sweet treats, beach getaway"},
]


def get_active_seasonal_hooks(today: date, businesses: list, lookahead_days: int = 14) -> list:
    """Return seasonal hooks active today or starting within lookahead_days."""
    active = []
    for hook in SEASONAL_HOOKS:
        # Build start/end date objects for this year (and next year wrap for flu season)
        year = today.year
        try:
            start = date(year, int(hook["start"].split("-")[0]), int(hook["start"].split("-")[1]))
            end_m, end_d = int(hook["end"].split("-")[0]), int(hook["end"].split("-")[1])
            end = date(year, end_m, end_d)
            # Handle year wrap (e.g., flu season Oct -> Feb)
            if end < start:
                end = date(year + 1, end_m, end_d)
        except ValueError:
            continue

        window_start = today
        window_end = today + timedelta(days=lookahead_days)

        # Check if hook overlaps with [today, today+lookahead]
        if start <= window_end and end >= window_start:
            # Check business relevance
            hook_businesses = hook["businesses"]
            if hook_businesses == ["all"] or any(b in hook_businesses for b in businesses):
                relevant_for = [b for b in businesses if hook_businesses == ["all"] or b in hook_businesses]
                days_until = max(0, (start - today).days)
                active.append({
                    "name": hook["name"],
                    "days_until": days_until,
                    "end": end,
                    "tip": hook["tip"],
                    "relevant_for": relevant_for,
                })

    return sorted(active, key=lambda x: x["days_until"])

# ─── program.md Parsers ───────────────────────────────────────────────────────

def read_program_md(business_key: str) -> str:
    path = BUSINESS_DIRS[business_key] / "program.md"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def parse_current_priorities(md_text: str) -> list:
    """Extract unchecked [ ] items from Current Priorities section that have real content."""
    priorities = []
    in_section = False
    for line in md_text.splitlines():
        if "## Current Priorities" in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and re.match(r'- \[ \]', line):
            # Only include if the line has real content (not just "_(fill in)_")
            content = re.sub(r'- \[ \]\s*\*\*[^*]+\*\*:?\s*', '', line).strip()
            label_match = re.search(r'\*\*([^*]+)\*\*', line)
            label = label_match.group(1) if label_match else line[6:].strip()
            if content and "fill in" not in content.lower():
                priorities.append({"label": label, "value": content})
            elif "fill in" not in label.lower():
                priorities.append({"label": label, "value": None})
    return priorities


def parse_posting_log(md_text: str) -> list:
    """Extract rows from the Posting Log table."""
    posts = []
    in_log = False
    header_parsed = False
    for line in md_text.splitlines():
        if "## Posting Log" in line:
            in_log = True
            header_parsed = False
            continue
        if in_log and line.startswith("## "):
            break
        if in_log and line.startswith("|"):
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if not cells:
                continue
            if not header_parsed:
                header_parsed = True
                continue  # skip header row
            if all(c.startswith("-") for c in cells):
                continue  # skip separator row
            if cells and "add after each post" not in cells[0].lower() and "fill in" not in cells[0].lower():
                posts.append(cells)
    return posts


def days_since_last_post(posting_log: list) -> int | None:
    """Parse the most recent post date from the log and return days since."""
    latest = None
    for row in posting_log:
        if not row:
            continue
        date_str = row[0].strip()
        if not date_str or date_str.startswith("_"):
            continue
        # Try common date formats
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
            try:
                d = datetime.strptime(date_str, fmt).date()
                if latest is None or d > latest:
                    latest = d
                break
            except ValueError:
                continue
    if latest is None:
        return None
    return (date.today() - latest).days


def parse_whats_working(md_text: str) -> list:
    """Extract non-placeholder bullet points from What's Working section."""
    items = []
    in_section = False
    for line in md_text.splitlines():
        if "## What's Working" in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("- ") and "add observations" not in line and "_(e.g." not in line:
            items.append(line[2:].strip())
    return items

# ─── Engagement History ───────────────────────────────────────────────────────

def load_engagement_history(business_key: str) -> list:
    path = BUSINESS_DIRS[business_key] / "engagement_history.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def get_top_angles(business_key: str, n: int = 3) -> list:
    """Return top N angles by avg weighted score (min 1 post)."""
    history = load_engagement_history(business_key)
    if not history:
        return []
    by_angle: dict = {}
    for entry in history:
        angle = entry.get("angle", "unknown")
        if angle not in by_angle:
            by_angle[angle] = []
        by_angle[angle].append(entry.get("score", 0))
    ranked = sorted(
        [{"angle": a, "avg": sum(s) / len(s), "count": len(s)} for a, s in by_angle.items()],
        key=lambda x: x["avg"],
        reverse=True,
    )
    return ranked[:n]

# ─── Keyword Rankings ─────────────────────────────────────────────────────────

def load_keyword_rankings() -> dict:
    """Load keyword ranking summary — only current config keywords (no stale data)."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "keyword_rank_tracker",
            Path(__file__).parent / "keyword_rank_tracker.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        all_rankings = mod.load_rankings_summary()

        # Filter to only keywords currently in config (removes stale/retired keywords)
        try:
            cfg_path = Path(__file__).parent / "keyword_rankings_config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            active_keywords = {
                biz: set(biz_data["keywords"])
                for biz, biz_data in cfg.get("businesses", {}).items()
            }
            return {
                biz: {kw: data for kw, data in kw_dict.items()
                      if kw in active_keywords.get(biz, set())}
                for biz, kw_dict in all_rankings.items()
                if biz in active_keywords
            }
        except Exception:
            return all_rankings
    except Exception:
        return {}


def _rank_badge(position: int | None, delta: int | None) -> str:
    """Format a rank position with color and delta arrow for HTML."""
    if position is None:
        return '<span style="color:#8b949e">—</span>'
    # Color: 1-3 green, 4-7 yellow, 8+ orange
    color = "#3fb950" if position <= 3 else ("#d29922" if position <= 7 else "#e3763f")
    badge = f'<span style="color:{color};font-weight:700">#{position}</span>'
    if delta is not None and delta != 0:
        if delta > 0:  # improved (lower number = higher rank)
            badge += f' <span style="color:#3fb950;font-size:11px">▲{delta}</span>'
        else:
            badge += f' <span style="color:#f85149;font-size:11px">▼{abs(delta)}</span>'
    elif delta == 0:
        badge += ' <span style="color:#8b949e;font-size:11px">—</span>'
    return badge


def generate_keyword_rankings_html(rankings: dict) -> str:
    """Generate HTML section for keyword rankings — one table per business."""
    if not rankings:
        return '<p style="color:#8b949e">No ranking data yet. Run: <code>python keyword_rank_tracker.py</code></p>'

    # Map tracker business keys to morning brief display names
    BIZ_DISPLAY = {
        "spi_fun_rentals":    "SPI Fun Rentals",
        "sugar_shack":        "The Sugar Shack",
        "island_arcade":      "Island Arcade",
        "island_candy":       "Island Candy",
        "custom_designs_tx":  "Custom Designs TX",
        "optimum_clinic":     "Optimum Clinic",
        "juan":               "Juan Elizondo RE/MAX",
        "optimum_foundation": "Optimum Foundation",
    }

    html_parts = []
    for biz_key, kw_data in rankings.items():
        name = BIZ_DISPLAY.get(biz_key, biz_key)
        if not kw_data:
            continue

        # Check last date
        dates = [v["date"] for v in kw_data.values() if v.get("date")]
        last_date = max(dates) if dates else "—"

        rows = []
        for keyword, info in kw_data.items():
            mp_pos      = info.get("map_pack_position")
            maps_pos    = info.get("maps_position")
            org_pos     = info.get("organic_position")
            mp_delta    = info.get("map_pack_delta")
            maps_delta  = info.get("maps_delta")
            org_delta   = info.get("organic_delta")

            # Position column: 3-pack wins, else extended maps, else organic
            if mp_pos:
                pos_badge = _rank_badge(mp_pos, mp_delta)
                pos_label = '<span style="color:#8b949e;font-size:10px">3-pack</span>'
            elif maps_pos:
                pos_badge = _rank_badge(maps_pos, maps_delta)
                pos_label = f'<span style="color:#8b949e;font-size:10px">maps #{maps_pos}</span>'
            else:
                pos_badge = '<span style="color:#8b949e;font-size:11px">Not ranking</span>'
                pos_label = ''

            org_badge = _rank_badge(org_pos, org_delta)

            # Top 3 from Maps full list — prefer top3_maps_entries (has reviews), fallback to map_pack then organic
            top3_entries = [e for e in info.get("top3_maps_entries", []) if e.get("name")][:3]
            if not top3_entries:
                top3_entries = [e for e in info.get("top3_map_pack", []) if e.get("name")][:3]
            if not top3_entries:
                top3_entries = [{"name": e["title"], "rating": "", "reviews": ""}
                                for e in info.get("top3_organic", []) if not e.get("is_ours")][:3]
            top3_str = " · ".join(
                f"{e['name'][:28]} ⭐{e.get('rating','')}({e.get('reviews','?')})"
                for e in top3_entries
            ) if top3_entries else "—"

            rows.append(
                f'<tr style="border-bottom:1px solid #21262d">'
                f'<td style="color:#e6edf3;padding:6px 8px;max-width:240px">{keyword}</td>'
                f'<td style="text-align:center;padding:6px 8px;white-space:nowrap">{pos_badge}<br>{pos_label}</td>'
                f'<td style="text-align:center;padding:6px 8px;white-space:nowrap">{org_badge}</td>'
                f'<td style="color:#8b949e;font-size:12px;padding:6px 8px">{top3_str}</td>'
                f'</tr>'
            )

        table = (
            f'<p style="color:#e6edf3;font-weight:700;margin:16px 0 6px">{name}'
            f'<span style="color:#8b949e;font-weight:400;font-size:12px;margin-left:10px">as of {last_date}</span></p>'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
            f'<thead><tr style="border-bottom:1px solid #30363d">'
            f'<th style="text-align:left;padding:4px 8px;color:#8b949e;font-weight:400">Keyword</th>'
            f'<th style="padding:4px 8px;color:#8b949e;font-weight:400">Local Rank</th>'
            f'<th style="padding:4px 8px;color:#8b949e;font-weight:400">Organic</th>'
            f'<th style="text-align:left;padding:4px 8px;color:#8b949e;font-weight:400">Top 3 in Google Maps</th>'
            f'</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody>'
            f'</table>'
        )
        html_parts.append(table)

    return "".join(html_parts) if html_parts else (
        '<p style="color:#8b949e">No ranking data. Run: <code>python keyword_rank_tracker.py</code></p>'
    )


# ─── Competitor Intelligence ──────────────────────────────────────────────────

def load_competitor_state() -> dict:
    if COMPETITOR_STATE.exists():
        try:
            return json.loads(COMPETITOR_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def get_competitor_alerts(business_key: str, state: dict) -> list:
    """Find competitor entries for this business with notable data."""
    alerts = []
    prefix = f"{business_key}__"
    for key, data in state.items():
        if key.startswith(prefix):
            comp_name = key[len(prefix):]
            rating = data.get("rating")
            count = data.get("review_count")
            checked = data.get("last_checked", "")
            if rating or count:
                alerts.append({
                    "name": comp_name,
                    "rating": rating,
                    "review_count": count,
                    "last_checked": checked,
                })
    return alerts


def get_latest_competitor_report() -> str:
    """Return text of the most recent competitor report file."""
    reports = sorted(COMPETITOR_REPORTS_DIR.glob("*.md"), reverse=True)
    if reports:
        try:
            return reports[0].read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return ""


def load_fb_competitor_report() -> dict:
    """Load today's Facebook competitor report if it exists, else most recent."""
    from datetime import date as _date
    today_str = _date.today().strftime("%Y-%m-%d")
    # Try today first, then fall back to most recent
    candidates = [COMPETITOR_REPORTS_DIR / f"facebook_{today_str}.json"]
    candidates += sorted(COMPETITOR_REPORTS_DIR.glob("facebook_*.json"), reverse=True)
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def load_adlibrary_report() -> dict:
    """Load today's Ad Library report if it exists, else most recent."""
    from datetime import date as _date
    today_str = _date.today().strftime("%Y-%m-%d")
    candidates = [COMPETITOR_REPORTS_DIR / f"adlibrary_{today_str}.json"]
    candidates += sorted(COMPETITOR_REPORTS_DIR.glob("adlibrary_*.json"), reverse=True)
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def load_ai_analysis() -> list:
    """Load today's AI competitor analysis if it exists, else most recent."""
    from datetime import date as _date
    today_str = _date.today().strftime("%Y-%m-%d")
    candidates = [COMPETITOR_REPORTS_DIR / f"ai_analysis_{today_str}.json"]
    candidates += sorted(COMPETITOR_REPORTS_DIR.glob("ai_analysis_*.json"), reverse=True)
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return []


def load_review_report() -> dict:
    """Load today's Google Review mining report if it exists, else most recent."""
    from datetime import date as _date
    today_str = _date.today().strftime("%Y-%m-%d")
    candidates = [COMPETITOR_REPORTS_DIR / f"reviews_{today_str}.json"]
    candidates += sorted(COMPETITOR_REPORTS_DIR.glob("reviews_*.json"), reverse=True)
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def load_delta_report() -> dict:
    """Load today's delta (movements) report if it exists, else most recent."""
    from datetime import date as _date
    today_str = _date.today().strftime("%Y-%m-%d")
    candidates = [COMPETITOR_REPORTS_DIR / f"delta_{today_str}.json"]
    candidates += sorted(COMPETITOR_REPORTS_DIR.glob("delta_*.json"), reverse=True)
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def render_movements_html(delta: dict) -> str:
    """
    Render the 'Movements Since Yesterday' card for the morning brief HTML.
    Returns an HTML string. Returns '' if no baseline or nothing changed.
    """
    if not delta or not delta.get("has_baseline"):
        baseline_date = delta.get("baseline_date") if delta else None
        if not baseline_date:
            return (
                '<div style="background:#161b22;border:1px solid #30363d;border-left:3px solid #58a6ff;'
                'border-radius:6px;padding:14px 18px;font-size:13px;color:#8b949e">'
                'Baseline not yet established. Run <code>delta_tracker.py</code> again tomorrow '
                'to see what changed.</div>'
            )
        return ""

    kw_moves    = delta.get("keyword_movements", [])
    gbp_changes = delta.get("competitor_rating_changes", [])
    ad_changes  = delta.get("ad_activity_changes", [])
    baseline    = delta.get("baseline_date", "yesterday")

    total = len(kw_moves) + len(gbp_changes) + len(ad_changes)

    if total == 0:
        return (
            '<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;'
            'padding:12px 18px;font-size:13px;color:#8b949e">'
            'No changes detected since yesterday. Steady state.'
            '</div>'
        )

    sections_html = ""

    # ── Keyword Rankings ──────────────────────────────────────────────────────
    if kw_moves:
        rows = ""
        for m in kw_moves:
            mp  = m.get("map_pack", {})
            org = m.get("organic", {})
            biz = m.get("business_name", m.get("business", ""))
            kw  = m.get("keyword", "")[:55]

            # Map Pack cell
            mp_dir = mp.get("direction", "same")
            if mp_dir == "up":
                mp_html = (f'<span style="color:#3fb950;font-weight:700">#{mp["curr"]}</span> '
                           f'<span style="color:#3fb950;font-size:11px">+{mp["delta"]} (was #{mp["prev"]})</span>')
            elif mp_dir == "down":
                mp_html = (f'<span style="color:#f85149;font-weight:700">#{mp["curr"]}</span> '
                           f'<span style="color:#f85149;font-size:11px">{mp["delta"]} (was #{mp["prev"]})</span>')
            elif mp_dir == "new":
                mp_html = f'<span style="color:#58a6ff;font-weight:700">#{mp["curr"]} NEW</span>'
            elif mp_dir == "lost":
                mp_html = f'<span style="color:#f85149;font-weight:700">DROPPED (was #{mp["prev"]})</span>'
            else:
                mp_html = f'<span style="color:#8b949e">#{mp.get("curr","—")}</span>'

            # Organic cell
            org_dir = org.get("direction", "same")
            if org_dir == "up":
                org_html = (f'<span style="color:#3fb950">#{org["curr"]}</span> '
                            f'<span style="color:#3fb950;font-size:11px">+{org["delta"]}</span>')
            elif org_dir == "down":
                org_html = (f'<span style="color:#f85149">#{org["curr"]}</span> '
                            f'<span style="color:#f85149;font-size:11px">{org["delta"]}</span>')
            elif org_dir == "new":
                org_html = f'<span style="color:#58a6ff">#{org["curr"]} NEW</span>'
            elif org_dir == "lost":
                org_html = f'<span style="color:#f85149">DROPPED</span>'
            else:
                org_html = f'<span style="color:#8b949e">{("#" + str(org.get("curr","—"))) if org.get("curr") else "—"}</span>'

            rows += (f'<tr style="border-bottom:1px solid #21262d">'
                     f'<td style="padding:8px 10px;color:#c9d1d9;font-size:13px">{biz}</td>'
                     f'<td style="padding:8px 10px;color:#8b949e;font-size:12px;max-width:240px">{kw}</td>'
                     f'<td style="padding:8px 10px">{mp_html}</td>'
                     f'<td style="padding:8px 10px">{org_html}</td>'
                     f'</tr>')

        sections_html += (
            f'<p style="color:#e6edf3;font-weight:700;font-size:13px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.05em">Keyword Rankings</p>'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:18px">'
            f'<thead><tr style="border-bottom:1px solid #30363d;color:#8b949e;font-size:11px">'
            f'<th style="text-align:left;padding:6px 10px">Business</th>'
            f'<th style="text-align:left;padding:6px 10px">Keyword</th>'
            f'<th style="text-align:left;padding:6px 10px">Map Pack</th>'
            f'<th style="text-align:left;padding:6px 10px">Organic</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>'
        )

    # ── Competitor GBP Changes ────────────────────────────────────────────────
    if gbp_changes:
        rows = ""
        for c in gbp_changes:
            r  = c.get("rating", {})
            rv = c.get("review_count", {})
            alert = c.get("alert", "")

            alert_badge = ""
            if alert == "RATING_DROP":
                alert_badge = '<span style="background:#f85149;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-left:6px">WATCH</span>'
            elif alert == "REVIEW_SURGE":
                alert_badge = '<span style="background:#f0883e;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-left:6px">SURGE</span>'

            rating_html = ""
            if r.get("changed"):
                delta_val = r.get("delta", 0)
                color = "#3fb950" if delta_val > 0 else "#f85149"
                sign  = "+" if delta_val > 0 else ""
                rating_html = (f'<span style="color:{color};font-weight:700">'
                               f'{r.get("prev","?")} &rarr; {r.get("curr","?")}</span> '
                               f'<span style="color:{color};font-size:11px">({sign}{delta_val:.1f})</span>')
            else:
                rating_html = f'<span style="color:#8b949e">{r.get("curr","—")}</span>'

            review_html = ""
            if rv.get("changed"):
                delta_val = rv.get("delta", 0)
                color = "#3fb950" if delta_val > 0 else "#f85149"
                sign  = "+" if delta_val > 0 else ""
                review_html = (f'<span style="color:{color}">'
                               f'{rv.get("prev","?")} &rarr; {rv.get("curr","?")}</span> '
                               f'<span style="color:{color};font-size:11px">({sign}{delta_val})</span>')
            else:
                review_html = f'<span style="color:#8b949e">{rv.get("curr","—")}</span>'

            rows += (f'<tr style="border-bottom:1px solid #21262d">'
                     f'<td style="padding:8px 10px;color:#c9d1d9;font-size:13px">'
                     f'{c.get("business_name","")} <span style="color:#8b949e;font-size:11px">&mdash; {c.get("competitor","")}</span>{alert_badge}</td>'
                     f'<td style="padding:8px 10px">{rating_html}</td>'
                     f'<td style="padding:8px 10px">{review_html}</td>'
                     f'</tr>')

        sections_html += (
            f'<p style="color:#e6edf3;font-weight:700;font-size:13px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.05em">Competitor GBP Activity</p>'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:18px">'
            f'<thead><tr style="border-bottom:1px solid #30363d;color:#8b949e;font-size:11px">'
            f'<th style="text-align:left;padding:6px 10px">Competitor</th>'
            f'<th style="text-align:left;padding:6px 10px">Rating</th>'
            f'<th style="text-align:left;padding:6px 10px">Reviews</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>'
        )

    # ── Facebook Ad Activity ──────────────────────────────────────────────────
    if ad_changes:
        rows = ""
        for c in ad_changes:
            ads   = c.get("active_ads", {})
            alert = c.get("alert", "")
            delta_val = ads.get("delta", 0)

            alert_badge = ""
            if alert == "STARTED_ADS":
                alert_badge = '<span style="background:#f85149;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-left:6px">STARTED ADS</span>'
            elif alert == "STOPPED_ADS":
                alert_badge = '<span style="background:#3fb950;color:#000;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-left:6px">STOPPED ADS</span>'
            elif alert == "ADS_INCREASED":
                alert_badge = '<span style="background:#f0883e;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-left:6px">SCALED UP</span>'

            color = "#f85149" if delta_val > 0 else "#3fb950"
            sign  = "+" if delta_val > 0 else ""
            ad_html = (f'<span style="color:{color};font-weight:700">'
                       f'{ads.get("prev","?")} &rarr; {ads.get("curr","?")}</span> '
                       f'<span style="color:{color};font-size:11px">({sign}{delta_val})</span>')

            rows += (f'<tr style="border-bottom:1px solid #21262d">'
                     f'<td style="padding:8px 10px;color:#c9d1d9;font-size:13px">'
                     f'{c.get("business_name","")} <span style="color:#8b949e;font-size:11px">&mdash; {c.get("competitor","")}</span>{alert_badge}</td>'
                     f'<td style="padding:8px 10px">{ad_html}</td>'
                     f'</tr>')

        sections_html += (
            f'<p style="color:#e6edf3;font-weight:700;font-size:13px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.05em">Facebook Ad Activity</p>'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:4px">'
            f'<thead><tr style="border-bottom:1px solid #30363d;color:#8b949e;font-size:11px">'
            f'<th style="text-align:left;padding:6px 10px">Competitor</th>'
            f'<th style="text-align:left;padding:6px 10px">Active Ads</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>'
        )

    return (
        f'<div style="background:#161b22;border:1px solid #30363d;border-left:3px solid #58a6ff;'
        f'border-radius:6px;padding:16px 20px">'
        f'<p style="color:#8b949e;font-size:11px;margin-bottom:14px">vs. {baseline}</p>'
        f'{sections_html}'
        f'</div>'
    )


def render_movements_markdown(delta: dict) -> str:
    """
    Render the 'Movements Since Yesterday' section for the markdown brief.
    Returns a markdown string.
    """
    if not delta or not delta.get("has_baseline"):
        return "_No baseline yet. Run delta_tracker.py again tomorrow._\n"

    kw_moves    = delta.get("keyword_movements", [])
    gbp_changes = delta.get("competitor_rating_changes", [])
    ad_changes  = delta.get("ad_activity_changes", [])
    baseline    = delta.get("baseline_date", "yesterday")
    total       = len(kw_moves) + len(gbp_changes) + len(ad_changes)

    if total == 0:
        return f"_No changes detected since {baseline}. Steady state._\n"

    lines = [f"_vs. {baseline}_\n"]

    if kw_moves:
        lines.append("**KEYWORD RANKINGS**")
        for m in kw_moves:
            mp  = m.get("map_pack", {})
            biz = m.get("business_name", "")
            kw  = m.get("keyword", "")[:55]
            mp_dir = mp.get("direction", "same")
            if mp_dir == "up":
                arrow = f"#{mp['prev']} -> #{mp['curr']} (+{mp['delta']})"
            elif mp_dir == "down":
                arrow = f"#{mp['prev']} -> #{mp['curr']} ({mp['delta']})"
            elif mp_dir == "new":
                arrow = f"NEW ENTRY #{mp['curr']}"
            elif mp_dir == "lost":
                arrow = f"DROPPED (was #{mp['prev']})"
            else:
                arrow = f"#{mp.get('curr','?')}"
            lines.append(f"  - {biz}: \"{kw}\" Map Pack {arrow}")

    if gbp_changes:
        lines.append("\n**COMPETITOR GBP CHANGES**")
        for c in gbp_changes:
            r     = c.get("rating", {})
            rv    = c.get("review_count", {})
            alert = f" [{c['alert']}]" if c.get("alert") else ""
            parts = []
            if r.get("changed"):
                sign = "+" if r.get("delta", 0) > 0 else ""
                parts.append(f"Rating {r['prev']} -> {r['curr']} ({sign}{r['delta']:.1f})")
            if rv.get("changed"):
                sign = "+" if rv.get("delta", 0) > 0 else ""
                parts.append(f"Reviews {rv['prev']} -> {rv['curr']} ({sign}{rv['delta']})")
            lines.append(f"  - {c['business_name']} / {c['competitor']}: {', '.join(parts)}{alert}")

    if ad_changes:
        lines.append("\n**FACEBOOK AD ACTIVITY**")
        for c in ad_changes:
            ads   = c.get("active_ads", {})
            alert = f" [{c['alert']}]" if c.get("alert") else ""
            sign  = "+" if ads.get("delta", 0) > 0 else ""
            lines.append(f"  - {c['business_name']} / {c['competitor']}: {ads['prev']} -> {ads['curr']} ads ({sign}{ads['delta']}){alert}")

    return "\n".join(lines) + "\n"


# ─── Google Calendar (via Node.js GWS helper) ────────────────────────────────

def _fetch_calendar_events() -> dict:
    """Call calendar_brief.js and return {events: [...], error: str|None}."""
    import subprocess
    script = Path("C:/Users/mario/gws-workspace/demos/calendar_brief.js")
    if not script.exists():
        return {"events": [], "error": "calendar_brief.js not found"}
    try:
        result = subprocess.run(
            ["node", str(script)],
            capture_output=True, text=True, timeout=15,
            cwd=str(script.parent),
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return {"events": [], "error": result.stderr.strip()[:200]}
        return json.loads(result.stdout.strip())
    except subprocess.TimeoutExpired:
        return {"events": [], "error": "Timed out"}
    except Exception as e:
        return {"events": [], "error": str(e)[:200]}


# ─── Gmail Urgents (via Node.js GWS helper) ──────────────────────────────────

def _fetch_gmail_urgents() -> dict:
    """Call gmail_brief.js and return {unread_count, urgent: [...], error}."""
    import subprocess
    script = Path("C:/Users/mario/gws-workspace/demos/gmail_brief.js")
    if not script.exists():
        return {"unread_count": 0, "urgent": [], "error": "gmail_brief.js not found"}
    try:
        result = subprocess.run(
            ["node", str(script)],
            capture_output=True, text=True, timeout=20,
            cwd=str(script.parent),
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return {"unread_count": 0, "urgent": [], "error": result.stderr.strip()[:200]}
        return json.loads(result.stdout.strip())
    except subprocess.TimeoutExpired:
        return {"unread_count": 0, "urgent": [], "error": "Timed out"}
    except Exception as e:
        return {"unread_count": 0, "urgent": [], "error": str(e)[:200]}


# ─── Screenpipe Client Attention Distribution (UC-4) ─────────────────────────

def _fetch_screenpipe_attention() -> dict:
    """Query Screenpipe OCR for each client name in yesterday's data.
    Returns {client_key: mention_count, ...} or empty dict if unavailable."""
    try:
        from screenpipe_verifier import screenpipe_healthy, screenpipe_search
    except ImportError:
        return {}
    if not screenpipe_healthy():
        return {}

    from datetime import timezone as _tz
    yesterday = datetime.now(_tz.utc) - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = yesterday.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Search terms per client (short distinctive strings)
    search_terms = {
        "sugar_shack": "Sugar Shack",
        "island_arcade": "Island Arcade",
        "island_candy": "Island Candy",
        "juan": "Juan Elizondo",
        "spi_fun_rentals": "SPI Fun Rentals",
        "custom_designs_tx": "Custom Designs",
        "optimum_clinic": "Optimum",
        "optimum_foundation": "Optimum Foundation",
    }
    counts = {}
    for biz_key, term in search_terms.items():
        try:
            results = screenpipe_search(term, content_type="ocr", limit=100,
                                        start_time=start, end_time=end)
            counts[biz_key] = len(results)
        except Exception:
            counts[biz_key] = 0
    return counts


def _fetch_screenpipe_time_breakdown() -> dict:
    """Query Screenpipe raw SQL for yesterday's app usage breakdown.
    Returns {app_name: {"minutes": float, "pct": float}, ...} or empty dict."""
    try:
        import urllib.request as _req
        from screenpipe_verifier import screenpipe_healthy, SCREENPIPE_BASE
    except ImportError:
        return {}
    if not screenpipe_healthy():
        return {}

    from datetime import timezone as _tz
    yesterday = datetime.now(_tz.utc) - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = yesterday.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        query = (f"SELECT app_name, COUNT(*) as frame_count FROM frames "
                 f"WHERE timestamp >= '{start}' AND timestamp <= '{end}' "
                 f"AND app_name != '' "
                 f"GROUP BY app_name ORDER BY frame_count DESC LIMIT 20")
        data = json.dumps({"query": query}).encode("utf-8")
        req = _req.Request(f"{SCREENPIPE_BASE}/raw_sql", data=data,
                           headers={"Content-Type": "application/json"})
        resp = _req.urlopen(req, timeout=15)
        rows = json.loads(resp.read())
    except Exception:
        return {}

    if not rows:
        return {}

    total_frames = sum(r["frame_count"] for r in rows)
    if total_frames == 0:
        return {}

    result = {}
    for r in rows:
        frames = r["frame_count"]
        minutes = frames * 4 / 60  # ~4 sec per frame
        pct = (frames / total_frames * 100)
        result[r["app_name"]] = {"minutes": round(minutes, 1), "pct": round(pct, 1)}
    return result


def _fetch_screenpipe_last_activity() -> dict:
    """Get the last active window from yesterday via Screenpipe.
    Returns {"app": str, "window": str, "time": str} or empty dict."""
    try:
        import urllib.request as _req
        from screenpipe_verifier import screenpipe_healthy, SCREENPIPE_BASE
    except ImportError:
        return {}
    if not screenpipe_healthy():
        return {}

    from datetime import timezone as _tz
    yesterday = datetime.now(_tz.utc) - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = yesterday.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        query = (f"SELECT app_name, window_name, timestamp FROM frames "
                 f"WHERE timestamp >= '{start}' AND timestamp <= '{end}' "
                 f"AND app_name != '' "
                 f"ORDER BY timestamp DESC LIMIT 1")
        data = json.dumps({"query": query}).encode("utf-8")
        req = _req.Request(f"{SCREENPIPE_BASE}/raw_sql", data=data,
                           headers={"Content-Type": "application/json"})
        resp = _req.urlopen(req, timeout=15)
        rows = json.loads(resp.read())
    except Exception:
        return {}

    if not rows:
        return {}

    r = rows[0]
    return {
        "app": r.get("app_name", "?"),
        "window": (r.get("window_name") or "?")[:100],
        "time": r.get("timestamp", "?"),
    }


def _fetch_claw_pending() -> dict:
    """Fetch pending CLAW items count from Supabase via claw_bridge.
    Returns {"total": int, "by_client": {name: count}, "by_type": {type: count}, "items": [...]}."""
    try:
        from claw_bridge import get_pending, BUSINESS_NAMES as _BN
    except ImportError:
        return {}
    try:
        items = get_pending()
    except Exception:
        return {}
    if not items:
        return {"total": 0, "by_client": {}, "by_type": {}, "items": []}

    by_client = {}
    by_type = {}
    for item in items:
        c = _BN.get(item.get("client_key", ""), item.get("client_key", "unknown"))
        t = item.get("item_type", "unknown")
        by_client[c] = by_client.get(c, 0) + 1
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total": len(items),
        "by_client": by_client,
        "by_type": by_type,
        "items": items[:10],  # first 10 for display
    }


# ─── Screenpipe Audio Insights (UC-5) ─────────────────────────────────────────

def _fetch_audio_insights() -> dict:
    """Query Screenpipe audio transcriptions from last 24h, tag by client,
    extract action items and strategy notes.
    Returns {"segments": int, "duration_min": float, "client_mentions": {key: count},
             "action_items": [str], "strategy_notes": [str]} or empty dict."""
    try:
        import urllib.request as _req
        import urllib.parse as _parse
        from screenpipe_verifier import screenpipe_healthy, SCREENPIPE_BASE
    except ImportError:
        return {}
    if not screenpipe_healthy():
        return {}

    from datetime import timezone as _tz
    yesterday = datetime.now(_tz.utc) - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = yesterday.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        params = _parse.urlencode({
            "content_type": "audio",
            "limit": "500",
            "start_time": start,
            "end_time": end,
            "min_length": "20",
        })
        url = f"{SCREENPIPE_BASE}/search?{params}"
        resp = _req.urlopen(url, timeout=15)
        data = json.loads(resp.read())
    except Exception:
        return {}

    audio_items = data.get("data", [])
    if not audio_items:
        return {"segments": 0, "duration_min": 0, "client_mentions": {},
                "action_items": [], "strategy_notes": []}

    # Client keyword map (same as screenpipe_audio_miner.py)
    client_kw = {
        "sugar_shack": ["sugar shack", "candy store", "candy shop", "taffy", "fudge"],
        "island_arcade": ["island arcade", "arcade", "claw machine", "game room"],
        "island_candy": ["island candy", "ice cream", "frozen treats", "gelato"],
        "juan": ["juan elizondo", "remax", "re/max", "real estate", "commercial property"],
        "spi_fun_rentals": ["spi fun rentals", "golf cart", "beach rental"],
        "custom_designs_tx": ["custom designs", "security camera", "alarm", "home theater", "surveillance"],
        "optimum_clinic": ["optimum clinic", "optimum health", "cash clinic", "night clinic"],
        "optimum_foundation": ["optimum foundation", "wound care", "nonprofit", "regenerative"],
    }
    action_triggers = ["i need to", "we need to", "we should", "don't forget",
                       "make sure", "remind me", "todo", "let's do", "have to",
                       "schedule", "deadline", "by friday", "by monday", "by tomorrow"]
    strategy_triggers = ["the strategy", "our angle", "competitor", "ad copy",
                         "campaign", "marketing", "engagement", "facebook",
                         "google business", "reviews", "seo", "content", "blog post"]

    client_counts = {}
    action_items = []
    strategy_notes = []
    total_dur = 0
    seen_actions = set()
    seen_strategy = set()

    for item in audio_items:
        content = item.get("content", {})
        text = content.get("transcription", "") or content.get("text", "")
        if not text or len(text.strip()) < 15:
            continue
        start_t = content.get("start_time", 0) or 0
        end_t = content.get("end_time", 0) or 0
        total_dur += max(0, end_t - start_t)
        text_lower = text.lower()

        # Tag clients
        for ckey, keywords in client_kw.items():
            if any(kw in text_lower for kw in keywords):
                client_counts[ckey] = client_counts.get(ckey, 0) + 1

        # Action items
        for trigger in action_triggers:
            idx = text_lower.find(trigger)
            if idx >= 0:
                s = max(0, text_lower.rfind(".", 0, idx) + 1)
                e = text_lower.find(".", idx)
                if e < 0:
                    e = min(len(text), idx + 150)
                sentence = text[s:e].strip()
                if len(sentence) > 15 and sentence[:50].lower() not in seen_actions:
                    seen_actions.add(sentence[:50].lower())
                    action_items.append(sentence[:200])
                break

        # Strategy notes
        if any(t in text_lower for t in strategy_triggers):
            short = text[:250].replace("\n", " ").strip()
            if short[:50].lower() not in seen_strategy:
                seen_strategy.add(short[:50].lower())
                strategy_notes.append(short)

    return {
        "segments": len(audio_items),
        "duration_min": round(total_dur / 60, 1),
        "client_mentions": client_counts,
        "action_items": action_items[:10],
        "strategy_notes": strategy_notes[:10],
    }


# ─── Engagement Correlation (UC-6) ───────────────────────────────────────────

def _fetch_engagement_correlation() -> dict:
    """Pull attention ↔ engagement correlation from engagement_logger.
    Returns the correlation dict or empty dict on failure."""
    try:
        from engagement_logger import correlate_attention_engagement
    except ImportError:
        return {}
    try:
        return correlate_attention_engagement(days_back=7)
    except Exception:
        return {}


# ─── Image Bucket Health Check (UC-7) ────────────────────────────────────────

def _check_image_buckets() -> dict:
    """Count ad images per client in ~/clientkey_ad_images/ folders.
    Returns {"clients": {client_key: {"count": int, "path": str}}, "low": [client_keys with < 5 images]}."""
    home = Path.home()
    folder_map = {
        "sugar_shack": home / "sugar_shack_ad_images",
        "island_arcade": home / "island_arcade_ad_images",
        "island_candy": home / "island_candy_ad_images",
        "juan": home / "juan_remax_ad_images",
        "spi_fun_rentals": home / "spi_fun_rentals_ad_images",
        "custom_designs_tx": home / "custom_designs_ad_images",
        "optimum_clinic": home / "optimum_clinic_ad_images",
        "optimum_foundation": home / "optimum_foundation_ad_images",
    }
    clients = {}
    low = []
    for biz_key, folder in folder_map.items():
        count = 0
        if folder.exists():
            count = sum(1 for f in folder.iterdir()
                        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
        clients[biz_key] = {"count": count, "path": str(folder)}
        if count < 5:
            low.append(biz_key)
    return {"clients": clients, "low": low}


# ─── Business Data Aggregator ─────────────────────────────────────────────────

def collect_business_data(business_key: str, state: dict) -> dict:
    md = read_program_md(business_key)
    posting_log = parse_posting_log(md)
    days_ago = days_since_last_post(posting_log)
    priorities = parse_current_priorities(md)
    whats_working = parse_whats_working(md)
    top_angles = get_top_angles(business_key)
    competitor_alerts = get_competitor_alerts(business_key, state)

    overdue = days_ago is not None and days_ago >= OVERDUE_THRESHOLD

    # Best recommendation
    recommendation = "No action needed"
    if overdue:
        if top_angles:
            recommendation = f"Post today — try \"{top_angles[0]['angle']}\" (avg score {top_angles[0]['avg']:.0f})"
        else:
            recommendation = f"Post today — {days_ago} days since last post"
    elif days_ago is None:
        recommendation = "No posts logged yet — start posting"

    return {
        "key": business_key,
        "name": BUSINESS_NAMES[business_key],
        "icon": BUSINESS_ICONS[business_key],
        "priorities": priorities,
        "posting_log": posting_log,
        "days_since_post": days_ago,
        "overdue": overdue,
        "whats_working": whats_working,
        "top_angles": top_angles,
        "competitor_alerts": competitor_alerts,
        "recommendation": recommendation,
    }

# ─── Action Items Generator ───────────────────────────────────────────────────

def generate_action_items(all_data: list, seasonal: list, kw_rankings: dict = None) -> list:
    items = []

    # Overdue posts (highest priority)
    for biz in all_data:
        if biz["overdue"]:
            days = biz["days_since_post"]
            name = biz["name"]
            if biz["top_angles"]:
                best = biz["top_angles"][0]
                items.append({
                    "priority": "high",
                    "text": f"{name}: {days} days since last post — try \"{best['angle']}\" (score {best['avg']:.0f})",
                })
            else:
                items.append({
                    "priority": "high",
                    "text": f"{name}: {days} days since last post — needs content today",
                })
        elif biz["days_since_post"] is None:
            items.append({
                "priority": "medium",
                "text": f"{biz['name']}: No posts logged yet — set up posting log in program.md",
            })

    # Top performing angles worth repeating
    for biz in all_data:
        for angle in biz["top_angles"][:1]:
            if angle["avg"] >= 50 and angle["count"] >= 2:
                items.append({
                    "priority": "info",
                    "text": f"{biz['name']}: \"{angle['angle']}\" averaging {angle['avg']:.0f} across {angle['count']} posts — proven winner, use again",
                })

    # Upcoming seasonal hooks (within 5 days)
    for hook in seasonal:
        if hook["days_until"] <= 5:
            if hook["days_until"] == 0:
                label = "TODAY"
            elif hook["days_until"] == 1:
                label = "tomorrow"
            else:
                label = f"in {hook['days_until']} days"
            items.append({
                "priority": "medium",
                "text": f"Seasonal: {hook['name']} starts {label} — {hook['tip']}",
            })

    # GBP new-profile advisory — Custom Designs TX
    if kw_rankings:
        cd_data = kw_rankings.get("custom_designs_tx", {})
        if cd_data and all(
            v.get("map_pack_position") is None and v.get("maps_position") is None
            for v in cd_data.values() if isinstance(v, dict)
        ):
            items.append({
                "priority": "info",
                "text": (
                    "Custom Designs TX: GBP is new (~1 month, 0 reviews) — not ranking yet is normal. "
                    "Actions: (1) Send review requests to past clients — need 5+ to start ranking, "
                    "(2) Verify service area covers McAllen/Edinburg/Mission/Pharr in GBP dashboard, "
                    "(3) Add GBP categories: 'Security System Installer' + 'Home Theater Store'. "
                    "Expect Maps appearances in 60–90 days once review velocity builds."
                ),
            })

    return items

# ─── Markdown Report ──────────────────────────────────────────────────────────

def generate_markdown(all_data: list, action_items: list, seasonal: list, today: date, competitor_report: str, gbp_data: dict = None, fb_health: list = None, fb_competitor_data: dict = None, competitor_state: dict = None, adlibrary_data: dict = None, ai_analysis: list = None, review_data: dict = None, delta_data: dict = None, calendar_data: dict = None, gmail_data: dict = None, attention_data: dict = None, time_breakdown_data: dict = None, last_activity_data: dict = None, claw_data: dict = None, audio_data: dict = None, correlation_data: dict = None, image_buckets: dict = None, openclaw_health: dict = None) -> str:
    lines = []
    weekday = today.strftime("%A")

    lines += [
        f"# Morning Brief — {weekday}, {today.strftime('%B %d, %Y')}",
        f"Generated: {datetime.now().strftime('%I:%M %p')}",
        "",
        "---",
        "",
    ]

    # Movements since yesterday (top — first thing to read)
    lines.append("## Movements Since Yesterday")
    lines.append("")
    lines.append(render_movements_markdown(delta_data))
    lines.append("")
    lines.append("---")
    lines.append("")

    # Facebook Session Status (top of brief — know before you try to post)
    if fb_health:
        failed = [r for r in fb_health if r["status"] == "FAIL"]
        warned = [r for r in fb_health if r["status"] == "WARN"]
        lines.append("## Facebook Session Status")
        lines.append("")
        if failed:
            lines.append("> **ACTION REQUIRED before posting:**")
            for r in failed:
                lines.append(f"- **[FAIL]** `{r['page']}` — {r['detail']}")
        if warned:
            for r in warned:
                lines.append(f"- **[WARN]** `{r['page']}` — {r['detail']}")
        ok_pages = [r["page"] for r in fb_health if r["status"] == "OK"]
        if ok_pages:
            lines.append(f"- [OK] Ready to post: {', '.join(ok_pages)}")
        if not failed and not warned:
            lines.append("- All profiles authenticated. All pages reachable. Ready to post.")
        lines += ["", "---", ""]

    # Today's Calendar
    lines.append("## Today's Calendar")
    lines.append("")
    if calendar_data and not calendar_data.get("error"):
        events = calendar_data.get("events", [])
        if events:
            for ev in events:
                if ev.get("all_day"):
                    lines.append(f"- **All day** — {ev['summary']}")
                else:
                    try:
                        t = datetime.fromisoformat(ev["start"]).strftime("%-I:%M %p")
                    except Exception:
                        t = ev["start"]
                    loc = f" ({ev['location']})" if ev.get("location") else ""
                    lines.append(f"- **{t}** — {ev['summary']}{loc}")
        else:
            lines.append("- No events scheduled today.")
    elif calendar_data and calendar_data.get("error"):
        lines.append(f"- Calendar unavailable: {calendar_data['error']}")
    else:
        lines.append("- Calendar data not loaded.")
    lines += ["", "---", ""]

    # Inbox Summary
    lines.append("## Inbox Summary")
    lines.append("")
    if gmail_data and not gmail_data.get("error"):
        unread = gmail_data.get("unread_count", 0)
        urgent = gmail_data.get("urgent", [])
        lines.append(f"**Unread inbox:** {unread}")
        if urgent:
            lines.append(f"**Needs attention ({len(urgent)} emails, last 48h):**")
            for email in urgent[:10]:
                sender = email["from"].split("<")[0].strip() if "<" in email["from"] else email["from"]
                lines.append(f"- **{sender}** — {email['subject']}")
        else:
            lines.append("- No urgent unread emails.")
    elif gmail_data and gmail_data.get("error"):
        lines.append(f"- Gmail unavailable: {gmail_data['error']}")
    else:
        lines.append("- Gmail data not loaded.")
    lines += ["", "---", ""]

    # Client Attention Distribution (Screenpipe)
    if attention_data:
        total = sum(attention_data.values())
        if total > 0:
            lines.append("## Yesterday's Client Attention")
            lines.append("")
            sorted_attn = sorted(attention_data.items(), key=lambda x: x[1], reverse=True)
            for biz_key, count in sorted_attn:
                name = BUSINESS_NAMES.get(biz_key, biz_key)
                pct = (count / total * 100) if total else 0
                bar = "#" * max(1, int(pct / 5))
                flag = " **[NEEDS ATTENTION]**" if count == 0 else ""
                lines.append(f"- {name}: {count} mentions ({pct:.0f}%) {bar}{flag}")
            zero_clients = [BUSINESS_NAMES.get(k, k) for k, v in attention_data.items() if v == 0]
            if zero_clients:
                lines.append(f"\n> Zero screen time yesterday: {', '.join(zero_clients)}")
            lines += ["", "---", ""]

    # Where You Left Off + Time Breakdown (Screenpipe)
    if last_activity_data:
        lines.append("## Where You Left Off")
        lines.append("")
        lines.append(f"> **{last_activity_data.get('app', '?')}** — {last_activity_data.get('window', '?')}")
        lines += ["", "---", ""]

    if time_breakdown_data:
        total_min = sum(v["minutes"] for v in time_breakdown_data.values())
        if total_min > 0:
            lines.append(f"## Yesterday's Time Breakdown ({total_min:.0f} min tracked)")
            lines.append("")
            sorted_apps = sorted(time_breakdown_data.items(), key=lambda x: x[1]["minutes"], reverse=True)
            for app_name, info in sorted_apps[:10]:
                bar = "#" * max(1, int(info["pct"] / 5))
                lines.append(f"- {app_name}: {info['minutes']:.0f} min ({info['pct']:.0f}%) {bar}")
            lines += ["", "---", ""]

    # OpenClaw Local Worker Status
    if openclaw_health:
        _wk = openclaw_health.get("worker", {})
        _q = _wk.get("queue", {})
        _ollama = openclaw_health.get("ollama", {})
        _or = openclaw_health.get("openrouter", {})
        lines.append(f"## OpenClaw Local Worker")
        lines.append("")
        lines.append(f"- **Default model:** {openclaw_health.get('default_model', '?')}")
        lines.append(f"- **OpenRouter:** {'connected' if _or.get('connected') else 'offline'}")
        lines.append(f"- **Ollama:** {'connected' if _ollama.get('connected') else 'offline'} "
                      f"({len(_ollama.get('models', []))} models)")
        lines.append(f"- **Tasks completed:** {_wk.get('tasks_completed', 0)} | "
                      f"Pending: {_q.get('pending', 0)} | Failed: {_q.get('failed', 0)}")
        lines.append("")
        lines.append("```bash")
        lines.append("python openclaw_dispatch.py --health   # detailed health")
        lines.append("python openclaw_dispatch.py --stats    # processing stats")
        lines.append("```")
        lines += ["", "---", ""]

    # CLAW Pending Items
    if claw_data and claw_data.get("total", 0) > 0:
        lines.append(f"## CLAW Pending Items ({claw_data['total']} awaiting approval)")
        lines.append("")
        if claw_data.get("by_client"):
            for client_name, count in sorted(claw_data["by_client"].items(), key=lambda x: -x[1]):
                lines.append(f"- **{client_name}**: {count}")
        if claw_data.get("by_type"):
            types_str = ", ".join(f"{t} ({c})" for t, c in sorted(claw_data["by_type"].items(), key=lambda x: -x[1]))
            lines.append(f"- Types: {types_str}")
        lines.append("")
        lines.append("```bash")
        lines.append("python claw_bridge.py              # view all pending")
        lines.append("python claw_bridge.py --approve 5  # approve item #5")
        lines.append("```")
        lines += ["", "---", ""]

    # Voice Notes Summary (Audio Miner)
    if audio_data and audio_data.get("segments", 0) > 0:
        lines.append(f"## Voice Notes Summary ({audio_data['segments']} audio segments, {audio_data['duration_min']:.0f} min)")
        lines.append("")
        if audio_data.get("client_mentions"):
            lines.append("**Client mentions in audio:**")
            for ckey, count in sorted(audio_data["client_mentions"].items(), key=lambda x: -x[1]):
                name = BUSINESS_NAMES.get(ckey, ckey)
                lines.append(f"- {name}: {count}")
            lines.append("")
        if audio_data.get("action_items"):
            lines.append("**Action items from voice:**")
            for item in audio_data["action_items"][:5]:
                lines.append(f"- {item}")
            lines.append("")
        if audio_data.get("strategy_notes"):
            lines.append("**Strategy notes from voice:**")
            for note in audio_data["strategy_notes"][:5]:
                lines.append(f"- {note[:200]}")
            lines.append("")
        lines += ["---", ""]

    # Attention ↔ Engagement Correlation
    if correlation_data and correlation_data.get("clients"):
        lines.append(f"## Attention vs Engagement ({correlation_data.get('period_days', 7)}d)")
        lines.append("")
        lines.append(f"| Client | Screen Time | Posts | Avg Score | Status |")
        lines.append(f"|---|---|---|---|---|")
        for biz_key, c in sorted(correlation_data["clients"].items(), key=lambda x: x[1]["attention_rank"]):
            status_icon = {"aligned": "=", "over-indexed": ">>", "under-indexed": "<<", "no-data": "—"}.get(c["correlation"], "?")
            lines.append(f"| {c['name']} | {c['attention_mentions']} | {c['posts_count']} | {c['avg_engagement']:.0f} | {status_icon} {c['correlation']} |")
        if correlation_data.get("insight"):
            lines.append("")
            lines.append(f"> {correlation_data['insight']}")
        lines += ["", "---", ""]

    # Image Bucket Health
    if image_buckets and image_buckets.get("low"):
        lines.append("## Image Buckets — Low Stock Warning")
        lines.append("")
        for biz_key in image_buckets["low"]:
            info = image_buckets["clients"].get(biz_key, {})
            name = BUSINESS_NAMES.get(biz_key, biz_key)
            count = info.get("count", 0)
            if count == 0:
                lines.append(f"- **{name}**: EMPTY — no ad images available")
            else:
                lines.append(f"- **{name}**: only {count} images (< 5)")
        lines.append("")
        lines.append("Run the client's ad skill to generate more images, or use fal.ai directly.")
        lines += ["", "---", ""]

    # Action Items
    lines.append("## Action Items (Read This First)")
    lines.append("")
    if action_items:
        high = [a for a in action_items if a["priority"] == "high"]
        medium = [a for a in action_items if a["priority"] == "medium"]
        info = [a for a in action_items if a["priority"] == "info"]
        for item in high:
            lines.append(f"- **[URGENT]** {item['text']}")
        for item in medium:
            lines.append(f"- **[TODAY]** {item['text']}")
        for item in info:
            lines.append(f"- [FYI] {item['text']}")
    else:
        lines.append("- All businesses are on track. Nothing urgent today.")
    lines += ["", "---", ""]

    # Per-business summaries
    lines.append("## Business Summaries")
    lines.append("")
    for biz in all_data:
        icon = biz["icon"]
        name = biz["name"]
        days = biz["days_since_post"]
        days_label = f"{days}d ago" if days is not None else "never logged"
        overdue_flag = " **[OVERDUE]**" if biz["overdue"] else ""

        lines.append(f"### {icon} {name}{overdue_flag}")
        lines.append("")
        lines.append(f"**Last post:** {days_label}")

        # Priorities
        unfilled = [p for p in biz["priorities"] if p.get("value") is None]
        if unfilled:
            lines.append(f"**Priorities not set:** {', '.join(p['label'] for p in unfilled[:3])}")

        # Top angles
        if biz["top_angles"]:
            top = biz["top_angles"][0]
            lines.append(f"**Top angle:** \"{top['angle']}\" — avg score {top['avg']:.0f} ({top['count']} posts)")
        else:
            lines.append("**Top angle:** No engagement data yet")

        # What's working
        if biz["whats_working"]:
            lines.append(f"**Working:** {biz['whats_working'][0]}")

        # Competitor alerts
        if biz["competitor_alerts"]:
            comp_lines = []
            for c in biz["competitor_alerts"][:2]:
                comp_lines.append(f"{c['name']}: {c.get('rating','?')} stars ({c.get('review_count','?')} reviews)")
            lines.append(f"**Competitors:** {' | '.join(comp_lines)}")

        lines.append(f"**Action:** {biz['recommendation']}")
        lines.append("")

    lines += ["---", ""]

    # Competitor Snapshot
    lines.append("## Competitor Snapshot")
    lines.append("")
    if competitor_report:
        # Extract just the Alerts section
        alert_match = re.search(r'## Alerts.*?(?=##|\Z)', competitor_report, re.DOTALL)
        if alert_match:
            snippet = alert_match.group(0).strip()
            lines.append(snippet[:1000])
        else:
            lines.append("Competitor report found but no alerts section detected.")
    else:
        lines.append("No competitor report found for today. Run: `python competitor_monitor.py`")
    lines += ["", "---", ""]

    # Competitor Social Activity (Facebook)
    lines.append("## Competitor Social Activity (Facebook)")
    lines.append("")
    active_biz_keys = {biz["key"] for biz in all_data}
    if fb_competitor_data:
        for biz_key in ["sugar_shack", "island_candy", "island_arcade", "spi_fun_rentals",
                        "juan", "custom_designs_tx", "optimum_clinic", "optimum_foundation"]:
            if biz_key not in active_biz_keys or biz_key not in fb_competitor_data:
                continue
            biz_name = BUSINESS_NAMES.get(biz_key, biz_key)
            lines.append(f"### {biz_name}")
            lines.append("| Competitor | Last Post | Posts/7d | Recent Content |")
            lines.append("|------------|-----------|----------|----------------|")
            for c in fb_competitor_data[biz_key]:
                name = c.get("name", "?")
                status = c.get("status", "ok")
                if status == "no_fb_page":
                    lines.append(f"| {name} | No FB page | — | — |")
                elif status == "scrape_failed":
                    lines.append(f"| {name} | ❌ Scrape failed | — | — |")
                else:
                    last = c.get("last_post_date") or "unknown"
                    p7d = c.get("posts_last_7d", 0)
                    posts = c.get("recent_posts", [])
                    if posts:
                        first = posts[0]
                        raw = first.get("excerpt", first) if isinstance(first, dict) else first
                        excerpt = str(raw)[:80].replace("|", "/")
                    else:
                        excerpt = "—"
                    lines.append(f"| {name} | {last} | {p7d} | {excerpt} |")
            lines.append("")
    else:
        lines.append("No Facebook competitor data for today.")
        lines.append("Run: `python competitor_facebook_monitor.py`")
    lines += ["", "---", ""]

    # Competitor Paid Ads (Facebook Ad Library)
    lines.append("## Competitor Paid Ads (Facebook Ad Library)")
    lines.append("")
    lines.append("_Active paid ads currently running — longer running = proven winner creative._")
    lines.append("")
    if adlibrary_data:
        any_ads     = False
        dark_list   = []
        active_list = []
        for biz_key, biz_data in adlibrary_data.items():
            for comp in biz_data.get("competitors", []):
                if comp.get("no_ads"):
                    dark_list.append(f"{comp['name']} ({biz_key})")
                elif comp.get("active_ad_count", 0) > 0:
                    any_ads = True
                    active_list.append(comp)
        if dark_list:
            lines.append("**Gone dark (0 active ads):** " + ", ".join(dark_list))
            lines.append("")
        for biz_key, biz_data in adlibrary_data.items():
            biz_name = BUSINESS_NAMES.get(biz_key, biz_key)
            comps_with_ads = [c for c in biz_data.get("competitors", []) if c.get("active_ad_count", 0) > 0]
            if not comps_with_ads:
                continue
            lines.append(f"### {biz_name}")
            for comp in comps_with_ads:
                lines.append(f"**{comp['name']}** — {comp['active_ad_count']} active ads")
                for ad in comp.get("ads", [])[:3]:
                    days  = f"{ad['days_running']}d" if ad.get("days_running") is not None else "?"
                    flag  = " ⭐" if ad.get("long_runner") else ""
                    lines.append(f"- [{days}]{flag} {ad['copy'][:200]}")
                lines.append("")
        if not any_ads and not dark_list:
            lines.append("No ad data found. Run: `python competitor_fb_adlibrary.py`")
    else:
        lines.append("No Ad Library data yet. Run: `python competitor_fb_adlibrary.py`")
    lines += ["", "---", ""]

    # AI Competitor Analysis (recommended ad angles)
    lines.append("## AI Competitor Analysis — Recommended Ad Angles")
    lines.append("")
    lines.append("_gpt-4o-mini analysis of competitor activity → specific counter-angles to run today._")
    lines.append("")
    if ai_analysis:
        active_biz_keys = {biz["key"] for biz in all_data}
        shown = 0
        for r in ai_analysis:
            if r.get("status") in ("no_data", "dry_run"):
                continue
            if r.get("business") not in active_biz_keys:
                continue
            lines += [
                f"### {r['our_name']}",
                "",
                r.get("analysis", ""),
                "",
            ]
            shown += 1
        if shown == 0:
            lines.append("No AI analysis available for active businesses.")
            lines.append("Run: `python competitor_ai_analyzer.py`")
    else:
        lines.append("No AI analysis yet. Run: `python competitor_ai_analyzer.py`")
    lines += ["", "---", ""]

    # Google Review Intel (customer voice)
    lines.append("## Customer Voice Intel (Google Reviews)")
    lines.append("")
    lines.append("_Competitor review sentiment — complaints = your ad angles, praise = bar to beat._")
    lines.append("")
    if review_data:
        active_biz_keys = {biz["key"] for biz in all_data}
        shown = 0
        for biz_key, biz_data in review_data.items():
            if biz_key not in active_biz_keys:
                continue
            ai_text = biz_data.get("ai_analysis", "")
            if not ai_text:
                continue
            lines += [f"### {biz_data['our_name']}", "", ai_text, ""]
            shown += 1
        if shown == 0:
            lines.append("No review analysis for active businesses.")
            lines.append("Run: `python competitor_review_miner.py`")
    else:
        lines.append("No review data yet. Run: `python competitor_review_miner.py`")
    lines += ["", "---", ""]

    # GBP Competitor Intel
    lines.append("## GBP Competitor Intel")
    lines.append("")
    GBP_KEY_MAP = {"custom_designs_tx": "custom_designs"}
    if competitor_state:
        all_dates = [v.get("last_checked", "") for v in competitor_state.values() if v.get("last_checked")]
        if all_dates:
            lines.append(f"_GBP data last updated: {sorted(all_dates)[-1][:10]}_")
            lines.append("")
        active_biz_keys = {biz["key"] for biz in all_data}
        has_section = False
        for biz_key in ["sugar_shack", "island_candy", "island_arcade", "spi_fun_rentals",
                        "custom_designs_tx", "juan", "optimum_clinic", "optimum_foundation"]:
            if biz_key not in active_biz_keys:
                continue
            prefix = f"{biz_key}__"
            comps = [(k[len(prefix):], v) for k, v in competitor_state.items() if k.startswith(prefix)]
            if not comps:
                continue
            has_section = True
            gbp_key = GBP_KEY_MAP.get(biz_key, biz_key)
            our_rating = None
            our_reviews = None
            if gbp_data and gbp_key in gbp_data:
                our_rating = gbp_data[gbp_key].get("rating")
                rv = gbp_data[gbp_key].get("review_count")
                our_reviews = int(rv) if rv is not None else None
            our_r_str = f"⭐ {our_rating}" if our_rating else "—"
            if our_reviews is not None:
                our_rv_str = str(our_reviews)
            elif our_rating is not None:
                our_rv_str = "< 5"
            else:
                our_rv_str = "—"
            biz_name = BUSINESS_NAMES.get(biz_key, biz_key)
            lines.append(f"### {biz_name} — us: {our_r_str} ({our_rv_str} reviews)")
            lines.append("| Competitor | Rating | ▲▼ Rating | Reviews | ▲▼ Reviews | Hours |")
            lines.append("|------------|--------|-----------|---------|------------|-------|")
            for comp_name, data in comps:
                rating = data.get("rating")
                raw_rv = data.get("review_count")
                reviews = int(raw_rv) if raw_rv is not None else None
                hours = (data.get("hours_today") or "—").replace("|", "/")
                r_str = f"⭐ {rating}" if rating else "—"
                rv_str = str(reviews) if reviews is not None else "—"
                if rating and our_rating:
                    diff = float(rating) - float(our_rating)
                    rdelta = f"▲ +{diff:.1f}" if diff > 0.05 else (f"▼ {diff:.1f}" if diff < -0.05 else "= tied")
                else:
                    rdelta = "—"
                if reviews is not None and our_reviews is not None:
                    rv_diff = reviews - our_reviews
                    rv_delta = f"▲ +{rv_diff}" if rv_diff > 0 else (f"▼ {rv_diff}" if rv_diff < 0 else "= same")
                elif reviews is not None and our_reviews is None and our_rating is not None:
                    rv_delta = f"▲ +{reviews} vs <5"
                else:
                    rv_delta = "—"
                lines.append(f"| {comp_name} | {r_str} | {rdelta} | {rv_str} | {rv_delta} | {hours} |")
            lines.append("")
        if not has_section:
            lines.append("No competitor GBP data found. Run: `python competitor_monitor.py`")
    else:
        lines.append("No competitor GBP data. Run: `python competitor_monitor.py`")
    lines += ["", "---", ""]

    # Google Business Profile Health
    lines.append("## Google Business Profiles")
    lines.append("")
    if gbp_data:
        lines.append("| Account | Rating | Reviews | Delta | Alerts |")
        lines.append("|---------|--------|---------|-------|--------|")
        for key, info in gbp_data.items():
            if info.get("status") == "error":
                lines.append(f"| {info.get('name', key)} | — | — | — | ❌ Error |")
                continue
            rating = f"⭐ {info['rating']}" if info.get("rating") else "—"
            reviews = str(info.get("review_count", "—"))
            delta = info.get("rating_delta") or 0.0
            delta_str = f"+{delta:.1f}" if delta > 0 else (f"{delta:.1f}" if delta < 0 else "—")
            alerts = info.get("alerts", [])
            alert_str = ("⚠️ " + "; ".join(alerts)) if alerts else "✅ None"
            name = info.get("name", key)
            lines.append(f"| {name} | {rating} | {reviews} | {delta_str} | {alert_str} |")
    else:
        lines.append("GBP data unavailable. Run: `python gbp_morning_check.py`")
    lines += ["", "---", ""]

    # Keyword Rankings
    lines.append("## Keyword Rankings")
    lines.append("")
    kw_rankings = load_keyword_rankings()
    _KW_DISPLAY = {
        "sugar_shack": "The Sugar Shack", "island_arcade": "Island Arcade",
        "island_candy": "Island Candy",   "spi_fun_rentals": "SPI Fun Rentals",
        "custom_designs_tx": "Custom Designs TX", "optimum_clinic": "Optimum Clinic",
        "juan": "Juan Elizondo RE/MAX",   "optimum_foundation": "Optimum Foundation",
    }
    if kw_rankings:
        for biz_key, kw_data in kw_rankings.items():
            dates = [v["date"] for v in kw_data.values() if v.get("date")]
            last_date = max(dates) if dates else "—"
            name = _KW_DISPLAY.get(biz_key, biz_key)
            lines.append(f"### {name}as of {last_date}")
            lines.append("")
            lines.append("| Keyword | Local Rank | Organic | Top 3 in Google Maps |")
            lines.append("|---------|-----------|---------|----------------------|")
            for keyword, info in kw_data.items():
                mp_pos   = info.get("map_pack_position")
                maps_pos = info.get("maps_position")
                org_pos  = info.get("organic_position")
                if mp_pos:
                    rank_str = f"#{mp_pos} 3-pack"
                elif maps_pos:
                    rank_str = f"Maps #{maps_pos}"
                else:
                    rank_str = "Not ranking"
                org_str = f"#{org_pos}" if org_pos else "—"
                top3 = info.get("top3_maps_entries") or info.get("top3_map_pack", [])
                top3_names = " · ".join(
                    f"{e.get('name','?')} ⭐{e.get('rating','')}({e.get('reviews','?')})"
                    for e in top3[:3]
                ) if top3 else "—"
                lines.append(f"| {keyword} | {rank_str} | {org_str} | {top3_names} |")
            lines.append("")
    else:
        lines.append("No ranking data yet. Run: `python keyword_rank_tracker.py`")
    lines += ["", "---", ""]

    # Seasonal Hooks
    lines.append("## Seasonal Hooks (Next 14 Days)")
    lines.append("")
    if seasonal:
        for hook in seasonal:
            days = hook["days_until"]
            end_str = hook["end"].strftime("%b %d")
            label = "ACTIVE NOW" if days == 0 else f"in {days} days"
            biznames = ", ".join(BUSINESS_NAMES.get(b, b) for b in hook["relevant_for"][:3])
            lines.append(f"- **{hook['name']}** ({label}, ends {end_str})")
            lines.append(f"  - For: {biznames}")
            lines.append(f"  - Tip: {hook['tip']}")
    else:
        lines.append("- No major seasonal hooks in the next 14 days.")
    lines += ["", "---", ""]

    lines.append("*Generated by morning_brief.py*")
    return "\n".join(lines)

# ─── HTML Report ──────────────────────────────────────────────────────────────

def priority_badge(priority: str) -> str:
    colors = {"high": "#f85149", "medium": "#f0883e", "info": "#3fb950"}
    labels = {"high": "URGENT", "medium": "TODAY", "info": "FYI"}
    color = colors.get(priority, "#8b949e")
    label = labels.get(priority, priority.upper())
    return f'<span style="background:{color};color:#fff;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:700;margin-right:8px">{label}</span>'


def generate_html(all_data: list, action_items: list, seasonal: list, today: date, competitor_report: str, gbp_data: dict = None, fb_health: list = None, fb_competitor_data: dict = None, competitor_state: dict = None, delta_data: dict = None, calendar_data: dict = None, gmail_data: dict = None, attention_data: dict = None, time_breakdown_data: dict = None, last_activity_data: dict = None, claw_data: dict = None, audio_data: dict = None, correlation_data: dict = None, image_buckets: dict = None) -> str:
    weekday = today.strftime("%A")
    date_str = today.strftime("%B %d, %Y")

    # Build Facebook session status HTML
    fb_html = ""
    if fb_health:
        failed = [r for r in fb_health if r["status"] == "FAIL"]
        warned  = [r for r in fb_health if r["status"] == "WARN"]
        ok      = [r for r in fb_health if r["status"] == "OK"]
        if failed:
            rows = "".join(
                f'<li style="margin:6px 0"><span style="background:#f85149;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600">FAIL</span> '
                f'<code>{r["page"]}</code> &mdash; {r["detail"]}</li>'
                for r in failed
            )
            fb_html += f'<p style="color:#f85149;font-weight:600;margin-bottom:8px">&#9888; Session issue — fix before posting:</p><ul style="list-style:none;padding:0">{rows}</ul>'
        if warned:
            rows = "".join(
                f'<li style="margin:4px 0"><span style="background:#f0883e;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px">WARN</span> '
                f'<code>{r["page"]}</code> &mdash; {r["detail"]}</li>'
                for r in warned
            )
            fb_html += f'<ul style="list-style:none;padding:4px 0 0">{rows}</ul>'
        if ok and not failed and not warned:
            pages_str = ", ".join(f"<code>{r['page']}</code>" for r in ok)
            fb_html = f'<p style="color:#3fb950">&#10003; All sessions OK &mdash; {pages_str} ready to post.</p>'
        elif ok:
            pages_str = ", ".join(f"<code>{r['page']}</code>" for r in ok)
            fb_html += f'<p style="color:#3fb950;margin-top:8px">OK: {pages_str}</p>'
    else:
        fb_html = '<p style="color:#8b949e">Health check did not run. Run: <code>python fb_health_check.py</code></p>'

    # Build action items HTML
    action_html = ""
    if action_items:
        items_html = ""
        for item in action_items:
            badge = priority_badge(item["priority"])
            items_html += f'<li style="margin:8px 0;line-height:1.5">{badge}{item["text"]}</li>\n'
        action_html = f'<ul style="list-style:none;padding:0;margin:0">{items_html}</ul>'
    else:
        action_html = '<p style="color:#3fb950">All businesses on track. Nothing urgent today.</p>'

    # Build business cards HTML
    cards_html = ""
    for biz in all_data:
        days = biz["days_since_post"]
        days_label = f"{days}d ago" if days is not None else "never logged"
        overdue_style = "border-left:3px solid #f85149;" if biz["overdue"] else "border-left:3px solid #30363d;"
        overdue_badge = ' <span style="background:#f85149;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px">OVERDUE</span>' if biz["overdue"] else ""

        top_angle_html = ""
        if biz["top_angles"]:
            top = biz["top_angles"][0]
            top_angle_html = f'<div style="color:#3fb950;font-size:13px">Top angle: &ldquo;{top["angle"]}&rdquo; &mdash; avg {top["avg"]:.0f} score ({top["count"]} posts)</div>'
        else:
            top_angle_html = '<div style="color:#8b949e;font-size:13px">No engagement data yet</div>'

        comp_html = ""
        if biz["competitor_alerts"]:
            comp_items = " &bull; ".join(
                f'{c["name"]}: {c.get("rating","?")}⭐'
                for c in biz["competitor_alerts"][:2]
            )
            comp_html = f'<div style="color:#8b949e;font-size:12px;margin-top:4px">Competitors: {comp_items}</div>'

        rec_color = "#f85149" if biz["overdue"] else "#8b949e"

        cards_html += f"""
        <details style="background:#161b22;border:1px solid #30363d;{overdue_style}border-radius:6px;padding:12px 16px;margin-bottom:10px">
          <summary style="cursor:pointer;font-size:16px;font-weight:600;color:#c9d1d9;list-style:none;display:flex;justify-content:space-between;align-items:center">
            <span>{biz["icon"]} {biz["name"]}{overdue_badge}</span>
            <span style="color:#8b949e;font-size:13px;font-weight:400">Last post: {days_label}</span>
          </summary>
          <div style="margin-top:12px">
            {top_angle_html}
            {comp_html}
            <div style="color:{rec_color};font-size:13px;margin-top:8px;font-weight:500">{biz["recommendation"]}</div>
          </div>
        </details>"""

    # Build seasonal hooks HTML
    seasonal_html = ""
    if seasonal:
        for hook in seasonal:
            days = hook["days_until"]
            end_str = hook["end"].strftime("%b %d")
            label = "ACTIVE NOW" if days == 0 else f"in {days} days"
            color = "#3fb950" if days == 0 else ("#f0883e" if days <= 5 else "#8b949e")
            biznames = ", ".join(BUSINESS_NAMES.get(b, b) for b in hook["relevant_for"][:3])
            seasonal_html += f"""<div style="margin-bottom:12px;padding:10px 14px;background:#161b22;border:1px solid #30363d;border-radius:6px">
            <div style="color:{color};font-weight:600">{hook["name"]} <span style="font-weight:400;font-size:13px">({label}, ends {end_str})</span></div>
            <div style="color:#8b949e;font-size:13px;margin-top:4px">For: {biznames}</div>
            <div style="color:#c9d1d9;font-size:13px;margin-top:2px">{hook["tip"]}</div>
            </div>"""
    else:
        seasonal_html = '<p style="color:#8b949e">No major seasonal hooks in the next 14 days.</p>'

    # Competitor snapshot
    comp_snippet = ""
    if competitor_report:
        alert_match = re.search(r'## Alerts.*?(?=##|\Z)', competitor_report, re.DOTALL)
        if alert_match:
            raw = alert_match.group(0).strip()
            # Convert markdown bullets to HTML
            lines = raw.splitlines()
            html_lines = []
            for line in lines[1:]:  # skip the "## Alerts" header
                line = line.strip()
                if line.startswith("- "):
                    html_lines.append(f'<li style="margin:6px 0">{line[2:]}</li>')
            comp_snippet = f'<ul style="color:#c9d1d9;font-size:14px;padding-left:20px">{"".join(html_lines)}</ul>'
        else:
            comp_snippet = '<p style="color:#8b949e">Competitor report found but no alerts detected.</p>'
    else:
        comp_snippet = '<p style="color:#8b949e">No competitor report for today. Run: <code>python competitor_monitor.py</code></p>'

    # Facebook Competitor Social Activity
    active_biz_keys = {biz["key"] for biz in all_data}
    today_str_fb = today.strftime("%Y-%m-%d")
    fb_social_html = ""
    if fb_competitor_data:
        sections = []
        for biz_key in ["sugar_shack", "island_candy", "island_arcade", "spi_fun_rentals",
                        "juan", "custom_designs_tx", "optimum_clinic", "optimum_foundation"]:
            if biz_key not in active_biz_keys or biz_key not in fb_competitor_data:
                continue
            biz_name = BUSINESS_NAMES.get(biz_key, biz_key)
            cards_html = ""
            for c in fb_competitor_data[biz_key]:
                name = c.get("name", "?")
                status = c.get("status", "ok")
                if status == "no_fb_page":
                    cards_html += f'<div style="padding:8px 0;color:#8b949e;border-bottom:1px solid #21262d">{name} — No Facebook page</div>'
                    continue
                if status == "scrape_failed":
                    cards_html += f'<div style="padding:8px 0;color:#f85149;border-bottom:1px solid #21262d">{name} — ❌ Scrape failed</div>'
                    continue

                # Activity badge
                p7d = c.get("posts_last_7d", 0)
                if p7d >= 3:
                    badge = '<span style="background:#1a4a1a;color:#3fb950;padding:2px 8px;border-radius:10px;font-size:11px">🟢 Active</span>'
                elif p7d >= 1:
                    badge = '<span style="background:#3d2a00;color:#f0883e;padding:2px 8px;border-radius:10px;font-size:11px">🟡 Moderate</span>'
                else:
                    badge = '<span style="background:#2d1a1a;color:#f85149;padding:2px 8px;border-radius:10px;font-size:11px">🔴 Silent</span>'

                followers = c.get("followers") or "?"
                last = c.get("last_post_date") or "unknown"
                name_slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
                ss_path = f"../competitor_reports/fb_screenshots/{name_slug}_{today_str_fb}.png"

                # Screenshot embed — try today first, fall back to yesterday
                ss_file = COMPETITOR_REPORTS_DIR / f"fb_screenshots/{name_slug}_{today_str_fb}.png"
                if not ss_file.exists():
                    from datetime import timedelta
                    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
                    fallback = COMPETITOR_REPORTS_DIR / f"fb_screenshots/{name_slug}_{yesterday_str}.png"
                    if fallback.exists():
                        ss_file = fallback
                        ss_path = f"../competitor_reports/fb_screenshots/{name_slug}_{yesterday_str}.png"
                ss_html = ""
                if ss_file.exists():
                    ss_html = (f'<div style="margin:10px 0">'
                               f'<img src="{ss_path}" style="max-width:100%;border:1px solid #30363d;border-radius:6px" '
                               f'alt="Screenshot of {name}" loading="lazy">'
                               f'</div>')
                else:
                    ss_html = '<p style="color:#8b949e;font-size:12px;margin:8px 0">[No screenshot]</p>'

                # Post cards
                posts = c.get("recent_posts", [])
                posts_html = ""
                for post in posts[:3]:
                    # Handle both old format (str) and new format (dict)
                    if isinstance(post, str):
                        excerpt = post[:120].replace("<", "&lt;").replace(">", "&gt;")
                        eng_row = ""
                    else:
                        excerpt = post.get("excerpt", "")[:120].replace("<", "&lt;").replace(">", "&gt;")
                        likes = post.get("likes", 0)
                        comments = post.get("comments", 0)
                        shares = post.get("shares", 0)
                        post_date = post.get("date", "")
                        eng_parts = []
                        if likes:    eng_parts.append(f"👍 {likes}")
                        if comments: eng_parts.append(f"💬 {comments}")
                        if shares:   eng_parts.append(f"↗ {shares}")
                        eng_str = "  ".join(eng_parts) if eng_parts else "No engagement data"
                        eng_row = (f'<div style="color:#8b949e;font-size:11px;margin-top:4px">'
                                   f'{eng_str}'
                                   + (f' &nbsp;·&nbsp; {post_date}' if post_date else '')
                                   + '</div>')
                    if excerpt:
                        posts_html += (f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;'
                                       f'padding:10px 14px;margin:6px 0">'
                                       f'<div style="color:#c9d1d9;font-size:13px">{excerpt}</div>'
                                       f'{eng_row}</div>')

                if not posts_html:
                    posts_html = '<p style="color:#8b949e;font-size:12px">No post text extracted (image-only or no recent posts)</p>'

                cards_html += f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:14px 16px;margin:10px 0">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span style="color:#e6edf3;font-weight:600;font-size:14px">{name}</span>
    {badge}
  </div>
  <div style="color:#8b949e;font-size:12px;margin-bottom:8px">
    {followers} &nbsp;·&nbsp; Last post: {last} &nbsp;·&nbsp; {p7d} post(s) this week
  </div>
  {ss_html}
  <div style="margin-top:8px;font-size:12px;color:#8b949e;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Recent Posts</div>
  {posts_html}
</div>"""

            sections.append(f'<p style="color:#e6edf3;font-weight:700;font-size:15px;margin:20px 0 10px">{biz_name}</p>{cards_html}')
        fb_social_html = "".join(sections) if sections else '<p style="color:#8b949e">No SPI businesses in this run.</p>'
    else:
        fb_social_html = '<p style="color:#8b949e">No Facebook competitor data for today. Run: <code>python competitor_facebook_monitor.py</code></p>'

    # GBP Competitor Intel
    GBP_KEY_MAP = {"custom_designs_tx": "custom_designs"}
    gbp_intel_html = ""
    if competitor_state:
        active_biz_keys = {biz["key"] for biz in all_data}
        sections_out = []
        for biz_key in ["sugar_shack", "island_candy", "island_arcade", "spi_fun_rentals",
                        "custom_designs_tx", "juan", "optimum_clinic", "optimum_foundation"]:
            if biz_key not in active_biz_keys:
                continue
            prefix = f"{biz_key}__"
            comps = [(k[len(prefix):], v) for k, v in competitor_state.items() if k.startswith(prefix)]
            if not comps:
                continue
            gbp_key = GBP_KEY_MAP.get(biz_key, biz_key)
            our_rating = None
            our_reviews = None
            if gbp_data and gbp_key in gbp_data:
                our_info = gbp_data[gbp_key]
                our_rating = our_info.get("rating")
                r_val = our_info.get("review_count")
                our_reviews = int(r_val) if r_val is not None else None
            biz_name = BUSINESS_NAMES.get(biz_key, biz_key)

            our_r_str = f"⭐ {our_rating}" if our_rating else "—"
            if our_reviews is not None:
                our_rv_str = f"{our_reviews:,}"
            elif our_rating is not None:
                our_rv_str = '&lt; 5'  # has a rating but count not shown by Google = very few
            else:
                our_rv_str = "—"

            # Our row (green highlight)
            rows = (f'<tr style="background:#0d2010;font-weight:600">'
                    f'<td style="padding:8px 10px;color:#3fb950;border-bottom:2px solid #238636">✦ {biz_name} (US)</td>'
                    f'<td style="padding:8px 10px;color:#3fb950;border-bottom:2px solid #238636">{our_r_str}</td>'
                    f'<td style="padding:8px 10px;color:#3fb950;border-bottom:2px solid #238636">{our_rv_str}</td>'
                    f'<td style="padding:8px 10px;border-bottom:2px solid #238636">—</td>'
                    f'<td style="padding:8px 10px;border-bottom:2px solid #238636">—</td>'
                    f'</tr>')

            for comp_name, data in comps:
                rating = data.get("rating")
                raw_rv = data.get("review_count")
                reviews = int(raw_rv) if raw_rv is not None else None
                hours = data.get("hours_today") or "—"
                last_chk = (data.get("last_checked") or "")[:10]
                r_str = f"⭐ {rating}" if rating else "—"
                rv_str = f"{reviews:,}" if reviews is not None else "—"

                # Rating delta
                if rating and our_rating:
                    diff = float(rating) - float(our_rating)
                    if diff > 0.05:
                        rdelta_str = f'▲ +{diff:.1f}'
                        rdelta_color = "#f85149"
                    elif diff < -0.05:
                        rdelta_str = f'▼ {diff:.1f}'
                        rdelta_color = "#3fb950"
                    else:
                        rdelta_str = "= tied"
                        rdelta_color = "#f0883e"
                else:
                    rdelta_str, rdelta_color = "—", "#8b949e"

                # Review volume comparison
                if reviews is not None and our_reviews is not None:
                    rv_diff = reviews - our_reviews
                    if rv_diff > 0:
                        rv_delta = f'▲ +{rv_diff:,}'
                        rv_color = "#f85149"
                    elif rv_diff < 0:
                        rv_delta = f'▼ {rv_diff:,}'
                        rv_color = "#3fb950"
                    else:
                        rv_delta = "= same"
                        rv_color = "#f0883e"
                elif reviews is not None and our_reviews is None and our_rating is not None:
                    rv_delta = f'▲ +{reviews:,} vs &lt;5'
                    rv_color = "#f85149"
                else:
                    rv_delta, rv_color = "—", "#8b949e"

                rows += (f'<tr style="border-bottom:1px solid #21262d">'
                         f'<td style="padding:8px 10px;color:#c9d1d9">{comp_name}'
                         f'<div style="color:#8b949e;font-size:11px">{last_chk}</div></td>'
                         f'<td style="padding:8px 10px;color:#c9d1d9">{r_str} '
                         f'<span style="color:{rdelta_color};font-weight:600;font-size:12px">{rdelta_str}</span></td>'
                         f'<td style="padding:8px 10px;color:#c9d1d9">{rv_str} '
                         f'<span style="color:{rv_color};font-size:12px">{rv_delta}</span></td>'
                         f'<td style="padding:8px 10px;color:#8b949e;font-size:12px">{hours}</td>'
                         f'</tr>')

            table = (f'<p style="color:#e6edf3;font-weight:700;font-size:15px;margin:20px 0 8px">{biz_name}</p>'
                     f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
                     f'<thead><tr style="border-bottom:1px solid #30363d;color:#8b949e">'
                     f'<th style="text-align:left;padding:6px 10px">Business</th>'
                     f'<th style="text-align:left;padding:6px 10px">Rating</th>'
                     f'<th style="text-align:left;padding:6px 10px">Reviews</th>'
                     f'<th style="text-align:left;padding:6px 10px">Hours Today</th>'
                     f'</tr></thead><tbody>{rows}</tbody></table>')
            sections_out.append(table)

        if sections_out:
            last_run = ""
            all_dates = [v.get("last_checked", "") for v in competitor_state.values() if v.get("last_checked")]
            if all_dates:
                latest = sorted(all_dates)[-1][:10]
                last_run = f'<p style="color:#8b949e;font-size:11px;margin-bottom:8px">GBP data last updated: {latest} — run <code>python competitor_monitor.py</code> to refresh</p>'
            gbp_intel_html = last_run + "".join(sections_out)
        else:
            gbp_intel_html = '<p style="color:#8b949e">No competitor GBP data. Run: <code>python competitor_monitor.py</code></p>'
    else:
        gbp_intel_html = '<p style="color:#8b949e">No competitor GBP data. Run: <code>python competitor_monitor.py</code></p>'

    # GBP Health table
    if gbp_data:
        rows = ""
        for key, info in gbp_data.items():
            if info.get("status") == "error":
                rows += f'<tr><td>{info.get("name", key)}</td><td>—</td><td>—</td><td>—</td><td style="color:#f85149">❌ Error</td></tr>'
                continue
            rating = f"⭐ {info['rating']}" if info.get("rating") else "—"
            reviews = str(info.get("review_count", "—"))
            delta = info.get("rating_delta") or 0.0
            delta_str = f"+{delta:.1f}" if delta > 0 else (f"{delta:.1f}" if delta < 0 else "—")
            alerts = info.get("alerts", [])
            alert_color = "#f0883e" if alerts else "#3fb950"
            alert_str = ("⚠️ " + "; ".join(alerts)) if alerts else "✅ None"
            rows += f'<tr><td>{info.get("name", key)}</td><td>{rating}</td><td>{reviews}</td><td>{delta_str}</td><td style="color:{alert_color}">{alert_str}</td></tr>'
        gbp_html = f"""<table style="width:100%;border-collapse:collapse;font-size:14px;color:#c9d1d9">
<thead><tr style="border-bottom:1px solid #30363d;color:#8b949e">
<th style="text-align:left;padding:6px 10px">Account</th>
<th style="text-align:left;padding:6px 10px">Rating</th>
<th style="text-align:left;padding:6px 10px">Reviews</th>
<th style="text-align:left;padding:6px 10px">Delta</th>
<th style="text-align:left;padding:6px 10px">Alerts</th>
</tr></thead><tbody>{rows}</tbody></table>"""
    else:
        gbp_html = '<p style="color:#8b949e">GBP data unavailable. Run: <code>python gbp_morning_check.py</code></p>'

    # Keyword rankings
    kw_rankings = load_keyword_rankings()
    kw_rankings_html = generate_keyword_rankings_html(kw_rankings)

    # Calendar HTML
    calendar_html = ""
    if calendar_data and not calendar_data.get("error"):
        events = calendar_data.get("events", [])
        if events:
            items = ""
            for ev in events:
                if ev.get("all_day"):
                    time_str = "All day"
                else:
                    try:
                        time_str = datetime.fromisoformat(ev["start"]).strftime("%I:%M %p").lstrip("0")
                    except Exception:
                        time_str = ev["start"]
                loc = f' &mdash; <span style="color:#8b949e">{ev["location"]}</span>' if ev.get("location") else ""
                items += f'<li style="margin:8px 0"><span style="color:#79c0ff;font-weight:600">{time_str}</span> {ev["summary"]}{loc}</li>\n'
            calendar_html = f'<ul style="list-style:none;padding:0">{items}</ul>'
        else:
            calendar_html = '<p style="color:#3fb950">No events scheduled today.</p>'
    elif calendar_data and calendar_data.get("error"):
        calendar_html = f'<p style="color:#f0883e">Calendar unavailable: {calendar_data["error"]}</p>'
    else:
        calendar_html = '<p style="color:#8b949e">Calendar data not loaded.</p>'

    # Gmail HTML
    gmail_html = ""
    if gmail_data and not gmail_data.get("error"):
        unread = gmail_data.get("unread_count", 0)
        urgent = gmail_data.get("urgent", [])
        gmail_html = f'<div style="margin-bottom:10px"><span style="font-size:20px;font-weight:700;color:#e6edf3">{unread}</span> <span style="color:#8b949e">unread in inbox</span></div>'
        if urgent:
            gmail_html += f'<p style="color:#f0883e;font-weight:600;margin-bottom:8px">{len(urgent)} email(s) need attention (last 48h):</p>'
            for email in urgent[:10]:
                sender = email["from"].split("<")[0].strip() if "<" in email["from"] else email["from"]
                subj = email["subject"][:80]
                gmail_html += f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:10px 14px;margin:6px 0"><span style="color:#e6edf3;font-weight:600">{sender}</span><div style="color:#c9d1d9;font-size:13px;margin-top:2px">{subj}</div></div>'
        else:
            gmail_html += '<p style="color:#3fb950">No urgent unread emails.</p>'
    elif gmail_data and gmail_data.get("error"):
        gmail_html = f'<p style="color:#f0883e">Gmail unavailable: {gmail_data["error"]}</p>'
    else:
        gmail_html = '<p style="color:#8b949e">Gmail data not loaded.</p>'

    # Screenpipe Attention HTML
    attention_html = ""
    if attention_data:
        total = sum(attention_data.values())
        if total > 0:
            sorted_attn = sorted(attention_data.items(), key=lambda x: x[1], reverse=True)
            bars = ""
            for biz_key, count in sorted_attn:
                name = BUSINESS_NAMES.get(biz_key, biz_key)
                pct = (count / total * 100) if total else 0
                bar_width = max(2, int(pct * 3))
                color = "#f85149" if count == 0 else ("#3fb950" if pct >= 15 else "#f0883e")
                flag = ' <span style="color:#f85149;font-weight:600">[NEEDS ATTENTION]</span>' if count == 0 else ""
                bars += (f'<div style="margin:6px 0;display:flex;align-items:center">'
                         f'<span style="color:#c9d1d9;width:220px;font-size:13px">{name}</span>'
                         f'<div style="background:{color};height:14px;width:{bar_width}px;border-radius:3px;margin-right:8px"></div>'
                         f'<span style="color:#8b949e;font-size:12px">{count} ({pct:.0f}%)</span>{flag}</div>')
            zero_clients = [BUSINESS_NAMES.get(k, k) for k, v in attention_data.items() if v == 0]
            zero_note = ""
            if zero_clients:
                zero_note = f'<p style="color:#f85149;font-size:12px;margin-top:10px">Zero screen time yesterday: {", ".join(zero_clients)}</p>'
            attention_html = f'{bars}{zero_note}'

    # Build "Where You Left Off" + Time Breakdown HTML
    left_off_html = ""
    if last_activity_data:
        app = last_activity_data.get("app", "?")
        window = last_activity_data.get("window", "?")
        left_off_html = (f'<div style="background:#161b22;border:1px solid #30363d;border-left:3px solid #58a6ff;'
                         f'border-radius:6px;padding:14px 18px;font-size:14px">'
                         f'<span style="color:#58a6ff;font-weight:600">{app}</span>'
                         f' &mdash; <span style="color:#c9d1d9">{window}</span></div>')

    time_breakdown_html = ""
    if time_breakdown_data:
        total_min = sum(v["minutes"] for v in time_breakdown_data.values())
        if total_min > 0:
            sorted_apps = sorted(time_breakdown_data.items(), key=lambda x: x[1]["minutes"], reverse=True)
            tb_bars = ""
            for app_name, info in sorted_apps[:10]:
                bar_width = max(2, int(info["pct"] * 3))
                color = "#3fb950" if info["pct"] >= 15 else ("#f0883e" if info["pct"] >= 5 else "#8b949e")
                tb_bars += (f'<div style="margin:6px 0;display:flex;align-items:center">'
                            f'<span style="color:#c9d1d9;width:220px;font-size:13px">{app_name}</span>'
                            f'<div style="background:{color};height:14px;width:{bar_width}px;border-radius:3px;margin-right:8px"></div>'
                            f'<span style="color:#8b949e;font-size:12px">{info["minutes"]:.0f} min ({info["pct"]:.0f}%)</span></div>')
            time_breakdown_html = tb_bars

    # Build CLAW pending items HTML
    claw_html = ""
    if claw_data and claw_data.get("total", 0) > 0:
        claw_rows = ""
        if claw_data.get("by_client"):
            for client_name, count in sorted(claw_data["by_client"].items(), key=lambda x: -x[1]):
                claw_rows += (f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                              f'border-bottom:1px solid #21262d">'
                              f'<span style="color:#c9d1d9">{client_name}</span>'
                              f'<span style="color:#f0883e;font-weight:600">{count}</span></div>')
        if claw_data.get("by_type"):
            types_str = ", ".join(f"{t} ({c})" for t, c in sorted(claw_data["by_type"].items(), key=lambda x: -x[1]))
            claw_rows += f'<div style="color:#8b949e;font-size:12px;margin-top:8px">Types: {types_str}</div>'
        claw_rows += ('<div style="color:#8b949e;font-size:12px;margin-top:10px">'
                      '<code style="background:#21262d;color:#79c0ff;padding:2px 6px;border-radius:4px;font-size:12px">'
                      'python claw_bridge.py</code> to review</div>')
        claw_html = claw_rows

    # Build Voice Notes (Audio Miner) HTML
    audio_html = ""
    if audio_data and audio_data.get("segments", 0) > 0:
        audio_parts = ""
        if audio_data.get("client_mentions"):
            audio_parts += '<div style="margin-bottom:10px;color:#8b949e;font-size:12px;font-weight:600">CLIENT MENTIONS</div>'
            for ckey, count in sorted(audio_data["client_mentions"].items(), key=lambda x: -x[1]):
                name = BUSINESS_NAMES.get(ckey, ckey)
                audio_parts += (f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
                                f'border-bottom:1px solid #21262d">'
                                f'<span style="color:#c9d1d9">{name}</span>'
                                f'<span style="color:#d2a8ff;font-weight:600">{count}</span></div>')
        if audio_data.get("action_items"):
            audio_parts += '<div style="margin:12px 0 6px;color:#8b949e;font-size:12px;font-weight:600">ACTION ITEMS FROM VOICE</div>'
            for item in audio_data["action_items"][:5]:
                audio_parts += (f'<div style="padding:4px 0;color:#f0883e;font-size:13px">'
                                f'&bull; {item[:200]}</div>')
        if audio_data.get("strategy_notes"):
            audio_parts += '<div style="margin:12px 0 6px;color:#8b949e;font-size:12px;font-weight:600">STRATEGY NOTES</div>'
            for note in audio_data["strategy_notes"][:5]:
                audio_parts += (f'<div style="padding:4px 0;color:#79c0ff;font-size:13px">'
                                f'&bull; {note[:200]}</div>')
        audio_html = audio_parts

    # Build Attention ↔ Engagement Correlation HTML
    correlation_html = ""
    if correlation_data and correlation_data.get("clients"):
        corr_rows = ""
        status_colors = {"aligned": "#3fb950", "over-indexed": "#f0883e", "under-indexed": "#79c0ff", "no-data": "#484f58"}
        for biz_key, c in sorted(correlation_data["clients"].items(), key=lambda x: x[1]["attention_rank"]):
            color = status_colors.get(c["correlation"], "#8b949e")
            corr_rows += (f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                          f'border-bottom:1px solid #21262d;font-size:13px">'
                          f'<span style="color:#c9d1d9;width:180px">{c["name"]}</span>'
                          f'<span style="color:#8b949e;width:70px;text-align:right">{c["attention_mentions"]} attn</span>'
                          f'<span style="color:#8b949e;width:55px;text-align:right">{c["posts_count"]} posts</span>'
                          f'<span style="color:#8b949e;width:60px;text-align:right">{c["avg_engagement"]:.0f} eng</span>'
                          f'<span style="color:{color};width:100px;text-align:right;font-weight:600">{c["correlation"]}</span>'
                          f'</div>')
        if correlation_data.get("insight"):
            corr_rows += (f'<div style="margin-top:10px;padding:8px 12px;background:#21262d;border-radius:4px;'
                          f'color:#d2a8ff;font-size:12px;font-style:italic">{correlation_data["insight"]}</div>')
        correlation_html = corr_rows

    # Build Image Bucket HTML
    image_bucket_html = ""
    if image_buckets and image_buckets.get("low"):
        rows = ""
        for biz_key in image_buckets["low"]:
            info = image_buckets["clients"].get(biz_key, {})
            name = BUSINESS_NAMES.get(biz_key, biz_key)
            count = info.get("count", 0)
            color = "#f85149" if count == 0 else "#f0883e"
            label = "EMPTY" if count == 0 else f"{count} images"
            rows += (f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                     f'border-bottom:1px solid #21262d">'
                     f'<span style="color:#c9d1d9">{name}</span>'
                     f'<span style="color:{color};font-weight:600">{label}</span></div>')
        rows += ('<div style="color:#8b949e;font-size:12px;margin-top:8px">'
                 'Run the client ad skill or fal.ai to replenish.</div>')
        image_bucket_html = rows

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Morning Brief — {date_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; padding: 24px; }}
  h1 {{ color: #e6edf3; font-size: 24px; margin-bottom: 4px; }}
  h2 {{ color: #e6edf3; font-size: 17px; margin: 28px 0 14px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
  .subtitle {{ color: #8b949e; font-size: 13px; margin-bottom: 28px; }}
  .container {{ max-width: 860px; margin: 0 auto; }}
  .section {{ margin-bottom: 32px; }}
  .action-box {{ background: #161b22; border: 1px solid #30363d; border-left: 3px solid #f85149; border-radius: 6px; padding: 16px 20px; }}
  code {{ background: #21262d; color: #79c0ff; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
  details > summary::-webkit-details-marker {{ display: none; }}
</style>
</head>
<body>
<div class="container">
  <h1>Morning Brief</h1>
  <div class="subtitle">{weekday}, {date_str} &mdash; Generated {datetime.now().strftime("%I:%M %p")}</div>

  <div class="section">
    <h2>&#128200; Movements Since Yesterday</h2>
    {render_movements_html(delta_data)}
  </div>

  <div class="section">
    <h2>&#128273; Facebook Session Status</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 18px;font-size:14px">
      {fb_html}
    </div>
  </div>

  <div class="section">
    <h2>&#128197; Today's Calendar</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 18px;font-size:14px">
      {calendar_html}
    </div>
  </div>

  <div class="section">
    <h2>&#128231; Inbox Summary</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 18px;font-size:14px">
      {gmail_html}
    </div>
  </div>

  {"" if not left_off_html else f'''<div class="section">
    <h2>&#128204; Where You Left Off</h2>
    {left_off_html}
  </div>'''}

  {"" if not attention_html else f'''<div class="section">
    <h2>&#128065; Yesterday's Client Attention</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 18px;font-size:14px">
      {attention_html}
    </div>
  </div>'''}

  {"" if not time_breakdown_html else f'''<div class="section">
    <h2>&#9201; Yesterday's Time Breakdown ({sum(v["minutes"] for v in time_breakdown_data.values()):.0f} min)</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 18px;font-size:14px">
      {time_breakdown_html}
    </div>
  </div>'''}

  {"" if not claw_html else f'''<div class="section">
    <h2>&#128230; CLAW Pending Items ({claw_data.get("total", 0)} awaiting approval)</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-left:3px solid #f0883e;border-radius:6px;padding:14px 18px;font-size:14px">
      {claw_html}
    </div>
  </div>'''}

  {"" if not audio_html else f'''<div class="section">
    <h2>&#127908; Voice Notes Summary ({audio_data.get("segments", 0)} segments, {audio_data.get("duration_min", 0):.0f} min)</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-left:3px solid #d2a8ff;border-radius:6px;padding:14px 18px;font-size:14px">
      {audio_html}
    </div>
  </div>'''}

  {"" if not correlation_html else f'''<div class="section">
    <h2>&#128200; Attention vs Engagement ({correlation_data.get("period_days", 7)}d)</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-left:3px solid #3fb950;border-radius:6px;padding:14px 18px;font-size:14px">
      {correlation_html}
    </div>
  </div>'''}

  {"" if not image_bucket_html else f'''<div class="section">
    <h2>&#127912; Image Buckets — Low Stock Warning</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-left:3px solid #f85149;border-radius:6px;padding:14px 18px;font-size:14px">
      {image_bucket_html}
    </div>
  </div>'''}

  <div class="section">
    <h2>Action Items</h2>
    <div class="action-box">{action_html}</div>
  </div>

  <div class="section">
    <h2>Business Summaries</h2>
    {cards_html}
  </div>

  <div class="section">
    <h2>Competitor Snapshot</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:16px 20px">
      {comp_snippet}
    </div>
  </div>

  <div class="section">
    <h2>&#128249; Competitor Social Activity (Facebook)</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:16px 20px">
      {fb_social_html}
    </div>
  </div>

  <div class="section">
    <h2>&#128205; Google Business Profiles — Our Accounts</h2>
    {gbp_html}
  </div>

  <div class="section">
    <h2>&#11088; GBP Competitor Intel</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:16px 20px">
      {gbp_intel_html}
    </div>
  </div>

  <div class="section">
    <h2>&#128269; Keyword Rankings</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:16px 20px">
      {kw_rankings_html}
    </div>
  </div>

  <div class="section">
    <h2>Seasonal Hooks (Next 14 Days)</h2>
    {seasonal_html}
  </div>

  <div style="color:#8b949e;font-size:12px;margin-top:32px;text-align:center">
    Generated by morning_brief.py &mdash; run nightly or before any posting session
  </div>
</div>
</body>
</html>"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def _queue_autoresearch(businesses: list) -> None:
    """Scan the latest intelligence report for Critical-impact items.
    For each critical item that maps to an active business, write an entry to
    autoresearch_queue.json so the optimizer can be run next.
    Prints a summary line for each queued item."""
    intel_dir = Path(__file__).parent.parent.parent / "scratch" / "03_RESOURCES" / "Intelligence_Reports"
    if not intel_dir.exists():
        return

    reports = sorted(intel_dir.glob("Report_*.md"), reverse=True)
    if not reports:
        return

    report_text = reports[0].read_text(encoding="utf-8", errors="replace")

    # Extract business keywords mentioned near Critical lines
    BIZ_KEYWORDS = {
        "sugar_shack":     ["sugar shack", "candy store", "spi candy"],
        "island_arcade":   ["island arcade", "arcade"],
        "island_candy":    ["island candy", "ice cream"],
        "juan":            ["juan elizondo", "remax", "real estate"],
        "spi_fun_rentals": ["spi fun rentals", "golf cart", "rentals"],
        "custom_designs":  ["custom designs", "security camera", "home theater"],
        "optimum_clinic":  ["optimum", "clinic", "wound care"],
        "optimum_foundation": ["optimum foundation", "nonprofit"],
    }

    queued = []
    lines = report_text.splitlines()
    for i, line in enumerate(lines):
        if "Critical" not in line and "Must-Have" not in line:
            continue
        # Look at surrounding context (5 lines above)
        context = "\n".join(lines[max(0, i - 5):i + 1]).lower()
        for biz_key, keywords in BIZ_KEYWORDS.items():
            if biz_key not in businesses:
                continue
            if any(kw in context for kw in keywords):
                queued.append(biz_key)
                break

    # Deduplicate while preserving order
    seen = set()
    queued = [b for b in queued if not (b in seen or seen.add(b))]

    if not queued:
        return

    # Write queue file
    queue_path = Path(__file__).parent / "autoresearch_queue.json"
    existing = []
    if queue_path.exists():
        try:
            existing = json.loads(queue_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    today_str = date.today().isoformat()
    new_entries = [{"business": b, "date": today_str, "source": reports[0].name} for b in queued]
    # Avoid duplicate same-day entries
    existing_keys = {(e["business"], e["date"]) for e in existing}
    to_add = [e for e in new_entries if (e["business"], e["date"]) not in existing_keys]
    if to_add:
        queue_path.write_text(json.dumps(existing + to_add, indent=2), encoding="utf-8")

    print(f"\n  [Auto-Research Queue] Critical gaps found — optimizer suggested for:")
    for b in queued:
        print(f"    python ad_copy_optimizer.py {b}")
    print(f"  Queue file: {queue_path}")


def _queue_ai_angles() -> None:
    """Read the latest AI competitor analysis and queue counter-angles for ad_copy_optimizer.
    Extracts the numbered counter-angles from each business analysis and writes
    them to ai_angles_queue.json so they can be run immediately.
    Prints ready-to-run optimizer commands."""
    analysis_list = load_ai_analysis()
    if not analysis_list:
        return

    import re as _re
    queue_path = Path(__file__).parent / "ai_angles_queue.json"
    today_str  = date.today().isoformat()

    # Load existing queue to avoid duplicates
    existing = []
    if queue_path.exists():
        try:
            existing = json.loads(queue_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing_keys = {(e["business"], e["date"], e.get("angle", "")[:40]) for e in existing}

    new_entries = []
    print("\n  [AI Angles Queue] Counter-angles ready for ad_copy_optimizer:")
    for r in analysis_list:
        if r.get("status") != "ok":
            continue
        biz = r.get("business", "")
        analysis_text = r.get("analysis", "")

        # Extract numbered counter-angles from the analysis text
        # Looks for: "1. **Headline**" or "1. Hook:" patterns
        angle_matches = _re.findall(
            r'\d+\.\s+\*{0,2}["\']?([^*\n]{15,120})',
            analysis_text
        )
        # Also try to extract the hook/headline text after common prefixes
        hook_matches = _re.findall(
            r'(?:Hook|Headline|Copy):\s*["\']?([^"\'\n]{15,120})',
            analysis_text
        )
        angles = list(dict.fromkeys(angle_matches + hook_matches))[:3]  # dedupe, max 3

        for angle in angles:
            angle_clean = angle.strip().strip('"').strip("'")[:100]
            key = (biz, today_str, angle_clean[:40])
            if key not in existing_keys:
                new_entries.append({
                    "business": biz,
                    "date":     today_str,
                    "angle":    angle_clean,
                    "command":  f'python ad_copy_optimizer.py {biz} --angle "{angle_clean}"',
                })
                existing_keys.add(key)
            print(f"    {biz}: {angle_clean[:70]}")

    if new_entries:
        queue_path.write_text(
            json.dumps(existing + new_entries, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n  To run all queued angles:")
        for e in new_entries:
            print(f"    {e['command']}")
        print(f"\n  Queue file: {queue_path}")
    else:
        print("    (no new angles queued today)")


def run_brief(businesses: list, text_only: bool = False, open_browser: bool = False):
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    date_str = today.strftime("%Y-%m-%d")

    print(f"\n=== Morning Brief — {today.strftime('%A, %B %d, %Y')} ===")
    print(f"Businesses: {', '.join(businesses)}")
    print()

    state = load_competitor_state()
    competitor_report = get_latest_competitor_report()

    # Collect data for all businesses
    all_data = []
    for biz_key in businesses:
        print(f"  Reading {BUSINESS_NAMES[biz_key]}...", end=" ")
        data = collect_business_data(biz_key, state)
        all_data.append(data)
        days = data["days_since_post"]
        overdue = " [OVERDUE]" if data["overdue"] else ""
        days_label = f"{days}d ago" if days is not None else "no log"
        print(f"last post: {days_label}{overdue}")

    seasonal = get_active_seasonal_hooks(today, businesses)
    action_items = generate_action_items(all_data, seasonal, kw_rankings=load_keyword_rankings())

    # Auto-research queue — scan latest intelligence report for Critical gaps
    _queue_autoresearch(businesses)

    # AI angles queue — surface counter-angles from latest AI competitor analysis
    _queue_ai_angles()

    # Facebook session health check — verify profiles are authenticated and pages are reachable
    fb_health = None
    try:
        print("  Checking Facebook sessions...", end=" ")
        fb_health = _run_fb_health_check_silent()
        failed = [r for r in fb_health if r["status"] == "FAIL"]
        warned = [r for r in fb_health if r["status"] == "WARN"]
        ok     = [r for r in fb_health if r["status"] == "OK"]
        print(f"done ({len(ok)} OK, {len(warned)} WARN, {len(failed)} FAIL)")
        if failed:
            for r in failed:
                print(f"    [FAIL] {r['page']}: {r['detail']}")
    except Exception as e:
        print(f"  Facebook health check skipped: {e}")

    # Load Facebook competitor report
    fb_competitor_data = load_fb_competitor_report()
    if fb_competitor_data:
        total_pages = sum(len(v) for v in fb_competitor_data.values())
        print(f"  FB competitor data loaded — {total_pages} competitor entries across {len(fb_competitor_data)} businesses")
    else:
        print("  No FB competitor data found. Run: python competitor_facebook_monitor.py")

    # Load Ad Library report
    adlibrary_data = load_adlibrary_report()
    if adlibrary_data:
        total_ads = sum(c.get("active_ad_count", 0) for b in adlibrary_data.values() for c in b.get("competitors", []))
        print(f"  Ad Library data loaded — {total_ads} active competitor ads tracked")
    else:
        print("  No Ad Library data found. Run: python competitor_fb_adlibrary.py")

    # Load AI analysis
    ai_analysis = load_ai_analysis()
    if ai_analysis:
        ok = sum(1 for r in ai_analysis if r.get("status") == "ok")
        print(f"  AI analysis loaded — {ok} businesses analyzed")
    else:
        print("  No AI analysis found. Run: python competitor_ai_analyzer.py")

    # Load Google Review mining report
    review_data = load_review_report()
    if review_data:
        total_reviews = sum(len(c.get("reviews", [])) for b in review_data.values() for c in b.get("scraped", []))
        print(f"  Review data loaded — {total_reviews} competitor reviews across {len(review_data)} businesses")
    else:
        print("  No review data found. Run: python competitor_review_miner.py")

    # Fetch GBP data (Layer 1 public scrape — no Chrome required)
    gbp_data = None
    try:
        import importlib.util, asyncio
        spec = importlib.util.spec_from_file_location(
            "gbp_morning_check",
            Path(__file__).parent / "gbp_morning_check.py"
        )
        gbp_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gbp_mod)
        print("  Checking GBP accounts...", end=" ")
        gbp_data = asyncio.run(gbp_mod.run_all())
        alerts = sum(1 for v in gbp_data.values() if v.get("alerts"))
        print(f"done ({len(gbp_data)} accounts, {alerts} alerts)")
    except Exception as e:
        print(f"  GBP check skipped: {e}")

    # Load delta report (movements since yesterday)
    delta_data = load_delta_report()
    if delta_data and delta_data.get("has_baseline"):
        kw  = len(delta_data.get("keyword_movements", []))
        gbp = len(delta_data.get("competitor_rating_changes", []))
        ads = len(delta_data.get("ad_activity_changes", []))
        total = kw + gbp + ads
        if total:
            print(f"  Delta loaded — {total} changes ({kw} rankings, {gbp} GBP, {ads} ads)")
        else:
            print("  Delta loaded — no changes since yesterday")
    else:
        print("  No delta baseline yet. Run: python delta_tracker.py")

    # Fetch Google Calendar events
    calendar_data = None
    try:
        print("  Fetching calendar...", end=" ")
        calendar_data = _fetch_calendar_events()
        if calendar_data.get("error"):
            print(f"error: {calendar_data['error']}")
        else:
            count = len(calendar_data.get("events", []))
            print(f"done ({count} event{'s' if count != 1 else ''})")
    except Exception as e:
        print(f"skipped: {e}")

    # Fetch Gmail urgents
    gmail_data = None
    try:
        print("  Fetching inbox...", end=" ")
        gmail_data = _fetch_gmail_urgents()
        if gmail_data.get("error"):
            print(f"error: {gmail_data['error']}")
        else:
            unread = gmail_data.get("unread_count", 0)
            urgent = len(gmail_data.get("urgent", []))
            print(f"done ({unread} unread, {urgent} need attention)")
    except Exception as e:
        print(f"skipped: {e}")

    # Fetch Screenpipe client attention distribution
    attention_data = None
    try:
        print("  Checking Screenpipe attention...", end=" ")
        attention_data = _fetch_screenpipe_attention()
        if attention_data:
            total = sum(attention_data.values())
            active = sum(1 for v in attention_data.values() if v > 0)
            print(f"done ({total} mentions across {active} clients)")
        else:
            print("Screenpipe not available")
    except Exception as e:
        print(f"skipped: {e}")

    # Fetch Screenpipe time breakdown + where you left off
    time_breakdown_data = None
    last_activity_data = None
    try:
        print("  Checking Screenpipe time breakdown...", end=" ")
        time_breakdown_data = _fetch_screenpipe_time_breakdown()
        last_activity_data = _fetch_screenpipe_last_activity()
        if time_breakdown_data:
            top_app = max(time_breakdown_data.items(), key=lambda x: x[1]["minutes"])[0]
            total_min = sum(v["minutes"] for v in time_breakdown_data.values())
            print(f"done ({total_min:.0f} min tracked, top: {top_app})")
        else:
            print("no data for yesterday")
        if last_activity_data:
            print(f"  Where you left off: {last_activity_data.get('app', '?')} — {last_activity_data.get('window', '?')[:60]}")
    except Exception as e:
        print(f"skipped: {e}")

    # Fetch CLAW pending items
    claw_data = None
    try:
        print("  Checking CLAW pending items...", end=" ")
        claw_data = _fetch_claw_pending()
        if claw_data and claw_data.get("total"):
            print(f"done ({claw_data['total']} items pending approval)")
        else:
            print("none pending")
    except Exception as e:
        print(f"skipped: {e}")

    # Check OpenClaw local worker status
    openclaw_health = None
    try:
        print("  Checking OpenClaw local worker...", end=" ")
        import urllib.request as _ur
        _resp = _ur.urlopen("http://127.0.0.1:8080/health", timeout=3)
        openclaw_health = json.loads(_resp.read())
        _stats = openclaw_health.get("worker", {})
        print(f"running (default: {openclaw_health.get('default_model', '?')}, "
              f"completed: {_stats.get('tasks_completed', 0)}, "
              f"queue: {_stats.get('queue', {}).get('pending', 0)} pending)")
    except Exception as e:
        print(f"offline ({e})")

    # Fetch Screenpipe audio insights
    audio_data = None
    try:
        print("  Mining audio transcriptions...", end=" ")
        audio_data = _fetch_audio_insights()
        if audio_data and audio_data.get("segments"):
            mentions = sum(audio_data.get("client_mentions", {}).values())
            actions = len(audio_data.get("action_items", []))
            print(f"done ({audio_data['segments']} segments, {mentions} client mentions, {actions} action items)")
        else:
            print("no audio data for yesterday")
    except Exception as e:
        print(f"skipped: {e}")

    # Fetch engagement correlation
    correlation_data = None
    try:
        print("  Running attention ↔ engagement correlation...", end=" ")
        correlation_data = _fetch_engagement_correlation()
        if correlation_data and correlation_data.get("clients"):
            aligned = sum(1 for c in correlation_data["clients"].values() if c["correlation"] == "aligned")
            total = len(correlation_data["clients"])
            print(f"done ({aligned}/{total} clients aligned)")
        else:
            print("no data")
    except Exception as e:
        print(f"skipped: {e}")

    # Check image buckets
    image_buckets = None
    try:
        print("  Checking image buckets...", end=" ")
        image_buckets = _check_image_buckets()
        low = image_buckets.get("low", [])
        if low:
            names = [BUSINESS_NAMES.get(k, k) for k in low]
            print(f"WARNING: {len(low)} clients low — {', '.join(names)}")
        else:
            print("all clients stocked")
    except Exception as e:
        print(f"skipped: {e}")

    # Generate markdown
    md_content = generate_markdown(all_data, action_items, seasonal, today, competitor_report, gbp_data, fb_health, fb_competitor_data, competitor_state=state, adlibrary_data=adlibrary_data, ai_analysis=ai_analysis, review_data=review_data, delta_data=delta_data, calendar_data=calendar_data, gmail_data=gmail_data, attention_data=attention_data, time_breakdown_data=time_breakdown_data, last_activity_data=last_activity_data, claw_data=claw_data, audio_data=audio_data, correlation_data=correlation_data, image_buckets=image_buckets, openclaw_health=openclaw_health)
    md_path = BRIEFS_DIR / f"{date_str}.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\n[Markdown: {md_path}]")

    # Generate HTML
    if not text_only:
        html_content = generate_html(all_data, action_items, seasonal, today, competitor_report, gbp_data, fb_health, fb_competitor_data, competitor_state=state, delta_data=delta_data, calendar_data=calendar_data, gmail_data=gmail_data, attention_data=attention_data, time_breakdown_data=time_breakdown_data, last_activity_data=last_activity_data, claw_data=claw_data, audio_data=audio_data, correlation_data=correlation_data, image_buckets=image_buckets)
        html_path = BRIEFS_DIR / f"{date_str}.html"
        html_path.write_text(html_content, encoding="utf-8")
        print(f"[HTML:     {html_path}]")

        if open_browser:
            webbrowser.open(html_path.as_uri())
            print("[Opened in browser]")

    # Print action item preview
    print()
    if action_items:
        high = [a for a in action_items if a["priority"] == "high"]
        if high:
            print("ACTION ITEMS:")
            for item in high:
                print(f"  [URGENT] {item['text']}")
        medium = [a for a in action_items if a["priority"] == "medium"]
        for item in medium:
            print(f"  [TODAY]  {item['text']}")
    else:
        print("All businesses on track. Nothing urgent today.")
    print()


def main():
    parser = argparse.ArgumentParser(description="Morning brief generator for all 8 client businesses")
    parser.add_argument("--business", choices=list(BUSINESS_DIRS.keys()), help="Single business only")
    parser.add_argument("--open", action="store_true", dest="open_browser", help="Auto-open HTML in browser")
    parser.add_argument("--text-only", action="store_true", help="Markdown only, skip HTML")
    args = parser.parse_args()

    businesses = [args.business] if args.business else list(BUSINESS_DIRS.keys())
    run_brief(businesses, text_only=args.text_only, open_browser=args.open_browser)


if __name__ == "__main__":
    main()
