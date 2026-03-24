#!/usr/bin/env python3
"""
time_tracker.py — Maps Screenpipe window titles to clients for time tracking.

Queries Screenpipe OCR data for client-related window titles and app usage,
then estimates how much screen time was spent on each client.

Schedule (Windows Task Scheduler — Friday 5 PM):
  schtasks /create /tn "Antigravity Time Tracker" /tr "python C:\\Users\\mario\\.gemini\\antigravity\\tools\\execution\\time_tracker.py" /sc weekly /d FRI /st 17:00 /f

Usage:
  python time_tracker.py                  # this week's report → Telegram
  python time_tracker.py --dry-run        # print only
  python time_tracker.py --days 1         # today only
  python time_tracker.py --days 30        # last month
  python time_tracker.py --detailed       # show per-app breakdown
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXECUTION_DIR = Path(__file__).parent

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

# Keywords that map OCR/window-title text to clients.
# More specific patterns first to avoid false matches.
CLIENT_PATTERNS = {
    "sugar_shack": [
        "sugar shack", "sugarshack", "sugar_shack",
        "61557735298128",  # FB profile ID
    ],
    "island_arcade": [
        "island arcade", "islandarcade", "island_arcade",
        "100090911360621",
    ],
    "island_candy": [
        "island candy", "islandcandy", "island_candy",
        "100090560413893",
    ],
    "juan": [
        "juan elizondo", "juanelizondo", "remax elite", "re/max elite",
        "JuanElizondoRemax",
    ],
    "spi_fun_rentals": [
        "spi fun rentals", "spifunrentals", "spi_fun_rentals",
        "fun rentals",
    ],
    "custom_designs_tx": [
        "custom designs", "customdesigns", "custom_designs",
        "security camera", "alarm system",
    ],
    "optimum_clinic": [
        "optimum clinic", "optimum health", "optimum_clinic",
        "cash night clinic", "optimumcare",
    ],
    "optimum_foundation": [
        "optimum foundation", "optimum_foundation",
        "wound care foundation",
    ],
}

# Non-client categories for general activity tracking
GENERAL_CATEGORIES = {
    "mission_control": ["mission control", "missioncontrol", "localhost:3001"],
    "antigravity_dev": ["antigravity", ".gemini/antigravity", "facebook_marketer"],
    "competitor_intel": ["competitor", "ad library", "adlibrary"],
    "email": ["gmail", "inbox", "email"],
    "coding": ["vscode", "visual studio code", "github", "terminal"],
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


def _match_client(text: str) -> str:
    """Match OCR text to a client. Returns biz_key or empty string."""
    text_lower = text.lower()
    for biz_key, patterns in CLIENT_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in text_lower:
                return biz_key
    return ""


def _match_category(text: str) -> str:
    """Match OCR text to a general category."""
    text_lower = text.lower()
    for cat, patterns in GENERAL_CATEGORIES.items():
        for pattern in patterns:
            if pattern.lower() in text_lower:
                return cat
    return ""


def get_time_data(days: int = 7) -> dict:
    """Query Screenpipe OCR for client-related screen time over N days.

    Returns:
        {
            "client_mentions": {biz_key: count, ...},
            "category_mentions": {cat: count, ...},
            "app_breakdown": {biz_key: {app_name: count, ...}, ...},
            "total_captures": int,
            "period_start": str,
            "period_end": str,
        }
    """
    try:
        sys.path.insert(0, str(EXECUTION_DIR))
        from screenpipe_verifier import screenpipe_healthy, screenpipe_search
    except ImportError:
        return {"error": "screenpipe_verifier.py not found"}

    if not screenpipe_healthy():
        return {"error": "Screenpipe not running"}

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    client_mentions = defaultdict(int)
    category_mentions = defaultdict(int)
    app_breakdown = defaultdict(lambda: defaultdict(int))
    total_captures = 0

    # Apps to exclude from client time tracking (code editors show all client names)
    CODE_APPS = {"Antigravity.exe", "Code.exe", "WindowsTerminal.exe", "cmd.exe",
                 "powershell.exe", "bash.exe", "mintty.exe"}

    # Search for each client by name
    for biz_key, name in BUSINESS_NAMES.items():
        results = screenpipe_search(name, content_type="ocr", limit=500,
                                     start_time=start_str, end_time=end_str)
        # Filter out code editor noise — only count browser/real-app usage
        filtered = [r for r in results
                    if r.get("content", {}).get("app_name", "") not in CODE_APPS]
        count = len(filtered)
        if count > 0:
            client_mentions[biz_key] = count
            total_captures += count
            for r in filtered:
                app = r.get("content", {}).get("app_name", "unknown")
                app_breakdown[biz_key][app] += 1

    # Search for general categories (include all apps for these)
    cat_search_terms = {
        "mission_control": "Mission Control",
        "antigravity_dev": "antigravity",
        "competitor_intel": "competitor",
        "email": "gmail",
        "coding": "vscode",
    }
    for cat, term in cat_search_terms.items():
        results = screenpipe_search(term, content_type="ocr", limit=500,
                                     start_time=start_str, end_time=end_str)
        if results:
            category_mentions[cat] = len(results)

    return {
        "client_mentions": dict(client_mentions),
        "category_mentions": dict(category_mentions),
        "app_breakdown": {k: dict(v) for k, v in app_breakdown.items()},
        "total_captures": total_captures,
        "period_start": start_str,
        "period_end": end_str,
    }


def build_report(days: int = 7, detailed: bool = False) -> str:
    """Build the time tracking report."""
    data = get_time_data(days)

    if data.get("error"):
        return f"[time_tracker] Error: {data['error']}"

    now = datetime.now()
    start_date = (now - timedelta(days=days)).strftime("%B %d")
    end_date = now.strftime("%B %d, %Y")

    lines = [f"TIME TRACKING: {start_date} - {end_date}"]
    lines.append("=" * 40)

    client_mentions = data["client_mentions"]
    total = data["total_captures"]

    if not client_mentions:
        lines.append("")
        lines.append("No client-related screen activity detected.")
        lines.append("(Screenpipe may not have been running, or no client work was done)")
        return "\n".join(lines)

    # Sort by mentions descending
    sorted_clients = sorted(client_mentions.items(), key=lambda x: x[1], reverse=True)

    lines.append("")
    lines.append("CLIENT SCREEN TIME (by OCR mentions):")
    lines.append(f"  {'Client':<25} {'Mentions':>8}  {'Share':>6}")
    lines.append(f"  {'-'*25} {'-'*8}  {'-'*6}")

    for biz_key, count in sorted_clients:
        name = BUSINESS_NAMES.get(biz_key, biz_key)
        pct = (count / total * 100) if total > 0 else 0
        bar = "#" * int(pct / 5)  # Simple bar chart
        lines.append(f"  {name:<25} {count:>8}  {pct:>5.1f}%  {bar}")

    # Clients with zero mentions
    zero_clients = [BUSINESS_NAMES[k] for k in BUSINESS_NAMES if k not in client_mentions]
    if zero_clients:
        lines.append("")
        lines.append(f"  ZERO attention: {', '.join(zero_clients)}")

    # General categories
    cat_mentions = data.get("category_mentions", {})
    if cat_mentions:
        lines.append("")
        lines.append("ACTIVITY CATEGORIES:")
        cat_names = {
            "mission_control": "Mission Control",
            "antigravity_dev": "Antigravity Dev",
            "competitor_intel": "Competitor Intel",
            "email": "Email/Gmail",
            "coding": "Coding/IDE",
        }
        for cat, count in sorted(cat_mentions.items(), key=lambda x: x[1], reverse=True):
            name = cat_names.get(cat, cat)
            lines.append(f"  {name:<25} {count:>8} mentions")

    # Per-app breakdown (detailed mode)
    if detailed:
        app_breakdown = data.get("app_breakdown", {})
        if app_breakdown:
            lines.append("")
            lines.append("APP BREAKDOWN PER CLIENT:")
            for biz_key, apps in sorted(app_breakdown.items(), key=lambda x: sum(x[1].values()), reverse=True):
                name = BUSINESS_NAMES.get(biz_key, biz_key)
                lines.append(f"  {name}:")
                for app, count in sorted(apps.items(), key=lambda x: x[1], reverse=True):
                    lines.append(f"    {app}: {count} mentions")

    lines.append("")
    lines.append(f"Total: {total} client-related screen captures over {days} day(s)")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Client time tracking via Screenpipe")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    parser.add_argument("--days", type=int, default=7, help="Lookback window (default: 7)")
    parser.add_argument("--detailed", action="store_true", help="Show per-app breakdown")
    args = parser.parse_args()

    msg = build_report(args.days, args.detailed)

    if args.dry_run:
        print(msg)
        return

    print("[time_tracker] Sending report to Telegram...")
    ok = notify_mario(msg)
    if ok:
        print("[time_tracker] Sent successfully")
    else:
        print("[time_tracker] Failed to send — printing instead:")
        print(msg)


if __name__ == "__main__":
    main()
