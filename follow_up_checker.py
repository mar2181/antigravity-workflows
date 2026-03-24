#!/usr/bin/env python3
"""
follow_up_checker.py — Alert Mario about emails needing a response (unread >24h).

Calls followup_check.js via Node.js, sends Telegram alert if any found.

Schedule (Windows Task Scheduler — runs twice daily):
  schtasks /create /tn "Antigravity Follow-Up Check" /tr "python C:\\Users\\mario\\.gemini\\antigravity\\tools\\execution\\follow_up_checker.py" /sc daily /st 09:00 /f
  schtasks /create /tn "Antigravity Follow-Up Check PM" /tr "python C:\\Users\\mario\\.gemini\\antigravity\\tools\\execution\\follow_up_checker.py" /sc daily /st 14:00 /f

Usage:
  python follow_up_checker.py            # check + send Telegram alert
  python follow_up_checker.py --dry-run  # print only
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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


def check_followups() -> dict:
    """Call followup_check.js and return parsed JSON."""
    script = Path("C:/Users/mario/gws-workspace/demos/followup_check.js")
    if not script.exists():
        return {"needs_followup": [], "error": "followup_check.js not found"}
    try:
        result = subprocess.run(
            ["node", str(script)],
            capture_output=True, text=True, timeout=20,
            cwd=str(script.parent),
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return {"needs_followup": [], "error": result.stderr.strip()[:200]}
        return json.loads(result.stdout.strip())
    except subprocess.TimeoutExpired:
        return {"needs_followup": [], "error": "Timed out"}
    except Exception as e:
        return {"needs_followup": [], "error": str(e)[:200]}


def main():
    parser = argparse.ArgumentParser(description="Check for emails needing follow-up")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't send")
    args = parser.parse_args()

    print("[follow_up] Checking for unanswered emails >24h...")
    data = check_followups()

    if data.get("error"):
        print(f"[follow_up] Error: {data['error']}")
        return

    emails = data.get("needs_followup", [])
    if not emails:
        print("[follow_up] OK -- no emails need follow-up")
        return

    # Build alert message
    lines = [f"EMAIL FOLLOW-UP NEEDED ({len(emails)})"]
    lines.append("Unread >24h, primary inbox:")
    lines.append("")
    for email in emails[:10]:
        sender = email["from"].split("<")[0].strip() if "<" in email["from"] else email["from"]
        hours = email.get("hours_ago", "?")
        if isinstance(hours, (int, float)) and hours >= 48:
            days = hours // 24
            age = f"{days}d ago"
        else:
            age = f"{hours}h ago"
        lines.append(f"  [{age}] {sender}")
        lines.append(f"    {email['subject']}")
        lines.append("")

    if len(emails) > 10:
        lines.append(f"  ... and {len(emails) - 10} more")

    msg = "\n".join(lines)

    if args.dry_run:
        print(msg)
        return

    print(f"[follow_up] {len(emails)} email(s) need follow-up -- sending Telegram alert")
    ok = notify_mario(msg)
    if ok:
        print("[follow_up] Alert sent")
    else:
        print("[follow_up] Failed to send Telegram -- printing instead:")
        print(msg)


if __name__ == "__main__":
    main()
