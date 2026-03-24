"""
Post Juan Elizondo RE/MAX Elite — Ad #2 (Luxury Showcase)
Auth: Mario's account (marioelizondo81@gmail.com) via facebook_mario_profile
Page: https://www.facebook.com/JuanElizondoRemax/

NOTE: This uses facebook_mario_profile — NOT facebook_sniffer_profile (Yehuda).
Run reauth_mario_facebook.py first if this is the first time posting as Mario.
"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

MARIO_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_mario_profile")
PAGE_URL      = "https://www.facebook.com/ElizondoReMax/"
IMAGE_PATH    = r"C:\Users\mario\juan_remax_ad_images\ad_2_luxury_showcase.png"

MESSAGE = """This is what luxury looks like in the Rio Grande Valley. \U0001f3e0\u2728

High ceilings. Open concept. Premium finishes. The kind of home that makes every day feel like a vacation.

The RGV luxury market has grown significantly \u2014 and buyers who move now are locking in real value before prices climb further.

\U0001f511 Luxury residential listings available now
\U0001f4ca RGV luxury inventory is limited \u2014 serious buyers act first
\U0001f4bc Juan Elizondo \u2014 RE/MAX Elite \u2014 your luxury RGV specialist

Ready to tour? Let\u2019s schedule a showing.

#LuxuryRealEstate #RGVHomes #RioGrandeValley"""

