"""Post Island Candy Ad #1 — Cool Down (SPI heat)
Auth: Mario's account (marioelizondo81@gmail.com) via facebook_mario_profile
Page: https://www.facebook.com/profile.php?id=100090560413893
"""
import sys, os, time, json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
from datetime import datetime

AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_mario_profile")
PAGE_URL = "https://www.facebook.com/profile.php?id=100090560413893"
IMAGE_PATH = r"C:\Users\mario\island_candy_ad_images\ad_1_cool_down.png"
MANIFEST_PATH = r"C:\Users\mario\.gemini\antigravity\scratch\skills\island-candy-facebook\ads_manifest.json"

MESSAGE = """SPI heat is no joke. We've got the cure. \U0001f366

Walk off the beach and into the sweetest spot on the island.

\U0001f368 Homemade ice cream \u2014 made fresh, not from a carton
\U0001f9ca Ice-cold slushies when you need instant relief
\U0001f30a Right inside Island Arcade at 2311 Padre Blvd

Open daily. Your next favorite stop on South Padre Island.

#IslandCandy #SouthPadreIsland #SPI"""

def mark_posted():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    for ad in manifest:
        if ad["id"] == 1:
            ad["posted"] = True
            ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("    [OK] Manifest updated")

with sync_playwright() as p:
    print("[1] Launching browser (Mario's profile)...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=AUTH_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("[2] Personal feed...")
    page.goto("https://www.facebook.com/")
    time.sleep(3)

    print("[3] Navigating to Island Candy page...")
    page.goto(PAGE_URL)
    time.sleep(5)

    print("[4] Clicking Switch to open dialog...")
    for sel in [
        "div[role='button']:has-text('Switch Now')",
        "[aria-label='Switch Now']",
        "div[role='button']:has-text('Switch')",
        "[aria-label='Switch']",
    ]:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                print(f"    Clicked: {sel}")
                time.sleep(3)
                break
        except:
            pass

    print("[5] Clicking blue Switch inside dialog...")
    try:
        sw = page.locator("[role='dialog'] div[role='button']:has-text('Switch')").first
        sw.wait_for(state="visible", timeout=5000)
        sw.click()
        print("    [OK] Dialog Switch clicked")
        time.sleep(4)
    except Exception as e:
        print(f"    [WARNING] {e}")
        try:
            btn = page.locator("button:has-text('Switch')").first
            btn.wait_for(state="visible", timeout=3000)
            btn.click()
            print("    [OK] Fallback Switch clicked")
            time.sleep(4)
        except Exception as e2:
            print(f"    [WARNING] Fallback: {e2}")

    print(f"    URL after switch: {page.url}")
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10000)
    except:
        pass
    time.sleep(5)

    print("[6] Scrolling to composer...")
    page.evaluate("window.scrollBy(0, 400)")
    time.sleep(2)

    print("[7] Opening composer...")
    composer_opened = False
    for sel in [
        "div[role='button']:has-text('Create post')",
        "[aria-label='Create post']",
        "div[role='button']:has-text(\"What's on your mind\")",
        "[aria-label*=\"What's on your mind\"]",
        "div[role='button']:has-text('Write something')",
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
        print("    [ERROR] Composer not found")
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

    try:
        page.keyboard.press("Escape")
        time.sleep(1)
    except:
        pass

    print("[10] Clicking Next / Post...")
    posted = False
    for sel in [
        "[role='dialog'] [aria-label='Post'][role='button']",
        "[role='dialog'] div[role='button']:has-text('Post')",
        "[role='dialog'] [aria-label='Next'][role='button']",
        "[role='dialog'] div[role='button']:has-text('Next')",
    ]:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=5000)
            btn.click()
            print(f"    [OK] Clicked: {sel}")
            time.sleep(3)
            if "Next" in sel:
                try:
                    final = page.locator("[role='dialog'] [aria-label='Post'][role='button']").first
                    final.wait_for(state="visible", timeout=5000)
                    final.click()
                    print("    [OK] Final Post clicked")
                    time.sleep(3)
                except:
                    pass
            posted = True
            break
        except Exception as e:
            print(f"    {sel}: {e}")

    # Dismiss any popups — phone number prompt, notifications, etc.
    time.sleep(3)
    for dismiss_sel in [
        "div[role='button']:has-text('No')",
        "[aria-label='No']",
        "div[role='button']:has-text('Not now')",
        "[aria-label='Not now']",
        "div[role='button']:has-text('Maybe later')",
        "div[role='button']:has-text('Close')",
        "[aria-label='Close']",
    ]:
        try:
            btn = page.locator(dismiss_sel).first
            if btn.is_visible():
                btn.click()
                print(f"    [OK] Dismissed popup: {dismiss_sel}")
                time.sleep(2)
        except:
            pass

    if posted:
        mark_posted()
        print("\n[SUCCESS] Island Candy Ad #1 (Cool Down) posted!")
    else:
        print("\n[ERROR] Post button not found")

    time.sleep(6)
    ctx.close()
