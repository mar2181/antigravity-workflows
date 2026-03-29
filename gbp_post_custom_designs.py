#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gbp_post_custom_designs.py — Post 2 ads to Custom Designs TX Google Business Profile
Uses Playwright with gbp_sniffer_profile (Mario's account, port 9224)
"""

import asyncio
import sys
import os
from pathlib import Path

try:
    from screenpipe_verifier import verify_and_notify_gbp
    SCREENPIPE_AVAILABLE = True
except ImportError:
    SCREENPIPE_AVAILABLE = False

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_mario_profile")
IMAGES_DIR = Path("C:/Users/mario/custom_designs_ad_images")

POSTS = [
    {
        "id": 1,
        "image": str(IMAGES_DIR / "ad_1_after_hours_blind_spot.png"),
        "text": (
            "You just locked up. Do you actually know what's happening at your business right now? 🔒\n\n"
            "Most business owners in the RGV don't — until something goes wrong.\n\n"
            "🎥 Monitor every corner of your property, 24/7\n"
            "📱 Watch live from your phone, anywhere, anytime\n"
            "⚡ Instant alerts the moment anything triggers\n"
            "🔒 Cameras and alarms working together — the complete system\n\n"
            "An alarm tells you after the fact. A camera system lets you act before a problem becomes a loss.\n\n"
            "Custom Designs installs professional-grade security camera systems for businesses across Hidalgo and Cameron County. "
            "We've worked with businesses of all sizes — from corner shops to commercial warehouses.\n\n"
            "📞 Free on-site consultation + written quote — no obligation.\n"
            "We come to your location, assess your space, and tell you exactly what coverage you need.\n\n"
            "👉 Message us to schedule yours today.\n\n"
            "#McAllen #RGVBusiness #SecurityCameras"
        ),
    },
    {
        "id": 2,
        "image": str(IMAGES_DIR / "ad_2_home_theater_reveal.png"),
        "text": (
            "Imagine watching your favorite movie the way it was meant to be seen. 🎬\n\n"
            "Not on a laptop. Not on a regular TV.\n"
            "On a dedicated home theater — designed and installed by professionals, right here in the RGV.\n\n"
            "🎥 Cinema-grade screen and display setup\n"
            "🔊 True surround sound that wraps around the room\n"
            "💡 Ambient lighting that sets the perfect atmosphere\n"
            "🛋️ Your space, your layout, your experience\n\n"
            "This isn't a luxury reserved for a select few. Custom Designs builds home theaters for families across "
            "Hidalgo and Cameron County — designed around how you actually live.\n\n"
            "📞 Free on-site consultation + written quote — no obligation.\n"
            "We visit your home, see your space, and design a setup built around your lifestyle.\n\n"
            "👉 Ready to transform your living room? Message us today.\n\n"
            "#HomeTheater #McAllen #RGV"
        ),
    },
]


def log(msg):
    print(f"[gbp_poster] {msg}", flush=True)


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
        log(f"Launching Chrome with gbp_sniffer_profile...")
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

            # Step 1: Navigate to GBP locations page
            log("Navigating to business.google.com/locations...")
            await page.goto("https://business.google.com/locations", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # Screenshot to verify we're logged in
            screenshot_path = str(SCRIPT_DIR / f"gbp_post_{post['id']}_step1.png")
            await page.screenshot(path=screenshot_path)
            log(f"Screenshot: {screenshot_path}")

            # Step 2: Click the "Add update" (post) icon in the CUSTOM DESIGNS row
            # In GBP table, each verified row has icons: pencil(edit), camera(photos), document(add update)
            # We want the "Add update" / post icon — NOT "See your profile" (that goes to public Maps page)
            log("Looking for 'Add update' icon in CUSTOM DESIGNS row...")

            # First: dump all aria-labels in the Custom Designs row so we know what's there
            row_buttons = await page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let row of rows) {
                    if (row.textContent.toUpperCase().includes('CUSTOM DESIGNS')) {
                        const btns = row.querySelectorAll('a, button, [role="button"]');
                        return Array.from(btns).map(b => ({
                            text: b.textContent.trim(),
                            aria: b.getAttribute('aria-label') || '',
                            title: b.getAttribute('title') || '',
                            href: b.getAttribute('href') || ''
                        }));
                    }
                }
                return [];
            }""")
            log(f"Row buttons found: {row_buttons}")

            post_clicked = await page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let row of rows) {
                    if (row.textContent.toUpperCase().includes('CUSTOM DESIGNS')) {
                        const btns = row.querySelectorAll('a, button, [role="button"]');
                        for (let btn of btns) {
                            const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                            const title = (btn.getAttribute('title') || '').toLowerCase();
                            const text = btn.textContent.toLowerCase();
                            // Match "Add update", "Create post", "Post update", or the pencil-with-doc icon
                            if (aria.includes('update') || aria.includes('post') ||
                                title.includes('update') || title.includes('post') ||
                                text.includes('add update') || text.includes('create post')) {
                                btn.click();
                                return aria || title || text || 'clicked';
                            }
                        }
                        // Fallback: click the 3rd button/icon in the row (after pencil and camera)
                        const actionBtns = Array.from(row.querySelectorAll('button, [role="button"]'))
                            .filter(b => !b.textContent.includes('See your profile') &&
                                        !b.textContent.includes('Manage profile'));
                        if (actionBtns.length >= 3) {
                            actionBtns[2].click();
                            return '3rd icon clicked';
                        }
                    }
                }
                return null;
            }""")

            if post_clicked:
                log(f"✅ Clicked post icon: {post_clicked}")
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)
            else:
                log("⚠️ Could not find post icon — check step2 screenshot")

            screenshot_path2 = str(SCRIPT_DIR / f"gbp_post_{post['id']}_step2.png")
            await page.screenshot(path=screenshot_path2)
            log(f"Screenshot: {screenshot_path2}")

            # The "Add post" modal is open inside an iframe.
            # Must find the correct frame first, then use it for all interactions.

            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_post_{post['id']}_step3_modal.png"))
            log(f"Screenshot modal open: gbp_post_{post['id']}_step3_modal.png")

            # Find the iframe containing the modal ("Add post" / "Description" textarea)
            log("Searching for modal iframe...")
            modal_frame = None
            await page.wait_for_timeout(1000)
            for frame in page.frames:
                try:
                    content = await frame.content()
                    if "Description" in content or "Add post" in content or "Select images" in content:
                        modal_frame = frame
                        log(f"✅ Found modal frame: {frame.url or frame.name or 'unnamed'}")
                        break
                except Exception:
                    pass

            if modal_frame is None:
                log("⚠️ Modal iframe not found — falling back to main page")
                modal_frame = page

            # Step 3: Upload image
            log("Uploading image via file chooser...")
            try:
                async with page.expect_file_chooser(timeout=8000) as fc_info:
                    select_link = modal_frame.get_by_text("Select images and videos").first
                    await select_link.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(post["image"])
                log(f"✅ Image uploaded: {post['image']}")
                await page.wait_for_timeout(4000)
            except Exception as e:
                log(f"⚠️ File chooser failed: {e}")
                try:
                    file_input = modal_frame.locator('input[type="file"]').first
                    await file_input.set_input_files(post["image"])
                    log("✅ Image uploaded via hidden input")
                    await page.wait_for_timeout(4000)
                except Exception as e2:
                    log(f"⚠️ Image upload fallback also failed: {e2}")

            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_post_{post['id']}_step4_image.png"))
            log(f"Screenshot after image: gbp_post_{post['id']}_step4_image.png")

            # Step 4: Fill Description textarea
            log("Filling Description textarea...")
            try:
                desc = modal_frame.locator('textarea[placeholder="Description"]').first
                await desc.wait_for(timeout=5000)
                await desc.click()
                await page.wait_for_timeout(300)
                await desc.fill(post["text"])
                log("✅ Text filled")
            except Exception as e:
                log(f"⚠️ Textarea error: {e}, trying generic textarea...")
                try:
                    desc = modal_frame.locator('textarea').first
                    await desc.click()
                    await desc.fill(post["text"])
                    log("✅ Text filled via generic textarea")
                except Exception as e2:
                    log(f"⚠️ Text fill failed: {e2}")

            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_post_{post['id']}_step5_text.png"))
            log(f"Screenshot with text: gbp_post_{post['id']}_step5_text.png")

            # Step 5: Click Post button (opens "Copy post" dialog — does NOT publish yet)
            log("Clicking Post button (opens Copy dialog)...")
            try:
                post_btn = modal_frame.locator('button:has-text("Post")').last
                await post_btn.wait_for(timeout=5000)
                await post_btn.click()
                log("Clicked Post — now need to handle Copy dialog")
            except Exception as e:
                log(f"Post button error: {e}, trying JS fallback...")
                for frame in page.frames:
                    try:
                        result = await frame.evaluate("""() => {
                            const btns = Array.from(document.querySelectorAll('button'));
                            for (let b of btns) {
                                if (b.textContent.trim() === 'Post') { b.click(); return true; }
                            }
                            return false;
                        }""")
                        if result:
                            log("Post clicked via JS frame fallback")
                            break
                    except Exception:
                        pass

            await page.wait_for_timeout(6000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_post_{post['id']}_step5_copy_dialog.png"))

            # CRITICAL: Click Skip in the Copy post dialog to actually publish
            published = await _click_skip_in_copy_dialog(page)

            screenshot_path5 = str(SCRIPT_DIR / f"gbp_post_{post['id']}_step6_final.png")
            await page.screenshot(path=screenshot_path5, full_page=True)
            log(f"Final screenshot: {screenshot_path5}")

            if published:
                log(f"Ad #{post['id']} POST CONFIRMED — live on GBP")
                if SCREENPIPE_AVAILABLE:
                    verify_and_notify_gbp("Custom Designs")
            else:
                log(f"Ad #{post['id']} — POST MAY NOT BE PUBLISHED. Check screenshots.")

            return published

        except Exception as e:
            log(f"❌ Error posting Ad #{post['id']}: {e}")
            try:
                err_path = str(SCRIPT_DIR / f"gbp_post_{post['id']}_error.png")
                await page.screenshot(path=err_path)
                log(f"Error screenshot: {err_path}")
            except Exception:
                pass
            return False
        finally:
            await page.wait_for_timeout(2000)
            await context.close()


async def main():
    log("Custom Designs TX — GBP Post Automation")
    log(f"Profile: {PROFILE_DIR}")
    log(f"Posting {len(POSTS)} ads\n")

    for post in POSTS:
        success = await post_to_gbp(post)
        if not success:
            log(f"⚠️ Ad #{post['id']} may need manual review. Check screenshots.")
        log("")
        # Small delay between posts
        if post["id"] < len(POSTS):
            log("Waiting 5s before next post...")
            await asyncio.sleep(5)

    log("=== Done ===")
    log("Check screenshots in the execution folder for each step.")


if __name__ == "__main__":
    asyncio.run(main())
