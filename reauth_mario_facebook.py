"""
Re-authenticate Mario's Facebook account into facebook_mario_profile.

Run this ONCE to log in as Mario (marioelizondo81@gmail.com).
The session will be saved and reused by all Juan Elizondo posting scripts.

Usage:
    cd C:/Users/mario/.gemini/antigravity/tools/execution
    python reauth_mario_facebook.py
"""
import os, sys, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

MARIO_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_mario_profile")

print("=" * 60)
print("RE-AUTH: Mario's Facebook Account")
print("Account: marioelizondo81@gmail.com")
print("Profile: facebook_mario_profile")
print("=" * 60)
print("\nBrowser will open. Log in as Mario if not already logged in.")
print("Once you see Facebook feed, CLOSE the browser window.")
print("Session will be saved automatically.\n")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=MARIO_PROFILE,
        headless=False,
        viewport={"width": 1280, "height": 900}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.facebook.com/")
    time.sleep(3)

    # Check if already logged in
    if "login" in page.url.lower() or page.query_selector("[name='email']"):
        print("[ACTION NEEDED] Please log in as Mario in the browser window.")
        print("  Email: marioelizondo81@gmail.com")
        print("  After login, navigate to: https://www.facebook.com/JuanElizondoRemax/")
        print("  Confirm the page loads correctly, then close the browser.\n")
    else:
        print("[OK] Already logged in. Navigating to Juan's page to verify...")
        page.goto("https://www.facebook.com/JuanElizondoRemax/")
        time.sleep(3)
        print(f"  Page URL: {page.url}")
        print("  Close the browser when done.")

    # Wait for user to close
    try:
        ctx.wait_for_event("close", timeout=300000)
    except:
        pass

    ctx.close()

print("\n[DONE] Session saved to facebook_mario_profile/")
print("You can now run: python post_juan_remax_ad1.py")
