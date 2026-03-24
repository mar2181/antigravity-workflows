#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post to Custom Designs TX GBP with hero image — Mario's gbp_mario_profile"""
import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

try:
    from screenpipe_verifier import verify_and_notify_gbp
    SCREENPIPE_AVAILABLE = True
except ImportError:
    SCREENPIPE_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_mario_profile")
IMAGE_PATH = str(SCRIPT_DIR / "blog_posts/custom_designs_tx/images/2026-03-18_security-camera-installation-mcallen-tx/hero.png")

POST_TEXT = (
    "\U0001f512 Professional Security Camera Installation in McAllen, TX\n\n"
    "At Custom Designs TX, we design and install pro-grade surveillance systems for homes and businesses across the Rio Grande Valley "
    "— McAllen, Mission, Edinburg, Pharr, Brownsville, and beyond.\n\n"
    "What you get with us:\n"
    "\u2714 Free on-site property assessment\n"
    "\u2714 4K cameras with night vision & remote access\n"
    "\u2714 Clean, concealed installation — no exposed wires\n"
    "\u2714 Full smartphone setup & walkthrough\n"
    "\u2714 Smart home integration available\n\n"
    "We don't just hang cameras. We engineer coverage — designed around your property, your entry points, and your peace of mind.\n\n"
    "Whether you're protecting a custom home in north McAllen or a commercial property in Hidalgo County, "
    "our systems are built to perform in South Texas conditions.\n\n"
    "\U0001f4de Call or text us to schedule your FREE on-site consultation — we come to you. "
    "No pressure. Just honest answers and a system that works.\n\n"
    "#McAllenSecurity #RGVSmartHome"
)


def log(msg):
    print(f"[gbp] {msg}", flush=True)


async def post():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        log("Launching Chrome with Mario's GBP profile...")
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        log("Navigating to business.google.com/locations...")
        await page.goto("https://business.google.com/locations", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(SCRIPT_DIR / "gbp_img_step1.png"))

        # JS: find the Add update icon in the Custom Designs row
        post_clicked = await page.evaluate(
            "() => {"
            "  const rows = Array.from(document.querySelectorAll('tr'));"
            "  for (let row of rows) {"
            "    if (row.textContent.toUpperCase().includes('CUSTOM DESIGNS')) {"
            "      const btns = row.querySelectorAll('a, button, [role=\"button\"]');"
            "      for (let btn of btns) {"
            "        const aria = (btn.getAttribute('aria-label') || '').toLowerCase();"
            "        const title = (btn.getAttribute('title') || '').toLowerCase();"
            "        const text = btn.textContent.toLowerCase();"
            "        if (aria.includes('update') || aria.includes('post') ||"
            "            title.includes('update') || title.includes('post') ||"
            "            text.includes('add update') || text.includes('create post')) {"
            "          btn.click(); return aria || title || text || 'clicked';"
            "        }"
            "      }"
            "      const ab = Array.from(row.querySelectorAll('button, [role=\"button\"]'))"
            "        .filter(b => !b.textContent.includes('See your profile') && !b.textContent.includes('Manage profile'));"
            "      if (ab.length >= 3) { ab[2].click(); return '3rd-icon'; }"
            "    }"
            "  }"
            "  const all = Array.from(document.querySelectorAll('button, [role=\"button\"]'));"
            "  for (let btn of all) {"
            "    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();"
            "    if (aria.includes('add update') || aria.includes('create post')) { btn.click(); return 'global'; }"
            "  }"
            "  return null;"
            "}"
        )

        if not post_clicked:
            log("ERROR: Could not find Add update button")
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_img_error.png"))
            await ctx.close()
            return

        log(f"Clicked post button: {post_clicked}")
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(SCRIPT_DIR / "gbp_img_step2.png"))

        # Find modal iframe
        modal_frame = page
        for frame in page.frames:
            try:
                content = await frame.content()
                if "Description" in content or "Add post" in content or "Select images" in content:
                    modal_frame = frame
                    log(f"Modal frame: {frame.url or 'unnamed'}")
                    break
            except Exception:
                pass

        # Upload image
        log(f"Uploading hero image...")
        image_uploaded = False
        try:
            async with page.expect_file_chooser(timeout=8000) as fc_info:
                select_link = modal_frame.get_by_text("Select images and videos").first
                await select_link.click()
            fc = await fc_info.value
            await fc.set_files(IMAGE_PATH)
            log("Uploaded via file chooser")
            await page.wait_for_timeout(5000)
            image_uploaded = True
        except Exception as e:
            log(f"File chooser failed: {e}")
            try:
                fi = modal_frame.locator('input[type="file"]').first
                await fi.set_input_files(IMAGE_PATH)
                log("Uploaded via hidden input")
                await page.wait_for_timeout(5000)
                image_uploaded = True
            except Exception as e2:
                log(f"Image upload failed: {e2} — continuing text-only")

        await page.screenshot(path=str(SCRIPT_DIR / "gbp_img_step3.png"))
        log(f"After image upload (uploaded={image_uploaded})")

        # Fill description
        try:
            desc = modal_frame.locator('textarea[placeholder="Description"]').first
            await desc.wait_for(timeout=5000)
            await desc.click()
            await page.wait_for_timeout(300)
            await desc.fill(POST_TEXT)
            log("Description filled")
        except Exception as e:
            log(f"Placeholder textarea failed: {e}")
            try:
                desc = modal_frame.locator('textarea').first
                await desc.click()
                await desc.fill(POST_TEXT)
                log("Description filled (generic)")
            except Exception as e2:
                log(f"FATAL: textarea fill failed: {e2}")
                await ctx.close()
                return

        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCRIPT_DIR / "gbp_img_step4.png"))

        # Click Post
        posted = False
        try:
            post_btn = modal_frame.locator('button:has-text("Post")').last
            await post_btn.wait_for(timeout=5000)
            await post_btn.click()
            posted = True
        except Exception as e:
            log(f"Post button error: {e}")
            for frame in page.frames:
                try:
                    ok = await frame.evaluate(
                        "() => { const btns = Array.from(document.querySelectorAll('button'));"
                        "  for (let b of btns) { if (b.textContent.trim() === 'Post') { b.click(); return true; } }"
                        "  return false; }"
                    )
                    if ok:
                        posted = True
                        break
                except Exception:
                    pass

        await page.wait_for_timeout(5000)
        await page.screenshot(path=str(SCRIPT_DIR / "gbp_img_step5_final.png"))

        if posted:
            print("GBP_POST_OK")
            log(f"SUCCESS — posted with image={image_uploaded}")
            if SCREENPIPE_AVAILABLE:
                verify_and_notify_gbp("Custom Designs")
        else:
            log("WARNING: Post button not clicked. Check screenshots.")

        await ctx.close()


asyncio.run(post())
