"""
Post SPI Fun Rentals Ad #3 — FOMO Slingshot
Auth: Yehuda's account (quepadre@live.com) via facebook_sniffer_profile
Page: https://www.facebook.com/spifunrentals
"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL     = "https://www.facebook.com/spifunrentals"
IMAGE_PATH   = r"C:\Users\mario\OneDrive\Documents\spi-fun-rentals-research\spi_ad_images\ad_3_fomo_slingshot.png"

MESSAGE = """Your friends are already planning this \U0001f525

While you\u2019re still thinking about it, other groups are already booking their slingshot adventures on South Padre Island.

Slingshot rental season is HERE.
\U0001f697 Feel the adrenaline
\U0001f3d6\ufe0f Check out hidden beaches
\U0001f305 Unforgettable views
\U0001f4b0 15% OFF this week for YOU

Don\u2019t be the one saying \u201cI wish I had gone.\u201d
Be the one planning the legend.

\U0001f4de (956) 761-9999 | Book Now

#Slingshot #SpringBreak #SouthPadreIsland"""


with sync_playwright() as p:
    print("[1] Launching browser (Yehuda/sniffer profile)...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=AUTH_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    try: page.keyboard.press("Escape")
    except: pass

    print("[2] Loading Facebook...")
    page.goto("https://www.facebook.com/")
    time.sleep(4)

    if "login" in page.url.lower() or page.query_selector("[name='email']"):
        print("[ERROR] Not logged in. Run reauth_facebook_sniffer.py first.")
        ctx.close()
        sys.exit(1)
    print(f"    Logged in: {page.url}")

    print("[3] Navigating to SPI Fun Rentals page...")
    page.goto(PAGE_URL)
    time.sleep(5)
    print(f"    URL: {page.url}")

    # Switch to SPI Fun Rentals page profile if needed
    print("[4] Checking for Switch button...")
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except:
        time.sleep(3)
    time.sleep(2)

    for sel in ["[aria-label='Switch']", "div[role='button']:has-text('Switch Now')", "div[role='button']:has-text('Switch')"]:
        try:
            btn = page.locator(sel).first
            if btn.is_visible():
                btn.click()
                print(f"    [OK] Clicked Switch: {sel}")
                time.sleep(3)
                for confirm in ["[role='dialog'] div[role='button']:has-text('Switch')", "[role='dialog'] [aria-label='Switch']"]:
                    try:
                        cb = page.locator(confirm).first
                        if cb.is_visible():
                            cb.click()
                            print("    [OK] Switch confirmed")
                            time.sleep(3)
                            break
                    except: pass
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except:
                    time.sleep(4)
                break
        except: pass

    print(f"    URL after switch: {page.url}")

    print("[4b] Scrolling to composer...")
    time.sleep(2)
    try:
        page.evaluate("window.scrollBy(0, 400)")
    except: pass
    time.sleep(2)

    print("[5] Opening composer...")
    composer_opened = False
    for sel in [
        "div[role='button']:has-text('Create post')",
        "[aria-label='Create post']",
        "div[role='button']:has-text(\"\u2019s on your mind\")",
        "div[role='button']:has-text(\"What\u2019s on your mind\")",
        "div[role='button']:has-text(\"What's on your mind\")",
        "div[role='button']:has-text('Write something')",
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
        except: pass

    if not composer_opened:
        print("    [ERROR] Composer not found")
        ctx.close()
        sys.exit(1)

    try:
        page.wait_for_selector("[role='dialog']", timeout=5000)
        print("    [OK] Dialog open")
    except:
        print("    [WARNING] No dialog — continuing")

    print("[6] Uploading image...")
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
            print(f"    [OK] Uploaded")
            uploaded = True
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    if not uploaded:
        print("    [ERROR] Upload failed")
        ctx.close()
        sys.exit(1)

    print("[7] Typing message...")
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

    try:
        page.keyboard.press("Escape")
        time.sleep(1)
    except: pass

    print("[8] Clicking Next...")
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

    print("[9] Clicking final Post button...")
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

    # Dismiss "Speak With People Directly" popup — REQUIRED to finalize post
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
        print("\n[SUCCESS] SPI Fun Rentals Ad #3 (Slingshot) posted!")
    else:
        print("\n[ERROR] Post button not found")

    time.sleep(4)
    ctx.close()
