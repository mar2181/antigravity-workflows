#!/usr/bin/env python3
"""
nightly_intelligence.py — Run the full competitor intelligence pipeline.

Chains all 4 intelligence scripts in order:
  1. competitor_monitor.py          -> GBP ratings, review counts, hours changes
  2. competitor_fb_adlibrary.py     -> Facebook paid ads (who's spending, who's dark)
  3. competitor_ai_analyzer.py      -> AI analysis: themes, winning content, 3 counter-angles
  4. competitor_review_miner.py     -> Google review text mining (weekly only)

Then runs morning_brief.py, sends the HTML file to Telegram as a download,
and starts a localhost server so you can open it in a browser.

Usage:
  python nightly_intelligence.py                 # full pipeline (skip reviews)
  python nightly_intelligence.py --with-reviews  # + review miner (~18 min, run weekly)
  python nightly_intelligence.py --headful       # show browser windows (debug)
  python nightly_intelligence.py --skip-ai       # skip AI analyzer (save API cost)
  python nightly_intelligence.py --business sugar_shack  # one business only

Telegram output:
  - Text message: pipeline summary + localhost URL
  - Document: the HTML file attached as a downloadable file
"""

import sys
import subprocess
import argparse
import json
import time
import socket
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR  = Path(__file__).parent
REPORTS_DIR    = EXECUTION_DIR / "competitor_reports"
BRIEFS_DIR     = EXECUTION_DIR / "morning_briefs"
REPORTS_DIR.mkdir(exist_ok=True)
BRIEFS_DIR.mkdir(exist_ok=True)

BRIEF_SERVER_PORT = 8901   # dedicated port for morning briefs

# ─── Telegram helpers ─────────────────────────────────────────────────────────

def _load_telegram_creds() -> tuple[str, str]:
    """Return (token, chat_id) from .env file."""
    env = {}
    env_path = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_USER_ID", "")


def notify_mario(text: str) -> bool:
    """Send a plain text Telegram message."""
    try:
        token, chat_id = _load_telegram_creds()
        if not token or not chat_id:
            return False
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
        resp = urllib.request.urlopen(
            urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage", data=data
            ), timeout=10
        )
        return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"  [Telegram text failed: {e}]")
        return False


def send_document_to_mario(file_path: Path, caption: str = "") -> bool:
    """Send a file to Mario via Telegram sendDocument (multipart/form-data)."""
    import email.mime.multipart
    import email.mime.base
    import email.encoders

    try:
        token, chat_id = _load_telegram_creds()
        if not token or not chat_id:
            return False

        if not file_path.exists():
            print(f"  [Telegram doc: file not found: {file_path}]")
            return False

        # Build multipart request manually (no requests library needed)
        boundary = "----TelegramBoundary7f3a9c"
        body_parts = []

        def field(name, value):
            return (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode()

        body_parts.append(field("chat_id", chat_id))
        if caption:
            body_parts.append(field("caption", caption[:1024]))

        file_bytes = file_path.read_bytes()
        file_part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="{file_path.name}"\r\n'
            f"Content-Type: text/html\r\n\r\n"
        ).encode() + file_bytes + b"\r\n"
        body_parts.append(file_part)
        body_parts.append(f"--{boundary}--\r\n".encode())

        body = b"".join(body_parts)
        req  = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        if not result.get("ok"):
            print(f"  [Telegram doc error: {result}]")
        return result.get("ok", False)

    except Exception as e:
        print(f"  [Telegram doc failed: {e}]")
        return False


# ─── Localhost server ─────────────────────────────────────────────────────────

