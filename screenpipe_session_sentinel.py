"""
screenpipe_session_sentinel.py — Session Expiry Sentinel (UC-2)

Runs every 30 minutes via Windows Task Scheduler.
Scans Screenpipe OCR for Facebook/Google login walls.
Alerts Mario via Telegram if a session has expired.

Setup (run once):
  schtasks /create /tn "Screenpipe Session Sentinel" /tr "python C:\\Users\\mario\\.gemini\\antigravity\\tools\\execution\\screenpipe_session_sentinel.py" /sc minute /mo 30 /f

Manual run:
  python screenpipe_session_sentinel.py
"""

import sys
from pathlib import Path

# Ensure the execution dir is on the path
sys.path.insert(0, str(Path(__file__).parent))

from screenpipe_verifier import (
    check_session_expired,
    notify_mario,
    screenpipe_healthy,
)


def main():
    if not screenpipe_healthy():
        print("[SENTINEL] Screenpipe not running — skipping check")
        return

    result = check_session_expired(window_minutes=30)

    if result["expired"]:
        platform = result["platform"]
        keyword = result["keyword_found"]
        app = result["app_name"]

        msg = (
            f"🔒 SESSION EXPIRED — {platform.upper()}\n"
            f"Detected: \"{keyword}\"\n"
            f"App: {app}\n"
            f"Action needed:\n"
        )

        if platform == "facebook":
            msg += (
                "  • Kill Chrome: Stop-Process -Name chrome -Force\n"
                "  • Clear lock: rm facebook_sniffer_profile/SingletonLock\n"
                "  • Re-auth: python reauth_facebook_sniffer.py\n"
                "  • Or for Mario: python reauth_mario_facebook.py"
            )
        elif platform == "google":
            msg += (
                "  • Re-auth GBP: python reauth_mario_gbp.py\n"
                "  • Check gbp_mario_profile/ or gbp_sniffer_profile/"
            )

        notify_mario(msg)
        print(f"[SENTINEL] ALERT sent: {platform} session expired")
    else:
        print("[SENTINEL] OK — No expired sessions detected")


if __name__ == "__main__":
    main()
