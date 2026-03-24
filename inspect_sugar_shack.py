"""Quick inspector — Sugar Shack page with sniffer profile"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL = "https://www.facebook.com/profile.php?id=61557735298128"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=AUTH_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    try: page.keyboard.press("Escape")
    except: pass

    page.goto("https://www.facebook.com/")
    time.sleep(4)
    page.goto(PAGE_URL)
    time.sleep(5)
    print(f"URL: {page.url}")

    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except: time.sleep(3)

    try: page.evaluate("window.scrollBy(0, 300)")
    except: pass
    time.sleep(2)

    print("\nVisible buttons:")
    buttons = page.query_selector_all("div[role='button'], button, [role='button'], [contenteditable='true']")
    found = []
    for btn in buttons:
        try:
            if btn.is_visible():
                text = btn.inner_text().strip()[:80]
                aria = btn.get_attribute("aria-label") or ""
                if text or aria:
                    found.append(f"  TEXT='{text[:60]}' | ARIA='{aria[:50]}'")
        except: pass

    for f in found[:50]:
        print(f)

    out = os.path.join(os.path.dirname(__file__), "sugar_shack_buttons.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        for line in found:
            f.write(line + "\n")
    print(f"\nSaved: {out}")
    time.sleep(10)
    ctx.close()
