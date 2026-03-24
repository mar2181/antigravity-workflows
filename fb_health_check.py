"""
Facebook Health Check — Run at the start of every session.
Verifies each profile is authenticated and each page's composer is reachable.
Takes ~15-20 seconds. Prints GREEN/RED per page.

Usage:
    python fb_health_check.py              # check all pages
    python fb_health_check.py optimum_clinic  # check one page
"""
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

CONFIG_PATH = "fb_pages_config.json"
BASE_DIR = Path(__file__).parent

GREEN = "[OK]  "
RED   = "[FAIL]"
WARN  = "[WARN]"

def check_page(p, page_key, page_info, profile_dir):
    """Check one page: authenticate, navigate to pages list, verify composer reachable."""
    result = {"page": page_key, "profile": profile_dir, "status": None, "detail": ""}
    page_id = str(page_info.get("page_id", ""))
    full_profile = str(BASE_DIR / profile_dir)

    try:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=full_profile,
            headless=True,
            args=["--no-sandbox"],
            viewport={"width": 1280, "height": 900}
        )
        pg = ctx.new_page()

        # Check authentication
        pg.goto("https://www.facebook.com/", timeout=15000)
        time.sleep(2)
        if "login" in pg.url.lower():
            result["status"] = "FAIL"
            result["detail"] = "Session expired — run reauth script"
            ctx.close()
            return result

        # Navigate to pages list and check account
        pg.goto("https://www.facebook.com/pages/?category=your_pages", timeout=15000)
        time.sleep(3)

        # Check account identity
        heading = pg.locator("h1, h2").first
        account_name = heading.inner_text(timeout=3000) if heading.count() > 0 else "unknown"

        # Check page is visible in list
        page_link = pg.locator(f'a[href*="{page_id}"]')
        if page_link.count() == 0:
            result["status"] = "FAIL"
            result["detail"] = f"Page not found on pages list (account: {account_name})"
            ctx.close()
            return result

        # Check Create post button is reachable
        create_btn = pg.locator(f'div:has(a[href*="{page_id}"]) [aria-label="Create post"]').first
        try:
            create_btn.wait_for(state="visible", timeout=5000)
            result["status"] = "OK"
            result["detail"] = f"Composer reachable | Account: {account_name}"
        except Exception:
            result["status"] = "WARN"
            result["detail"] = f"Page found but Create post button not visible | Account: {account_name}"

        ctx.close()

    except Exception as e:
        result["status"] = "FAIL"
        result["detail"] = str(e)[:120]

    return result


def main():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    pages = config["pages"]
    default_profile = config.get("auth_profile", "facebook_sniffer_profile")

    # Filter to specific page if provided
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if target:
        if target not in pages:
            print(f"Unknown page key: {target}")
            print(f"Available: {list(pages.keys())}")
            sys.exit(1)
        pages = {target: pages[target]}

    # Group by profile to avoid launching browsers twice
    profile_groups = {}
    for key, info in pages.items():
        profile = info.get("auth_profile", default_profile)
        profile_groups.setdefault(profile, []).append((key, info))

    print("\nFacebook Health Check")
    print("=" * 50)

    all_ok = True
    with sync_playwright() as p:
        for profile, page_list in profile_groups.items():
            print(f"\nProfile: {profile}")
            for page_key, page_info in page_list:
                result = check_page(p, page_key, page_info, profile)
                icon = GREEN if result["status"] == "OK" else (WARN if result["status"] == "WARN" else RED)
                print(f"  {icon} {page_key:20s}  {result['detail']}")
                if result["status"] == "FAIL":
                    all_ok = False

    print("\n" + "=" * 50)
    if all_ok:
        print("All checks passed. Ready to post.\n")
    else:
        print("One or more checks FAILED. See FACEBOOK_SESSION_GUIDE.md for fixes.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
