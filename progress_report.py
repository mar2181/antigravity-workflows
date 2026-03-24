#!/usr/bin/env python3
"""
progress_report.py — Weekly keyword ranking progress report for all 8 clients.

Shows 7-day and 30-day position movements (Map Pack + Organic).
Generates an HTML report per client, sends via Telegram.

Usage:
  python progress_report.py                    # all clients
  python progress_report.py --client sugar_shack  # one client
  python progress_report.py --open             # open HTML in browser
  python progress_report.py --no-telegram      # skip Telegram
"""

import sys
import json
import argparse
import webbrowser
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import date, datetime, timedelta

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR   = Path(__file__).parent
RANKINGS_STATE  = EXECUTION_DIR / "keyword_rankings_state.json"
REPORTS_DIR     = EXECUTION_DIR / "progress_reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ─── Config ───────────────────────────────────────────────────────────────────

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

BUSINESS_COLORS = {
    "sugar_shack":       "#e91e63",
    "island_arcade":     "#7c3aed",
    "island_candy":      "#f59e0b",
    "juan":              "#0ea5e9",
    "spi_fun_rentals":   "#10b981",
    "custom_designs_tx": "#3b82f6",
    "optimum_clinic":    "#ef4444",
    "optimum_foundation":"#8b5cf6",
}


# ─── Data ─────────────────────────────────────────────────────────────────────

