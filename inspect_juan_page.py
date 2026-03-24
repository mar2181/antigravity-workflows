"""
Inspect Juan Elizondo RE/MAX page using Mario's profile
Finds all buttons/interactive elements to update composer selectors
"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

MARIO_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_mario_profile")
PAGE_URL = "https://www.facebook.com/JuanElizondoRemax/"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=MARIO_PROFILE,
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("[1] Loading Facebook...")
    page.goto("https://www.facebook.com/")
    time.sleep(3)

    if "login" in page.url.lower() or page.query_selector("[name='email']"):
        print("[ERROR] Not logged in.")
        ctx.close()
        sys.exit(1)

    print("[2] Navigating to Juan's page...")
    page.goto(PAGE_URL)
    time.sleep(5)
    print(f"    URL: {page.url}")

    print("[3] Scrolling slightly...")
    try:
        page.evaluate("window.scrollBy(0, 300)")
    except:
        pass
    time.sleep(2)

    print("\n[4] All role='button' elements visible on page:")
    buttons = page.query_selector_all("div[role='button'], button, [role='button']")
    found = []
    for btn in buttons:
        try:
            if btn.is_visible():
                text = btn.inner_text().strip()[:80]
                aria = btn.get_attribute("aria-label") or ""
                placeholder = btn.get_attribute("placeholder") or ""
                if text or aria:
                    found.append(f"  text='{text}' | aria='{aria}' | placeholder='{placeholder}'")
        except:
            pass

    for f in found[:50]:
        print(f)

    output_path = os.path.join(os.path.dirname(__file__), "juan_page_buttons.txt")
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(f"URL: {page.url}\n\n")
        out.write("BUTTONS:\n")
        for f in found:
            out.write(f + "\n")

    print(f"\n[SAVED] {output_path}")
    print("\n[WAITING] Press Ctrl+C or close browser to exit...")
    time.sleep(15)
    ctx.close()
