#!/usr/bin/env python3
"""
weekly_changelog.py — Weekly git changelog sent to Telegram every Monday 8 AM.

Summarizes the past 7 days of git activity across key repositories:
  - Antigravity (tools/execution automation)
  - Mission Control (dashboard)
  - Home (top-level repo)

Schedule (Windows Task Scheduler):
  schtasks /create /tn "Antigravity Weekly Changelog" /tr "python C:\\Users\\mario\\.gemini\\antigravity\\tools\\execution\\weekly_changelog.py" /sc weekly /d MON /st 08:00 /f

Usage:
  python weekly_changelog.py           # send to Telegram
  python weekly_changelog.py --dry-run # print only
  python weekly_changelog.py --days 14 # custom lookback
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import date, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TODAY = date.today()

REPOS = [
    ("Antigravity", "C:/Users/mario/.gemini/antigravity"),
    ("Mission Control", "C:/Users/mario/missioncontrol/dashboard"),
    ("Home", "C:/Users/mario"),
    ("Fishing App", "C:/Users/mario/OneDrive/Documents/fishing-app"),
    ("HS Solutions", "C:/Users/mario/OneDrive/Documents/hs-solutions-allinone-tool"),
]


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


def _get_commits(repo_path: str, since_date: str) -> list:
    """Get commits from a repo since a given date."""
    if not Path(repo_path).joinpath(".git").exists():
        return []
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since_date}", "--oneline", "--no-merges", "-50"],
            capture_output=True, text=True, timeout=10,
            cwd=repo_path,
            encoding="utf-8", errors="replace",
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()
        return []
    except Exception:
        return []


def _get_file_stats(repo_path: str, since_date: str) -> dict:
    """Get files changed / insertions / deletions stats."""
    if not Path(repo_path).joinpath(".git").exists():
        return {}
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", f"--since={since_date}", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=repo_path,
            encoding="utf-8", errors="replace",
        )
        # Try diffstat shortstat instead
        result2 = subprocess.run(
            ["git", "log", f"--since={since_date}", "--no-merges", "--shortstat", "--oneline"],
            capture_output=True, text=True, timeout=10,
            cwd=repo_path,
            encoding="utf-8", errors="replace",
        )
        if result2.returncode == 0 and result2.stdout.strip():
            # Parse shortstat lines: " 3 files changed, 45 insertions(+), 12 deletions(-)"
            files_changed = 0
            insertions = 0
            deletions = 0
            for line in result2.stdout.strip().splitlines():
                line = line.strip()
                if "file" in line and "changed" in line:
                    parts = line.split(",")
                    for part in parts:
                        part = part.strip()
                        if "file" in part:
                            try:
                                files_changed += int(part.split()[0])
                            except (ValueError, IndexError):
                                pass
                        elif "insertion" in part:
                            try:
                                insertions += int(part.split()[0])
                            except (ValueError, IndexError):
                                pass
                        elif "deletion" in part:
                            try:
                                deletions += int(part.split()[0])
                            except (ValueError, IndexError):
                                pass
            if files_changed or insertions or deletions:
                return {"files": files_changed, "insertions": insertions, "deletions": deletions}
        return {}
    except Exception:
        return {}


def build_changelog(days: int = 7) -> str:
    """Build the weekly changelog message."""
    since = (TODAY - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = TODAY.strftime("%B %d, %Y")
    start_date = (TODAY - timedelta(days=days)).strftime("%B %d")

    lines = [f"WEEKLY CHANGELOG: {start_date} - {end_date}"]
    lines.append("=" * 40)

    total_commits = 0
    total_insertions = 0
    total_deletions = 0

    for repo_name, repo_path in REPOS:
        commits = _get_commits(repo_path, since)
        if not commits:
            continue

        stats = _get_file_stats(repo_path, since)
        total_commits += len(commits)
        total_insertions += stats.get("insertions", 0)
        total_deletions += stats.get("deletions", 0)

        lines.append("")
        stat_str = ""
        if stats:
            stat_str = f" (+{stats['insertions']}/-{stats['deletions']})"
        lines.append(f"{repo_name}: {len(commits)} commit(s){stat_str}")

        # Show up to 15 commits per repo
        for c in commits[:15]:
            lines.append(f"  {c.strip()}")
        if len(commits) > 15:
            lines.append(f"  ... and {len(commits) - 15} more")

    if total_commits == 0:
        lines.append("")
        lines.append("(no commits this week)")
    else:
        lines.append("")
        lines.append(f"TOTAL: {total_commits} commits, +{total_insertions}/-{total_deletions} lines")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Weekly git changelog to Telegram")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    parser.add_argument("--days", type=int, default=7, help="Lookback window (default: 7)")
    args = parser.parse_args()

    msg = build_changelog(args.days)

    if args.dry_run:
        print(msg)
        return

    print("[weekly_changelog] Sending to Telegram...")
    ok = notify_mario(msg)
    if ok:
        print("[weekly_changelog] Sent successfully")
    else:
        print("[weekly_changelog] Failed to send — printing instead:")
        print(msg)


if __name__ == "__main__":
    main()
