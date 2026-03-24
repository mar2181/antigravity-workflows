#!/usr/bin/env python3
"""Open a persistent browser with Yehuda's Facebook session on the Sugar Shack page."""

from playwright.sync_api import sync_playwright
import os

PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL = "https://www.facebook.com/profile.php?id=61557735298128"

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE,
        headless=False,
        args=["--start-maximized"],
        no_viewport=True,
    )
    page = browser.pages[0] if browser.pages else browser.new_page()
    page.goto(PAGE_URL)
    print("[OK] Browser open — navigate to your test posts and delete them manually.")
    print("     Close the browser window when you're done.")
    # Keep running until the browser is closed by the user
    try:
        page.wait_for_event("close", timeout=0)
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass
