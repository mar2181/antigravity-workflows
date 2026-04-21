#!/usr/bin/env python3
import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

PROFILE_DIR = str(Path(r"C:/Users/mario/.gemini/antigravity/tools/execution/facebook_mario_profile"))
SCRIPT_DIR = Path(r"C:/Users/mario/.gemini/antigravity/tools/execution")
PAGE_URL = "https://www.facebook.com/profile.php?id=1003933732800661"

async def verify():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False,
            args=["--start-maximized"], no_viewport=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("Navigating to Optimum Clinic page...")
        await page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=str(SCRIPT_DIR / "optimum_verify_feed.png"))
        print("Screenshot saved: optimum_verify_feed.png")
        await ctx.close()

asyncio.run(verify())
