#!/usr/bin/env python3
"""
SPI Fun Rentals — Spring Break Campaign Scheduler
Posts ads 3–6, 9–12 at scheduled times.

Dropped by user: #2 (Family Connection), #7 (Fleet Showcase), #8 (Adventure Montage)
Already posted: #1 (Urgency Play)

Schedule (from manifest):
  Mar 13 13:30 → Ad #3  (FOMO Slingshot)
  Mar 13 17:45 → Ad #4  (Five Star Experience)
  Mar 14 10:00 → Ad #5  (Scooter Romantic)
  Mar 14 17:30 → Ad #6  (Comparison Split)
  Mar 16 10:00 → Ad #9  (Last Call)
  Mar 16 16:00 → Ad #10 (Instagram Worthy)
  Mar 17 12:00 → Ad #11 (Couples Getaway)
  Mar 17 19:00 → Ad #12 (Group Party Vibes)
"""

import sys
import os
import time
import json
from datetime import datetime

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright

# Paths
AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL = "https://www.facebook.com/spifunrentals"
MANIFEST_PATH = r"C:\Users\mario\.gemini\antigravity\scratch\skills\spi-fun-rentals-facebook\ads_manifest.json"

# Ads to post in order (skipping 2, 7, 8 per user approval)
SCHEDULE = [3, 4, 5, 6, 9, 10, 11, 12]


def load_manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(data):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_ad(manifest, ad_id):
    for ad in manifest:
        if ad["id"] == ad_id:
            return ad
    return None


def post_ad(ad):
    """Post a single ad using the working two-step Switch + Playwright flow."""
    image_path = ad["image"]
    copy = ad["copy"]
    ad_id = ad["id"]
    angle = ad["angle"]

    print(f"\n[POST] Ad #{ad_id} — {angle}")
    print(f"       Image: {os.path.basename(image_path)}")

    if not os.path.exists(image_path):
        print(f"  [ERROR] Image not found: {image_path}")
        return False

    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=AUTH_PROFILE,
                headless=False,
                viewport={"width": 1920, "height": 1080}
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            # Step 1: personal feed first
            print("  [1] Personal feed...")
            page.goto("https://www.facebook.com/")
            time.sleep(3)

            # Step 2: navigate to SPI page
            print("  [2] Navigating to SPI Fun Rentals...")
            page.goto(PAGE_URL)
            time.sleep(5)

            # Step 3: click sidebar Switch button to open the switch dialog
            print("  [3] Clicking Switch to open dialog...")
            for sel in [
                "div[role='button']:has-text('Switch Now')",
                "[aria-label='Switch Now']",
                "div[role='button']:has-text('Switch')",
                "[aria-label='Switch']",
            ]:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        print(f"     Clicked: {sel}")
                        time.sleep(3)
                        break
                except Exception:
                    pass

            # Step 4: click blue "Switch" button INSIDE the dialog
            print("  [4] Clicking Switch inside dialog...")
            try:
                switch_in_dialog = page.locator("[role='dialog'] div[role='button']:has-text('Switch')").first
                switch_in_dialog.wait_for(state="visible", timeout=5000)
                switch_in_dialog.click()
                print("     [OK] Dialog Switch clicked")
                time.sleep(4)
            except Exception as e:
                print(f"     [WARNING] Dialog Switch not found: {e}")
                try:
                    btn = page.locator("button:has-text('Switch')").first
                    btn.wait_for(state="visible", timeout=3000)
                    btn.click()
                    print("     [OK] Fallback Switch clicked")
                    time.sleep(4)
                except Exception as e2:
                    print(f"     [WARNING] Fallback also failed: {e2}")

            print(f"     URL after switch: {page.url}")

            # Step 5: scroll to composer area
            print("  [5] Scrolling to composer...")
            page.evaluate("window.scrollBy(0, 400)")
            time.sleep(2)

            # Step 6: open post composer
            print("  [6] Opening composer...")
            composer_opened = False
            for sel in [
                "div[role='button']:has-text('Create post')",
                "[aria-label='Create post']",
                "div[role='button']:has-text(\"What's on your mind\")",
                "[aria-label*=\"What's on your mind\"]",
                "div[role='button']:has-text('Write something')",
            ]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        time.sleep(2)
                        print(f"     [OK] Composer: {sel}")
                        composer_opened = True
                        break
                except Exception:
                    pass

            if not composer_opened:
                print("  [ERROR] Composer not found")
                ctx.close()
                return False

            try:
                page.wait_for_selector("[role='dialog']", timeout=5000)
                print("     [OK] Composer dialog open")
            except Exception:
                print("     [WARNING] No dialog detected — continuing")

            # Step 7: upload image
            print("  [7] Uploading image...")
            uploaded = False
            for sel in [
                "[role='dialog'] [aria-label='Photo/video']",
                "[aria-label='Photo/video']",
            ]:
                try:
                    btn = page.locator(sel).first
                    btn.wait_for(state="visible", timeout=5000)
                    with page.expect_file_chooser(timeout=6000) as fc_info:
                        btn.click()
                    fc_info.value.set_files(image_path)
                    time.sleep(5)
                    print(f"     [OK] Image uploaded via {sel}")
                    uploaded = True
                    break
                except Exception as e:
                    print(f"     [{sel}] failed: {e}")

            if not uploaded:
                print("  [ERROR] Image upload failed")
                ctx.close()
                return False

            # Step 8: type message
            print("  [8] Typing message...")
            typed = False
            for sel in [
                "[role='dialog'] div[role='textbox']",
                "[role='dialog'] [contenteditable='true']",
            ]:
                try:
                    el = page.locator(sel).first
                    el.wait_for(state="visible", timeout=6000)
                    el.click()
                    time.sleep(0.5)
                    el.press_sequentially(copy, delay=5)
                    time.sleep(0.5)
                    print("     [OK] Message typed")
                    typed = True
                    break
                except Exception as e:
                    print(f"     [{sel}] failed: {e}")

            if not typed:
                print("  [ERROR] Could not type message")
                ctx.close()
                return False

            # Step 9: click Post
            print("  [9] Clicking Post button...")
            posted = False
            for sel in [
                "[role='dialog'] [aria-label='Post'][role='button']",
                "[role='dialog'] div[role='button']:has-text('Post')",
                "[role='dialog'] [aria-label='Next'][role='button']",
                "[role='dialog'] div[role='button']:has-text('Next')",
            ]:
                try:
                    btn = page.locator(sel).first
                    btn.wait_for(state="visible", timeout=5000)
                    btn.click()
                    time.sleep(3)
                    print(f"     [OK] Clicked: {sel}")
                    if "Next" in sel:
                        try:
                            final = page.locator("[role='dialog'] [aria-label='Post'][role='button']").first
                            final.wait_for(state="visible", timeout=5000)
                            final.click()
                            time.sleep(3)
                            print("     [OK] Final Post button clicked")
                        except Exception:
                            pass
                    posted = True
                    break
                except Exception as e:
                    print(f"     [{sel}] failed: {e}")

            time.sleep(4)
            ctx.close()
            return posted

    except Exception as e:
        print(f"  [ERROR] Playwright exception: {e}")
        return False


