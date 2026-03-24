"""Post Sugar Shack Ad #2 — Souvenir Play
Auth: Yehuda's account via facebook_sniffer_profile
Page: https://www.facebook.com/profile.php?id=61557735298128
"""
import sys, os, time, json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
from datetime import datetime

AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL = "https://www.facebook.com/profile.php?id=61557735298128"
IMAGE_PATH = r"C:\Users\mario\sugar_shack_ad_images\ad_2_souvenir_play.png"
MANIFEST_PATH = r"C:\Users\mario\.gemini\antigravity\scratch\skills\sugar-shack-facebook\ads_manifest.json"

MESSAGE = """Because "I got you a candy from a gas station" isn\u2019t a souvenir. \U0001f381

Spring break is flying by, and you\u2019re about to go home empty-handed
with no actual PROOF you were here.

Here\u2019s what you DO instead:

Stop by The Sugar Shack, grab a cute bag of hand-picked local treats,
and suddenly you\u2019ve got:
\u2192 A gift everyone actually WANTS
\u2192 A perfect flat-lay for your Instagram story
\u2192 Proof you thought of people back home
\u2192 South Padre Island credentials (you found the LOCAL spot)

Bulk candy = budget-friendly. Custom bags = personalized gifts.
Local vibes = authentic.

This is how you leave the island remembered.

VISIT THE SUGAR SHACK | 910 Padre Blvd

Open 9 AM daily | (956) 524-8009

#SouthPadreIsland #SpringBreak #LocalLove"""

def mark_posted():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    for ad in manifest:
        if ad["id"] == 2:
            ad["posted"] = True
            ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("    [OK] Manifest updated")

with sync_playwright() as p:
    print("[1] Launching browser (Yehuda's profile)...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=AUTH_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("[2] Personal feed...")
    page.goto("https://www.facebook.com/")
    time.sleep(3)

    print("[3] Navigating to Sugar Shack page...")
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
        print("\n[SUCCESS] Sugar Shack Ad #2 (Souvenir Play) posted!")
    else:
        print("\n[ERROR] Post button not found")

    time.sleep(4)
    ctx.close()
