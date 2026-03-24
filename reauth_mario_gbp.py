#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reauth_mario_gbp.py — Authenticate Mario's Google account for GBP automation
Saves screenshots at each step. Run this, then check the screenshots.
"""

import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_mario_profile")
SCREENSHOT_DIR = SCRIPT_DIR
EMAIL    = "marioelizondo81@gmail.com"
PASSWORD = "Lalaelisan1950."


def ss(name):
    return str(SCREENSHOT_DIR / f"reauth_{name}.png")


async def main():
    from playwright.async_api import async_playwright

    print(f"Profile: {PROFILE_DIR}")
    print(f"Account: {EMAIL}\n")

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--no-first-run",
                ],
                ignore_default_args=["--enable-automation"],
                no_viewport=True,
            )
            print("Using real Chrome")
        except Exception as e:
            print(f"Real Chrome failed ({e}), using Playwright Chromium")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                ignore_default_args=["--enable-automation"],
                no_viewport=True,
            )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = context.pages[0] if context.pages else await context.new_page()

        # Step 1: Go to Google sign-in
        print("Step 1: Navigating to Google accounts...")
        await page.goto("https://accounts.google.com/signin/v2/identifier", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=ss("step1_landingpage"))
        print(f"  Screenshot: reauth_step1_landingpage.png | URL: {page.url}")

        # If already at GBP or Google home, skip login
        if "myaccount" in page.url or "business.google.com" in page.url:
            print("Already logged in!")
        else:
            # Step 2: Enter email
            print("Step 2: Entering email...")
            try:
                email_field = page.locator('input[type="email"]').first
                await email_field.wait_for(timeout=8000)
                await email_field.click()
                await page.wait_for_timeout(500)
                await email_field.type(EMAIL, delay=80)
                await page.wait_for_timeout(500)
                await page.screenshot(path=ss("step2_email_filled"))
                print(f"  Email typed. Screenshot: reauth_step2_email_filled.png")

                # Click Next button
                next_btn = page.locator('button:has-text("Next"), #identifierNext').first
                await next_btn.click()
                print("  Clicked Next")
                await page.wait_for_timeout(5000)
                await page.screenshot(path=ss("step3_after_email_next"))
                print(f"  Screenshot: reauth_step3_after_email_next.png | URL: {page.url}")

            except Exception as e:
                await page.screenshot(path=ss("step2_error"))
                print(f"  ⚠️ Email step error: {e}")
                print(f"  URL: {page.url}")

            # Step 3: Enter password
            print("Step 3: Entering password...")
            try:
                pwd_field = page.locator('input[type="password"]').first
                await pwd_field.wait_for(timeout=12000)
                await pwd_field.click()
                await page.wait_for_timeout(500)
                await pwd_field.type(PASSWORD, delay=80)
                await page.wait_for_timeout(500)
                await page.screenshot(path=ss("step4_password_filled"))
                print(f"  Password typed. Screenshot: reauth_step4_password_filled.png")

                next_btn2 = page.locator('button:has-text("Next"), #passwordNext').first
                await next_btn2.click()
                print("  Clicked Next")
                await page.wait_for_timeout(8000)
                await page.screenshot(path=ss("step5_after_password"))
                print(f"  Screenshot: reauth_step5_after_password.png | URL: {page.url}")

            except Exception as e:
                await page.screenshot(path=ss("step3_password_error"))
                print(f"  ⚠️ Password step error: {e}")
                print(f"  URL: {page.url}")
                print("  Check reauth_step3_password_error.png")

        # Step 4: Navigate to GBP regardless
        print("\nStep 4: Navigating to Google Business Profile...")
        await page.goto("https://business.google.com/locations", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path=ss("step6_gbp_locations"))
        print(f"  Screenshot: reauth_step6_gbp_locations.png | URL: {page.url}")

        content = await page.content()
        if "Custom Designs" in content:
            print("\n✅ SUCCESS — Custom Designs TX is visible!")
            print("   Session saved to gbp_mario_profile/")
            print("   Run: python gbp_post_custom_designs.py")
        elif "business.google.com" in page.url:
            print("\n⚠️ At GBP but Custom Designs TX not visible.")
            print("   Check reauth_step6_gbp_locations.png to see what account is loaded.")
        else:
            print(f"\n⚠️ Not at GBP — current URL: {page.url}")
            print("   May need 2FA or additional verification. Check screenshots.")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
