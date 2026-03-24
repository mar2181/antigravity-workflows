"""
screenpipe_verifier.py — Screenpipe OCR verification for Antigravity Digital

Shared module for querying Screenpipe's REST API to verify Facebook posts,
GBP posts, and detect session expiry. Used by facebook_marketer.py, GBP
posting scripts, and screenpipe_session_sentinel.py.

Screenpipe must be running at localhost:3030 (see ~/.screenpipe/start_screenpipe.bat).
"""

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCREENPIPE_BASE = "http://localhost:3030"
EXECUTION_DIR = Path(__file__).parent


# ─── Telegram ────────────────────────────────────────────────────────────────

def _load_telegram_creds() -> tuple:
    env = {}
    env_path = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_USER_ID", "")


def notify_mario(text: str) -> bool:
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
        print(f"  [Telegram failed: {e}]")
        return False


# ─── Screenpipe API ──────────────────────────────────────────────────────────

def screenpipe_healthy() -> bool:
    try:
        resp = urllib.request.urlopen(f"{SCREENPIPE_BASE}/health", timeout=5)
        data = json.loads(resp.read())
        return data.get("status") == "healthy"
    except Exception:
        return False


def screenpipe_search(
    query: str,
    content_type: str = "ocr",
    limit: int = 10,
    start_time: str = None,
    end_time: str = None,
    app_name: str = None,
) -> list:
    """Query Screenpipe OCR/audio search. Returns list of result items."""
    params = {
        "q": query,
        "content_type": content_type,
        "limit": str(limit),
    }
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if app_name:
        params["app_name"] = app_name

    url = f"{SCREENPIPE_BASE}/search?{urllib.parse.urlencode(params)}"
    try:
        resp = urllib.request.urlopen(url, timeout=15)
        data = json.loads(resp.read())
        return data.get("data", [])
    except Exception as e:
        print(f"  [Screenpipe search error: {e}]")
        return []


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_ago(seconds: int) -> str:
    t = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── Facebook Post Verification (UC-1) ──────────────────────────────────────

# Strings that indicate a successful Facebook post
FB_SUCCESS_INDICATORS = [
    "just now",
    "Just now",
    "1m",
    "shared a post",
    "Published",
]

# Strings that indicate a Facebook failure
FB_FAILURE_INDICATORS = [
    "Something went wrong",
    "couldn't create your post",
    "Try again",
    "We couldn't process",
    "There was a problem",
    "Post failed",
]


def verify_fb_post(
    page_key: str,
    page_name: str,
    post_type: str = "image",
    wait_seconds: int = 8,
    window_seconds: int = 90,
) -> dict:
    """
    After a Facebook post, check Screenpipe OCR for verification.

    Args:
        page_key: e.g. "sugar_shack"
        page_name: e.g. "The Sugar Shack SPI"
        post_type: "text", "image", or "video"
        wait_seconds: seconds to wait before querying (let FB render)
        window_seconds: how far back to search in OCR data

    Returns:
        {
            "verified": bool,
            "page_name_found": bool,
            "success_indicator": str or None,
            "failure_detected": str or None,
            "details": str,
        }
    """
    if not screenpipe_healthy():
        return {
            "verified": False,
            "page_name_found": False,
            "success_indicator": None,
            "failure_detected": None,
            "details": "Screenpipe not running",
        }

    time.sleep(wait_seconds)

    start = _iso_ago(window_seconds)
    end = _iso_now()

    # Search for the page name in recent OCR
    results = screenpipe_search(
        query=page_name,
        content_type="ocr",
        limit=5,
        start_time=start,
        end_time=end,
    )

    page_name_found = len(results) > 0

    # Check all recent OCR text for success/failure indicators
    all_results = screenpipe_search(
        query="post",
        content_type="ocr",
        limit=10,
        start_time=start,
        end_time=end,
    )

    all_text = ""
    for r in results + all_results:
        all_text += r.get("content", {}).get("text", "") + "\n"

    # Check for failures first (higher priority)
    failure_detected = None
    for indicator in FB_FAILURE_INDICATORS:
        if indicator.lower() in all_text.lower():
            failure_detected = indicator
            break

    # Check for success indicators
    success_indicator = None
    for indicator in FB_SUCCESS_INDICATORS:
        if indicator in all_text:
            success_indicator = indicator
            break

    verified = page_name_found and success_indicator and not failure_detected

    details = []
    if page_name_found:
        details.append(f"Page '{page_name}' visible on screen")
    else:
        details.append(f"Page '{page_name}' NOT found in OCR")
    if success_indicator:
        details.append(f"Success indicator: '{success_indicator}'")
    if failure_detected:
        details.append(f"FAILURE detected: '{failure_detected}'")

    return {
        "verified": bool(verified),
        "page_name_found": page_name_found,
        "success_indicator": success_indicator,
        "failure_detected": failure_detected,
        "details": " | ".join(details),
    }