def load_rankings() -> dict:
    if not RANKINGS_STATE.exists():
        return {}
    try:
        return json.loads(RANKINGS_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_position_on_date(history: dict, target_date: date) -> dict | None:
    """Return the entry closest to target_date (on or before)."""
    dates = sorted(history.keys())
    best = None
    for d in dates:
        if d <= target_date.isoformat():
            best = d
    if best:
        entry = history[best]
        return entry if not entry.get("error") else None
    return None


def compute_movements(rankings: dict, days_back: int) -> dict:
    """
    For each client and keyword, compute: position today vs. N days ago.
    Returns { biz_key: [ {keyword, mp_prev, mp_curr, mp_delta, org_prev, org_curr, org_delta} ] }
    """
    today      = date.today()
    past_date  = today - timedelta(days=days_back)
    results    = {}

    for biz_key, keywords in rankings.items():
        rows = []
        for kw_text, date_history in keywords.items():
            curr = get_position_on_date(date_history, today)
            prev = get_position_on_date(date_history, past_date)
            if not curr:
                continue

            def delta(p, c):
                if p is None or c is None:
                    return None
                return p - c  # positive = improved (lower rank # is better)

            mp_curr = curr.get("map_pack_position")
            mp_prev = prev.get("map_pack_position") if prev else None
            org_curr = curr.get("organic_position")
            org_prev = prev.get("organic_position") if prev else None

            rows.append({
                "keyword":   kw_text,
                "mp_curr":   mp_curr,
                "mp_prev":   mp_prev,
                "mp_delta":  delta(mp_prev, mp_curr),
                "org_curr":  org_curr,
                "org_prev":  org_prev,
                "org_delta": delta(org_prev, org_curr),
            })

        # Sort: biggest movers first
        rows.sort(key=lambda r: abs(r["mp_delta"] or 0), reverse=True)
        results[biz_key] = rows

    return results


# ─── HTML rendering ───────────────────────────────────────────────────────────

def arrow(delta):
    if delta is None:
        return '<span style="color:#94a3b8">—</span>'
    if delta > 0:
        return f'<span style="color:#22c55e">▲{delta}</span>'
    if delta < 0:
        return f'<span style="color:#ef4444">▼{abs(delta)}</span>'
    return '<span style="color:#94a3b8">→</span>'


def position_cell(pos, delta):
    if pos is None:
        return '<td style="color:#94a3b8;text-align:center">—</td>'
    arrow_html = arrow(delta)
    return f'<td style="text-align:center;color:#f0f6ff">#{pos} {arrow_html}</td>'


def render_client_section(biz_key: str, rows_7d: list, rows_30d: list, color: str) -> str:
    name = BUSINESS_NAMES.get(biz_key, biz_key)

    if not rows_7d and not rows_30d:
        return f"""
        <div style="background:#1e293b;border-radius:12px;padding:20px;margin-bottom:24px;border-left:4px solid {color}">
          <h2 style="color:{color};margin:0 0 8px">{name}</h2>
          <p style="color:#94a3b8;font-size:14px">No ranking data available yet.</p>
        </div>"""

    # Merge keywords by name, use 7d data but augment with 30d delta
    kw_map_7d  = {r["keyword"]: r for r in rows_7d}
    kw_map_30d = {r["keyword"]: r for r in rows_30d}
    all_kws    = sorted(set(list(kw_map_7d.keys()) + list(kw_map_30d.keys())))

    rows_html = ""
    for kw in all_kws:
        r7  = kw_map_7d.get(kw, {})
        r30 = kw_map_30d.get(kw, {})
        mp_curr   = r7.get("mp_curr") or r30.get("mp_curr")
        mp_7d_d   = r7.get("mp_delta")
        mp_30d_d  = r30.get("mp_delta")
        org_curr  = r7.get("org_curr") or r30.get("org_curr")
        org_7d_d  = r7.get("org_delta")
        org_30d_d = r30.get("org_delta")

        rows_html += f"""
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05)">
          <td style="padding:8px 12px;color:#f0f6ff;font-size:14px">{kw}</td>
          {position_cell(mp_curr, mp_7d_d)}
          <td style="text-align:center">{arrow(mp_7d_d)}</td>
          <td style="text-align:center">{arrow(mp_30d_d)}</td>
          {position_cell(org_curr, org_7d_d)}
          <td style="text-align:center">{arrow(org_7d_d)}</td>
          <td style="text-align:center">{arrow(org_30d_d)}</td>
        </tr>"""

    # Summary counts
    improved_7d = sum(1 for r in rows_7d if (r.get("mp_delta") or 0) > 0)
    declined_7d = sum(1 for r in rows_7d if (r.get("mp_delta") or 0) < 0)

    return f"""
    <div style="background:#1e293b;border-radius:12px;padding:20px;margin-bottom:24px;border-left:4px solid {color}">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <h2 style="color:{color};margin:0">{name}</h2>
        <div style="font-size:13px;color:#94a3b8">
          <span style="color:#22c55e">▲{improved_7d} up</span>
          &nbsp;·&nbsp;
          <span style="color:#ef4444">▼{declined_7d} down</span>
          &nbsp;(7-day)
        </div>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead>
          <tr style="border-bottom:2px solid rgba(255,255,255,0.1)">
            <th style="text-align:left;padding:6px 12px;color:#94a3b8;font-weight:500">Keyword</th>
            <th style="text-align:center;padding:6px;color:#94a3b8;font-weight:500" colspan="3">Map Pack</th>
            <th style="text-align:center;padding:6px;color:#94a3b8;font-weight:500" colspan="3">Organic</th>
          </tr>
          <tr style="border-bottom:1px solid rgba(255,255,255,0.05)">
            <th></th>
            <th style="text-align:center;padding:4px;color:#64748b;font-size:11px">Current</th>
            <th style="text-align:center;padding:4px;color:#64748b;font-size:11px">7-day</th>
            <th style="text-align:center;padding:4px;color:#64748b;font-size:11px">30-day</th>
            <th style="text-align:center;padding:4px;color:#64748b;font-size:11px">Current</th>
            <th style="text-align:center;padding:4px;color:#64748b;font-size:11px">7-day</th>
            <th style="text-align:center;padding:4px;color:#64748b;font-size:11px">30-day</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>"""


def generate_html(movements_7d: dict, movements_30d: dict, date_str: str) -> str:
    week_end   = datetime.strptime(date_str, "%Y-%m-%d")
    week_start = week_end - timedelta(days=6)
    period_str = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"

    client_sections = ""
    for biz_key in BUSINESS_NAMES:
        rows_7d  = movements_7d.get(biz_key, [])
        rows_30d = movements_30d.get(biz_key, [])
        if not rows_7d and not rows_30d:
            continue
        color = BUSINESS_COLORS.get(biz_key, "#6b7280")
        client_sections += render_client_section(biz_key, rows_7d, rows_30d, color)

    if not client_sections:
        client_sections = '<p style="color:#94a3b8;text-align:center;padding:40px">No ranking data found. Run the nightly pipeline to collect data.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Weekly Progress Report — {period_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #f0f6ff; padding: 32px; }}
  .header {{ max-width: 900px; margin: 0 auto 32px; }}
  .header h1 {{ font-size: 28px; font-weight: 700; color: #f0f6ff; }}
  .header p {{ color: #94a3b8; margin-top: 6px; font-size: 15px; }}
  .legend {{ max-width: 900px; margin: 0 auto 24px; display: flex; gap: 20px; font-size: 13px; color: #94a3b8; }}
  .content {{ max-width: 900px; margin: 0 auto; }}
</style>
</head>
<body>

<div class="header">
  <h1>Weekly Progress Report</h1>
  <p>{period_str} &nbsp;·&nbsp; Generated {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
</div>

<div class="legend">
  <span><span style="color:#22c55e">▲N</span> = improved N positions</span>
  <span><span style="color:#ef4444">▼N</span> = dropped N positions</span>
  <span><span style="color:#94a3b8">→</span> = no change</span>
  <span><span style="color:#94a3b8">—</span> = no data</span>
</div>

<div class="content">
  {client_sections}
</div>

</body>
</html>"""


# ─── Telegram ─────────────────────────────────────────────────────────────────

def notify_mario(text: str) -> bool:
    try:
        env = {}
        env_path = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
        token   = env.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = env.get("TELEGRAM_USER_ID", "")
        if not token or not chat_id:
            return False
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
        resp = urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data),
            timeout=10
        )
        return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"  [Telegram] {e}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Weekly ranking progress report")
    parser.add_argument("--client", default=None, help="One client key (e.g. sugar_shack)")
    parser.add_argument("--open", action="store_true", help="Open HTML in browser after generating")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    args = parser.parse_args()

    today_str = date.today().isoformat()
    print(f"\nWeekly Progress Report — {today_str}")

    rankings = load_rankings()
    if not rankings:
        print("  ERROR: keyword_rankings_state.json not found or empty.")
        return 1

    # Filter to one client if requested
    if args.client:
        if args.client not in rankings:
            print(f"  ERROR: Client '{args.client}' not found in rankings state.")
            print(f"  Available: {', '.join(rankings.keys())}")
            return 1
        rankings = {args.client: rankings[args.client]}

    print(f"  Clients: {', '.join(rankings.keys())}")

    movements_7d  = compute_movements(rankings, days_back=7)
    movements_30d = compute_movements(rankings, days_back=30)

    # Count movers
    total_7d  = sum(len(v) for v in movements_7d.values())
    total_30d = sum(len(v) for v in movements_30d.values())
    print(f"  Keywords with 7-day data:  {total_7d}")
    print(f"  Keywords with 30-day data: {total_30d}")

    # Generate HTML
    html     = generate_html(movements_7d, movements_30d, today_str)
    out_path = REPORTS_DIR / f"progress_{today_str}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\n  Report saved: {out_path}")

    if args.open:
        webbrowser.open(out_path.as_uri())
        print("  Opened in browser.")

    # Telegram summary
    if not args.no_telegram:
        improved = sum(
            sum(1 for r in rows if (r.get("mp_delta") or 0) > 0)
            for rows in movements_7d.values()
        )
        declined = sum(
            sum(1 for r in rows if (r.get("mp_delta") or 0) < 0)
            for rows in movements_7d.values()
        )
        msg = (
            f"[WEEKLY REPORT] {today_str}\n\n"
            f"7-day movements:\n"
            f"  ▲ {improved} keywords improved\n"
            f"  ▼ {declined} keywords declined\n\n"
            f"Clients: {', '.join(rankings.keys())}\n"
            f"Full report: {out_path}"
        )
        if notify_mario(msg):
            print("  Telegram: sent.")
        else:
            print("  Telegram: skipped (no credentials or not connected).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
