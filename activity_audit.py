#!/usr/bin/env python3
"""
activity_audit.py — Weekly cross-channel activity audit trail per client.

Aggregates all marketing activity across channels for each client:
  1. Facebook posts (from program.md posting logs)
  2. GBP/blog posts (from blog_posts/ metadata)
  3. Screenpipe screen mentions (OCR frequency)
  4. Git commits touching client files
  5. Engagement data logged (from engagement_history.json)

Generates a per-client activity summary and sends to Telegram.

Schedule (Windows Task Scheduler — Sunday 7 PM):
  schtasks /create /tn "Antigravity Activity Audit" /tr "python C:\\Users\\mario\\.gemini\\antigravity\\tools\\execution\\activity_audit.py" /sc weekly /d SUN /st 19:00 /f

Usage:
  python activity_audit.py                  # full weekly audit → Telegram
  python activity_audit.py --dry-run        # print only
  python activity_audit.py --days 30        # monthly audit
  python activity_audit.py --client sugar_shack  # single client only
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict

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


def _fb_posts(biz_key: str, days: int) -> list:
    """Get Facebook posts from program.md posting log."""
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
            if len(parts) >= 2 and len(parts[0]) >= 10 and parts[0][:4].isdigit():
                if parts[0] >= cutoff:
                    posts.append({"date": parts[0], "angle": parts[1]})
    return posts


def _gbp_posts(biz_key: str, days: int) -> list:
    """Get GBP/blog posts from metadata files."""
    blog_dir = EXECUTION_DIR / "blog_posts"
    if not blog_dir.exists():
        return []

    cutoff = (TODAY - timedelta(days=days)).strftime("%Y-%m-%d")
    posts = []
    for meta_file in blog_dir.rglob("*_meta.json"):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            created = meta.get("created", "")
            client = meta.get("client", "")
            if client == biz_key and created >= cutoff:
                posts.append({
                    "date": created[:10],
                    "title": meta.get("title", meta_file.stem),
                })
        except Exception:
            pass
    return posts


def _screenpipe_mentions(biz_key: str, days: int) -> int:
    """Count Screenpipe OCR mentions."""
    try:
        sys.path.insert(0, str(EXECUTION_DIR))
        from screenpipe_verifier import screenpipe_healthy, screenpipe_search
    except ImportError:
        return -1
    if not screenpipe_healthy():
        return -1

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    name = BUSINESS_NAMES.get(biz_key, biz_key)
    try:
        results = screenpipe_search(name, content_type="ocr", limit=100,
                                     start_time=start_str, end_time=end_str)
        return len(results)
    except Exception:
        return -1


def _git_commits(biz_key: str, days: int) -> int:
    """Count git commits mentioning this client's directory."""
    since = (TODAY - timedelta(days=days)).strftime("%Y-%m-%d")
    repo_path = str(EXECUTION_DIR.parent.parent.parent)  # antigravity root

    if not Path(repo_path).joinpath(".git").exists():
        return 0

    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline", "--no-merges",
             "--", f"tools/execution/{biz_key}/*"],
            capture_output=True, text=True, timeout=10,
            cwd=repo_path,
            encoding="utf-8", errors="replace",
        )
        if result.returncode == 0 and result.stdout.strip():
            return len(result.stdout.strip().splitlines())
        return 0
    except Exception:
        return 0


