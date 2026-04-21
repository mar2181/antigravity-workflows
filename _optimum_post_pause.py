#!/usr/bin/env python3
"""Posts to Optimum Clinic Facebook — stops at Post settings and waits for user to click Post."""
import asyncio, sys, time, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(r"C:/Users/mario/.gemini/antigravity/tools/execution")
PROFILE_DIR = str(SCRIPT_DIR / "facebook_mario_profile")
PAGE_URL = "https://www.facebook.com/profile.php?id=1003933732800661"

meta = json.loads((SCRIPT_DIR / "blog_posts/optimum_clinic/2026-03-19_walkin-clinic-pharr-tx_meta.json").read_text(encoding='utf-8'))
TEXT  = meta["fb_copy"]
IMAGE = meta["images"]["hero"]

DONE_FILE = SCRIPT_DIR / "_optimum_pause_done.txt"
if DONE_FILE.exists():
    DONE_FILE.unlink()

async def run():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False,
            args=["--start-maximized"], no_viewport=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        print("[1] Navigating to Optimum Clinic page...")
        await page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        print("[2] Opening composer...")
        for sel in ["div[role='button']:has-text('Create post')", "[aria-label='Create post']", "div:has-text('What\'s on your mind?')"]:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    print(f"    Opened via: {sel}")
                    break
            except Exception:
                continue
        await page.wait_for_timeout(3000)

        print("[3] Filling post text...")
        for sel in ["[role='dialog'] [contenteditable='true']", "[contenteditable='true'][role='textbox']", "div[contenteditable='true']"]:
            try:
                tb = page.locator(sel).first
                await tb.wait_for(state="visible", timeout=5000)
                await tb.click()
                await page.wait_for_timeout(500)
                await tb.fill(TEXT)
                print(f"    Text filled via: {sel}")
                break
            except Exception:
                continue
        await page.wait_for_timeout(1000)

        print("[4] Attaching image...")
        try:
            for sel in ["[aria-label='Photo/video']", "div[role='button']:has-text('Photo/video')"]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        async with page.expect_file_chooser(timeout=5000) as fc_info:
                            await btn.click()
                        fc = await fc_info.value
                        await fc.set_files(IMAGE)
                        print("    Image attached")
                        break
                except Exception:
                    continue
            await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"    Image error: {e}")

        print("[5] Clicking Next...")
        for sel in ["[role='dialog'] div[role='button']:has-text('Next')", "div[role='button']:has-text('Next')"]:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    print(f"    Next clicked via: {sel}")
                    break
            except Exception:
                continue
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(SCRIPT_DIR / "pause_step5_post_settings.png"))

        print("\n" + "="*60)
        print("  BROWSER IS OPEN AT POST SETTINGS.")
        print("  YOU ARE IN CONTROL — click Post and handle any prompts.")
        print(f"  When done, create this file to close the browser:")
        print(f"  {DONE_FILE}")
        print("="*60)

        # Wait up to 10 minutes for done file
        for _ in range(600):
            await asyncio.sleep(1)
            if DONE_FILE.exists():
                print("Done file detected — taking final screenshot...")
                break
        
        await page.screenshot(path=str(SCRIPT_DIR / "pause_step6_after_user.png"))
        print("Final screenshot saved: pause_step6_after_user.png")
        await ctx.close()

asyncio.run(run())
