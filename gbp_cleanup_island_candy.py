#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gbp_cleanup_island_candy.py — Delete the "Test post" from Island Candy GBP.
Approach: locations → click business name → NMX dashboard → click Posts tab → delete test post.
Business ID: 4798477906868509722 | Profile: gbp_sniffer_profile (Yehuda)
"""

import asyncio, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_sniffer_profile")
SNAP = 0


def log(msg): print(f"[cleanup] {msg}", flush=True)


async def snap(page, label):
    global SNAP
    SNAP += 1
    path = str(SCRIPT_DIR / f"cleanup_{SNAP:02d}_{label}.png")
    await page.screenshot(path=path, full_page=True)
    log(f"  snap {SNAP}: {label}")


async def cleanup():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False,
            args=["--start-maximized"], no_viewport=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            try:
                await page.keyboard.press("Escape")
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            except Exception:
                pass

            # STEP 1: Navigate to locations
            log("STEP 1: Opening locations page...")
            await page.goto("https://business.google.com/locations", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)
            await snap(page, "locations")

            # STEP 2: Click Island Candy name to open NMX dashboard
            log("STEP 2: Clicking Island Candy name link...")
            await page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let row of rows) {
                    if (row.textContent.toUpperCase().includes('ISLAND CANDY')) {
                        const link = row.querySelector('a[href]');
                        if (link) { link.click(); return true; }
                    }
                }
                return false;
            }""")
            await page.wait_for_timeout(5000)
            await snap(page, "nmx_dashboard")
            log(f"  URL: {page.url}")

            # STEP 3: Click the "Posts" button on the NMX dashboard
            # The button text appears as "postsposts" (icon + label), so use includes
            log("STEP 3: Clicking Posts tab on NMX dashboard...")
            posts_clicked = False
            for frame in page.frames:
                try:
                    result = await frame.evaluate("""() => {
                        const btns = document.querySelectorAll('button, [role="tab"], a');
                        for (let btn of btns) {
                            const text = btn.textContent.trim().toLowerCase();
                            // Match "posts" but NOT "add update" or "create post"
                            if (text.includes('posts') && !text.includes('add') && !text.includes('create')
                                && btn.offsetParent !== null) {
                                btn.click();
                                return 'clicked: ' + text.slice(0, 40);
                            }
                        }
                        return null;
                    }""")
                    if result:
                        log(f"  Posts tab: {result}")
                        posts_clicked = True
                        break
                except Exception:
                    pass

            if not posts_clicked:
                log("  Posts tab not found via text. Trying aria-label...")
                for frame in page.frames:
                    try:
                        result = await frame.evaluate("""() => {
                            const btns = document.querySelectorAll('button, [role="tab"], a, div[role="button"]');
                            for (let btn of btns) {
                                const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                                if (aria.includes('posts') && !aria.includes('create') && btn.offsetParent !== null) {
                                    btn.click();
                                    return 'clicked aria: ' + aria;
                                }
                            }
                            return null;
                        }""")
                        if result:
                            log(f"  Posts tab: {result}")
                            posts_clicked = True
                            break
                    except Exception:
                        pass

            await page.wait_for_timeout(4000)
            await snap(page, "posts_tab_clicked")

            # STEP 4: We should now see the posts list. Scan for "Test post"
            log("STEP 4: Scanning for 'Test post' in all frames...")
            test_post_frame = None
            for fi, frame in enumerate(page.frames):
                try:
                    found = await frame.evaluate("""() => {
                        const text = document.body ? document.body.innerText : '';
                        if (text.includes('Test post')) {
                            // Also get a content preview
                            return {found: true, preview: text.slice(0, 800)};
                        }
                        return {found: false};
                    }""")
                    if found.get('found'):
                        log(f"  FOUND 'Test post' in frame {fi}")
                        test_post_frame = frame
                        break
                except Exception:
                    pass

            if not test_post_frame:
                log("  'Test post' NOT found. Checking if page shows posts at all...")
                # Dump what we see
                for fi, frame in enumerate(page.frames):
                    try:
                        preview = await frame.evaluate("() => (document.body ? document.body.innerText : '').slice(0, 300)")
                        if preview and len(preview) > 20:
                            log(f"  Frame {fi}: {preview[:150]}")
                    except Exception:
                        pass
                await snap(page, "no_test_post_found")
                log("RESULT: Test post not found. It may have been auto-removed by Google.")
                log("CHECK SCREENSHOTS to see what posts currently exist.")
                return "not_found"

            # STEP 5: Click the Test post itself to open its detail view
            log("STEP 5: Clicking on Test post to open detail view...")
            click_result = await test_post_frame.evaluate("""() => {
                const allElements = document.querySelectorAll('*');
                for (let el of allElements) {
                    if (el.children.length === 0 && el.textContent.trim().startsWith('Test post')) {
                        // Click the text element or its parent (the post card)
                        el.click();
                        return 'clicked test post text element';
                    }
                }
                return 'not found';
            }""")
            log(f"  Click result: {click_result}")
            await page.wait_for_timeout(3000)
            await snap(page, "post_detail_opened")

            # STEP 5b: Now in detail view, dump ALL buttons to find delete
            log("STEP 5b: Looking for delete in detail view...")
            for fi, frame in enumerate(page.frames):
                try:
                    all_btns = await frame.evaluate("""() => {
                        const btns = document.querySelectorAll('button, [role="button"], a, [role="menuitem"]');
                        return Array.from(btns).filter(b => b.offsetParent !== null).map(b => ({
                            text: b.textContent.trim().slice(0, 50),
                            aria: b.getAttribute('aria-label') || '',
                            tag: b.tagName,
                            href: (b.getAttribute('href') || '').slice(0, 50)
                        }));
                    }""")
                    if all_btns and len(all_btns) > 0:
                        # Filter to interesting ones
                        interesting = [b for b in all_btns if any(w in (b.get('text','') + b.get('aria','')).lower()
                            for w in ['delete', 'remove', 'more', 'option', 'menu', 'trash', 'edit', 'overflow'])]
                        if interesting:
                            log(f"  Frame {fi} interesting buttons: {interesting}")
                        else:
                            log(f"  Frame {fi}: {len(all_btns)} buttons, none with delete/more/menu")
                except Exception:
                    pass

            await snap(page, "detail_view_buttons")

            # Try clicking a 3-dot/more menu in the detail view
            menu_result = None
            for frame in page.frames:
                try:
                    result = await frame.evaluate("""() => {
                        const btns = document.querySelectorAll('button, [role="button"]');
                        for (let btn of btns) {
                            const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                            const text = btn.textContent.trim().toLowerCase();
                            // Look for more/options/overflow menu
                            if ((aria.includes('more') || aria.includes('option') || aria.includes('menu') ||
                                 aria.includes('overflow') || text === '⋮' || text === '...') &&
                                !aria.includes('previous') && !aria.includes('next') &&
                                btn.offsetParent !== null) {
                                btn.click();
                                return 'clicked: aria=' + aria + ' text=' + text;
                            }
                        }
                        return null;
                    }""")
                    if result:
                        menu_result = result
                        log(f"  More menu: {result}")
                        break
                except Exception:
                    pass

            if not menu_result:
                log("  No more/options menu found. Trying to find delete button directly...")

            await page.wait_for_timeout(1500)
            await snap(page, "after_more_menu")
            log(f"  Menu result: {menu_result}")
            await page.wait_for_timeout(2000)
            await snap(page, "menu_opened")

            # STEP 6: Click Delete in the menu
            log("STEP 6: Clicking Delete...")
            deleted = False
            for frame in page.frames:
                try:
                    result = await frame.evaluate("""() => {
                        const items = document.querySelectorAll(
                            '[role="menuitem"], [role="option"], li, button, a, span, div'
                        );
                        for (let item of items) {
                            const text = item.textContent.trim().toLowerCase();
                            if ((text === 'delete' || text === 'delete post' || text === 'delete update' || text === 'remove')
                                && item.offsetParent !== null) {
                                item.click();
                                return 'clicked: ' + text;
                            }
                        }
                        return null;
                    }""")
                    if result:
                        log(f"  Delete: {result}")
                        deleted = True
                        break
                except Exception:
                    pass

            await page.wait_for_timeout(2000)
            await snap(page, "delete_clicked")

            # STEP 7: Confirm deletion
            log("STEP 7: Confirming deletion...")
            for frame in page.frames:
                try:
                    result = await frame.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        for (let b of btns) {
                            const text = b.textContent.trim().toLowerCase();
                            if ((text === 'delete' || text === 'confirm' || text === 'yes' || text === 'ok')
                                && b.offsetParent !== null) {
                                b.click();
                                return 'confirmed: ' + text;
                            }
                        }
                        return null;
                    }""")
                    if result:
                        log(f"  Confirm: {result}")
                        break
                except Exception:
                    pass

            await page.wait_for_timeout(3000)
            await snap(page, "confirmed")

            # STEP 8: Final verification
            log("STEP 8: Final verification...")
            await page.wait_for_timeout(2000)
            await snap(page, "final")

            still_exists = False
            for frame in page.frames:
                try:
                    exists = await frame.evaluate("() => (document.body?.innerText || '').includes('Test post')")
                    if exists:
                        still_exists = True
                        break
                except Exception:
                    pass

            if still_exists:
                log("WARNING: 'Test post' still visible after deletion attempt")
                return "still_exists"
            else:
                log("SUCCESS: 'Test post' no longer visible")
                return "deleted"

        except Exception as e:
            log(f"ERROR: {e}")
            try:
                await snap(page, "error")
            except Exception:
                pass
            return "error"
        finally:
            await page.wait_for_timeout(2000)
            await ctx.close()


if __name__ == "__main__":
    result = asyncio.run(cleanup())
    log(f"=== FINAL: {result} ===")
