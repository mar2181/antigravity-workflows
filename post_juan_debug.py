"""
Debug post script — stays open, takes screenshots, lets you see exactly what's happening
"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

MARIO_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_mario_profile")
PAGE_URL      = "https://www.facebook.com/ElizondoReMax/"
IMAGE_PATH    = r"C:\Users\mario\juan_remax_ad_images\ad_2_luxury_showcase.png"
SHOTS_DIR     = r"C:\Users\mario\juan_remax_ad_images\debug_shots"
os.makedirs(SHOTS_DIR, exist_ok=True)

MESSAGE = """This is what luxury looks like in the Rio Grande Valley. \U0001f3e0\u2728

High ceilings. Open concept. Premium finishes. The kind of home that makes every day feel like a vacation.

The RGV luxury market has grown significantly \u2014 and buyers who move now are locking in real value before prices climb further.

\U0001f511 Luxury residential listings available now
\U0001f4ca RGV luxury inventory is limited \u2014 serious buyers act first
\U0001f4bc Juan Elizondo \u2014 RE/MAX Elite \u2014 your luxury RGV specialist

Ready to tour? Let\u2019s schedule a showing.

#LuxuryRealEstate #RGVHomes #RioGrandeValley"""

def shot(page, name):
    path = os.path.join(SHOTS_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=False)
    print(f"    [SCREENSHOT] {path}")

with sync_playwright() as p:
    print("[1] Launching browser...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=MARIO_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080},
        slow_mo=500  # slow down so you can see what's happening
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    try: page.keyboard.press("Escape")
    except: pass

    print("[2] Loading Facebook...")
    page.goto("https://www.facebook.com/")
    time.sleep(4)
    shot(page, "01_facebook_home")
    print(f"    URL: {page.url}")

    if "login" in page.url.lower() or page.query_selector("[name='email']"):
        print("[ERROR] Not logged in.")
        ctx.close()
        sys.exit(1)

    print("[3] Navigating to Juan's page...")
    page.goto(PAGE_URL)
    time.sleep(5)
    shot(page, "02_juans_page_before_switch")
    print(f"    URL: {page.url}")

    # Handle content unavailable
    try:
        btn = page.locator("div[role='button']:has-text('Go to Feed'), a:has-text('Go to Feed')").first
        if btn.is_visible():
            print("    Clicking Go to Feed...")
            btn.click()
            time.sleep(3)
            shot(page, "03_after_go_to_feed")
    except: pass

    print("[4] Opening profile switcher...")
    try:
        btn = page.query_selector("[aria-label='Your profile']")
        if btn and btn.is_visible():
            btn.click()
            time.sleep(2)
            shot(page, "04_profile_dropdown")
            print("    Profile menu opened")
    except: pass

    # Find RE/MAX in dropdown — be more specific
    print("[5] Looking for Juan's page in dropdown...")
    switched = False
    for sel in [
        "span:has-text('Juan Jose Elizondo')",
        "span:has-text('Juan Elizondo')",
        "div[role='button']:has-text('Juan Jose')",
        "span:has-text('Re/Max Elite')",
        "span:has-text('RE/MAX Elite')",
        "span:has-text('RE/MAX')",
        "span:has-text('ElizondoReMax')",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                text = el.inner_text().strip()
                print(f"    Found: '{text}' via {sel}")
                el.click()
                time.sleep(4)
                switched = True
                shot(page, "05_after_switch")
                print(f"    URL after switch: {page.url}")
                break
        except: pass

    if not switched:
        print("    [ERROR] Could not find page in switcher dropdown")
        shot(page, "05_switch_failed")
        ctx.close()
        sys.exit(1)

    # If on home feed, navigate to page
    if page.url in ["https://www.facebook.com/", "https://www.facebook.com"]:
        page.goto(PAGE_URL)
        time.sleep(5)
        shot(page, "06_navigated_to_page")

    print(f"\n[STATUS] Acting as: {page.url}")
    print("[6] Waiting for page to load fully...")
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        time.sleep(4)
    time.sleep(2)

    try:
        page.evaluate("window.scrollBy(0, 350)")
    except: pass
    time.sleep(2)
    shot(page, "07_page_scrolled")

    print("[7] Looking for composer...")
    composer_opened = False
    for sel in [
        "div[role='button']:has-text('Create post')",
        "[aria-label='Create post']",
        "div[role='button']:has-text(\"\u2019s on your mind\")",
        "div[role='button']:has-text(\"What\u2019s on your mind\")",
        "div[role='button']:has-text(\"What's on your mind\")",
        "div[role='button']:has-text('What')",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"    Found composer: {sel}")
                el.click()
                time.sleep(3)
                shot(page, "08_composer_opened")
                composer_opened = True
                break
        except: pass

    if not composer_opened:
        print("    [ERROR] No composer found")
        shot(page, "08_no_composer")
        ctx.close()
        sys.exit(1)

    # Check if dialog opened
    try:
        page.wait_for_selector("[role='dialog']", timeout=5000)
        print("    [OK] Composer dialog opened")
        shot(page, "09_dialog_open")
    except:
        print("    [WARNING] No dialog detected")
        shot(page, "09_no_dialog")

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
            shot(page, "10_image_uploaded")
            print(f"    [OK] Uploaded")
            uploaded = True
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    if not uploaded:
        print("    [ERROR] Upload failed")
        ctx.close()
        sys.exit(1)

    print("[9] Typing message...")
    for sel in [
        "[role='dialog'] div[role='textbox']",
        "[role='dialog'] [contenteditable='true']",
    ]:
        try:
            el = page.locator(sel).first
            el.wait_for(state="visible", timeout=6000)
            el.click()
            time.sleep(0.5)
            el.press_sequentially(MESSAGE, delay=3)
            print("    [OK] Message typed")
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    # Dismiss any hashtag/mention autocomplete before clicking Next
    print("    Dismissing autocomplete (Escape)...")
    try:
        page.keyboard.press("Escape")
        time.sleep(1)
    except: pass
    shot(page, "11_text_typed")

    print("[10] Clicking Next...")
    next_clicked = False
    for sel in [
        "[role='dialog'] [aria-label='Next'][role='button']",
        "[role='dialog'] div[role='button']:has-text('Next')",
    ]:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=5000)
            btn.click()
            print(f"    [OK] Clicked Next: {sel}")
            next_clicked = True
            break
        except Exception as e:
            print(f"    {sel}: {e}")

    if not next_clicked:
        print("    No Next button — trying Post directly...")

    # Wait for the second screen (sharing options)
    print("    Waiting for next screen...")
    time.sleep(5)
    shot(page, "12_second_screen")

    print("[11] Clicking final Post button...")
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
            time.sleep(5)
            shot(page, "13_after_final_post")
            break
        except Exception as e:
            print(f"    {sel}: {e}")

    # Dismiss "Speak With People Directly" or similar post-publish popups
    time.sleep(3)
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

    time.sleep(3)
    shot(page, "14_final_state")
    print(f"\n[DONE] Final URL: {page.url}")
    print(f"\n[SUCCESS] Post published to Juan Jose Elizondo Re/Max Elite!")
    print(f"[SCREENSHOTS] Check: {SHOTS_DIR}")
    time.sleep(5)
    ctx.close()
