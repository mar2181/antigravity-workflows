#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""get_supabase_service_key.py — Log into Supabase and extract service_role key."""

import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_REF = "sctefvytgcmwhuopeqbd"
PROFILE_DIR = str(Path(__file__).parent / "gbp_mario_profile")
EMAIL = "marioelizondo81@gmail.com"
PASSWORD = "Lalaelisan1950."


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False,
            args=["--start-maximized"], no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Go to login page
        print("Navigating to Supabase login...")
        await page.goto("https://supabase.com/dashboard/sign-in", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # Fill credentials
        try:
            await page.fill('input[name="email"]', EMAIL)
            await page.fill('input[name="password"]', PASSWORD)
            await page.click('button[type="submit"]')
            print("Submitted login form")
            await page.wait_for_timeout(5000)
            await page.screenshot(path=str(Path(__file__).parent / "supabase_login.png"))
        except Exception as e:
            print(f"Login form error: {e}")
            await page.screenshot(path=str(Path(__file__).parent / "supabase_login_error.png"))

        # Navigate to project API settings
        api_url = f"https://supabase.com/dashboard/project/{PROJECT_REF}/settings/api"
        print(f"Navigating to {api_url}")
        await page.goto(api_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path=str(Path(__file__).parent / "supabase_api_page.png"))

        # Click all "Reveal" buttons to show hidden keys
        try:
            reveal_btns = page.get_by_role("button", name="Reveal")
            count = await reveal_btns.count()
            print(f"Found {count} Reveal buttons")
            for i in range(count):
                await reveal_btns.nth(i).click()
                await page.wait_for_timeout(500)
        except Exception as e:
            print(f"Reveal error: {e}")

        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(Path(__file__).parent / "supabase_revealed.png"))

        # Extract keys from inputs/textareas
        keys = await page.evaluate("""
            () => {
                var found = {};
                var inputs = document.querySelectorAll('input, textarea');
                for (var i = 0; i < inputs.length; i++) {
                    var val = inputs[i].value;
                    if (val && val.startsWith('eyJ') && val.length > 100) {
                        var label = '';
                        var p = inputs[i].parentElement;
                        for (var j = 0; j < 5 && p; j++) {
                            label = p.textContent.substring(0, 100);
                            if (label.indexOf('service_role') >= 0 || label.indexOf('anon') >= 0) break;
                            p = p.parentElement;
                        }
                        found[label.indexOf('service_role') >= 0 ? 'service_role' : 'other_' + i] = val;
                    }
                }
                return found;
            }
        """)
        print("Keys found:", json.dumps(keys, indent=2) if keys else "None")

        await context.close()


import json
if __name__ == "__main__":
    asyncio.run(main())