def verify_and_notify_fb(page_key: str, page_name: str, post_type: str = "image") -> bool:
    """Verify a Facebook post and notify Mario if it failed. Returns True if verified."""
    result = verify_fb_post(page_key, page_name, post_type)

    if result["failure_detected"]:
        notify_mario(
            f"🚨 FB POST FAILED — {page_name}\n"
            f"Type: {post_type}\n"
            f"Error: {result['failure_detected']}\n"
            f"Details: {result['details']}"
        )
        print(f"[VERIFY] FAILED: {result['details']}")
        return False

    if result["verified"]:
        print(f"[VERIFY] OK: {result['details']}")
        return True

    # Uncertain — page name not found or no success indicator
    print(f"[VERIFY] UNCERTAIN: {result['details']}")
    notify_mario(
        f"⚠️ FB POST UNVERIFIED — {page_name}\n"
        f"Type: {post_type}\n"
        f"Details: {result['details']}\n"
        f"Check debug_snap_POST_SUCCESS_{post_type}_{page_key}.png manually."
    )
    return False


# ─── GBP Post Verification (UC-3) ───────────────────────────────────────────

GBP_SUCCESS_INDICATORS = [
    "Your post has been published",
    "Post published",
    "GBP_POST_OK",
    "posted successfully",
    "Copy post",
]

GBP_FAILURE_INDICATORS = [
    "Upload failed",
    "couldn't publish",
    "Error publishing",
    "Something went wrong",
    "Try again later",
]


def verify_gbp_post(
    business_name: str,
    wait_seconds: int = 8,
    window_seconds: int = 90,
) -> dict:
    """
    After a GBP post, check Screenpipe OCR for verification.

    Args:
        business_name: e.g. "Custom Designs" or "Optimum"
        wait_seconds: seconds to wait before querying
        window_seconds: how far back to search

    Returns same dict structure as verify_fb_post.
    """
    if not screenpipe_healthy():
        return {
            "verified": False,
            "page_name_found": False,
            "success_indicator": None,
            "failure_detected": None,
            "details": "Screenpipe not running",
        }

    time.sleep(wait_seconds)

    start = _iso_ago(window_seconds)
    end = _iso_now()

    results = screenpipe_search(
        query=business_name,
        content_type="ocr",
        limit=5,
        start_time=start,
        end_time=end,
    )

    page_name_found = len(results) > 0

    # Search for GBP-specific success/failure strings
    gbp_results = screenpipe_search(
        query="post",
        content_type="ocr",
        limit=10,
        start_time=start,
        end_time=end,
    )

    all_text = ""
    for r in results + gbp_results:
        all_text += r.get("content", {}).get("text", "") + "\n"

    failure_detected = None
    for indicator in GBP_FAILURE_INDICATORS:
        if indicator.lower() in all_text.lower():
            failure_detected = indicator
            break

    success_indicator = None
    for indicator in GBP_SUCCESS_INDICATORS:
        if indicator.lower() in all_text.lower():
            success_indicator = indicator
            break

    verified = page_name_found and success_indicator and not failure_detected

    details = []
    if page_name_found:
        details.append(f"Business '{business_name}' visible")
    else:
        details.append(f"Business '{business_name}' NOT found in OCR")
    if success_indicator:
        details.append(f"Success: '{success_indicator}'")
    if failure_detected:
        details.append(f"FAILURE: '{failure_detected}'")

    return {
        "verified": bool(verified),
        "page_name_found": page_name_found,
        "success_indicator": success_indicator,
        "failure_detected": failure_detected,
        "details": " | ".join(details),
    }


