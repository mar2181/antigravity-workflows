#!/usr/bin/env python3
"""Open Facebook, navigate to Optimum Clinic, open composer, click Next, 
   then dump all visible buttons in Post settings panel to find the right selector."""
import asyncio, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

PROFILE_DIR = str(Path(r"C:/Users/mario/.gemini/antigravity/tools/execution/facebook_mario_profile"))
SCRIPT_DIR = Path(r"C:/Users/mario/.gemini/antigravity/tools/execution")
PAGE_URL = "https://www.facebook.com/profile.php?id=1003933732800661"

TEXT = "Test debug post - finding selectors"

async def run():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False,
            args=["--start-maximized"], no_viewport=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Open composer
        for sel in ["div[role='button']:has-text('Create post')", "[aria-label='Create post']", "div[aria-label='Create post']"]:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    print(f"Opened composer via: {sel}")
                    break
            except Exception:
                continue
        await page.wait_for_timeout(3000)

        # Type text
        try:
            textbox = page.locator("[role='dialog'] [contenteditable='true']").first
            await textbox.click()
            await textbox.fill(TEXT)
            print("Filled text")
        except Exception as e:
            print(f"Could not fill text: {e}")
        await page.wait_for_timeout(1000)

        # Click Next
        try:
            nxt = page.locator("[role='dialog'] div[role='button']:has-text('Next')").first
            await nxt.wait_for(state="visible", timeout=5000)
            await nxt.click()
            print("Clicked Next")
        except Exception as e:
            print(f"Next button error: {e}")
        await page.wait_for_timeout(3000)

        await page.screenshot(path=str(SCRIPT_DIR / "debug_post_settings_panel.png"))
        print("Screenshot saved")

        # Dump ALL visible buttons on entire page
        all_btns = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('[role="button"], button'));
            return btns
                .filter(b => {
                    const r = b.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                })
                .map(b => ({
                    text: b.textContent.trim().slice(0, 60),
                    aria: b.getAttribute('aria-label') || '',
                    role: b.getAttribute('role') || b.tagName,
                    class: b.className.slice(0, 80),
                    inDialog: !!b.closest('[role="dialog"]'),
                    tagName: b.tagName
                }));
        }""")
        print(f"\n=== ALL VISIBLE BUTTONS ({len(all_btns)}) ===")
        for b in all_btns:
            print(f"  tag={b['tagName']} role={b['role']} text='{b['text']}' aria='{b['aria']}' inDialog={b['inDialog']}")

        # Close without posting
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Escape")
        await ctx.close()

asyncio.run(run())
