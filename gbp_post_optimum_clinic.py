#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gbp_post_optimum_clinic.py — Post 2 ads to Optimum Health & Wellness Clinic GBP
Uses Playwright with gbp_mario_profile (Mario's account)
GBP Business ID: 16753182239006365635 | Listed as: Optimum Health & Wellness Clinic (Cash Night Clinic)
"""

import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

try:
    from screenpipe_verifier import verify_and_notify_gbp
    SCREENPIPE_AVAILABLE = True
except ImportError:
    SCREENPIPE_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_mario_profile")
IMAGES_DIR = Path("C:/Users/mario/optimum_clinic_ad_images")
BUSINESS_NAME_KEYWORD = "OPTIMUM"

POSTS = [
    {
        "id": 1,
        "image": str(IMAGES_DIR / "ad_23_parent_sick_child.png"),
        "text": (
            "It's 8 PM. Your little one has a fever. The pediatrician is closed - and the ER feels like too much.\n\n"
            "That's exactly why we're here.\n\n"
            "Optimum Health & Wellness Clinic is open every night from 5 PM to 10 PM, 7 days a week. "
            "Walk right in - no appointment needed, no insurance required.\n\n"
            "Our bilingual team can help with sick visits, rapid flu and strep tests, and more - tonight in Pharr.\n\n"
            "Sick visits starting at $75\n"
            "Rapid flu/COVID/strep tests available\n"
            "No appointment needed - just walk in\n"
            "Bilingual staff - hablamos espanol\n\n"
            "Families across the RGV trust us when it matters most.\n\n"
            "Call (956) 627-3258 | 3912 N Jackson Rd, Pharr, TX\n"
            "Open tonight until 10 PM - walk in now.\n\n"
            "#Pharr #RGV #NightClinic"
        ),
    },
    {
        "id": 2,
        "image": str(IMAGES_DIR / "ad_28_working_parent.png"),
        "text": (
            "You pushed through a full day of work. Now it's after 6 PM, you're not feeling well, "
            "and every clinic in town is already closed.\n\n"
            "Don't spend 4+ hours sitting in the ER.\n\n"
            "Optimum Health & Wellness Clinic is open every evening from 5 PM to 10 PM - "
            "walk-in care, no appointment needed, no insurance required.\n\n"
            "Get seen tonight in Pharr for a fraction of the ER cost. Sick visits starting at $75.\n\n"
            "No appointment needed - just walk in\n"
            "No insurance required\n"
            "Prescription refills available\n"
            "Bilingual staff - hablamos espanol\n\n"
            "You work hard. Your healthcare should work around your schedule.\n\n"
            "Call (956) 627-3258 | 3912 N Jackson Rd, Pharr, TX\n"
            "Walk in tonight - open until 10 PM.\n\n"
            "#Pharr #McAllen #RGV"
        ),
    },
]


def log(msg):
    print(f"[gbp_optimum] {msg}", flush=True)


async def _click_skip_in_copy_dialog(page):
    """CRITICAL: After clicking Post, Google shows 'Copy post to other profiles' dialog.
    The Skip button is a <button> with text 'Skip' inside an IFRAME (not the main page).
    We MUST click Skip to finalize the post. Without this, the post is NOT published.

    Strategy: search ALL frames for a button whose text is exactly 'Skip'.
    Do NOT break early on Close/Back buttons — those are on the outer page and do nothing."""
    log("STEP: Dismissing 'Copy post' dialog (clicking Skip in iframe)...")

    for attempt in range(3):
        for frame in page.frames:
            try:
                result = await frame.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    for (let b of btns) {
                        if (b.textContent.trim() === 'Skip' && b.offsetParent !== null) {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if result:
                    log(f"SUCCESS: Clicked Skip in iframe — post is now published")
                    await page.wait_for_timeout(3000)
                    return True
            except Exception:
                pass

        try:
            result = await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                for (let b of btns) {
                    if (b.textContent.trim() === 'Skip' && b.offsetParent !== null) {
                        b.click();
                        return true;
                    }
                }
                return false;
            }""")
            if result:
                log(f"SUCCESS: Clicked Skip on main page — post is now published")
                await page.wait_for_timeout(3000)
                return True
        except Exception:
            pass

        log(f"Skip not found yet (attempt {attempt+1}/3), waiting...")
        await page.wait_for_timeout(2000)

    log("FAILED: Could not find Skip button after 3 attempts — POST MAY NOT BE PUBLISHED")
    return False


