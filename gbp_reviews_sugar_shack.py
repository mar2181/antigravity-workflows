#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gbp_reviews_sugar_shack.py — Open Sugar Shack GBP reviews page (Yehuda account), screenshot negative reviews."""

import asyncio, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_sniffer_profile")
BUSINESS_ID = "13038061471302579308"
# Direct URL to the reviews management page
REVIEWS_URL = f"https://business.google.com/reviews?hrid={BUSINESS_ID}"
# Fallback: locations list
LOCATIONS_URL = "https://business.google.com/locations"

def log(msg): print(f"[gbp_reviews_ss] {msg}", flush=True)


async def open_reviews():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            log("Navigating to GBP locations list...")
            await page.goto(LOCATIONS_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_rev_step1_locations.png"))
            log("Step 1 screenshot saved.")

            # Try to click into Sugar Shack management panel
            log("Looking for Sugar Shack row to open dashboard...")
            clicked = await page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll('tr, [role="row"]'));
                for (let row of rows) {
                    if (row.textContent.toUpperCase().includes('SUGAR SHACK')) {
                        // Try to find a manage/view link
                        const links = row.querySelectorAll('a, button, [role="button"]');
                        for (let l of links) {
                            const txt = (l.textContent || '').trim().toLowerCase();
                            const aria = (l.getAttribute('aria-label') || '').toLowerCase();
                            if (txt.includes('manage') || aria.includes('manage') || txt === '') {
                                l.click();
                                return txt || aria || 'clicked first link in row';
                            }
                        }
                        // Click anywhere on the row text
                        row.click();
                        return 'row clicked';
                    }
                }
                return null;
            }""")
            log(f"Row click result: {clicked}")
            await page.wait_for_timeout(4000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_rev_step2_dashboard.png"))
            log(f"Step 2 screenshot — current URL: {page.url}")

            # Try navigating directly to reviews tab
            log("Attempting direct reviews URL...")
            try:
                await page.goto(REVIEWS_URL, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)
            except Exception:
                pass

            # If still on locations, try searching for reviews link
            current_url = page.url
            log(f"Current URL: {current_url}")
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_rev_step3_reviews_page.png"))
            log("Step 3 screenshot saved.")

            # Scroll down to see all reviews
            await page.evaluate("window.scrollTo(0, 500)")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_rev_step4_scrolled.png"), full_page=True)
            log("Step 4 (full page) screenshot saved.")

            log("✅ Done. Check screenshots:")
            log(f"  {SCRIPT_DIR}/gbp_rev_step1_locations.png")
            log(f"  {SCRIPT_DIR}/gbp_rev_step2_dashboard.png")
            log(f"  {SCRIPT_DIR}/gbp_rev_step3_reviews_page.png")
            log(f"  {SCRIPT_DIR}/gbp_rev_step4_scrolled.png")
            log("Browser left open — navigate to Reviews section manually if needed.")

            # Keep browser open for manual navigation
            input("\n>>> Browser is open. Navigate to Reviews, then press ENTER here to close.\n")

        except Exception as e:
            log(f"❌ Error: {e}")
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_rev_error.png"))
        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(open_reviews())
