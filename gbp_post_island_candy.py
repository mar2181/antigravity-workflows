#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gbp_post_island_candy.py — Post to Island Candy GBP (Yehuda account)
Reads latest *_meta.json from blog_posts/island_candy/ for text and image.

IMPORTANT: After clicking Post, Google shows a "Copy post" dialog in an IFRAME.
The Skip button lives in that iframe (usually frame index 2), NOT the main page.
We must search ALL frames for a <button> with text "Skip" and click it to finalize.
Without this step, the post is NOT published. Do NOT remove this logic."""

import asyncio, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

try:
    from screenpipe_verifier import verify_and_notify_gbp
    SCREENPIPE_AVAILABLE = True
except ImportError:
    SCREENPIPE_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_sniffer_profile")
BUSINESS_NAME = "ISLAND CANDY"

# Load latest blog meta
_meta_dir = SCRIPT_DIR / "blog_posts" / "island_candy"
_metas = sorted(_meta_dir.glob("*_meta.json"))
if not _metas:
    print("No Island Candy meta file found"); sys.exit(1)
_meta = json.loads(_metas[-1].read_text(encoding="utf-8"))
TEXT = _meta.get("gbp", "")
IMAGE = _meta.get("images", {}).get("hero", "")
print(f"Meta: {_metas[-1].name}")
print(f"Image: {IMAGE}  exists={Path(IMAGE).exists() if IMAGE else False}")


def log(msg): print(f"[gbp_island_candy] {msg}", flush=True)


async def _click_skip_in_copy_dialog(page):
    """CRITICAL: After clicking Post, Google shows 'Copy post to other profiles' dialog.
    The Skip button is a <button> with text 'Skip' inside an IFRAME (not the main page).
    We MUST click Skip to finalize the post. Without this, the post is NOT published.

    Strategy: search ALL frames for a button whose text is exactly 'Skip'.
    Do NOT break early on Close/Back buttons — those are on the outer page and do nothing."""
    log("STEP: Dismissing 'Copy post' dialog (clicking Skip in iframe)...")

    for attempt in range(3):  # Retry up to 3 times
        for frame in page.frames:  # Search iframes first (skip main page)
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

        # Also try main page
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


async def post():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False,
            args=["--start-maximized"], no_viewport=True,
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

            log("Navigating to business.google.com/locations...")
            await page.goto("https://business.google.com/locations", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ic_step1.png"))

            log(f"Finding '{BUSINESS_NAME}' row and clicking Create post...")
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
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ic_step2.png"))

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
            if IMAGE and Path(IMAGE).exists():
                log(f"Uploading image: {Path(IMAGE).name}")
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
            else:
                log("No image specified or file not found — posting text only")
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ic_step3.png"))

            # Fill text
            log("Filling description...")
            try:
                desc = modal_frame.locator('textarea[placeholder="Description"]').first
                await desc.wait_for(timeout=5000)
                await desc.click()
                await desc.fill(TEXT)
                log("Text filled")
            except Exception as e:
                log(f"Textarea placeholder not found: {e}")
                try:
                    desc = modal_frame.locator('textarea').first
                    await desc.click()
                    await desc.fill(TEXT)
                    log("Text filled via generic textarea")
                except Exception as e2:
                    log(f"Text fill FAILED: {e2}")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ic_step4.png"))

            # Click Post (this opens the "Copy post" dialog — does NOT publish yet)
            log("Clicking Post button (opens Copy dialog)...")
            published = False
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
                            for (let b of btns) { if (b.textContent.trim() === 'Post') { b.click(); return true; } }
                            return false;
                        }""")
                        if result:
                            log("Post clicked via JS fallback")
                            break
                    except Exception:
                        pass

            await page.wait_for_timeout(6000)
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ic_step5_copy_dialog.png"))

            # CRITICAL: Click Skip in the Copy post dialog to actually publish
            published = await _click_skip_in_copy_dialog(page)

            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ic_step6_final.png"), full_page=True)
            if published and SCREENPIPE_AVAILABLE:
                verify_and_notify_gbp("Island Candy")

            if published:
                log("POST CONFIRMED: Island Candy GBP update is live")
            else:
                log("WARNING: Post may not have published — check GBP manually")
            return published
        except Exception as e:
            log(f"ERROR: {e}")
            await page.screenshot(path=str(SCRIPT_DIR / "gbp_ic_error.png"))
            return False
        finally:
            await page.wait_for_timeout(2000)
            await context.close()


if __name__ == "__main__":
    asyncio.run(post())
