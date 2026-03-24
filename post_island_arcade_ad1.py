"""Post Island Arcade Ad #1 — Island Arrival (run immediately)"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL = "https://www.facebook.com/profile.php?id=100090911360621"
IMAGE_PATH = r"C:\Users\mario\island_arcade_ad_images\ad_1_island_arrival.png"

MESSAGE = """Spring break officially starts the moment you walk through our doors.

Island Arcade is South Padre Island's most epic entertainment destination — 100+ arcade games, world-class VR, racing simulators, claw machines, and MORE. All under one roof.

Whether you're 8 or 28, you're about to have the best hour of your trip.

🎮 100+ games
🏆 Compete. Win. Repeat.
🍕 Pizza, nachos & ice cream inside
📍 2311 Padre Blvd, South Padre Island

Open late. Come in.

#IslandArcade #SpringBreak #SouthPadreIsland"""

with sync_playwright() as p:
    print("[1] Launching browser...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=AUTH_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("[2] Personal feed...")
    page.goto("https://www.facebook.com/")
    time.sleep(3)

    print("[3] Navigating to Island Arcade page...")
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
        switch_in_dialog = page.locator("[role='dialog'] div[role='button']:has-text('Switch')").first
        switch_in_dialog.wait_for(state="visible", timeout=5000)
        switch_in_dialog.click()
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
        page.wait_for_load_state("networkidle", timeout=8000)
    except:
        time.sleep(5)

    print("[6] Scrolling to composer...")
    try:
        page.evaluate("window.scrollBy(0, 400)")
    except:
        time.sleep(1)
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

    print("[10] Clicking Post...")
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
            time.sleep(3)
            print(f"    [OK] Clicked: {sel}")
            if "Next" in sel:
                try:
                    final = page.locator("[role='dialog'] [aria-label='Post'][role='button']").first
                    final.wait_for(state="visible", timeout=5000)
                    final.click()
                    time.sleep(3)
                    print("    [OK] Final Post clicked")
                except:
                    pass
            posted = True
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    if posted:
        print("\n[SUCCESS] Ad #1 posted to Island Arcade!")
    else:
        print("\n[ERROR] Post button not found")

    time.sleep(4)
    ctx.close()