def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def start_brief_server(briefs_dir: Path, port: int = BRIEF_SERVER_PORT) -> bool:
    """
    Start serve.py in the background serving morning_briefs/.
    If something is already on that port, skip (assume it's still running).
    Returns True if server is (now) available.
    """
    if _port_in_use(port):
        print(f"  [Brief server already running on port {port}]")
        return True

    serve_py = EXECUTION_DIR / "serve.py"
    if not serve_py.exists():
        print(f"  [serve.py not found — skipping localhost server]")
        return False

    try:
        subprocess.Popen(
            [sys.executable, str(serve_py), str(briefs_dir), str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(EXECUTION_DIR),
        )
        # Wait up to 4s for it to come up
        for _ in range(8):
            time.sleep(0.5)
            if _port_in_use(port):
                print(f"  [Brief server started on port {port}]")
                return True
        print(f"  [Brief server did not start in time on port {port}]")
        return False
    except Exception as e:
        print(f"  [Brief server error: {e}]")
        return False


# ─── Script runner ────────────────────────────────────────────────────────────

def run_script(script_name: str, extra_args: list = None, label: str = None) -> tuple[bool, str]:
    """Run a Python script in the execution dir. Returns (success, summary_string)."""
    label = label or script_name
    args  = [sys.executable, str(EXECUTION_DIR / script_name)] + (extra_args or [])

    print(f"\n{'-'*60}")
    print(f">>  {label}")
    print(f"{'-'*60}")

    start = time.time()
    try:
        result = subprocess.run(
            args,
            capture_output=False,
            text=True,
            cwd=str(EXECUTION_DIR),
            timeout=900,
        )
        elapsed = round(time.time() - start, 1)
        success = result.returncode == 0
        status  = "OK" if success else f"FAILED (exit {result.returncode})"
        print(f"\n   {status} - {elapsed}s")
        return success, f"{label}: {status} ({elapsed}s)"
    except subprocess.TimeoutExpired:
        print(f"\n   TIMEOUT after 15 min")
        return False, f"{label}: TIMEOUT"
    except Exception as e:
        print(f"\n   ERROR: {e}")
        return False, f"{label}: ERROR - {e}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nightly competitor intelligence pipeline")
    parser.add_argument("--with-reviews", action="store_true",
                        help="Run competitor_review_miner.py (adds ~10 min)")
    parser.add_argument("--skip-ai",      action="store_true",
                        help="Skip AI analyzer (no OpenRouter cost)")
    parser.add_argument("--headful",      action="store_true",
                        help="Show browser windows (debug)")
    parser.add_argument("--business",     default=None,
                        help="Run for one business only (e.g. sugar_shack)")
    parser.add_argument("--no-telegram",  action="store_true",
                        help="Don't send Telegram notification")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")
    start_ts = time.time()

    print(f"\n{'='*60}")
    print(f"  NIGHTLY INTELLIGENCE PIPELINE - {date_str}")
    print(f"{'='*60}")

    common_args = []
    if args.headful:
        common_args += ["--headful"]
    if args.business:
        common_args += ["--business", args.business]

    results = []

    # Step 1 — GBP competitor monitor
    ok, summary = run_script(
        "competitor_monitor.py",
        extra_args=common_args,
        label="Step 1 - GBP Competitor Monitor (ratings, reviews, hours)"
    )
    results.append(summary)

    # Step 2 — Facebook Ad Library
    adlib_args = (["--headful"] if args.headful else []) + (["--business", args.business] if args.business else [])
    ok2, summary2 = run_script(
        "competitor_fb_adlibrary.py",
        extra_args=adlib_args,
        label="Step 2 - Facebook Ad Library (paid ads intel)"
    )
    results.append(summary2)

    # Step 3 — AI analysis
    if not args.skip_ai:
        ok3, summary3 = run_script(
            "competitor_ai_analyzer.py",
            extra_args=(["--business", args.business] if args.business else []),
            label="Step 3 - AI Competitor Analysis (themes, weaknesses, counter-angles)"
        )
        results.append(summary3)
    else:
        results.append("Step 3 - AI Analyzer: SKIPPED (--skip-ai)")
        print("\n  [Skipped AI analyzer]")

    # Step 4 — Google Review miner (weekly or on demand)
    if args.with_reviews:
        ok4, summary4 = run_script(
            "competitor_review_miner.py",
            extra_args=(["--business", args.business] if args.business else []),
            label="Step 4 - Google Review Miner (customer voice intel)"
        )
        results.append(summary4)
    else:
        results.append("Step 4 - Review Miner: SKIPPED (use --with-reviews to run)")
        print("\n  [Skipping review miner - run with --with-reviews weekly]")

    # Step 4.5 — Delta tracker (compute movements BEFORE morning brief generates)
    ok_delta, summary_delta = run_script(
        "delta_tracker.py",
        extra_args=[],
        label="Step 4.5 - Delta Tracker (movements since yesterday)"
    )
    results.append(summary_delta)

    # Step 5 — Morning brief
    ok5, summary5 = run_script(
        "morning_brief.py",
        extra_args=[],
        label="Step 5 - Morning Brief (synthesize all intel)"
    )
    results.append(summary5)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_time = round(time.time() - start_ts, 1)
    errors     = [r for r in results if "FAILED" in r or "TIMEOUT" in r or "ERROR" in r]
    skipped    = [r for r in results if "SKIPPED" in r]
    successes  = [r for r in results if ": OK" in r]

    brief_html = BRIEFS_DIR / f"{date_str}.html"

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE - {total_time}s")
    print(f"{'='*60}")
    for r in results:
        icon = "  [OK]" if ": OK" in r else ("  [--]" if "SKIPPED" in r else "  [!!]")
        print(f"{icon}  {r}")

    # ── Start localhost server ─────────────────────────────────────────────────
    localhost_url = None
    if brief_html.exists():
        server_ok = start_brief_server(BRIEFS_DIR, BRIEF_SERVER_PORT)
        if server_ok:
            localhost_url = f"http://localhost:{BRIEF_SERVER_PORT}/{date_str}.html"
            print(f"\n  Morning brief: {localhost_url}")

    # ── Telegram: text summary + HTML file ────────────────────────────────────
    if not args.no_telegram:
        if errors:
            msg = (
                f"[FAIL] Nightly Intelligence [{date_str}] - {len(errors)} error(s)\n\n"
                + "\n".join(results)
                + f"\n\nTotal: {total_time}s"
            )
            notify_mario(msg)
        else:
            skip_note = f"\nSkipped: {len(skipped)} steps" if skipped else ""
            url_line  = f"\n\nOpen in browser:\n{localhost_url}" if localhost_url else ""
            msg = (
                f"[DONE] Nightly Intelligence [{date_str}]\n\n"
                f"{len(successes)} scripts ran OK{skip_note}\n"
                f"Total: {total_time}s"
                f"{url_line}"
            )
            sent_msg = notify_mario(msg)
            if sent_msg:
                print("  Telegram: summary sent")

            # Send HTML as downloadable file
            if brief_html.exists():
                cap = f"Morning Brief {date_str} - tap to open or download"
                sent_doc = send_document_to_mario(brief_html, caption=cap)
                if sent_doc:
                    print("  Telegram: HTML file sent")
                else:
                    print("  Telegram: HTML file send failed")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
