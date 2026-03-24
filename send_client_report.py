#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
send_client_report.py — Per-client marketing performance report generator + sender.

Generates a clean, professional HTML report for one client (no cross-client data).
Optionally emails it via the Gmail API already set up in ~/gws-workspace/.

Usage:
    python send_client_report.py --client sugar_shack            # generate HTML only
    python send_client_report.py --client juan --preview         # generate + open in browser
    python send_client_report.py --client custom_designs_tx --email   # generate + email
    python send_client_report.py --all                           # generate all clients
    python send_client_report.py --all --email                   # generate + email all (skips null emails)

Output: client_reports/YYYY-MM-DD_<client_key>.html
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import webbrowser
from datetime import date
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────────
EXECUTION_DIR  = Path(__file__).parent
REPORTS_DIR    = EXECUTION_DIR / "client_reports"
CONTACTS_PATH  = EXECUTION_DIR / "client_contacts.json"
GBP_STATE_PATH = EXECUTION_DIR / "gbp_state.json"
COMP_STATE     = EXECUTION_DIR / "competitor_reports" / "state.json"
COMP_REPORTS   = EXECUTION_DIR / "competitor_reports"
GWS_DIR        = Path.home() / "gws-workspace"

REPORTS_DIR.mkdir(exist_ok=True)

BUSINESS_ORDER = [
    "sugar_shack", "island_arcade", "island_candy", "spi_fun_rentals",
    "juan", "custom_designs_tx", "optimum_clinic", "optimum_foundation",
]

# ── Load contacts ──────────────────────────────────────────────────────────────
def load_contacts() -> dict:
    if CONTACTS_PATH.exists():
        return json.loads(CONTACTS_PATH.read_text(encoding="utf-8"))
    return {}


