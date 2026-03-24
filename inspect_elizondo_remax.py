"""Quick inspector — navigate to ElizondoReMax after profile switch, dump all buttons"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

MARIO_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_mario_profile")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=MARIO_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    try: page.keyboard.press("Escape")
    except: pass

    page.goto("https://www.facebook.com/")
    time.sleep(4)

    # Go to JuanElizondoRemax to trigger the content-unavailable
    page.goto("https://www.facebook.com/JuanElizondoRemax/")
    time.sleep(4)

    # Click Go to Feed if present
    try:
        btn = page.locator("div[role='button']:has-text('Go to Feed'), a:has-text('Go to Feed')").first
        if btn.is_visible():
            btn.click()
            print("Clicked Go to Feed")
            time.sleep(3)
    except: pass

    # Click profile switcher
    try:
        btn = page.query_selector("[aria-label='Your profile']")
        if btn and btn.is_visible():
            btn.click()
            print("Clicked profile menu")
            time.sleep(2)
    except: pass

    # Click RE/MAX in dropdown
    try:
        el = page.locator("span:has-text('RE/MAX')").first
        if el.is_visible():
            el.click()
            print("Switched to RE/MAX page")
            time.sleep(5)
    except: pass

    print(f"\nCurrent URL: {page.url}")
    print("\nScrolling...")
    try: page.evaluate("window.scrollBy(0, 300)")
    except: pass
    time.sleep(2)

    print("\nAll visible buttons/interactive elements:")
    buttons = page.query_selector_all("div[role='button'], button, [role='button'], [contenteditable='true']")
    found = []
    for btn in buttons:
        try:
            if btn.is_visible():
                text = btn.inner_text().strip()[:100]
                aria = btn.get_attribute("aria-label") or ""
                ph = btn.get_attribute("placeholder") or ""
                if text or aria or ph:
                    found.append(f"  TEXT='{text[:60]}' | ARIA='{aria[:60]}' | PH='{ph}'")
        except: pass

    for f in found[:60]:
        print(f)

    out = os.path.join(os.path.dirname(__file__), "elizondo_remax_buttons.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        for line in found:
            f.write(line + "\n")
    print(f"\nSaved to: {out}")

    input("\nPress Enter to close browser...")
    ctx.close()
