"""
schedule_optimum_clinic.py
--------------------------
Schedules 2 posts on the Optimum Health & Wellness Clinic Facebook page
using the saved Mario Playwright profile.

Posts:
  Post 1 → 2026-03-21 17:00  (Saturday 5 PM -- English, walk-in tonight)
  Post 2 → 2026-03-22 18:00  (Sunday 6 PM -- Spanish, $75 vs ER)

Run:
  cd C:/Users/mario/.gemini/antigravity/tools/execution
  python schedule_optimum_clinic.py
"""

import time
import pyperclip
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path(__file__).parent / "facebook_mario_profile")
PAGE_URL    = "https://www.facebook.com/profile.php?id=61588407637377"

IMAGE_1 = r"C:\Users\mario\optimum_clinic_ad_images\ad_10_walk_in_tonight.png"
IMAGE_2 = r"C:\Users\mario\optimum_clinic_ad_images\ad_11_late_night_relief.png"

COPY_1 = """Sick after work? Don't wait until tomorrow. 🌙

Optimum Health & Wellness Clinic is open tonight until 10 PM -- no insurance needed, no appointment required.

✅ Walk-ins welcome
✅ $75 consultation
✅ Results tonight -- not next week

📍 3912 N Jackson Rd, Pharr TX
📞 (956) 627-3258

Open Mon-Sun: 5 PM - 10 PM

#NightClinic #RGVHealth #OptimumClinic"""

COPY_2 = """¿Te sientes mal y ya cerraron los demás? Nosotros estamos abiertos. 🏥

Optimum Health & Wellness Clinic abre hasta las 10 PM -- todos los días.

Sin seguro. Sin cita. Sin esperar horas en urgencias.

💰 Consulta desde $75 (vs. $2,200+ en urgencias)
🗣️ Personal completamente bilingüe
📍 3912 N Jackson Rd, Pharr TX
📞 (956) 627-3258

#ClinicaNocturna #SaludRGV #OptimumClinic"""

POSTS = [
    {"copy": COPY_1, "image": IMAGE_1, "date": "03/21/2026", "time_str": "05:00 PM"},
    {"copy": COPY_2, "image": IMAGE_2, "date": "03/22/2026", "time_str": "06:00 PM"},
]


def snap(page, label):
    try:
        page.screenshot(path=f"debug_snap_optimum_schedule_{label}.png")
        print(f"  [SNAP] {label}")
    except Exception:
        pass


