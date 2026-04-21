#!/usr/bin/env python3
import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

PROFILE_DIR = str(Path(r"C:/Users/mario/.gemini/antigravity/tools/execution/facebook_mario_profile"))
SCRIPT_DIR = Path(r"C:/Users/mario/.gemini/antigravity/tools/execution")

async def verify():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False,
            args=["--start-maximized"], no_viewport=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        
        # Go to the page
        await page.goto("https://www.facebook.com/profile.php?id=1003933732800661", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        
        # Click the Posts tab
        try:
            posts_tab = page.locator("a[href*='sk=timeline'], a:has-text('Posts')").first
            await posts_tab.click()
            await page.wait_for_timeout(3000)
            print("Clicked Posts tab")
        except Exception as e:
            print(f"Could not click Posts tab: {e}")
        
        await page.screenshot(path=str(SCRIPT_DIR / "optimum_page_posts.png"))
        
        # Scroll down to see posts
        await page.evaluate("window.scrollTo(0, 600)")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(SCRIPT_DIR / "optimum_page_scrolled.png"))
        
        await ctx.close()

asyncio.run(verify())
