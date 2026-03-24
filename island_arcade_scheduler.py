#!/usr/bin/env python3
"""
Island Arcade — Spring Break Campaign Scheduler
Posts ads 2–4, 6–12 at optimal engagement times.

Ad #1 posted immediately via post_island_arcade_ad1.py
Ad #5 dropped (fal.ai filter)

Schedule:
  Mar 12 13:30 → Ad #2  (Beat the High Score)
  Mar 12 19:00 → Ad #3  (VR Shock & Awe)
  Mar 13 10:00 → Ad #4  (Family Showdown)
  Mar 13 13:30 → Ad #6  (Prize Haul)
  Mar 13 19:00 → Ad #7  (Sweet + Play Combo)
  Mar 14 10:00 → Ad #8  (Retro Nostalgia)
  Mar 14 13:30 → Ad #9  (Spring Break Alternative)
  Mar 14 19:00 → Ad #10 (Sunday Wind-Down)
  Mar 15 10:00 → Ad #11 (World's Largest Pac-Man)
  Mar 15 14:00 → Ad #12 (Rainy Day Hero)
"""

import sys, os, time, json
from datetime import datetime

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright

AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL = "https://www.facebook.com/profile.php?id=100090911360621"
MANIFEST_PATH = r"C:\Users\mario\.gemini\antigravity\scratch\skills\island-arcade-facebook\ads_manifest.json"

SCHEDULE = [
    {"ad_id": 2,  "post_at": "2026-03-12 13:30"},
    {"ad_id": 3,  "post_at": "2026-03-12 19:00"},
    {"ad_id": 4,  "post_at": "2026-03-13 10:00"},
    {"ad_id": 6,  "post_at": "2026-03-13 13:30"},
    {"ad_id": 7,  "post_at": "2026-03-13 19:00"},
    {"ad_id": 8,  "post_at": "2026-03-14 10:00"},
    {"ad_id": 9,  "post_at": "2026-03-14 13:30"},
    {"ad_id": 10, "post_at": "2026-03-14 19:00"},
    {"ad_id": 11, "post_at": "2026-03-15 10:00"},
    {"ad_id": 12, "post_at": "2026-03-15 14:00"},
]


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
    image_path = ad["image"].replace("/", "\\")
    copy = ad["copy"]

    print(f"\n  Image: {os.path.basename(image_path)}")

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

            page.goto("https://www.facebook.com/")
            time.sleep(3)

            page.goto(PAGE_URL)
            time.sleep(5)

            # Two-step Switch: open dialog, then confirm
            for sel in ["div[role='button']:has-text('Switch Now')", "div[role='button']:has-text('Switch')"]:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        time.sleep(3)
                        break
                except:
                    pass

            try:
                dlg_btn = page.locator("[role='dialog'] div[role='button']:has-text('Switch')").first
                dlg_btn.wait_for(state="visible", timeout=5000)
                dlg_btn.click()
                time.sleep(4)
            except Exception as e:
                print(f"  [WARNING] Dialog Switch: {e}")
                try:
                    page.locator("button:has-text('Switch')").first.click()
                    time.sleep(4)
                except:
                    pass

            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except:
                time.sleep(5)

            try:
                page.evaluate("window.scrollBy(0, 400)")
            except:
                time.sleep(1)
            time.sleep(2)

            # Open composer
            composer_opened = False
            for sel in [
                "div[role='button']:has-text('Create post')",
                "[aria-label='Create post']",
                "div[role='button']:has-text(\"What's on your mind\")",
                "div[role='button']:has-text('Write something')",
            ]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        time.sleep(2)
                        composer_opened = True
                        print(f"  [OK] Composer: {sel}")
                        break
                except:
                    pass

            if not composer_opened:
                print("  [ERROR] Composer not found")
                ctx.close()
                return False

            try:
                page.wait_for_selector("[role='dialog']", timeout=5000)
            except:
                pass

            # Upload image
            uploaded = False
            for sel in ["[role='dialog'] [aria-label='Photo/video']", "[aria-label='Photo/video']"]:
                try:
                    btn = page.locator(sel).first
                    btn.wait_for(state="visible", timeout=5000)
                    with page.expect_file_chooser(timeout=6000) as fc_info:
                        btn.click()
                    fc_info.value.set_files(image_path)
                    time.sleep(5)
                    print(f"  [OK] Image uploaded")
                    uploaded = True
                    break
                except Exception as e:
                    print(f"  [{sel}] failed: {e}")

            if not uploaded:
                ctx.close()
                return False

            # Type message
            typed = False
            for sel in ["[role='dialog'] div[role='textbox']", "[role='dialog'] [contenteditable='true']"]:
                try:
                    el = page.locator(sel).first
                    el.wait_for(state="visible", timeout=6000)
                    el.click()
                    time.sleep(0.5)
                    el.press_sequentially(copy, delay=5)
                    print(f"  [OK] Message typed")
                    typed = True
                    break
                except Exception as e:
                    print(f"  [{sel}] failed: {e}")

            if not typed:
                ctx.close()
                return False

            # Click Post
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
                    if "Next" in sel:
                        try:
                            page.locator("[role='dialog'] [aria-label='Post'][role='button']").first.click()
                            time.sleep(3)
                        except:
                            pass
                    posted = True
                    break
                except:
                    pass

            time.sleep(4)
            ctx.close()
            return posted

    except Exception as e:
        print(f"  [ERROR] Playwright: {e}")
        return False


