#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gbp_post_sugar_shack.py — Post latest blog GBP content to Sugar Shack GBP (Yehuda account)"""

import asyncio, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

try:
    from screenpipe_verifier import verify_and_notify_gbp
    SCREENPIPE_AVAILABLE = True
except ImportError:
    SCREENPIPE_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_sniffer_profile")  # Yehuda's GBP account
BUSINESS_NAME = "SUGAR SHACK"

# Load latest blog meta
_meta_dir = SCRIPT_DIR / "blog_posts" / "sugar_shack"
_metas = sorted(_meta_dir.glob("*_meta.json"))
if not _metas:
    print("❌ No Sugar Shack meta file found"); sys.exit(1)
_meta = json.loads(_metas[-1].read_text(encoding="utf-8"))
TEXT  = _meta.get("gbp", "")
IMAGE = _meta.get("images", {}).get("hero", "")
print(f"Meta: {_metas[-1].name}")
print(f"Image: {IMAGE}  exists={Path(IMAGE).exists() if IMAGE else False}")


def log(msg): print(f"[gbp_sugar_shack] {msg}", flush=True)


async def post():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False,
            args=["--start-maximized"], no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            log("Navigating to business.google.com/locations...")
            await page.goto("https://business.google.com/locations", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ss_step1.png"))

            log(f"Finding '{BUSINESS_NAME}' row and clicking Add update...")
            row_buttons = await page.evaluate(f"""() => {{
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let row of rows) {{
                    if (row.textContent.toUpperCase().includes('{BUSINESS_NAME}')) {{
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
                    if (row.textContent.toUpperCase().includes('{BUSINESS_NAME}')) {{
                        const btns = row.querySelectorAll('a, button, [role="button"]');
                        for (let btn of btns) {{
                            const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                            const title = (btn.getAttribute('title') || '').toLowerCase();
                            if (aria.includes('create post') || title.includes('create post')) {{
                                btn.click(); return aria || title || 'create post clicked';
                            }}
                        }}
                    }}
                }}
                return null;
            }}""")
            log(f"Clicked: {clicked}")
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ss_step2.png"))

            # Find modal frame
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
                modal_frame = page

            # Upload image
            log("Uploading image...")
            try:
                async with page.expect_file_chooser(timeout=8000) as fc_info:
                    await modal_frame.get_by_text("Select images and videos").first.click()
                fc = await fc_info.value
                await fc.set_files(IMAGE)
                log("Image uploaded via file chooser")
                await page.wait_for_timeout(4000)
            except Exception as e:
                log(f"File chooser failed: {e}, trying hidden input...")
                try:
                    await modal_frame.locator('input[type="file"]').first.set_input_files(IMAGE)
                    await page.wait_for_timeout(4000)
                except Exception as e2:
                    log(f"Hidden input also failed: {e2}")
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ss_step3.png"))

            # Fill text
            log("Filling description...")
            try:
                desc = modal_frame.locator('textarea[placeholder="Description"]').first
                await desc.wait_for(timeout=5000)
                await desc.click()
                await desc.fill(TEXT)
                log("Text filled")
            except Exception as e:
                log(f"Textarea error: {e}")
                try:
                    desc = modal_frame.locator('textarea').first
                    await desc.click()
                    await desc.fill(TEXT)
                    log("Text filled via generic textarea")
                except Exception as e2:
                    log(f"Text fill failed: {e2}")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ss_step4.png"))

            # Click Post
            log("Clicking Post...")
            published = False
            try:
                post_btn = modal_frame.locator('button:has-text("Post")').last
                await post_btn.wait_for(timeout=5000)
                await post_btn.click()
                published = True
                log("Clicked Post button")
            except Exception as e:
                log(f"Post button error: {e}")
                for frame in page.frames:
                    try:
                        result = await frame.evaluate("""() => {
                            const btns = Array.from(document.querySelectorAll('button'));
                            for (let b of btns) { if (b.textContent.trim() === 'Post') { b.click(); return true; } }
                            return false;
                        }""")
                        if result:
                            published = True
                            log("Post clicked via JS fallback")
                            break
                    except Exception:
                        pass

            await page.wait_for_timeout(4000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ss_step5_final.png"), full_page=True)
            if published and SCREENPIPE_AVAILABLE:
                verify_and_notify_gbp("Sugar Shack")
            log(f"{'Posted OK!' if published else 'Check screenshots.'}")
            return published
        except Exception as e:
            log(f"❌ Error: {e}")
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ss_error.png"))
            return False
        finally:
            await page.wait_for_timeout(2000)
            await context.close()


if __name__ == "__main__":
    asyncio.run(post())