with sync_playwright() as p:
    print("[1] Launching browser (Mario's profile)...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=MARIO_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("[2] Loading Facebook (dismissing any Chromium restore popup)...")
    # Dismiss "Restore pages?" Chromium popup by forcing fresh navigation
    try:
        page.keyboard.press("Escape")
        time.sleep(1)
    except:
        pass
    page.goto("https://www.facebook.com/")
    time.sleep(4)

    # Handle "Go to Feed" if it lands on content-unavailable page
    try:
        btn = page.locator("div[role='button']:has-text('Go to Feed'), a:has-text('Go to Feed')").first
        if btn.is_visible():
            print("    [INFO] Hitting 'Go to Feed' on FB homepage...")
            btn.click()
            time.sleep(3)
    except:
        pass

    # Safety check — make sure we're logged in
    if "login" in page.url.lower() or page.query_selector("[name='email']"):
        print("[ERROR] Not logged in. Run reauth_mario_facebook.py first.")
        ctx.close()
        sys.exit(1)
    print(f"    Feed loaded: {page.url}")

    print("[3] Navigating to Juan's RE/MAX page...")
    page.goto(PAGE_URL)
    time.sleep(5)
    print(f"    URL: {page.url}")

    # Handle "Go to Feed" on Juan's page (content unavailable = not in admin mode yet)
    try:
        btn = page.locator("div[role='button']:has-text('Go to Feed'), a:has-text('Go to Feed')").first
        if btn.is_visible():
            print("    [INFO] Juan page shows 'content unavailable' — clicking Go to Feed then navigating via Pages...")
            btn.click()
            time.sleep(3)
    except:
        pass

    # Switch to Page profile via account switcher dropdown
    print("[4] Switching to Juan Elizondo RE/MAX page profile...")
    switched = False

    # Step 1: Click the profile/account switcher in top nav
    for profile_sel in [
        "[aria-label='Your profile']",
        "[aria-label='Account']",
        "[data-testid='blue_bar_profile_link']",
    ]:
        try:
            btn = page.query_selector(profile_sel)
            if btn and btn.is_visible():
                btn.click()
                print(f"    Clicked profile menu: {profile_sel}")
                time.sleep(2)
                break
        except:
            pass

    # Step 2: Look for Juan's page in the dropdown
    for page_sel in [
        "span:has-text('Juan Elizondo')",
        "span:has-text('RE/MAX')",
        "[role='menuitem']:has-text('Juan')",
        "div[role='button']:has-text('Juan Elizondo')",
        "a:has-text('Juan Elizondo')",
    ]:
        try:
            el = page.locator(page_sel).first
            if el.is_visible():
                el.click()
                print(f"    Switched to page via: {page_sel}")
                time.sleep(4)
                switched = True
                break
        except:
            pass

    if not switched:
        # Fallback: navigate to Pages feed to access Juan's page as admin
        print("    [FALLBACK] Navigating to Pages feed to switch to admin mode...")
        page.goto("https://www.facebook.com/pages/feed")
        time.sleep(4)
        print(f"    Pages feed URL: {page.url}")
        for sel in [
            "a:has-text('Juan Elizondo')",
            "span:has-text('Juan Elizondo')",
            "div[role='button']:has-text('Juan Elizondo')",
            "a[href*='JuanElizondoRemax']",
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.click()
                    time.sleep(4)
                    switched = True
                    print(f"    [OK] Opened page via Pages feed: {sel}")
                    break
            except:
                pass

        if not switched:
            # Last resort: go directly to the page URL (admin context from pages/feed)
            page.goto(PAGE_URL)
            time.sleep(4)
            switched = True
            print("    [OK] Navigated directly to page URL after Pages feed")

    print(f"    URL after switch: {page.url}")

    # After switching, we land on the page we manage — use that URL, don't force-navigate
    current_url = page.url
    print(f"[5] Now acting as page: {current_url}")
    # If we landed on the home feed, navigate to the page
    if current_url in ["https://www.facebook.com/", "https://www.facebook.com"]:
        print("    Still on home feed — navigating to page URL...")
        page.goto(PAGE_URL)
        time.sleep(5)
        print(f"    Page URL: {page.url}")
    else:
        print("    [OK] Already on a page — using this context")

    print("[6] Scrolling to composer...")
    try:
        page.wait_for_load_state("domcontentloaded", timeout=8000)
    except:
        time.sleep(3)
    time.sleep(2)
    try:
        page.evaluate("window.scrollBy(0, 400)")
    except:
        pass
    time.sleep(2)

    print("[7] Opening composer...")
    composer_opened = False
    for sel in [
        "div[role='button']:has-text('Create post')",
        "[aria-label='Create post']",
        "div[role='button']:has-text(\"What\u2019s on your mind\")",  # curly apostrophe
        "div[role='button']:has-text(\"What's on your mind\")",       # straight apostrophe
        "[aria-label*=\"What's on your mind\"]",
        "div[role='button']:has-text('Write something')",
        "div[role='button']:has-text('Write post')",
        "div[role='button']:has-text('What')",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                time.sleep(2)
                print(f"    [OK] Opened: {sel}")
                composer_opened = True
                break
        except:
            pass

    if not composer_opened:
        print("    [ERROR] Composer not found — check if Switch succeeded")
        ctx.close()
        sys.exit(1)

    try:
        page.wait_for_selector("[role='dialog']", timeout=5000)
        print("    [OK] Dialog open")
    except:
        print("    [WARNING] No dialog — continuing")

    print("[8] Uploading image...")
    uploaded = False
    for sel in [
        "[role='dialog'] [aria-label='Photo/video']",
        "[aria-label='Photo/video']",
    ]:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=5000)
            with page.expect_file_chooser(timeout=6000) as fc_info:
                btn.click()
            fc_info.value.set_files(IMAGE_PATH)
            time.sleep(5)
            print(f"    [OK] Uploaded via {sel}")
            uploaded = True
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    if not uploaded:
        print("    [ERROR] Upload failed")
        ctx.close()
        sys.exit(1)

    print("[9] Typing message...")
    typed = False
    for sel in [
        "[role='dialog'] div[role='textbox']",
        "[role='dialog'] [contenteditable='true']",
    ]:
        try:
            el = page.locator(sel).first
            el.wait_for(state="visible", timeout=6000)
            el.click()
            time.sleep(0.5)
            el.press_sequentially(MESSAGE, delay=5)
            print("    [OK] Message typed")
            typed = True
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    if not typed:
        print("    [ERROR] Could not type message")
        ctx.close()
        sys.exit(1)

    # Dismiss hashtag autocomplete before clicking
    try:
        page.keyboard.press("Escape")
        time.sleep(1)
    except: pass

    print("[10] Clicking Next...")
    for sel in [
        "[role='dialog'] [aria-label='Next'][role='button']",
        "[role='dialog'] div[role='button']:has-text('Next')",
    ]:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=5000)
            btn.click()
            print(f"    [OK] Clicked Next: {sel}")
            break
        except Exception as e:
            print(f"    {sel}: {e}")

    print("    Waiting for second screen...")
    time.sleep(5)

    print("[11] Clicking final Post button...")
    posted = False
    for sel in [
        "[role='dialog'] [aria-label='Post'][role='button']",
        "[role='dialog'] div[role='button']:has-text('Post')",
        "div[role='button']:has-text('Post')",
        "[aria-label='Post']",
    ]:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=6000)
            btn.click()
            print(f"    [OK] Posted via: {sel}")
            posted = True
            time.sleep(4)
            break
        except Exception as e:
            print(f"    {sel}: {e}")

    # Dismiss post-publish popups ("Speak With People Directly", etc.)
    time.sleep(2)
    for dismiss_sel in [
        "div[role='button']:has-text('Not now')",
        "[aria-label='Not now']",
        "div[role='button']:has-text('Close')",
        "[aria-label='Close']",
    ]:
        try:
            btn = page.locator(dismiss_sel).first
            if btn.is_visible():
                btn.click()
                print(f"    [OK] Dismissed popup: {dismiss_sel}")
                time.sleep(2)
                break
        except: pass

    if posted:
        print("\n[SUCCESS] Juan Elizondo Ad #2 (Luxury Showcase) posted!")
    else:
        print("\n[ERROR] Post button not found")

    time.sleep(4)
    ctx.close()
