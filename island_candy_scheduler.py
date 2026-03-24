"""Island Candy Facebook Ad Scheduler — Ads #3-#11 (excluding #1,#6,#12)
Schedule: 3/day at 10:00 AM, 1:30 PM, 7:00 PM
Mar 13: #3, #4, #5
Mar 14: #7, #8, #9
Mar 15: #10, #11
"""
import sys, os, time, json
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime
from playwright.sync_api import sync_playwright

AUTH_PROFILE = os.path.join(os.path.dirname(__file__), "facebook_sniffer_profile")
PAGE_URL = "https://www.facebook.com/profile.php?id=100090560413893"
MANIFEST_PATH = r"C:\Users\mario\.gemini\antigravity\scratch\skills\island-candy-facebook\ads_manifest.json"

SCHEDULE = [
    {"id": 3,  "angle": "homemade_icecream",   "run_at": "2026-03-13 10:00"},
    {"id": 4,  "angle": "instagram_cone",       "run_at": "2026-03-13 13:30"},
    {"id": 5,  "angle": "candy_store_wonder",   "run_at": "2026-03-13 19:00"},
    {"id": 7,  "angle": "family_tradition",     "run_at": "2026-03-14 10:00"},
    {"id": 8,  "angle": "late_night_sweet",     "run_at": "2026-03-14 13:30"},
    {"id": 9,  "angle": "candy_discovery",      "run_at": "2026-03-14 19:00"},
    {"id": 10, "angle": "arcade_powerup",       "run_at": "2026-03-15 10:00"},
    {"id": 11, "angle": "spring_break_treat",   "run_at": "2026-03-15 13:30"},
]

def load_manifest():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_manifest(manifest):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

def mark_posted(ad_id):
    manifest = load_manifest()
    for ad in manifest:
        if ad["id"] == ad_id:
            ad["posted"] = True
            ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_manifest(manifest)

def get_copy(ad_id):
    manifest = load_manifest()
    for ad in manifest:
        if ad["id"] == ad_id:
            return ad["copy"]
    return None

def get_image(ad_id, angle):
    return rf"C:\Users\mario\island_candy_ad_images\ad_{ad_id}_{angle}.png"

def post_ad(ad_id, angle):
    message = get_copy(ad_id)
    image_path = get_image(ad_id, angle)

    if not message:
        print(f"[ERROR] No copy found for ad #{ad_id}")
        return False
    if not os.path.exists(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        return False

    print(f"\n{'='*60}")
    print(f"[POSTING] Ad #{ad_id} — {angle}")
    print(f"{'='*60}")

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

        # Two-step Switch flow
        for sel in [
            "div[role='button']:has-text('Switch Now')",
            "[aria-label='Switch Now']",
            "div[role='button']:has-text('Switch')",
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(3)
                    break
            except:
                pass

        try:
            sw = page.locator("[role='dialog'] div[role='button']:has-text('Switch')").first
            sw.wait_for(state="visible", timeout=5000)
            sw.click()
            time.sleep(4)
        except Exception as e:
            print(f"    [WARNING] Switch dialog: {e}")

        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except:
            time.sleep(5)

        try:
            page.evaluate("window.scrollBy(0, 400)")
        except:
            pass
        time.sleep(2)

        # Open composer
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
                    composer_opened = True
                    break
            except:
                pass

        if not composer_opened:
            print("    [ERROR] Composer not found")
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
                uploaded = True
                break
            except Exception as e:
                print(f"    upload [{sel}] failed: {e}")

        if not uploaded:
            print("    [ERROR] Upload failed")
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
                el.press_sequentially(message, delay=5)
                typed = True
                break
            except Exception as e:
                print(f"    type [{sel}] failed: {e}")

        if not typed:
            print("    [ERROR] Could not type message")
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
                        final = page.locator("[role='dialog'] [aria-label='Post'][role='button']").first
                        final.wait_for(state="visible", timeout=5000)
                        final.click()
                        time.sleep(3)
                    except:
                        pass
                posted = True
                break
            except Exception as e:
                print(f"    post [{sel}] failed: {e}")

        time.sleep(4)
        ctx.close()

    if posted:
        mark_posted(ad_id)
        print(f"[SUCCESS] Ad #{ad_id} ({angle}) posted and manifest updated!")
    else:
        print(f"[ERROR] Ad #{ad_id} — Post button not found")
    return posted


def main():
    print("[Island Candy Scheduler] Starting...")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Watching schedule...\n")

    for entry in SCHEDULE:
        ad_id = entry["id"]
        angle = entry["angle"]
        run_at = datetime.strptime(entry["run_at"], "%Y-%m-%d %H:%M")

        # Check if already posted
        manifest = load_manifest()
        already_posted = any(a["id"] == ad_id and a.get("posted") for a in manifest)
        if already_posted:
            print(f"[SKIP] Ad #{ad_id} already posted")
            continue

        now = datetime.now()
        wait_seconds = (run_at - now).total_seconds()

        if wait_seconds > 0:
            print(f"[WAIT] Ad #{ad_id} ({angle}) — scheduled {entry['run_at']} ({int(wait_seconds/3600)}h {int((wait_seconds%3600)/60)}m from now)")
            time.sleep(wait_seconds)

        post_ad(ad_id, angle)
        time.sleep(10)  # Brief pause between posts if somehow back-to-back

    print("\n[DONE] All scheduled ads posted.")


if __name__ == "__main__":
    main()