def verify_and_notify_gbp(business_name: str) -> bool:
    """Verify a GBP post and notify Mario if it failed."""
    result = verify_gbp_post(business_name)

    if result["failure_detected"]:
        notify_mario(
            f"🚨 GBP POST FAILED — {business_name}\n"
            f"Error: {result['failure_detected']}\n"
            f"Details: {result['details']}"
        )
        print(f"[GBP-VERIFY] FAILED: {result['details']}")
        return False

    if result["verified"]:
        print(f"[GBP-VERIFY] OK: {result['details']}")
        return True

    print(f"[GBP-VERIFY] UNCERTAIN: {result['details']}")
    return False


# ─── Session Expiry Detection (UC-2) ────────────────────────────────────────

SESSION_EXPIRED_KEYWORDS = [
    "Log in to Facebook",
    "Log Into Facebook",
    "Session expired",
    "Your session has expired",
    "Please log in again",
    "you must log in",
    "Sign in to Google",
    "Couldn't sign you in",
]


def check_session_expired(window_minutes: int = 30) -> dict:
    """
    Check if any login walls appeared on screen in the last N minutes.

    Returns:
        {
            "expired": bool,
            "platform": "facebook" | "google" | None,
            "keyword_found": str or None,
            "app_name": str or None,
        }
    """
    if not screenpipe_healthy():
        return {"expired": False, "platform": None, "keyword_found": None, "app_name": None}

    start = _iso_ago(window_minutes * 60)
    end = _iso_now()

    for keyword in SESSION_EXPIRED_KEYWORDS:
        results = screenpipe_search(
            query=keyword,
            content_type="ocr",
            limit=1,
            start_time=start,
            end_time=end,
        )

        if results:
            app = results[0].get("content", {}).get("app_name", "unknown")
            platform = "facebook" if "facebook" in keyword.lower() else "google"
            return {
                "expired": True,
                "platform": platform,
                "keyword_found": keyword,
                "app_name": app,
            }

    return {"expired": False, "platform": None, "keyword_found": None, "app_name": None}


# ─── Playwright Failure Forensics (UC-5) ─────────────────────────────────────

def get_screen_context_at_failure(seconds_back: int = 30) -> str:
    """
    When a Playwright action fails, grab what Screenpipe saw on screen.
    Returns OCR text from the failure window for debugging.
    """
    if not screenpipe_healthy():
        return "[Screenpipe not running — cannot get screen context]"

    start = _iso_ago(seconds_back)
    end = _iso_now()

    results = screenpipe_search(
        query="",
        content_type="ocr",
        limit=3,
        start_time=start,
        end_time=end,
    )

    if not results:
        return "[No OCR data in the last {seconds_back}s]"

    texts = []
    for r in results:
        content = r.get("content", {})
        app = content.get("app_name", "?")
        text = content.get("text", "")[:500]
        texts.append(f"[{app}] {text}")

    return "\n---\n".join(texts)


# ─── CLI for testing ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("Screenpipe Verifier — Test Mode")
    print(f"  Screenpipe healthy: {screenpipe_healthy()}")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "session":
            result = check_session_expired(window_minutes=30)
            print(f"  Session check: {result}")

        elif cmd == "fb":
            page_name = sys.argv[2] if len(sys.argv) > 2 else "Sugar Shack"
            result = verify_fb_post("test", page_name)
            print(f"  FB verify: {result}")

        elif cmd == "gbp":
            biz = sys.argv[2] if len(sys.argv) > 2 else "Custom Designs"
            result = verify_gbp_post(biz)
            print(f"  GBP verify: {result}")

        elif cmd == "context":
            text = get_screen_context_at_failure(seconds_back=60)
            print(f"  Screen context:\n{text.encode('ascii', 'replace').decode()}")

        elif cmd == "search":
            query = sys.argv[2] if len(sys.argv) > 2 else "Facebook"
            results = screenpipe_search(query, limit=3)
            print(f"  Found {len(results)} results for '{query}'")
            for r in results[:2]:
                c = r.get("content", {})
                print(f"    App: {c.get('app_name')} | Text: {c.get('text','')[:100]}...")
    else:
        print("  Usage: python screenpipe_verifier.py [session|fb|gbp|context|search] [args]")
        print("  Testing basic search...")
        results = screenpipe_search("Claude", limit=2)
        print(f"  Found {len(results)} results for 'Claude'")
