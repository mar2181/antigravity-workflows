#!/usr/bin/env python3
"""
meeting_prep.py — Generate a client meeting brief and send to Telegram.

Aggregates:
  1. Recent posting activity (last 7 days from program.md posting log)
  2. Engagement data (from engagement history CSVs)
  3. Screenpipe screen mentions (last 7 days — how much attention this client got)
  4. Current priorities + pending items from program.md
  5. Upcoming calendar events mentioning the client (if GWS available)

Usage:
  python meeting_prep.py sugar_shack              # send brief to Telegram
  python meeting_prep.py optimum_clinic --dry-run # print to console only
  python meeting_prep.py juan --days 14           # look back 14 days instead of 7
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import date, datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXECUTION_DIR = Path(__file__).parent
TODAY = date.today()

BUSINESS_NAMES = {
    "sugar_shack":       "Sugar Shack",
    "island_arcade":     "Island Arcade",
    "island_candy":      "Island Candy",
    "juan":              "Juan Elizondo",
    "spi_fun_rentals":   "SPI Fun Rentals",
    "custom_designs_tx": "Custom Designs TX",
    "optimum_clinic":    "Optimum Clinic",
    "optimum_foundation":"Optimum Foundation",
}


def notify_mario(text):
    """Send message via Telegram."""
    import urllib.parse, urllib.request
    env = {}
    env_path = Path("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env")
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    token, chat_id = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_USER_ID", "")
    if not token or not chat_id:
        return False
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
    resp = urllib.request.urlopen(
        urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data),
        timeout=10
    )
    return json.loads(resp.read()).get("ok", False)


def _recent_posts(biz_key: str, days: int = 7) -> list:
    """Extract posting log entries from the last N days."""
    program = EXECUTION_DIR / biz_key / "program.md"
    if not program.exists():
        return []

    cutoff = (TODAY - timedelta(days=days)).strftime("%Y-%m-%d")
    text = program.read_text(encoding="utf-8", errors="replace")
    posts = []
    in_log = False
    for line in text.splitlines():
        if "## Posting Log" in line or "## posting log" in line.lower():
            in_log = True
            continue
        if in_log and line.startswith("##"):
            break
        if in_log and "|" in line and line.strip().startswith("|"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            # Skip header/separator rows — first col must be a date YYYY-MM-DD
            if len(parts) >= 2 and len(parts[0]) >= 10 and parts[0][:4].isdigit() and parts[0] >= cutoff:
                posts.append({"date": parts[0], "angle": parts[1],
                              "status": parts[2] if len(parts) > 2 else ""})
    return posts


def _current_priorities(biz_key: str) -> list:
    """Extract current priorities from program.md."""
    program = EXECUTION_DIR / biz_key / "program.md"
    if not program.exists():
        return []

    text = program.read_text(encoding="utf-8", errors="replace")
    priorities = []
    in_section = False
    for line in text.splitlines():
        if "## Current Priorities" in line or "## current priorities" in line.lower():
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if in_section and line.strip().startswith(("-", "*", "1", "2", "3", "4", "5")):
            priorities.append(line.strip().lstrip("-*0123456789. "))
    return priorities[:10]


def _engagement_summary(biz_key: str, days: int = 7) -> dict:
    """Get recent engagement stats from CSV history."""
    csv_path = EXECUTION_DIR / biz_key / "engagement_history.csv"
    if not csv_path.exists():
        return {}

    cutoff = (TODAY - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        lines = csv_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) < 2:
            return {}
        headers = [h.strip() for h in lines[0].split(",")]
        total_likes = 0
        total_comments = 0
        total_shares = 0
        total_reach = 0
        count = 0
        for row in lines[1:]:
            cols = [c.strip() for c in row.split(",")]
            if len(cols) < 2:
                continue
            row_date = cols[0]
            if row_date < cutoff:
                continue
            count += 1
            # Try to sum numeric columns (likes, comments, shares, reach)
            for i, h in enumerate(headers):
                if i >= len(cols):
                    break
                try:
                    val = int(cols[i])
                except (ValueError, IndexError):
                    continue
                hl = h.lower()
                if "like" in hl:
                    total_likes += val
                elif "comment" in hl:
                    total_comments += val
                elif "share" in hl:
                    total_shares += val
                elif "reach" in hl:
                    total_reach += val
        if count == 0:
            return {}
        return {
            "posts_tracked": count,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_reach": total_reach,
        }
    except Exception:
        return {}


def _screenpipe_mentions(biz_key: str, days: int = 7) -> int:
    """Count Screenpipe OCR mentions of this client in the last N days."""
    try:
        sys.path.insert(0, str(EXECUTION_DIR))
        from screenpipe_verifier import screenpipe_healthy, screenpipe_search
    except ImportError:
        return -1
    if not screenpipe_healthy():
        return -1

    from datetime import timezone as _tz
    now_utc = datetime.now(_tz.utc)
    start = (now_utc - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

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
    term = search_terms.get(biz_key, BUSINESS_NAMES.get(biz_key, biz_key))
    try:
        results = screenpipe_search(term, content_type="ocr", limit=100,
                                    start_time=start_str, end_time=end_str)
        return len(results)
    except Exception:
        return -1


def _calendar_events(biz_key: str) -> list:
    """Check Google Calendar for upcoming events mentioning this client."""
    script = Path("C:/Users/mario/gws-workspace/demos/calendar_brief.js")
    if not script.exists():
        return []
    try:
        result = subprocess.run(
            ["node", str(script)],
            capture_output=True, text=True, timeout=15,
            cwd=str(script.parent),
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout.strip())
        if data.get("error"):
            return []
        name = BUSINESS_NAMES.get(biz_key, biz_key)
        matching = []
        for ev in data.get("events", []):
            text = f"{ev.get('summary', '')} {ev.get('description', '')}".lower()
            if name.lower() in text or biz_key.replace("_", " ") in text:
                matching.append(ev)
        return matching
    except Exception:
        return []


def build_meeting_brief(biz_key: str, days: int = 7) -> str:
    """Build the meeting prep message for a client."""
    name = BUSINESS_NAMES.get(biz_key, biz_key)
    lines = [f"MEETING PREP: {name}"]
    lines.append(f"Generated: {TODAY.strftime('%B %d, %Y')}")
    lines.append("=" * 40)

    # Recent posts
    posts = _recent_posts(biz_key, days)
    lines.append("")
    lines.append(f"POSTING ACTIVITY (last {days} days): {len(posts)} post(s)")
    if posts:
        for p in posts[-10:]:  # last 10
            status = f" [{p['status']}]" if p["status"] else ""
            lines.append(f"  {p['date']}: {p['angle']}{status}")
    else:
        lines.append("  (no posts logged)")

    # Engagement
    eng = _engagement_summary(biz_key, days)
    if eng:
        lines.append("")
        lines.append(f"ENGAGEMENT ({eng['posts_tracked']} posts tracked):")
        lines.append(f"  Likes: {eng['total_likes']}  Comments: {eng['total_comments']}  Shares: {eng['total_shares']}")
        if eng["total_reach"] > 0:
            lines.append(f"  Total reach: {eng['total_reach']:,}")

    # Screenpipe attention
    mentions = _screenpipe_mentions(biz_key, days)
    if mentions >= 0:
        lines.append("")
        lines.append(f"SCREEN ATTENTION (last {days} days): {mentions} OCR mentions")
        if mentions == 0:
            lines.append("  This client got ZERO screen time — may need more focus")
        elif mentions >= 100:
            lines.append("  High attention (100+ mentions)")

    # Current priorities
    priorities = _current_priorities(biz_key)
    if priorities:
        lines.append("")
        lines.append("CURRENT PRIORITIES:")
        for p in priorities:
            lines.append(f"  - {p}")

    # Calendar
    cal_events = _calendar_events(biz_key)
    if cal_events:
        lines.append("")
        lines.append("UPCOMING CALENDAR:")
        for ev in cal_events[:5]:
            start = ev.get("start", "")
            summary = ev.get("summary", "")
            lines.append(f"  {start}: {summary}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Client meeting prep brief")
    parser.add_argument("client", help="Business key (e.g. sugar_shack, optimum_clinic)")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    args = parser.parse_args()

    biz_key = args.client
    if biz_key not in BUSINESS_NAMES:
        # Try fuzzy match
        for k in BUSINESS_NAMES:
            if biz_key.lower() in k.lower() or biz_key.lower() in BUSINESS_NAMES[k].lower():
                biz_key = k
                break
        else:
            print(f"[ERROR] Unknown client: {args.client}")
            print(f"  Available: {', '.join(BUSINESS_NAMES.keys())}")
            sys.exit(1)

    print(f"[meeting_prep] Generating brief for {BUSINESS_NAMES[biz_key]}...")
    msg = build_meeting_brief(biz_key, args.days)

    if args.dry_run:
        print(msg)
        return

    print("[meeting_prep] Sending to Telegram...")
    ok = notify_mario(msg)
    if ok:
        print("[meeting_prep] Sent successfully")
    else:
        print("[meeting_prep] Failed to send — printing instead:")
        print(msg)


if __name__ == "__main__":
    main()