def _engagement_data(biz_key: str, days: int) -> dict:
    """Get engagement stats from history JSON."""
    history_path = EXECUTION_DIR / biz_key / "engagement_history.json"
    if not history_path.exists():
        return {}

    cutoff = (TODAY - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
        recent = [e for e in history if e.get("date", "") >= cutoff]
        if not recent:
            return {}
        total_score = sum(e.get("score", 0) for e in recent)
        avg_score = total_score / len(recent)
        return {
            "posts_tracked": len(recent),
            "avg_score": avg_score,
            "total_likes": sum(e.get("likes", 0) for e in recent),
            "total_comments": sum(e.get("comments", 0) for e in recent),
        }
    except Exception:
        return {}


def build_audit(days: int = 7, client_filter: str = "") -> str:
    """Build the cross-channel activity audit."""
    end_date = TODAY.strftime("%B %d, %Y")
    start_date = (TODAY - timedelta(days=days)).strftime("%B %d")

    lines = [f"ACTIVITY AUDIT: {start_date} - {end_date}"]
    lines.append("=" * 40)

    clients = {client_filter: BUSINESS_NAMES[client_filter]} if client_filter else BUSINESS_NAMES
    total_fb = 0
    total_gbp = 0
    active_clients = 0

    for biz_key, name in clients.items():
        fb = _fb_posts(biz_key, days)
        gbp = _gbp_posts(biz_key, days)
        sp = _screenpipe_mentions(biz_key, days)
        git = _git_commits(biz_key, days)
        eng = _engagement_data(biz_key, days)

        has_activity = bool(fb or gbp or (sp and sp > 0) or git or eng)
        if has_activity:
            active_clients += 1

        total_fb += len(fb)
        total_gbp += len(gbp)

        lines.append("")
        activity_flag = "" if has_activity else " [INACTIVE]"
        lines.append(f"{name}{activity_flag}")
        lines.append(f"  Facebook: {len(fb)} post(s)")
        if fb:
            for p in fb[-5:]:
                lines.append(f"    {p['date']}: {p['angle'][:50]}")
            if len(fb) > 5:
                lines.append(f"    ... and {len(fb) - 5} more")

        lines.append(f"  GBP/Blog: {len(gbp)} post(s)")
        if gbp:
            for p in gbp[-3:]:
                lines.append(f"    {p['date']}: {p['title'][:50]}")

        if sp >= 0:
            attention = "HIGH" if sp >= 50 else "LOW" if sp > 0 else "ZERO"
            lines.append(f"  Screen time: {sp} mentions ({attention})")
        else:
            lines.append(f"  Screen time: (Screenpipe unavailable)")

        if git > 0:
            lines.append(f"  Git commits: {git}")

        if eng:
            lines.append(f"  Engagement: {eng['posts_tracked']} tracked, avg score {eng['avg_score']:.0f}")

    # Summary
    inactive = len(clients) - active_clients
    lines.append("")
    lines.append("-" * 40)
    lines.append(f"SUMMARY ({days} days):")
    lines.append(f"  Active clients: {active_clients}/{len(clients)}")
    lines.append(f"  Total FB posts: {total_fb}")
    lines.append(f"  Total GBP posts: {total_gbp}")
    if inactive > 0:
        inactive_names = [BUSINESS_NAMES[k] for k in clients
                          if not _fb_posts(k, days) and not _gbp_posts(k, days)]
        if inactive_names:
            lines.append(f"  Need attention: {', '.join(inactive_names)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Weekly cross-channel activity audit")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    parser.add_argument("--days", type=int, default=7, help="Lookback window (default: 7)")
    parser.add_argument("--client", help="Single client only (e.g. sugar_shack)")
    args = parser.parse_args()

    if args.client and args.client not in BUSINESS_NAMES:
        # Fuzzy match
        for k in BUSINESS_NAMES:
            if args.client.lower() in k.lower() or args.client.lower() in BUSINESS_NAMES[k].lower():
                args.client = k
                break
        else:
            print(f"[ERROR] Unknown client: {args.client}")
            print(f"  Available: {', '.join(BUSINESS_NAMES.keys())}")
            sys.exit(1)

    msg = build_audit(args.days, args.client or "")

    if args.dry_run:
        print(msg)
        return

    print("[activity_audit] Sending to Telegram...")
    ok = notify_mario(msg)
    if ok:
        print("[activity_audit] Sent successfully")
    else:
        print("[activity_audit] Failed to send — printing instead:")
        print(msg)


if __name__ == "__main__":
    main()