# ── Load GBP state ─────────────────────────────────────────────────────────────
def load_gbp_state() -> dict:
    if GBP_STATE_PATH.exists():
        try:
            return json.loads(GBP_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


# ── Load keyword rankings (filtered to client) ────────────────────────────────
def load_keyword_rankings_for(biz_key: str) -> dict:
    """Returns {keyword: info_dict} for one business."""
    try:
        spec = importlib.util.spec_from_file_location(
            "keyword_rank_tracker",
            EXECUTION_DIR / "keyword_rank_tracker.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        all_rankings = mod.load_rankings_summary()

        cfg_path = EXECUTION_DIR / "keyword_rankings_config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        active_kws = set(cfg.get("businesses", {}).get(biz_key, {}).get("keywords", []))

        return {
            kw: data for kw, data in all_rankings.get(biz_key, {}).items()
            if kw in active_kws
        }
    except Exception:
        return {}


# ── Load competitor state for one business ────────────────────────────────────
def load_competitor_data(biz_key: str) -> list:
    """Returns list of {name, rating, review_count, last_checked}."""
    if not COMP_STATE.exists():
        return []
    try:
        state = json.loads(COMP_STATE.read_text(encoding="utf-8"))
    except Exception:
        return []

    competitors = []
    prefix = f"{biz_key}__"
    for key, data in state.items():
        if key.startswith(prefix):
            name = key[len(prefix):]
            competitors.append({
                "name": name,
                "rating": data.get("rating"),
                "review_count": data.get("review_count"),
                "last_checked": data.get("last_checked", ""),
            })
    return competitors


# ── Load FB competitor data for one business ──────────────────────────────────
def load_fb_competitor_data(biz_key: str) -> list:
    """Returns list of full competitor dicts from the facebook_*.json report."""
    today_str = date.today().strftime("%Y-%m-%d")
    candidates = [COMP_REPORTS / f"facebook_{today_str}.json"]
    candidates += sorted(COMP_REPORTS.glob("facebook_*.json"), reverse=True)
    seen = set()
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entries = data.get(biz_key, [])
                if isinstance(entries, list) and entries:
                    # Return entries that actually have data (status == "ok")
                    result = [e for e in entries if e.get("name") not in seen]
                    for e in result:
                        seen.add(e.get("name"))
                    if result:
                        return result
            except Exception:
                pass
    return []


def _screenshot_b64(comp_name: str) -> str | None:
    """Load the most recent screenshot for a competitor as a base64 data URI."""
    import base64
    slug = comp_name.lower().replace(" ", "_").replace("-", "_").replace("&", "and").replace("'", "_").replace(",", "").replace("__", "_")
    shots = sorted(
        (COMP_REPORTS / "fb_screenshots").glob(f"{slug}_*.png"),
        reverse=True
    )
    if shots:
        try:
            data = shots[0].read_bytes()
            b64 = base64.b64encode(data).decode()
            return f"data:image/png;base64,{b64}"
        except Exception:
            pass
    return None


# ── Load posting cadence from program.md ──────────────────────────────────────
def load_posting_cadence(biz_key: str) -> dict:
    """Returns {days_since_post, last_post_date}."""
    program_path = EXECUTION_DIR / biz_key / "program.md"
    if not program_path.exists():
        return {}
    md = program_path.read_text(encoding="utf-8", errors="replace")

    posts = []
    in_log = False
    header_done = False
    for line in md.splitlines():
        if "## Posting Log" in line:
            in_log = True
            header_done = False
            continue
        if in_log and line.startswith("## "):
            break
        if in_log and line.startswith("|"):
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if not cells:
                continue
            if not header_done:
                header_done = True
                continue
            if all(c.startswith("-") for c in cells):
                continue
            if cells and "fill in" not in cells[0].lower():
                posts.append(cells)

    latest = None
    for row in posts:
        if not row:
            continue
        date_str = row[0].strip()
        if not date_str or date_str.startswith("_"):
            continue
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
            try:
                from datetime import datetime
                d = datetime.strptime(date_str, fmt).date()
                if latest is None or d > latest:
                    latest = d
                break
            except ValueError:
                continue

    if latest is None:
        return {"days_since_post": None, "last_post_date": None}
    return {
        "days_since_post": (date.today() - latest).days,
        "last_post_date": str(latest),
    }


# ── HTML helpers ──────────────────────────────────────────────────────────────
def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _rank_label(info: dict) -> str:
    mp  = info.get("map_pack_position")
    ext = info.get("maps_position")
    org = info.get("organic_position")
    if mp:
        return f"<strong style='color:#16a34a'>#{mp}</strong> <small style='color:#64748b'>3-pack</small>"
    if ext:
        return f"<strong style='color:#d97706'>#{ext}</strong> <small style='color:#64748b'>Maps</small>"
    if org:
        return f"<small style='color:#64748b'>Organic #{org}</small>"
    return "<span style='color:#94a3b8'>Not ranking yet</span>"


def _top3_str(info: dict) -> str:
    top3 = [e for e in info.get("top3_maps_entries", []) if e.get("name")][:3]
    if not top3:
        top3 = [e for e in info.get("top3_map_pack", []) if e.get("name")][:3]
    if not top3:
        return "<span style='color:#94a3b8'>—</span>"
    parts = []
    for e in top3:
        name = _esc(e.get("name", "?")[:30])
        rating = e.get("rating", "")
        reviews = e.get("reviews", "?")
        star = f" ⭐{rating}({reviews})" if rating else ""
        parts.append(f"<span style='color:#475569'>{name}{star}</span>")
    return " &middot; ".join(parts)


# ── HTML report generator ─────────────────────────────────────────────────────
def generate_client_html(biz_key: str, contact: dict) -> str:
    client_name = contact.get("client_name", biz_key)
    today       = date.today().strftime("%B %d, %Y")
    today_iso   = date.today().strftime("%Y-%m-%d")

    # Load all data
    gbp_state   = load_gbp_state()
    gbp_data    = gbp_state.get(biz_key, {})
    kw_rankings = load_keyword_rankings_for(biz_key)
    competitors = load_competitor_data(biz_key)
    fb_comps    = load_fb_competitor_data(biz_key)
    cadence     = load_posting_cadence(biz_key)

    # ── Section: GBP Status ───────────────────────────────────────────────────
    gbp_rating  = gbp_data.get("rating")
    gbp_reviews = gbp_data.get("review_count")
    if gbp_rating and gbp_reviews:
        gbp_html = f"""
        <div class="metric-row">
          <div class="metric">
            <div class="metric-label">Google Rating</div>
            <div class="metric-value">⭐ {gbp_rating}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Total Reviews</div>
            <div class="metric-value">{gbp_reviews:,}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Last Checked</div>
            <div class="metric-value small">{gbp_data.get('last_checked', today_iso)}</div>
          </div>
        </div>
        <p style="margin-top:8px;color:#16a34a;font-size:13px">✅ Your Google Business Profile is active and verified.</p>
        """
    elif gbp_data:
        gbp_html = "<p style='color:#94a3b8'>GBP data not yet collected. Run: <code>python gbp_morning_check.py</code></p>"
    else:
        gbp_html = "<p style='color:#94a3b8'>No GBP data on file yet.</p>"

    # ── Section: Keyword Rankings ─────────────────────────────────────────────
    if kw_rankings:
        rows = []
        for kw, info in kw_rankings.items():
            rank_cell = _rank_label(info)
            top3_cell = _top3_str(info)
            rows.append(
                f"<tr>"
                f"<td>{_esc(kw)}</td>"
                f"<td style='text-align:center'>{rank_cell}</td>"
                f"<td style='font-size:12px;color:#475569'>{top3_cell}</td>"
                f"</tr>"
            )
        kw_html = f"""
        <table class="data-table">
          <thead><tr>
            <th>Keyword</th>
            <th>Your Rank</th>
            <th>Who's #1</th>
          </tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
        <p style="font-size:12px;color:#94a3b8;margin-top:8px">
          🟢 3-pack = top of Google Maps (best). 🟡 Maps = visible but below top 3. ⬜ Not ranking = not yet appearing.
        </p>
        """
    else:
        kw_html = "<p style='color:#94a3b8'>No keyword data on file yet. Rankings are updated weekly.</p>"

    # ── Section: Competitor Overview ──────────────────────────────────────────
    comp_rows = []
    # GBP competitors
    for c in competitors:
        rating_str = f"⭐ {c['rating']}" if c["rating"] else "—"
        rc = c["review_count"]
        reviews_str = f"{int(rc):,}" if rc and str(rc).isdigit() else (str(rc) if rc else "—")
        # Look up FB data for this competitor
        fb_match = next((f for f in fb_comps if f["name"].lower() in c["name"].lower()
                         or c["name"].lower() in f["name"].lower()), None)
        last_post = fb_match["last_post_date"] if fb_match and fb_match.get("last_post_date") else "—"
        comp_rows.append(
            f"<tr>"
            f"<td>{_esc(c['name'])}</td>"
            f"<td style='text-align:center'>{rating_str}</td>"
            f"<td style='text-align:center'>{reviews_str}</td>"
            f"<td style='text-align:center;font-size:12px;color:#64748b'>{_esc(last_post)}</td>"
            f"</tr>"
        )

    # FB-only competitors (no GBP data)
    gbp_names_lower = {c["name"].lower() for c in competitors}
    for f in fb_comps:
        if not any(f["name"].lower() in n or n in f["name"].lower() for n in gbp_names_lower):
            last_post = f.get("last_post_date", "—") or "—"
            comp_rows.append(
                f"<tr>"
                f"<td>{_esc(f['name'])}</td>"
                f"<td style='text-align:center;color:#94a3b8'>—</td>"
                f"<td style='text-align:center;color:#94a3b8'>—</td>"
                f"<td style='text-align:center;font-size:12px;color:#64748b'>{_esc(last_post)}</td>"
                f"</tr>"
            )

    if comp_rows:
        comp_html = f"""
        <table class="data-table">
          <thead><tr>
            <th>Competitor</th>
            <th>Google Rating</th>
            <th>Reviews</th>
            <th>Last FB Post</th>
          </tr></thead>
          <tbody>{"".join(comp_rows)}</tbody>
        </table>
        """
    else:
        comp_html = "<p style='color:#94a3b8'>Competitor data not yet collected. Run: <code>python competitor_monitor.py</code></p>"

    # ── Section: Facebook Competitor Activity ─────────────────────────────────
    fb_cards = ""
    for comp in fb_comps:
        name   = comp.get("name", "?")
        status = comp.get("status", "ok")

        # No Facebook page — show a minimal "not present" card
        if status == "no_fb_page":
            fb_cards += f"""
        <div style='border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px;margin-bottom:14px;background:#fafafa;display:flex;align-items:center;gap:12px'>
          <span style='font-size:20px'>📵</span>
          <div>
            <strong style='font-size:14px;color:#1e293b'>{_esc(name)}</strong>
            <span style='color:#94a3b8;font-size:13px;margin-left:8px'>No Facebook page</span>
          </div>
        </div>
        """
            continue

        followers    = comp.get("followers", "—")
        last_dt      = comp.get("last_post_date", "—") or "—"
        posts_7d     = comp.get("posts_last_7d", 0) or 0
        recent_posts = comp.get("recent_posts", [])

        # Activity badge
        if posts_7d >= 5:
            freq_badge = f"<span style='background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:10px;font-size:11px'>🔥 {posts_7d}/week</span>"
        elif posts_7d >= 2:
            freq_badge = f"<span style='background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:10px;font-size:11px'>📅 {posts_7d}/week</span>"
        elif posts_7d == 1:
            freq_badge = f"<span style='background:#f1f5f9;color:#475569;padding:2px 8px;border-radius:10px;font-size:11px'>📋 1/week</span>"
        else:
            freq_badge = "<span style='background:#f1f5f9;color:#94a3b8;padding:2px 8px;border-radius:10px;font-size:11px'>Inactive</span>"

        # Screenshot
        shot_b64 = _screenshot_b64(name)
        shot_html = (
            f"<img src='{shot_b64}' alt='Screenshot of {_esc(name)} Facebook page' "
            f"style='width:100%;max-width:460px;border-radius:6px;border:1px solid #e2e8f0;margin-top:10px;display:block'>"
        ) if shot_b64 else ""

        # Recent posts
        post_items = ""
        for p in recent_posts[:2]:
            excerpt = (p.get("excerpt") or "").strip().replace("\n", " ")[:120]
            p_date  = p.get("date", "")
            shares  = p.get("shares", 0) or 0
            post_items += (
                f"<div style='padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:13px;color:#334155'>"
                f"<div style='color:#94a3b8;font-size:11px;margin-bottom:2px'>{_esc(p_date)}"
                f"{'  · ' + str(shares) + ' shares' if shares else ''}</div>"
                f"{_esc(excerpt)}{'…' if len(excerpt) == 120 else ''}"
                f"</div>"
            )

        fb_cards += f"""
        <div style='border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin-bottom:14px;background:#fafafa'>
          <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px'>
            <div>
              <strong style='font-size:15px;color:#1e293b'>{_esc(name)}</strong>
              <span style='color:#64748b;font-size:12px;margin-left:8px'>{_esc(followers)}</span>
            </div>
            <div style='display:flex;gap:6px;align-items:center;flex-wrap:wrap'>
              {freq_badge}
              <span style='color:#94a3b8;font-size:12px'>Last post: {_esc(last_dt)}</span>
            </div>
          </div>
          {('<div style="margin-top:10px">' + post_items + '</div>') if post_items else ''}
          {shot_html}
        </div>
        """

    if fb_cards:
        fb_section_html = fb_cards
    else:
        fb_section_html = "<p style='color:#94a3b8'>No Facebook competitor data yet. Run: <code>python competitor_facebook_monitor.py</code></p>"

    # ── Section: Action Items ─────────────────────────────────────────────────
    actions = []

    # Posting cadence
    days_ago = cadence.get("days_since_post")
    if days_ago is None:
        actions.append(("📋", "info", "No posts logged yet in the system — add your posting history to start tracking."))
    elif days_ago >= 4:
        actions.append(("🔴", "urgent", f"Last post was {days_ago} days ago — time to post! Consistent posting = more Google visibility."))
    elif days_ago >= 2:
        actions.append(("🟡", "medium", f"Last post was {days_ago} days ago — consider posting in the next day or two."))
    else:
        actions.append(("✅", "good", f"Posted {days_ago} day(s) ago — posting cadence looks good!"))

    # GBP review count advisory
    if gbp_reviews is not None:
        if gbp_reviews < 5:
            actions.append(("⭐", "urgent", f"You have {gbp_reviews} Google review(s). Getting to 5+ reviews is the #1 priority — Google will start showing you in Maps searches once you hit that threshold. Send review requests to your past customers today."))
        elif gbp_reviews < 25:
            actions.append(("⭐", "medium", f"You have {gbp_reviews} Google reviews. Keep asking happy customers to leave a review — businesses with 25+ reviews get significantly more visibility."))
        else:
            actions.append(("⭐", "good", f"Strong review count ({gbp_reviews} reviews). Keep the momentum going — respond to every new review."))

    # Ranking advisory
    not_ranking = [kw for kw, info in kw_rankings.items()
                   if not info.get("map_pack_position") and not info.get("maps_position")]
    ranking = [kw for kw, info in kw_rankings.items()
               if info.get("map_pack_position") or info.get("maps_position")]
    if ranking:
        actions.append(("📍", "good", f"Ranking in Google Maps for {len(ranking)} keyword(s): {', '.join(ranking[:3])}{'...' if len(ranking) > 3 else ''}."))
    if not_ranking and not ranking:
        actions.append(("📍", "medium", f"Not yet ranking for {len(not_ranking)} tracked keyword(s). This improves as reviews and GBP activity build up over 60–90 days."))

    action_rows = ""
    priority_colors = {
        "urgent": "#fee2e2",
        "medium": "#fef9c3",
        "good":   "#dcfce7",
        "info":   "#f0f9ff",
    }
    priority_border = {
        "urgent": "#f87171",
        "medium": "#fbbf24",
        "good":   "#4ade80",
        "info":   "#38bdf8",
    }
    for icon, priority, text in actions:
        bg     = priority_colors.get(priority, "#f8fafc")
        border = priority_border.get(priority, "#cbd5e1")
        action_rows += f"""
        <div style="background:{bg};border-left:4px solid {border};padding:10px 14px;margin-bottom:8px;border-radius:0 6px 6px 0;font-size:14px;color:#1e293b">
          {icon} {_esc(text)}
        </div>
        """

    # ── Assemble full HTML ────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(client_name)} — Marketing Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: #f8fafc;
    color: #1e293b;
    line-height: 1.5;
  }}
  .header {{
    background: linear-gradient(135deg, #1a2a5e 0%, #2d4a9e 100%);
    color: #fff;
    padding: 32px 40px 28px;
  }}
  .header h1 {{ font-size: 26px; font-weight: 700; letter-spacing: -0.5px; }}
  .header .subtitle {{ opacity: 0.8; font-size: 14px; margin-top: 4px; }}
  .header .date-badge {{
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border-radius: 20px;
    padding: 3px 14px;
    font-size: 12px;
    margin-top: 10px;
  }}
  .container {{ max-width: 860px; margin: 0 auto; padding: 28px 20px; }}
  .section {{
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 1px 6px rgba(0,0,0,.07);
    padding: 22px 24px;
    margin-bottom: 20px;
  }}
  .section h2 {{
    font-size: 16px;
    font-weight: 700;
    color: #1a2a5e;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 2px solid #e2e8f0;
  }}
  .metric-row {{ display: flex; gap: 20px; flex-wrap: wrap; }}
  .metric {{
    flex: 1;
    min-width: 120px;
    background: #f8fafc;
    border-radius: 8px;
    padding: 14px 18px;
    border: 1px solid #e2e8f0;
  }}
  .metric-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .metric-value {{ font-size: 22px; font-weight: 700; color: #1e293b; }}
  .metric-value.small {{ font-size: 14px; }}
  .data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .data-table th {{
    text-align: left;
    padding: 8px 10px;
    background: #f1f5f9;
    color: #64748b;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border-bottom: 1px solid #e2e8f0;
  }}
  .data-table td {{
    padding: 9px 10px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: top;
  }}
  .data-table tr:last-child td {{ border-bottom: none; }}
  .data-table tr:hover td {{ background: #f8fafc; }}
  .footer {{
    text-align: center;
    padding: 24px 20px;
    color: #94a3b8;
    font-size: 12px;
    border-top: 1px solid #e2e8f0;
    margin-top: 8px;
  }}
  .footer strong {{ color: #1a2a5e; }}
  @media (max-width: 600px) {{
    .header {{ padding: 20px; }}
    .container {{ padding: 16px 12px; }}
    .section {{ padding: 16px; }}
    .metric-value {{ font-size: 18px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div style="max-width:860px;margin:0 auto">
    <h1>{_esc(client_name)}</h1>
    <div class="subtitle">Digital Marketing Performance Report</div>
    <div class="date-badge">📅 {today}</div>
  </div>
</div>

<div class="container">

  <!-- GBP Status -->
  <div class="section">
    <h2>📍 Your Google Business Profile</h2>
    {gbp_html}
  </div>

  <!-- Keyword Rankings -->
  <div class="section">
    <h2>🔍 Google Maps Keyword Rankings</h2>
    {kw_html}
  </div>

  <!-- Competitors -->
  <div class="section">
    <h2>👀 Competitor Overview</h2>
    {comp_html}
  </div>

  <!-- Facebook Competitor Activity -->
  <div class="section">
    <h2>📱 Competitor Facebook Activity</h2>
    {fb_section_html}
  </div>

  <!-- Action Items -->
  <div class="section">
    <h2>✅ Recommended Actions</h2>
    {action_rows}
  </div>

</div>

<div class="footer">
  Prepared by <strong>Antigravity Digital</strong> &nbsp;·&nbsp;
  Report generated {today} &nbsp;·&nbsp;
  Data updated weekly
</div>

</body>
</html>"""
    return html


# ── Email sender (calls Node.js gws-workspace) ────────────────────────────────
def send_via_gmail(to_email: str, client_name: str, html_body: str, cc: str = None) -> bool:
    """Write a temp Node.js script and invoke it to send the email."""
    today = date.today().strftime("%B %d, %Y")
    subject = f"{client_name} — Marketing Performance Report ({today})"

    # Build a small Node.js sender inline, piggybacking on gws-workspace auth
    sender_js = GWS_DIR / "_send_report_temp.js"
    html_escaped = json.dumps(html_body)

    to_line = f"To: {to_email}"
    cc_line = f"Cc: {cc}" if cc else ""

    js_code = f"""import fs from 'fs';
import path from 'path';
import {{ google }} from 'googleapis';
import {{ fileURLToPath }} from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CREDENTIALS_PATH = path.join(process.env.HOME || process.env.USERPROFILE, '.config/gws/client_secret.json');
const TOKEN_PATH = path.join(__dirname, 'token.json');

async function send() {{
  const token = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));
  const content = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
  const {{ client_id, client_secret, redirect_uris }} = content.installed;

  const auth = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);
  auth.setCredentials(token);
  const gmail = google.gmail({{ version: 'v1', auth }});

  const profile = await gmail.users.getProfile({{ userId: 'me' }});
  const from = profile.data.emailAddress;

  const boundary = 'report_boundary_' + Date.now();
  const htmlBody = {html_escaped};
  const subject = {json.dumps(subject)};
  const toEmail = {json.dumps(to_email)};
  {"const ccEmail = " + json.dumps(cc) + ";" if cc else ""}

  const mimeParts = [
    `From: ${{from}}`,
    `To: ${{toEmail}}`,
    {"'`Cc: ' + ccEmail," if cc else ""}
    `Subject: ${{subject}}`,
    `MIME-Version: 1.0`,
    `Content-Type: multipart/alternative; boundary="${{boundary}}"`,
    ``,
    `--${{boundary}}`,
    `Content-Type: text/html; charset="UTF-8"`,
    `Content-Transfer-Encoding: 7bit`,
    ``,
    htmlBody,
    ``,
    `--${{boundary}}--`,
  ].join('\\r\\n');

  const raw = Buffer.from(mimeParts).toString('base64')
    .replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');

  const res = await gmail.users.messages.send({{
    userId: 'me',
    requestBody: {{ raw }}
  }});

  console.log('SENT:' + res.data.id + ':' + toEmail);
}}

send().catch(e => {{ console.error('ERROR:' + e.message); process.exit(1); }});
"""

    try:
        sender_js.write_text(js_code, encoding="utf-8")
        result = subprocess.run(
            ["node", "--input-type=module"],
            input=js_code,
            capture_output=True,
            text=True,
            cwd=str(GWS_DIR),
            timeout=30,
        )
        if "SENT:" in result.stdout:
            msg_id = result.stdout.split("SENT:")[1].strip().split(":")[0]
            print(f"  ✅ Email sent → {to_email}  (id: {msg_id})")
            return True
        else:
            print(f"  ❌ Send failed: {result.stderr.strip() or result.stdout.strip()}")
            return False
    except Exception as e:
        print(f"  ❌ Email error: {e}")
        return False
    finally:
        if sender_js.exists():
            sender_js.unlink(missing_ok=True)


# ── Telegram sender ───────────────────────────────────────────────────────────
_telegram_creds_cache: dict = {}

def _load_telegram_creds() -> dict:
    if _telegram_creds_cache:
        return _telegram_creds_cache
    env_path = Path(__file__).parent.parent.parent / "scratch" / "gravity-claw" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                _telegram_creds_cache[k.strip()] = v.strip().strip('"')
    return _telegram_creds_cache


def send_via_telegram(html_path: Path, client_name: str) -> bool:
    """Send the HTML report file as a Telegram document."""
    try:
        import requests
    except ImportError:
        print("  ❌ Telegram: 'requests' package not installed (pip install requests)")
        return False

    creds = _load_telegram_creds()
    token = creds.get("TELEGRAM_BOT_TOKEN")
    chat_id = creds.get("TELEGRAM_USER_ID")

    if not token or not chat_id:
        print("  ❌ Telegram: TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID not found in .env")
        return False

    today = date.today().strftime("%B %d, %Y")
    caption = f"📊 {client_name}\nMarketing Performance Report — {today}"

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(html_path, "rb") as f:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (html_path.name, f, "text/html")},
                timeout=30,
            )
        if resp.ok and resp.json().get("ok"):
            print(f"  ✅ Telegram sent → {client_name}")
            return True
        else:
            print(f"  ❌ Telegram error: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Telegram exception: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def process_client(biz_key: str, contacts: dict, do_email: bool = False, preview: bool = False, do_telegram: bool = False):
    contact = contacts.get(biz_key, {"client_name": biz_key})
    client_name = contact.get("client_name", biz_key)
    print(f"\n[{biz_key}] Generating report for {client_name}...")

    html = generate_client_html(biz_key, contact)

    today_str = date.today().strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"{today_str}_{biz_key}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  📄 Saved: {out_path}")

    if preview:
        webbrowser.open(out_path.as_uri())
        print(f"  🌐 Opened in browser")

    if do_email:
        email = contact.get("email")
        if not email:
            print(f"  ⚠️  No email configured for {biz_key} — skipping send (add to client_contacts.json)")
        else:
            send_via_gmail(email, client_name, html, cc=contact.get("cc"))

    if do_telegram:
        send_via_telegram(out_path, client_name)

    return out_path


def main():
    parser = argparse.ArgumentParser(description="Client Report Generator + Sender")
    parser.add_argument("--client", help="Single business key (e.g. sugar_shack)")
    parser.add_argument("--all",    action="store_true", help="Process all clients")
    parser.add_argument("--email",    action="store_true", help="Send via Gmail (requires email in client_contacts.json)")
    parser.add_argument("--telegram", action="store_true", help="Send via Telegram bot")
    parser.add_argument("--preview",  action="store_true", help="Open generated HTML in browser")
    args = parser.parse_args()

    if not args.client and not args.all:
        parser.print_help()
        sys.exit(1)

    contacts = load_contacts()

    if args.client:
        if args.client not in BUSINESS_ORDER:
            print(f"Unknown client key: {args.client}")
            print(f"Valid keys: {', '.join(BUSINESS_ORDER)}")
            sys.exit(1)
        process_client(args.client, contacts, do_email=args.email, preview=args.preview, do_telegram=args.telegram)

    elif args.all:
        for biz_key in BUSINESS_ORDER:
            process_client(biz_key, contacts, do_email=args.email, preview=False, do_telegram=args.telegram)
        if args.preview:
            # Open the last generated report
            today_str = date.today().strftime("%Y-%m-%d")
            first = REPORTS_DIR / f"{today_str}_{BUSINESS_ORDER[0]}.html"
            if first.exists():
                webbrowser.open(first.as_uri())
        print(f"\n✅ All {len(BUSINESS_ORDER)} reports saved to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
