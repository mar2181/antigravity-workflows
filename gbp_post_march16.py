#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gbp_post_march16.py — March 16, 2026 GBP posts for 3 accessible accounts:
  1. Sugar Shack       → gbp_sniffer_profile (Yehuda)
  2. Island Candy      → gbp_sniffer_profile (Yehuda)
  3. Custom Designs TX → gbp_mario_profile   (Mario)
"""

import asyncio, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).parent
SNIFFER_PROFILE = str(SCRIPT_DIR / "gbp_sniffer_profile")
MARIO_PROFILE   = str(SCRIPT_DIR / "gbp_mario_profile")

POSTS = [
    {
        "key":     "sugar_shack",
        "biz":     "SUGAR SHACK",
        "profile": SNIFFER_PROFILE,
        "image":   r"C:\Users\mario\fb_posts_march16\new_sugar_shack.png",
        "text": (
            "Spring break runs on sugar. ⚡🍬\n\n"
            "More energy = more fun = more memories.\n\n"
            "Stop by The Sugar Shack and fuel up on hand-picked candies that'll "
            "keep you going through beach day, dinner, and whatever adventure's next.\n\n"
            "We've got the energy boost your crew needs.\n\n"
            "Come in. Load up. Get back out there.\n\n"
            "THE SUGAR SHACK\n"
            "910 Padre Blvd, South Padre Island\n"
            "(956) 524-8009\n\n"
            "#SpringBreakFuel #CandyStore #SouthPadreIsland"
        ),
    },
    {
        "key":     "island_candy",
        "biz":     "ISLAND CANDY",
        "profile": SNIFFER_PROFILE,
        "image":   r"C:\Users\mario\fb_posts_march16\new_island_candy.png",
        "text": (
            "Spring break treat, unlocked. 🍦🍊\n\n"
            "You've been on that beach all day — you've earned this.\n\n"
            "Island Candy is serving up homemade ice cream inside Island Arcade. "
            "Pick your flavor, build your dream order, and make the afternoon even better.\n\n"
            "Starting at $3.99. Walk-ins welcome. Ice cream required.\n\n"
            "📍 Inside Island Arcade, South Padre Island, TX\n\n"
            "#SouthPadreIsland #IceCream #SpringBreak"
        ),
    },
    {
        "key":     "custom_designs",
        "biz":     "CUSTOM DESIGNS",
        "profile": MARIO_PROFILE,
        "image":   r"C:\Users\mario\custom_designs_ad_images\ad_1_after_hours_blind_spot.png",
        "text": (
            "You just locked up. Do you actually know what's happening at your business right now? 🔒\n\n"
            "Most business owners in the RGV don't — until something goes wrong.\n\n"
            "🎥 Monitor every corner of your property, 24/7\n"
            "📱 Watch live from your phone, anywhere, anytime\n"
            "⚡ Instant alerts the moment anything triggers\n"
            "🔒 Cameras and alarms working together — the complete system\n\n"
            "Custom Designs installs professional-grade security camera systems for businesses "
            "across Hidalgo and Cameron County.\n\n"
            "📞 Free on-site consultation + written quote — no obligation.\n\n"
            "👉 Message us to schedule yours today.\n\n"
            "#McAllen #RGVBusiness #SecurityCameras"
        ),
    },
]


def log(key, msg):
    print(f"[{key}] {msg}", flush=True)


async def post_one(post: dict) -> bool:
    from playwright.async_api import async_playwright

    key = post["key"]
    log(key, f"=== Starting GBP post ===")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=post["profile"],
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            log(key, "Navigating to business.google.com/locations...")
            await page.goto(
                "https://business.google.com/locations",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_{key}_step1.png"))

            # Find business row and click Create post (NOT the updates-count button)
            biz = post["biz"]
            clicked = await page.evaluate(f"""() => {{
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let row of rows) {{
                    if (row.textContent.toUpperCase().includes('{biz}')) {{
                        const btns = row.querySelectorAll('a, button, [role="button"]');
                        // Pass 1: exact "create post" match only
                        for (let btn of btns) {{
                            const aria  = (btn.getAttribute('aria-label') || '').toLowerCase();
                            const title = (btn.getAttribute('title') || '').toLowerCase();
                            const text  = btn.textContent.trim().toLowerCase();
                            if (aria.includes('create post') || title.includes('create post') ||
                                text === 'create post' || text === 'add update') {{
                                btn.click();
                                return 'pass1: ' + (aria || title || text);
                            }}
                        }}
                        // Pass 2: fallback — 3rd action button in the row
                        // (edit pencil = 1st, photos = 2nd, create post = 3rd typically)
                        const actionBtns = Array.from(row.querySelectorAll('button, [role="button"]'))
                            .filter(b => !b.textContent.includes('See your profile') &&
                                        !b.textContent.includes('Manage profile') &&
                                        !/\\d+ google update/i.test(b.textContent));
                        if (actionBtns.length >= 3) {{
                            actionBtns[2].click();
                            return 'pass2: 3rd icon';
                        }} else if (actionBtns.length > 0) {{
                            actionBtns[actionBtns.length - 1].click();
                            return 'pass2: last icon (' + actionBtns.length + ')';
                        }}
                    }}
                }}
                return null;
            }}""")
            log(key, f"Row click result: {clicked}")
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_{key}_step2.png"))

            # Find modal frame
            modal_frame = None
            for frame in page.frames:
                try:
                    content = await frame.content()
                    if "Description" in content or "Add post" in content or "Select images" in content:
                        modal_frame = frame
                        log(key, f"Modal frame: {frame.url or 'unnamed'}")
                        break
                except Exception:
                    pass
            if modal_frame is None:
                modal_frame = page
                log(key, "No iframe found — using main page")

            # Upload image
            log(key, f"Uploading image: {post['image']}")
            try:
                async with page.expect_file_chooser(timeout=8000) as fc_info:
                    await modal_frame.get_by_text("Select images and videos").first.click()
                fc = await fc_info.value
                await fc.set_files(post["image"])
                log(key, "Image uploaded via file chooser")
                await page.wait_for_timeout(4000)
            except Exception as e:
                log(key, f"File chooser failed: {e} — trying hidden input...")
                try:
                    await modal_frame.locator('input[type="file"]').first.set_input_files(post["image"])
                    log(key, "Image uploaded via hidden input")
                    await page.wait_for_timeout(4000)
                except Exception as e2:
                    log(key, f"Hidden input also failed: {e2}")
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_{key}_step3_image.png"))

            # Fill description
            log(key, "Filling description...")
            try:
                desc = modal_frame.locator('textarea[placeholder="Description"]').first
                await desc.wait_for(timeout=5000)
                await desc.click()
                await desc.fill(post["text"])
                log(key, "Text filled")
            except Exception as e:
                log(key, f"Textarea[placeholder] failed: {e} — trying generic...")
                try:
                    desc = modal_frame.locator("textarea").first
                    await desc.click()
                    await desc.fill(post["text"])
                    log(key, "Text filled via generic textarea")
                except Exception as e2:
                    log(key, f"Text fill failed: {e2}")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_{key}_step4_text.png"))

            # Click Post
            log(key, "Clicking Post button...")
            published = False
            try:
                post_btn = modal_frame.locator('button:has-text("Post")').last
                await post_btn.wait_for(timeout=5000)
                await post_btn.click()
                published = True
                log(key, "Clicked Post button")
            except Exception as e:
                log(key, f"Post button error: {e} — trying JS fallback...")
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
                            published = True
                            log(key, "Post clicked via JS fallback")
                            break
                    except Exception:
                        pass

            await page.wait_for_timeout(4000)
            await page.screenshot(path=str(SCRIPT_DIR / f"gbp_{key}_step5_final.png"), full_page=True)
            log(key, f"{'✅ Posted!' if published else '⚠️  Check screenshots.'}")
            return published

        except Exception as e:
            log(key, f"❌ Error: {e}")
            try:
                await page.screenshot(path=str(SCRIPT_DIR / f"gbp_{key}_error.png"))
            except Exception:
                pass
            return False
        finally:
            await page.wait_for_timeout(2000)
            await context.close()


async def main():
    print("\n=== GBP Posts — March 16, 2026 ===\n", flush=True)
    for post in POSTS:
        success = await post_one(post)
        status = "✅ Success" if success else "⚠️  Check screenshots"
        print(f"  {post['key']}: {status}\n", flush=True)
        if post is not POSTS[-1]:
            print("Waiting 5s before next account...\n", flush=True)
            await asyncio.sleep(5)
    print("=== All GBP posts done ===", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
