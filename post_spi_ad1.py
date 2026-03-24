"""Post SPI Fun Rentals Ad #1 - Urgency Play"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL = "https://www.facebook.com/spifunrentals"
IMAGE_PATH = r"C:\Users\mario\OneDrive\Documents\spi-fun-rentals-research\spi_ad_images\ad_1_urgency_play.png"

MESSAGE = """SPRING BREAK ALERT: 15% OFF THIS WEEK ONLY

Your spring break crew is about to have the BEST day on South Padre Island.

Rent a golf cart, slingshot, or scooter from SPI Fun Rentals and get 15% off every rental this week. But hurry - these deals are going FAST during peak season!

Book now: (956) 761-9999
1314 Padre Blvd #A, South Padre Island

#SpringBreak #SouthPadreIsland #FunRentals"""

with sync_playwright() as p:
    print("[1] Launching browser...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=AUTH_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Step 1: personal feed first
    print("[2] Personal feed...")
    page.goto("https://www.facebook.com/")
    time.sleep(3)

    # Step 2: navigate to SPI page
    print("[3] Navigating to SPI Fun Rentals...")
    page.goto(PAGE_URL)
    time.sleep(5)

    # Step 3: click the sidebar/banner Switch button to OPEN the switch dialog
    print("[4] Clicking Switch button to open dialog...")
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

    # Step 4: click the blue "Switch" button INSIDE the dialog
    print("[5] Clicking blue Switch button inside the dialog...")
    try:
        switch_in_dialog = page.locator("[role='dialog'] div[role='button']:has-text('Switch')").first
        switch_in_dialog.wait_for(state="visible", timeout=5000)
        switch_in_dialog.click()
        print("    [OK] Clicked Switch inside dialog")
        time.sleep(4)
    except Exception as e:
        print(f"    [WARNING] Dialog Switch not found: {e}")
        try:
            btn = page.locator("button:has-text('Switch')").first
            btn.wait_for(state="visible", timeout=3000)
            btn.click()
            print("    [OK] Fallback Switch clicked")
            time.sleep(4)
        except Exception as e2:
            print(f"    [WARNING] Fallback also failed: {e2}")

    print(f"    URL after switch: {page.url}")

    # Step 5: scroll down to expose composer
    print("[6] Scrolling to composer area...")
    page.evaluate("window.scrollBy(0, 400)")
    time.sleep(2)

    # Step 6: click Create post
    print("[7] Opening post composer...")
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
                print(f"    [OK] Opened composer: {sel}")
                composer_opened = True
                break
        except:
            pass

    if not composer_opened:
        print("    [ERROR] Could not find composer button")
        ctx.close()
        sys.exit(1)

    try:
        page.wait_for_selector("[role='dialog']", timeout=5000)
        print("    [OK] Composer dialog open")
    except:
        print("    [WARNING] No dialog detected")

    # Step 7: upload image
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
            print(f"    [OK] Image uploaded via {sel}")
            uploaded = True
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    if not uploaded:
        print("    [ERROR] Image upload failed")
        ctx.close()
        sys.exit(1)

    # Step 8: type message
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
            time.sleep(0.5)
            print("    [OK] Message typed")
            typed = True
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    if not typed:
        print("    [ERROR] Could not type message")
        ctx.close()
        sys.exit(1)

    # Step 9: click Post
    print("[10] Clicking Post button...")
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
                    print("    [OK] Final Post button clicked")
                except:
                    pass
            posted = True
            break
        except Exception as e:
            print(f"    [{sel}] failed: {e}")

    if posted:
        print("\n[SUCCESS] Ad #1 posted to SPI Fun Rentals!")
    else:
        print("\n[ERROR] Could not find Post button")

    time.sleep(4)
    ctx.close()