def wait_until(target_str):
    target = datetime.strptime(target_str, "%Y-%m-%d %H:%M")
    diff = (target - datetime.now()).total_seconds()
    if diff <= 0:
        return
    hours, mins = int(diff // 3600), int((diff % 3600) // 60)
    print(f"\n[WAIT] Next post at {target_str} — {hours}h {mins}m away...")
    chunk = 900
    while diff > 0:
        time.sleep(min(chunk, diff))
        diff -= chunk
        if diff > 0:
            rem = (target - datetime.now()).total_seconds()
            print(f"  [{datetime.now().strftime('%H:%M')}] {int(rem//3600)}h {int((rem%3600)//60)}m remaining...")


def main():
    print("=" * 60)
    print("ISLAND ARCADE — SPRING BREAK CAMPAIGN SCHEDULER")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    manifest = load_manifest()

    # Mark ad #1 as posted
    ad1 = get_ad(manifest, 1)
    if ad1 and not ad1.get("posted"):
        ad1["posted"] = True
        ad1["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_manifest(manifest)
        print("[NOTE] Marked Ad #1 as posted")

    print("\nUpcoming schedule:")
    for item in SCHEDULE:
        ad = get_ad(manifest, item["ad_id"])
        status = "[DONE]" if ad and ad.get("posted") else "[    ]"
        angle = ad["angle"] if ad else "?"
        print(f"  {status} Ad #{item['ad_id']:2d} ({angle}) → {item['post_at']}")
    print()

    posted_count = 0
    failed_count = 0

    for item in SCHEDULE:
        ad_id = item["ad_id"]
        post_at = item["post_at"]
        ad = get_ad(manifest, ad_id)

        if not ad:
            print(f"[SKIP] Ad #{ad_id} not in manifest")
            continue
        if ad.get("posted"):
            print(f"[SKIP] Ad #{ad_id} already posted")
            continue

        wait_until(post_at)

        print(f"\n[{datetime.now().strftime('%H:%M')}] Posting Ad #{ad_id} — {ad['angle']}...")
        success = post_ad(ad)

        if success:
            ad["posted"] = True
            ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_manifest(manifest)
            posted_count += 1
            print(f"[OK] Ad #{ad_id} posted — manifest updated")
        else:
            failed_count += 1
            print(f"[ERROR] Ad #{ad_id} failed — retrying in 5 min...")
            time.sleep(300)
            success = post_ad(ad)
            if success:
                ad["posted"] = True
                ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_manifest(manifest)
                posted_count += 1
                failed_count -= 1
                print(f"[OK] Ad #{ad_id} posted on retry")
            else:
                print(f"[FAIL] Ad #{ad_id} failed twice — moving on")

        if item != SCHEDULE[-1]:
            time.sleep(60)

    print("\n" + "=" * 60)
    print(f"CAMPAIGN DONE: {posted_count} posted, {failed_count} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
