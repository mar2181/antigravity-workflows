#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gbp_extract_sugar_shack_reviews.py
Opens GBP reviews page (Yehuda), filters to Sugar Shack, expands all review text,
extracts full review data, saves JSON + screenshots.
"""

import asyncio, sys, json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
PROFILE_DIR = str(SCRIPT_DIR / "gbp_sniffer_profile")
OUTPUT_FILE = SCRIPT_DIR / "sugar_shack_reviews.json"
REVIEWS_URL = "https://business.google.com/reviews"

def log(msg): print(f"[ss_reviews] {msg}", flush=True)


async def extract():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        all_reviews = []
        try:
            log("Loading reviews page...")
            await page.goto(REVIEWS_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCRIPT_DIR / "ss_rev_1_loaded.png"))

            # Try to use filter button to show only Sugar Shack
            log("Looking for filter/sort button...")
            try:
                filter_btn = page.locator('[aria-label*="filter"], [aria-label*="Filter"], button:has-text("Filter")').first
                if await filter_btn.is_visible(timeout=3000):
                    await filter_btn.click()
                    await page.wait_for_timeout(1500)
                    await page.screenshot(path=str(SCRIPT_DIR / "ss_rev_2_filter_open.png"))
                    log("Filter menu opened")
            except Exception as e:
                log(f"No filter button found: {e}")

            # Try the sort/filter icon (the lines icon at top right of content)
            try:
                sort_icon = page.locator('button[aria-label*="Sort"], [data-tooltip*="Sort"], .sort-button').first
                if await sort_icon.is_visible(timeout=2000):
                    await sort_icon.click()
                    await page.wait_for_timeout(1500)
                    log("Sort/filter icon clicked")
                    await page.screenshot(path=str(SCRIPT_DIR / "ss_rev_2b_sort_open.png"))
            except Exception:
                pass

            # Expand all "More" links to get full review text
            log("Expanding all truncated reviews...")
            more_links = page.locator('a:has-text("More"), span:has-text("More")')
            count = await more_links.count()
            log(f"Found {count} 'More' links to expand")
            for i in range(count):
                try:
                    await more_links.nth(i).click()
                    await page.wait_for_timeout(300)
                except Exception:
                    pass

            await page.screenshot(path=str(SCRIPT_DIR / "ss_rev_3_expanded.png"), full_page=True)

            # Scroll to load more reviews
            log("Scrolling to load all reviews...")
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(800)
                # Expand any new "More" links
                more_links2 = page.locator('a:has-text("More"), span:has-text("More")')
                c2 = await more_links2.count()
                for i in range(c2):
                    try:
                        await more_links2.nth(i).click()
                        await page.wait_for_timeout(200)
                    except Exception:
                        pass

            await page.screenshot(path=str(SCRIPT_DIR / "ss_rev_4_all_loaded.png"), full_page=True)

            # Extract all review cards from page
            log("Extracting review data...")
            reviews_raw = await page.evaluate("""() => {
                const results = [];
                // Each review block has a business name + reviewer section
                const cards = Array.from(document.querySelectorAll('[data-cardloc], .WNxzHc, .Jtu6Td'));

                // Fallback: find all review sections by structure
                // Look for sections that contain star ratings
                const sections = Array.from(document.querySelectorAll('div[jscontroller], section, article'));

                // Best approach: find all reviewer name elements
                const reviewerEls = Array.from(document.querySelectorAll('.d6SCIc, .reviewer-name, [class*="reviewer"]'));

                // Actually let's just extract all text blocks near star ratings
                // Find all star rating icons
                const starEls = Array.from(document.querySelectorAll('[aria-label*="star"], [role="img"][aria-label*="star"]'));

                const seen = new Set();
                for (const star of starEls) {
                    try {
                        // Walk up to find the review container
                        let container = star.closest('li, [jsaction*="review"], .gws-reviews__review, div[data-review-id]');
                        if (!container) {
                            // Go up a few levels
                            let el = star;
                            for (let i = 0; i < 6; i++) {
                                el = el.parentElement;
                                if (!el) break;
                                if (el.innerText && el.innerText.length > 50) {
                                    container = el;
                                    break;
                                }
                            }
                        }
                        if (!container || seen.has(container)) continue;
                        seen.add(container);

                        const text = container.innerText || '';
                        const ariaLabel = star.getAttribute('aria-label') || '';
                        const stars = ariaLabel.match(/(\\d+)/)?.[1] || '?';
                        results.push({ stars, text: text.trim().slice(0, 2000) });
                    } catch(e) {}
                }

                return results;
            }""")

            log(f"Raw extraction: {len(reviews_raw)} items")

            # Better extraction: get the full page text and parse it
            page_text = await page.evaluate("() => document.body.innerText")

            # Parse review blocks from structured content
            structured = await page.evaluate("""() => {
                const out = [];

                // Try to find review rows/cards by looking for elements with both
                // a business name (Sugar Shack or Island Candy) and a star rating
                const allDivs = Array.from(document.querySelectorAll('div, li, section'));
                const seen = new Set();

                for (const div of allDivs) {
                    const text = (div.innerText || '').trim();
                    if (text.length < 30 || text.length > 5000) continue;

                    // Must contain a business reference and have a rating
                    const hasBiz = text.includes('Sugar Shack') || text.includes('Island Candy') || text.includes('The Sugar');
                    const hasRating = div.querySelector('[aria-label*="star"]') !== null;

                    if (hasBiz && hasRating && !seen.has(text.slice(0, 100))) {
                        seen.add(text.slice(0, 100));

                        // Extract star count
                        const starEl = div.querySelector('[aria-label*="star"]');
                        const ariaLabel = starEl ? starEl.getAttribute('aria-label') : '';
                        const stars = ariaLabel.match(/(\\d+)/)?.[1] || '?';

                        // Determine business
                        const biz = text.includes('Sugar Shack') ? 'Sugar Shack' : 'Island Candy';

                        out.push({
                            business: biz,
                            stars: parseInt(stars),
                            text: text
                        });
                    }
                }

                return out;
            }""")

            log(f"Structured extraction: {len(structured)} items")

            # Filter to Sugar Shack only, 1-3 stars
            ss_negative = [r for r in structured if r.get('business') == 'Sugar Shack' and r.get('stars', 5) <= 3]
            log(f"Sugar Shack negative reviews (≤3 stars): {len(ss_negative)}")

            # Save full data
            output = {
                'all_reviews': structured,
                'sugar_shack_negative': ss_negative,
                'page_text_sample': page_text[:3000]
            }
            OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
            log(f"✅ Saved to {OUTPUT_FILE}")

            # Print Sugar Shack negative reviews
            log("\n===== SUGAR SHACK NEGATIVE REVIEWS =====")
            for i, r in enumerate(ss_negative[:10], 1):
                log(f"\n--- Review #{i} ({r['stars']} stars) ---")
                # Show only relevant lines (not the full card text)
                lines = r['text'].split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 5:
                        log(f"  {line}")

            if not ss_negative:
                log("No structured Sugar Shack negatives found — dumping full page text for manual review")
                log(page_text[:4000])

            await page.screenshot(path=str(SCRIPT_DIR / "ss_rev_5_final.png"), full_page=True)

        except Exception as e:
            log(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=str(SCRIPT_DIR / "ss_rev_error.png"))
        finally:
            await context.close()
            log("Browser closed.")


if __name__ == "__main__":
    asyncio.run(extract())