async def post_to_gbp(post: dict) -> bool:
    from playwright.async_api import async_playwright

    log(f"=== Posting Ad #{post['id']} ===")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Clear any stale dialogs from previous runs
            try:
                await page.keyboard.press("Escape")
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            except Exception:
                pass

            # Step 1: Navigate
            log("Navigating to business.google.com/locations...")
            await page.goto("https://business.google.com/locations", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_optimum_{post['id']}_step1_locations.png"))

            # Step 2: Click "Create post" in the Optimum row
            log("Finding Optimum row and clicking Create post...")
            row_buttons = await page.evaluate(f"""() => {{
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let row of rows) {{
                    if (row.textContent.toUpperCase().includes('{BUSINESS_NAME_KEYWORD}')) {{
                        const btns = row.querySelectorAll('a, button, [role="button"]');
                        return Array.from(btns).map(b => ({{
                            text: b.textContent.trim().slice(0,60),
                            aria: b.getAttribute('aria-label') || '',
                            title: b.getAttribute('title') || ''
                        }}));
                    }}
                }}
                return [];
            }}""")
            log(f"Row buttons: {row_buttons}")

            clicked = await page.evaluate(f"""() => {{
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let row of rows) {{
                    if (row.textContent.toUpperCase().includes('{BUSINESS_NAME_KEYWORD}')) {{
                        const btns = row.querySelectorAll('a, button, [role="button"]');
                        for (let btn of btns) {{
                            const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                            const title = (btn.getAttribute('title') || '').toLowerCase();
                            if (aria === 'create post' || title === 'create post') {{
                                btn.click();
                                return aria || title || 'create post clicked';
                            }}
                        }}
                    }}
                }}
                return null;
            }}""")
            log(f"Clicked: {clicked}")
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_optimum_{post['id']}_step2_modal_open.png"))

            # Step 3: Find modal iframe
            log("Finding modal iframe...")
            modal_frame = None
            for frame in page.frames:
                try:
                    content = await frame.content()
                    if "Description" in content or "Add post" in content or "Select images" in content:
                        modal_frame = frame
                        log(f"Modal frame: {frame.url or 'unnamed'}")
                        break
                except Exception:
                    pass
            if modal_frame is None:
                log("Modal iframe not found, using main page")
                modal_frame = page

            # Step 4: Upload image
            log("Uploading image...")
            try:
                async with page.expect_file_chooser(timeout=8000) as fc_info:
                    await modal_frame.get_by_text("Select images and videos").first.click()
                fc = await fc_info.value
                await fc.set_files(post["image"])
                log(f"Image uploaded: {post['image']}")
                await page.wait_for_timeout(5000)
            except Exception as e:
                log(f"File chooser failed: {e}, trying hidden input...")
                try:
                    await modal_frame.locator('input[type="file"]').first.set_input_files(post["image"])
                    log("Image uploaded via hidden input")
                    await page.wait_for_timeout(5000)
                except Exception as e2:
                    log(f"Hidden input also failed: {e2}")
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_optimum_{post['id']}_step3_image_uploaded.png"))

            # Step 5: Fill description - try all frames, verify char count
            log("Filling description...")
            text_filled = False
            filled_chars = 0

            for frame in [modal_frame] + [f for f in page.frames if f != modal_frame]:
                # Try placeholder="Description" first, then any textarea
                for locator_str in ['textarea[placeholder="Description"]', 'textarea']:
                    try:
                        desc = frame.locator(locator_str).first
                        await desc.wait_for(state="visible", timeout=3000)
                        await desc.click()
                        await page.wait_for_timeout(500)
                        await desc.fill(post["text"])
                        filled_chars = await desc.evaluate("el => el.value.length")
                        if filled_chars > 50:
                            log(f"Text filled: {filled_chars} chars in frame {frame.url or 'main'}")
                            text_filled = True
                            break
                    except Exception:
                        pass
                if text_filled:
                    break

            if not text_filled:
                log("WARNING: Text could not be filled in any frame!")

            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_optimum_{post['id']}_step4_text_filled.png"))

            # Step 6: Click Post button (opens "Copy post" dialog — does NOT publish yet)
            log("Clicking Post button (opens Copy dialog)...")
            try:
                post_btn = modal_frame.locator('button:has-text("Post")').last
                await post_btn.wait_for(state="visible", timeout=8000)
                await post_btn.click()
                log("Clicked Post — now need to handle Copy dialog")
            except Exception as e:
                log(f"Modal Post button error: {e} — trying JS across all frames")
                for frame in page.frames:
                    try:
                        result = await frame.evaluate("""() => {
                            const btns = Array.from(document.querySelectorAll('button'));
                            for (let b of btns) {
                                if (b.textContent.trim() === 'Post' && !b.disabled) {
                                    b.click(); return true;
                                }
                            }
                            return false;
                        }""")
                        if result:
                            log(f"Post clicked via JS in {frame.url or 'main'}")
                            break
                    except Exception:
                        pass

            # Wait for Copy dialog to appear (6s to handle slow networks)
            await page.wait_for_timeout(6000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_optimum_{post['id']}_step5_copy_dialog.png"), full_page=True)

            # CRITICAL: Click Skip in the Copy post dialog to actually publish
            published = await _click_skip_in_copy_dialog(page)

            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_optimum_{post['id']}_step6_final.png"), full_page=True)

            if published and SCREENPIPE_AVAILABLE:
                verify_and_notify_gbp("Optimum")

            if published:
                log(f"POST CONFIRMED: Optimum Clinic ad #{post['id']} is live on GBP")
            else:
                log(f"WARNING: Ad #{post['id']} may not have published — check GBP manually")
            return published

        except Exception as e:
            log(f"Error: {e}")
            try:
                await page.screenshot(path=str(SCRIPT_DIR / f"gbp_optimum_{post['id']}_error.png"))
            except Exception:
                pass
            return False
        finally:
            await page.wait_for_timeout(2000)
            await context.close()


async def main():
    log("Optimum Health & Wellness Clinic — GBP Post Automation")
    for post in POSTS:
        success = await post_to_gbp(post)
        if not success:
            log(f"Ad #{post['id']} — manual review needed. Check screenshots.")
        if post["id"] < len(POSTS):
            log("Waiting 5s before next post...")
            await asyncio.sleep(5)
    log("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