def schedule_one(page, post):
    print(f"\n-- Scheduling post for {post['date']} {post['time_str']} --")

    # 1. Navigate to page
    print("[STEP] Navigating to Optimum Clinic page...")
    page.goto(PAGE_URL)
    page.wait_for_timeout(4000)
    snap(page, "01_page_loaded")

    # 2. Open composer
    print("[STEP] Opening composer...")
    for selector in [
        "div[role='button']:has-text('Create post')",
        "div[role='button']:has-text('Write something')",
        "[aria-label='Create post']",
        "div[data-pagelet='ProfileComposer']",
    ]:
        try:
            page.locator(selector).first.click(timeout=4000)
            page.wait_for_timeout(2000)
            snap(page, "02_composer_open")
            print(f"  [OK] Composer opened via: {selector}")
            break
        except Exception:
            continue

    # 3. Upload image via file input
    print(f"[STEP] Uploading image: {Path(post['image']).name}")
    try:
        # Click photo/video button
        for photo_sel in [
            "[aria-label='Photo/video']",
            "div[role='button']:has-text('Photo')",
            "[aria-label='Add photos or videos']",
        ]:
            try:
                page.locator(photo_sel).first.click(timeout=3000)
                page.wait_for_timeout(1500)
                break
            except Exception:
                continue

        with page.expect_file_chooser(timeout=8000) as fc_info:
            # Try clicking the visible add media button inside composer
            for sel in [
                "[aria-label='Add photos or videos']",
                "input[type='file']",
                "[data-testid='photo-attach-button']",
            ]:
                try:
                    page.locator(sel).first.click(timeout=3000)
                    break
                except Exception:
                    continue
        file_chooser = fc_info.value
        file_chooser.set_files(post["image"])
        page.wait_for_timeout(3000)
        snap(page, "03_image_uploaded")
        print("  [OK] Image uploaded")
    except Exception as e:
        print(f"  [WARN] Image upload: {e}")

    # 4. Type message via clipboard
    print("[STEP] Typing message...")
    try:
        # Find the text area in the composer
        for txt_sel in [
            "div[contenteditable='true'][aria-label*='post']",
            "div[contenteditable='true'][role='textbox']",
            "div[contenteditable='true']",
        ]:
            try:
                el = page.locator(txt_sel).first
                el.click(timeout=3000)
                break
            except Exception:
                continue
        pyperclip.copy(post["copy"])
        page.keyboard.press("Control+a")
        page.keyboard.press("Control+v")
        page.wait_for_timeout(1500)
        snap(page, "04_message_typed")
        print("  [OK] Message typed")
    except Exception as e:
        print(f"  [WARN] Message: {e}")

    # 5. Click "Next" to reach posting options
    print("[STEP] Clicking Next...")
    for next_sel in [
        "div[aria-label='Next'][role='button']",
        "div[role='button']:has-text('Next')",
    ]:
        try:
            page.locator(next_sel).first.click(timeout=4000)
            page.wait_for_timeout(2000)
            snap(page, "05_after_next")
            print("  [OK] Clicked Next")
            break
        except Exception:
            continue

    # 6. Look for scheduling dropdown -- click the chevron/arrow next to Post button
    print("[STEP] Looking for schedule dropdown...")
    snap(page, "06_pre_schedule")
    scheduled = False

    # Try dropdown arrow next to Post button
    for arrow_sel in [
        "[aria-label='Schedule post']",
        "div[aria-label*='chedule']",
        "div[role='button'][aria-label*='schedule']",
        "i.sp_schedule",
        # chevron/arrow adjacent to Post button
        "div[role='dialog'] [aria-label='Actions for this post']",
    ]:
        try:
            page.locator(arrow_sel).first.click(timeout=3000)
            page.wait_for_timeout(1500)
            snap(page, "07_schedule_dropdown")
            print(f"  [OK] Opened schedule via: {arrow_sel}")
            scheduled = True
            break
        except Exception:
            continue

    if not scheduled:
        # Try the "Actions for this post" button which often reveals scheduling
        try:
            page.locator("[aria-label='Actions for this post']").first.click(timeout=3000)
            page.wait_for_timeout(1000)
            snap(page, "07b_actions_menu")
            # Look for Schedule option in the dropdown
            page.locator("text=Schedule").first.click(timeout=3000)
            page.wait_for_timeout(1500)
            snap(page, "07c_schedule_selected")
            scheduled = True
            print("  [OK] Found Schedule via Actions menu")
        except Exception as e:
            print(f"  [WARN] Actions menu: {e}")

    if not scheduled:
        # Last resort: look for any element with "schedule" text
        try:
            page.locator("text=Schedule for later").first.click(timeout=3000)
            page.wait_for_timeout(1500)
            scheduled = True
            print("  [OK] Clicked 'Schedule for later'")
        except Exception:
            pass

    if not scheduled:
        print("  [WARN] Could not find schedule UI. Dumping all dialog buttons:")
        btns = page.query_selector_all("[role='dialog'] [role='button'], [data-pagelet] [role='button']")
        for b in btns[:20]:
            print(f"    text={b.inner_text()[:40]!r}  aria={b.get_attribute('aria-label')!r}")
        snap(page, "07_schedule_fail_dump")
        print("  [ERROR] Cannot schedule -- closing without posting.")
        # Close dialog
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False

    # 7. Fill in date
    print(f"[STEP] Setting date to {post['date']}...")
    try:
        date_input = page.locator("input[placeholder*='MM/DD'], input[type='date'], [aria-label*='Date']").first
        date_input.triple_click(timeout=3000)
        date_input.type(post["date"], delay=80)
        page.wait_for_timeout(500)
        page.keyboard.press("Tab")
        page.wait_for_timeout(500)
        print(f"  [OK] Date set")
    except Exception as e:
        print(f"  [WARN] Date field: {e}")

    # 8. Fill in time
    print(f"[STEP] Setting time to {post['time_str']}...")
    try:
        time_input = page.locator("input[placeholder*='HH:MM'], input[type='time'], [aria-label*='Time']").first
        time_input.triple_click(timeout=3000)
        time_input.type(post["time_str"].replace(" ", ""), delay=80)
        page.wait_for_timeout(500)
        page.keyboard.press("Tab")
        page.wait_for_timeout(500)
        print(f"  [OK] Time set")
    except Exception as e:
        print(f"  [WARN] Time field: {e}")

    snap(page, "08_date_time_set")

    # 9. Confirm scheduling
    print("[STEP] Confirming schedule...")
    for confirm_sel in [
        "div[role='button']:has-text('Schedule')",
        "div[role='button']:has-text('Save')",
        "[aria-label='Schedule']",
    ]:
        try:
            page.locator(confirm_sel).first.click(timeout=4000)
            page.wait_for_timeout(3000)
            snap(page, "09_scheduled")
            print(f"  [OK] Post scheduled!")
            return True
        except Exception:
            continue

    print("  [WARN] Could not click confirm button.")
    snap(page, "09_confirm_fail")
    return False


with sync_playwright() as p:
    print("[LAUNCH] Opening browser with Mario's saved session...")
    browser = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--start-maximized"],
        no_viewport=True,
    )
    page = browser.new_page()

    results = []
    for i, post in enumerate(POSTS, 1):
        print(f"\n{'='*50}")
        print(f"POST {i} of {len(POSTS)}")
        print(f"{'='*50}")
        ok = schedule_one(page, post)
        results.append(ok)
        if i < len(POSTS):
            time.sleep(3)

    browser.close()

print("\n-- RESULTS --")
for i, (post, ok) in enumerate(zip(POSTS, results), 1):
    status = "✅ Scheduled" if ok else "❌ Failed"
    print(f"  Post {i} ({post['date']} {post['time_str']}): {status}")
