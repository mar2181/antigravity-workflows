#!/usr/bin/env python3
"""
daily_wrap.py — End-of-day summary sent to Telegram at 6 PM.

Collects:
  1. Facebook posts made today (from posting logs in program.md files)
  2. GBP posts made today (from blog_posts/*/_meta.json timestamps)
  3. Screenpipe client attention distribution (if available)
  4. Gmail inbox status (unread count + urgent emails)

Schedule (Windows Task Scheduler):
  schtasks /create /tn "Antigravity Daily Wrap" /tr "python C:\\Users\\mario\\.gemini\\antigravity\\tools\\execution\\daily_wrap.py" /sc daily /st 18:00 /f

Usage:
  python daily_wrap.py           # send wrap to Telegram
  python daily_wrap.py --dry-run # print to console only
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
TODAY_STR = TODAY.strftime("%Y-%m-%d")

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


def _posts_today_from_logs() -> dict:
    """Parse each business's program.md posting log for entries dated today.
    Returns {biz_key: [angle1, angle2, ...]}."""
    results = {}
    for biz_key in BUSINESS_NAMES:
        biz_dir = EXECUTION_DIR / biz_key
        program = biz_dir / "program.md"
        if not program.exists():
            continue

        text = program.read_text(encoding="utf-8", errors="replace")
        # Find the posting log table and extract rows matching today's date
        posts_today = []
        in_log = False
        for line in text.splitlines():
            if "## Posting Log" in line or "## posting log" in line.lower():
                in_log = True
                continue
            if in_log and line.startswith("##"):
                break
            if in_log and TODAY_STR in line:
                # Extract angle from table row: | 2026-03-23 | angle text | ... |
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    posts_today.append(parts[1])  # angle/description column
        if posts_today:
            results[biz_key] = posts_today
    return results


def _gbp_posts_today() -> list:
    """Check blog_posts/*/meta files for GBP posts created today."""
    blog_dir = EXECUTION_DIR / "blog_posts"
    if not blog_dir.exists():
        return []
    gbp_posts = []
    for meta_file in blog_dir.rglob("*_meta.json"):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            created = meta.get("created", "")
            if TODAY_STR in created:
                biz = meta.get("client", meta_file.parent.name)
                title = meta.get("title", meta_file.stem)
                gbp_posts.append(f"{biz}: {title}")
        except Exception:
            pass
    return gbp_posts


def _screenpipe_attention() -> dict:
    """Get client attention distribution from Screenpipe OCR."""
    try:
        sys.path.insert(0, str(EXECUTION_DIR))
        from screenpipe_verifier import screenpipe_healthy, screenpipe_search
    except ImportError:
        return {}
    if not screenpipe_healthy():
        return {}

    from datetime import timezone as _tz
    now_utc = datetime.now(_tz.utc)
    start = now_utc.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

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


def _screenpipe_posting_detection() -> dict:
    """Cross-check: query Screenpipe OCR for Facebook posting activity today.
    Looks for success indicators ('just now', 'Published') near each client's
    page name. Returns {biz_key: bool} — True if posting activity detected."""
    try:
        sys.path.insert(0, str(EXECUTION_DIR))
        from screenpipe_verifier import screenpipe_healthy, screenpipe_search
    except ImportError:
        return {}
    if not screenpipe_healthy():
        return {}

    from datetime import timezone as _tz
    now_utc = datetime.now(_tz.utc)
    start = now_utc.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Page names as they appear on Facebook (OCR targets)
    page_names = {
        "sugar_shack": "Sugar Shack",
        "island_arcade": "Island Arcade",
        "island_candy": "Island Candy",
        "juan": "Juan Elizondo",
        "spi_fun_rentals": "SPI Fun Rentals",
        "custom_designs_tx": "Custom Designs",
        "optimum_clinic": "Optimum",
        "optimum_foundation": "Optimum Foundation",
    }

    detected = {}
    for biz_key, name in page_names.items():
        try:
            # Search for page name near posting indicators
            results = screenpipe_search(name, content_type="ocr", limit=20,
                                        start_time=start, end_time=end)
            # Check if any result contains posting indicators
            # Only match actual Facebook UI text, not code references
            posting_indicators = ["just now", "Just now", "shared a post", "Your post is now published"]
            found = False
            for r in results:
                text = r.get("content", {}).get("text", "")
                if any(ind in text for ind in posting_indicators):
                    found = True
                    break
            detected[biz_key] = found
        except Exception:
            detected[biz_key] = False
    return detected


def _git_activity_today() -> list:
    """Get today's git commits across key repositories."""
    repos = [
        ("Antigravity", "C:/Users/mario/.gemini/antigravity"),
        ("Mission Control", "C:/Users/mario/missioncontrol/dashboard"),
        ("Home", "C:/Users/mario"),
    ]
    commits = []
    for repo_name, repo_path in repos:
        if not Path(repo_path).joinpath(".git").exists():
            continue
        try:
            result = subprocess.run(
                ["git", "log", f"--since={TODAY_STR}", "--oneline", "--no-merges", "-10"],
                capture_output=True, text=True, timeout=10,
                cwd=repo_path,
                encoding="utf-8", errors="replace",
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    commits.append(f"  [{repo_name}] {line.strip()}")
        except Exception:
            pass
    return commits


def _gmail_status() -> str:
    """Quick Gmail inbox status."""
    script = Path("C:/Users/mario/gws-workspace/demos/gmail_brief.js")
    if not script.exists():
        return ""
    try:
        result = subprocess.run(
            ["node", str(script)],
            capture_output=True, text=True, timeout=15,
            cwd=str(script.parent),
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return ""
        data = json.loads(result.stdout.strip())
        unread = data.get("unread_count", 0)
        urgent = len(data.get("urgent", []))
        if urgent > 0:
            return f"\n\nInbox: {unread} unread, {urgent} need response"
        elif unread > 0:
            return f"\n\nInbox: {unread} unread (none urgent)"
        return "\n\nInbox: clear"
    except Exception:
        return ""


def build_wrap() -> str:
    """Build the daily wrap-up message."""
    weekday = TODAY.strftime("%A")
    lines = [f"Daily Wrap -- {weekday}, {TODAY.strftime('%B %d, %Y')}"]
    lines.append("=" * 40)

    # Facebook posts
    fb_posts = _posts_today_from_logs()
    total_fb = sum(len(v) for v in fb_posts.values())

    lines.append("")
    lines.append(f"FACEBOOK: {total_fb} post(s)")
    if fb_posts:
        for biz_key, angles in fb_posts.items():
            name = BUSINESS_NAMES.get(biz_key, biz_key)
            for angle in angles:
                lines.append(f"  [OK] {name}: {angle}")
    else:
        lines.append("  (none today)")

    # Clients with no posts
    posted_keys = set(fb_posts.keys())
    no_post = [BUSINESS_NAMES[k] for k in BUSINESS_NAMES if k not in posted_keys]
    if no_post:
        lines.append(f"  No posts: {', '.join(no_post)}")

    # GBP posts
    gbp = _gbp_posts_today()
    lines.append("")
    lines.append(f"GBP/BLOG: {len(gbp)} post(s)")
    if gbp:
        for item in gbp:
            lines.append(f"  [OK] {item}")
    else:
        lines.append("  (none today)")

    # Screenpipe posting cross-check (UC-12)
    sp_detected = _screenpipe_posting_detection()
    if sp_detected:
        # Find clients where Screenpipe saw posting activity but program.md has no log
        unlogged = [BUSINESS_NAMES[k] for k, v in sp_detected.items()
                    if v and k not in posted_keys]
        if unlogged:
            lines.append("")
            lines.append("UNLOGGED POSTS (Screenpipe detected but not in program.md):")
            for name in unlogged:
                lines.append(f"  [?] {name} — posting activity detected on screen")

    # Screenpipe attention
    attention = _screenpipe_attention()
    if attention:
        total = sum(attention.values())
        if total > 0:
            lines.append("")
            lines.append("SCREEN TIME:")
            sorted_a = sorted(attention.items(), key=lambda x: x[1], reverse=True)
            for biz_key, count in sorted_a:
                if count > 0:
                    name = BUSINESS_NAMES.get(biz_key, biz_key)
                    pct = count / total * 100
                    lines.append(f"  {name}: {count} mentions ({pct:.0f}%)")
            zero = [BUSINESS_NAMES[k] for k, v in attention.items() if v == 0]
            if zero:
                lines.append(f"  Zero attention: {', '.join(zero)}")

    # Git activity (CW-7)
    git_commits = _git_activity_today()
    if git_commits:
        lines.append("")
        lines.append(f"GIT: {len(git_commits)} commit(s) today")
        lines.extend(git_commits)

    # Gmail
    gmail = _gmail_status()
    if gmail:
        lines.append(gmail)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="End-of-day summary to Telegram")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    args = parser.parse_args()

    msg = build_wrap()

    if args.dry_run:
        print(msg)
        return

    print("[daily_wrap] Sending to Telegram...")
    ok = notify_mario(msg)
    if ok:
        print("[daily_wrap] Sent successfully")
    else:
        print("[daily_wrap] Failed to send — check Telegram credentials")
        print(msg)


if __name__ == "__main__":
    main()
