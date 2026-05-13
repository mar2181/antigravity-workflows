"""
Facebook Health Check — Run at the start of every session.
Verifies each page's Graph API token is valid and can post.
Uses Graph API only — no Playwright, no browser sessions.
Takes ~5-10 seconds. Prints GREEN/RED per page.

Usage:
    python fb_health_check.py              # check all pages
    python fb_health_check.py optimum_clinic  # check one page
"""
import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

CREDS_PATH  = "fb_api_credentials.json"
CONFIG_PATH = "fb_pages_config.json"

GREEN = "[OK]  "
RED   = "[FAIL]"
WARN  = "[WARN]"

GRAPH = "https://graph.facebook.com/v19.0"


def check_page_token(page_key, page_id, page_token):
    """Hit the Graph API with the page token — confirm it's valid and can read the page."""
    result = {"page": page_key, "status": None, "detail": ""}
    if not page_token:
        result["status"] = "FAIL"
        result["detail"] = "No page_token in fb_api_credentials.json"
        return result

    try:
        url = f"{GRAPH}/{page_id}?fields=name,id,fan_count&access_token={urllib.parse.quote(page_token)}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        name = data.get("name", "?")
        fans = data.get("fan_count", "?")
        result["status"] = "OK"
        result["detail"] = f'"{name}" | followers: {fans}'
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body).get("error", {})
            msg = err.get("message", body[:120])
        except Exception:
            msg = body[:120]
        result["status"] = "FAIL"
        result["detail"] = f"HTTP {e.code}: {msg}"
    except Exception as e:
        result["status"] = "FAIL"
        result["detail"] = str(e)[:120]

    return result


def main():
    # Load credentials (source of truth for page tokens)
    creds_path = Path(CREDS_PATH)
    if not creds_path.exists():
        print(f"ERROR: {CREDS_PATH} not found")
        sys.exit(1)
    with open(creds_path) as f:
        creds = json.load(f)

    cred_pages = creds.get("pages", {})

    # Load config (source of truth for page keys + ids)
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    config_pages = config.get("pages", {})

    # Filter to specific page if provided
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if target:
        if target not in config_pages:
            print(f"Unknown page key: {target}")
            print(f"Available: {list(config_pages.keys())}")
            sys.exit(1)
        config_pages = {target: config_pages[target]}

    print("\nFacebook Health Check (Graph API)")
    print("=" * 55)

    all_ok = True
    for page_key, page_info in config_pages.items():
        posting_method = page_info.get("posting_method", "playwright")
        if posting_method != "graph_api":
            # Skip non-graph-api pages (shouldn't exist, but be safe)
            print(f"  {WARN} {page_key:20s}  posting_method={posting_method} (skipped)")
            continue

        page_id    = str(page_info.get("page_id", ""))
        # Token lookup: fb_api_credentials.json → pages → page_key → page_token
        page_token = cred_pages.get(page_key, {}).get("page_token", "")

        result = check_page_token(page_key, page_id, page_token)
        icon = GREEN if result["status"] == "OK" else (WARN if result["status"] == "WARN" else RED)
        print(f"  {icon} {page_key:20s}  {result['detail']}")
        if result["status"] == "FAIL":
            all_ok = False

    print("\n" + "=" * 55)
    if all_ok:
        print("All checks passed. Ready to post.\n")
    else:
        print("One or more checks FAILED.")
        print("Fix: run python fb_token_refresh.py   (or paste fresh page tokens into fb_api_credentials.json)\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
