"""
reauth_mario_graph_api.py
─────────────────────────
Refreshes Facebook Page Access Tokens for juan + optimum_clinic using the
Mission Control Meta app.

Uses the saved mario browser profile to navigate to the Facebook Access Token
Tool — no OAuth dialog, no redirects, no manual steps beyond closing the window.

Run:
  cd C:/Users/mario/.gemini/antigravity/tools/execution
  python reauth_mario_graph_api.py
"""

import json
import sys
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

APP_ID     = "3528802383934007"
APP_SECRET = "40a12a231443a0480c8ae7cb7df3d14a"
CREDS_FILE  = Path(__file__).parent / "fb_api_credentials.json"
PROFILE_DIR = str(Path(__file__).parent / "facebook_mario_profile")
GRAPH       = "https://graph.facebook.com/v19.0"

PAGE_ID_MAP = {
    "316634185463817":  "juan",
    "1003933732800661": "optimum_clinic",
}

def exchange_long_lived(short_token):
    resp = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "grant_type":        "fb_exchange_token",
            "client_id":         APP_ID,
            "client_secret":     APP_SECRET,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"Token exchange failed: {data}")
    return data["access_token"]

def get_page_tokens(long_user_token):
    resp = requests.get(
        f"{GRAPH}/me/accounts",
        params={"access_token": long_user_token, "fields": "id,name,access_token"},
        timeout=30,
    )
    data = resp.json()
    if "data" not in data:
        raise RuntimeError(f"Failed to get pages: {data}")
    return data["data"]

with sync_playwright() as p:
    print("[STEP 1] Opening Facebook Developer Token Tool...")
    browser = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--start-maximized"],
        no_viewport=True,
    )
    page = browser.new_page()

    # Navigate to the Graph API Explorer pre-loaded with our app
    token_tool_url = (
        f"https://developers.facebook.com/tools/explorer/"
        f"?app_id={APP_ID}&type=USER&fields=id,name"
    )
    page.goto(token_tool_url)
    page.wait_for_timeout(4000)

    print("[STEP 2] Clicking 'Generate Access Token'...")
    try:
        # Try clicking the Generate Access Token button
        btn = page.locator("text=Generate Access Token").first
        btn.click()
        page.wait_for_timeout(3000)
        # A Facebook dialog may appear asking to approve — click OK/Continue
        for label in ["Continue", "OK", "Allow", "Yes"]:
            try:
                page.locator(f"text={label}").first.click(timeout=3000)
                page.wait_for_timeout(2000)
                break
            except Exception:
                pass
    except Exception as e:
        print(f"  [WARN] Could not auto-click Generate button: {e}")
        print("  Please click 'Generate Access Token' manually in the browser window.")
        input("  Press Enter once you see a token appear in the input field...")

    print("[STEP 3] Extracting token from page...")
    short_token = None

    # Try to grab token from the input field
    for attempt in range(10):
        try:
            val = page.locator("input[placeholder*='Access Token'], input[aria-label*='Access Token'], input[name*='token']").first.input_value(timeout=3000)
            if val and len(val) > 20:
                short_token = val
                break
        except Exception:
            pass
        page.wait_for_timeout(1000)

    if not short_token:
        print("[MANUAL] Could not auto-extract token.")
        print("  In the browser: copy the full token from the 'Access Token' input box.")
        short_token = input("  Paste the token here and press Enter: ").strip()

    browser.close()

if not short_token:
    print("[ERROR] No token obtained. Exiting.")
    sys.exit(1)

print(f"[OK] Got token: {short_token[:30]}...")

print("[STEP 4] Exchanging for 60-day long-lived token...")
try:
    long_token = exchange_long_lived(short_token)
    print(f"[OK] Long-lived token obtained.")
except RuntimeError as e:
    print(f"[WARN] Exchange failed ({e}) — will try using token as-is.")
    long_token = short_token

print("[STEP 5] Fetching page tokens...")
try:
    pages = get_page_tokens(long_token)
except RuntimeError as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print(f"[OK] Found {len(pages)} page(s):")
for pg in pages:
    print(f"  • {pg['name']} (id: {pg['id']})")

print("[STEP 6] Updating fb_api_credentials.json...")
creds = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
creds["mario_user_token"] = long_token

updated = []
for pg in pages:
    key = PAGE_ID_MAP.get(pg["id"])
    if key and key in creds.get("pages", {}):
        creds["pages"][key]["page_token"] = pg["access_token"]
        creds["pages"][key]["page_id"]    = pg["id"]
        updated.append(key)
        print(f"  ✓ {key}: {pg['name']}")

CREDS_FILE.write_text(json.dumps(creds, indent=2, ensure_ascii=False), encoding="utf-8")

if updated:
    print(f"\n✅ Done. Tokens refreshed for: {updated}")
    print("You can now schedule posts for juan and optimum_clinic.")
else:
    print("\n⚠️  No matching pages found in fb_api_credentials.json.")
    print("   Pages returned by Facebook:")
    for pg in pages:
        print(f"   id={pg['id']} name={pg['name']}")
    print("   Check PAGE_ID_MAP in this script and add any missing IDs.")