def wait_until(target_str):
    target = datetime.strptime(target_str, "%Y-%m-%d %H:%M")
    now = datetime.now()
    diff = (target - now).total_seconds()
    if diff <= 0:
        return  # Already past — post immediately
    hours = int(diff // 3600)
    mins = int((diff % 3600) // 60)
    print(f"\n[WAIT] Next post at {target_str} — sleeping {hours}h {mins}m...")
    chunk = 900  # 15-minute check-ins
    while diff > 0:
        sleep_time = min(chunk, diff)
        time.sleep(sleep_time)
        diff -= sleep_time
        if diff > 0:
            remaining = datetime.strptime(target_str, "%Y-%m-%d %H:%M") - datetime.now()
            r_hours = int(remaining.total_seconds() // 3600)
            r_mins = int((remaining.total_seconds() % 3600) // 60)
            print(f"  [{datetime.now().strftime('%H:%M')}] Still waiting... {r_hours}h {r_mins}m until next post")


def main():
    print("=" * 60)
    print("SPI FUN RENTALS — SPRING BREAK CAMPAIGN SCHEDULER")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Ads to post: {len(SCHEDULE)}")
    print()

    manifest = load_manifest()

    # First: mark Ad #1 as posted if not already done
    ad1 = get_ad(manifest, 1)
    if ad1 and not ad1.get("posted"):
        ad1["posted"] = True
        ad1["posted_at"] = "2026-03-12 09:00"
        save_manifest(manifest)
        print("[NOTE] Marked Ad #1 as posted (posted earlier this session)")

    # Print schedule
    for ad_id in SCHEDULE:
        ad = get_ad(manifest, ad_id)
        if ad:
            status = "[DONE]" if ad.get("posted") else "[ ] "
            print(f"  {status} Ad #{ad_id:2d} ({ad['angle']}) → {ad['schedule']}")
    print()

    posted_count = 0
    failed_count = 0

    for ad_id in SCHEDULE:
        ad = get_ad(manifest, ad_id)

        if not ad:
            print(f"[ERROR] Ad #{ad_id} not found in manifest — skipping")
            continue

        if ad.get("posted"):
            print(f"[SKIP] Ad #{ad_id} already posted — skipping")
            continue

        post_at = ad["schedule"]

        # Wait until posting time
        wait_until(post_at)

        print(f"\n[{datetime.now().strftime('%H:%M')}] Posting Ad #{ad_id}...")
        success = post_ad(ad)

        if success:
            ad["posted"] = True
            ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_manifest(manifest)
            posted_count += 1
            print(f"[OK] Ad #{ad_id} posted — manifest updated")
        else:
            failed_count += 1
            print(f"[ERROR] Ad #{ad_id} failed — retrying in 5 minutes...")
            time.sleep(300)
            print(f"[RETRY] Ad #{ad_id}...")
            success = post_ad(ad)
            if success:
                ad["posted"] = True
                ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_manifest(manifest)
                posted_count += 1
                failed_count -= 1
                print(f"[OK] Ad #{ad_id} posted on retry — manifest updated")
            else:
                print(f"[FAIL] Ad #{ad_id} failed twice — moving on")

        # 60-second cooldown between posts
        if ad_id != SCHEDULE[-1]:
            print(f"  [cooldown] 60s between posts...")
            time.sleep(60)

    print("\n" + "=" * 60)
    print(f"CAMPAIGN COMPLETE: {posted_count} posted, {failed_count} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
