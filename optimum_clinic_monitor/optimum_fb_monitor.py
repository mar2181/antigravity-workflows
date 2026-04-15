#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimum Clinic Facebook Group Monitor
Monitors 23+ RGV oilfield/trucking/refinery Facebook groups for keywords
like "DOT physical", "drug test", "pre-employment", "CDL medical"
and auto-responds with Optimum Clinic info.

Usage (Windows):
  Use Python 3.10: C:/Users/mario/AppData/Local/Programs/Python/Python310/python.exe
  python optimum_fb_monitor.py --monitor
  python optimum_fb_monitor.py --post-all
  python optimum_fb_monitor.py --test
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────

WINDOWS_BASE = Path(r"C:/Users/mario/.gemini/antigravity/tools/execution")
PROFILE_DIR = str(WINDOWS_BASE / "facebook_mario_profile")
STATE_FILE = WINDOWS_BASE / "optimum_clinic_monitor" / "monitor_state.json"
LOG_FILE = WINDOWS_BASE / "optimum_clinic_monitor" / "monitor.log"

STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

GROUPS = [
    # CDL/Trucking (HIGH PRIORITY)
    {"url": "https://www.facebook.com/groups/1013746516693122/", "name": "Cdl jobs RGV", "category": "cdl", "priority": "high"},
    {"url": "https://www.facebook.com/groups/870723480480940/", "name": "CDL DRIVERS RIO GRANDE VALLEY", "category": "cdl", "priority": "high"},
    {"url": "https://www.facebook.com/groups/501675461926929/", "name": "RGV CDL & Hotshot drivers", "category": "cdl", "priority": "high"},
    {"url": "https://www.facebook.com/groups/562405257106552/", "name": "RGV Truck Drivers", "category": "cdl", "priority": "high"},
    {"url": "https://www.facebook.com/groups/679183069326222/", "name": "CDL Class A Driver Hotshot McAllen", "category": "cdl", "priority": "high"},
    # Oilfield
    {"url": "https://www.facebook.com/groups/255624324572045/", "name": "South Texas Oil Field Workers", "category": "oilfield", "priority": "medium"},
    {"url": "https://www.facebook.com/groups/756425147779769/", "name": "Oilfield Job Fair", "category": "oilfield", "priority": "medium"},
    {"url": "https://www.facebook.com/groups/808791922195758/", "name": "Real Oilfield jobs", "category": "oilfield", "priority": "medium"},
    {"url": "https://www.facebook.com/groups/7030751236997136/", "name": "Koch Specialty Plant Services McAllen", "category": "oilfield", "priority": "medium"},
    {"url": "https://www.facebook.com/groups/1411334002431699/", "name": "ABOUT SOUTH TEXAS", "category": "general", "priority": "low"},
    # Refinery
    {"url": "https://www.facebook.com/groups/800112602044805/", "name": "Refinery Jobs Texas", "category": "refinery", "priority": "medium"},
    # Additional groups from search (names unknown)
    {"url": "https://www.facebook.com/groups/1206689270003516/", "name": "Unknown Group 1", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/1251880415269178/", "name": "Unknown Group 2", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/1577236383312313/", "name": "Unknown Group 3", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/1771038946493495/", "name": "Unknown Group 4", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/204832344246804/", "name": "Unknown Group 5", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/253158925338411/", "name": "Unknown Group 6", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/2824170354516964/", "name": "Unknown Group 7", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/318840269360467/", "name": "Unknown Group 8", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/3802316020021940/", "name": "Unknown Group 9", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/458372128296339/", "name": "Unknown Group 10", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/475198616347449/", "name": "Unknown Group 11", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/479896960399056/", "name": "Unknown Group 12", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/533047550714924/", "name": "Unknown Group 13", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/790799450544606/", "name": "Unknown Group 14", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/8038163819/", "name": "Unknown Group 15", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/822724358478799/", "name": "Unknown Group 16", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/840098781196047/", "name": "Unknown Group 17", "category": "unknown", "priority": "low"},
    {"url": "https://www.facebook.com/groups/941540563421854/", "name": "Unknown Group 18", "category": "unknown", "priority": "low"},
]

KEYWORDS = [
    "dot physical", "dot physicals", "drug test", "drug tests",
    "drug screening", "drug screen", "pre-employment", "pre employment",
    "cdl medical", "cdl exam", "medical exam", "physical exam",
    "dot certification", "dot card", "cdl physical", "truck driver physical",
    "oilfield physical", "refinery physical", "work physical",
    "employment physical", "job physical", "hiring physical",
    "dot drug test", "5-panel drug test", "10-panel drug test",
]

RESPONSE_TEMPLATES = [
    "Hey! Optimum Clinic in Pharr does DOT physicals and drug screens. Open until 10 PM, $75 cash. Perfect for night shift workers. No appointment needed — just walk in.",
    "You can get your DOT physical + drug screen at Optimum Clinic in Pharr. They're open until 10 PM (only clinic in the area with late hours). $75 cash pay. Walk-ins welcome.",
    "Optimum Clinic (Pharr) — DOT physicals, drug screens, pre-employment exams. Open till 10 PM, $75 cash. Great for CDL drivers and oilfield workers who can't do 9-to-5.",
    "Try Optimum Clinic in Pharr for DOT physicals and drug testing. $75, open until 10 PM, no insurance needed. Walk in after your shift.",
]

# ─── Helpers ────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except IOError:
        pass

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"responded_posts": {}, "last_check": {}}
    return {"responded_posts": {}, "last_check": {}}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)

def contains_keyword(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)

def get_response_template(post_id: str) -> str:
    idx = hash(post_id) % len(RESPONSE_TEMPLATES)
    return RESPONSE_TEMPLATES[idx]

# ─── Core Functions ─────────────────────────────────────────────────────────

async def extract_recent_posts(page, max_posts: int = 15) -> list:
    """Extract recent posts from the current group page."""
    posts = []
    try:
        # Scroll to load posts
        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

        # Try to find post elements
        # Facebook's class names are obfuscated, so we use role-based selectors
        selectors = [
            "div[role='article']",
            "article",
            "div[data-visualcompletion='ignore']",
        ]

        elements = []
        for sel in selectors:
            try:
                elements = await page.query_selector_all(sel)
                if elements:
                    break
            except Exception:
                continue

        if not elements:
            log("WARNING: No post elements found")
            return []

        for el in elements[:max_posts]:
            try:
                text = await el.inner_text()
                if not text or len(text.strip()) < 30:
                    continue

                post_id = await el.get_attribute("id") or str(hash(text))
                posts.append({
                    "text": text,
                    "post_id": post_id,
                    "element": el,
                })
            except Exception:
                continue

        log(f"Extracted {len(posts)} posts from group")
        return posts

    except Exception as e:
        log(f"ERROR extracting posts: {e}")
        return []

async def respond_to_post(page, post_element, response_text: str) -> bool:
    """Click comment on a post, type response, and submit."""
    try:
        # Scroll post into view
        await post_element.scroll_into_view_if_needed()
        await asyncio.sleep(1)

        # Find and click "Comment" button
        comment_btn = await page.query_selector("div[aria-label='Comment']")
        if not comment_btn:
            # Try alternative: find by text
            comment_btn = await page.query_selector("text=Comment")
        if not comment_btn:
            log("WARNING: Could not find Comment button")
            return False

        await comment_btn.click()
        await asyncio.sleep(2)

        # Find the comment input box
        input_box = await page.query_selector("div[contenteditable='true'][role='textbox']")
        if not input_box:
            input_box = await page.query_selector("textarea[aria-label*='Comment']")
        if not input_box:
            log("WARNING: Could not find comment input")
            return False

        # Type response
        await input_box.fill("")
        await input_box.type(response_text, delay=30)
        await asyncio.sleep(1)

        # Find and click Reply/Post button
        reply_btn = await page.query_selector("div[aria-label='Reply']")
        if not reply_btn:
            reply_btn = await page.query_selector("text=Reply")
        if not reply_btn:
            # Fallback: press Enter
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
            log("SUCCESS: Response posted (via Enter)")
            return True

        await reply_btn.click()
        await asyncio.sleep(2)
        log("SUCCESS: Response posted")
        return True

    except Exception as e:
        log(f"ERROR responding to post: {e}")
        return False

# ─── Mode: Monitor ──────────────────────────────────────────────────────────

async def mode_monitor(max_groups: int = None, dry_run: bool = False):
    log("=" * 60)
    log("STARTING OPTIMUM CLINIC FB MONITOR")
    log("=" * 60)

    state = load_state()
    groups_to_check = GROUPS[:max_groups] if max_groups else GROUPS

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Verify logged in
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await asyncio.sleep(5)

            if "login" in page.url.lower():
                log("ERROR: Not logged into Facebook. Please log in manually.")
                input("Press Enter after logging in...")

            responded_count = 0
            checked_count = 0

            for group in groups_to_check:
                try:
                    log(f"\n--- Checking: {group['name']} ({group['category']}) ---")
                    # Verify browser is still responsive before navigating
                    try:
                        await page.evaluate("1+1")
                    except Exception:
                        log("FATAL: Browser context is dead. Stopping monitor.")
                        log(f"  Completed: {checked_count}/{len(groups_to_check)} groups")
                        log(f"  Responses: {responded_count}")
                        break

                    await page.goto(group["url"], wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(4)

                    posts = await extract_recent_posts(page, max_posts=15)
                    checked_count += 1

                    for post in posts:
                        if not contains_keyword(post["text"]):
                            continue

                        if post["post_id"] in state.get("responded_posts", {}):
                            log(f"  SKIP: Already responded to this post")
                            continue

                        log(f"  MATCH: Found relevant post")
                        log(f"  Preview: {post['text'][:100]}...")

                        if dry_run:
                            log("  DRY RUN: Would respond")
                            continue

                        response = get_response_template(post["post_id"])
                        success = await respond_to_post(page, post["element"], response)

                        if success:
                            state.setdefault("responded_posts", {})[post["post_id"]] = {
                                "group": group["name"],
                                "responded_at": datetime.now().isoformat(),
                            }
                            save_state(state)
                            responded_count += 1
                            log(f"  RESPONDED")

                        await asyncio.sleep(5)  # Rate limit

                    await asyncio.sleep(3)  # Between groups

                except Exception as e:
                    # Check if browser context is closed
                    error_str = str(e).lower()
                    if any(phrase in error_str for phrase in ["browser has been closed", "target page, context or browser", "context is closed", "invalid context"]):
                        log(f"FATAL: Browser context lost after {checked_count} groups. Stopping monitor.")
                        log(f"  Completed: {checked_count}/{len(groups_to_check)} groups")
                        log(f"  Responses: {responded_count}")
                        break  # Exit the loop - can't continue without a browser
                    else:
                        log(f"ERROR processing group {group['name']}: {e}")
                        continue

            log(f"\n{'=' * 60}")
            log(f"MONITOR COMPLETE")
            log(f"Groups checked: {checked_count}/{len(groups_to_check)}")
            log(f"Responses posted: {responded_count}")
            log(f"{'=' * 60}")

        finally:
            await context.close()

# ─── Mode: Post All ─────────────────────────────────────────────────────────

async def mode_post_all():
    log("=" * 60)
    log("STARTING OPTIMUM CLINIC MASS POST")
    log("=" * 60)

    groups_to_post = [g for g in GROUPS if g["priority"] in ("high", "medium")]

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await asyncio.sleep(5)

            if "login" in page.url.lower():
                log("ERROR: Not logged in. Please log in manually.")
                input("Press Enter after logging in...")

            posted_count = 0

            for group in groups_to_post:
                try:
                    log(f"\n--- Posting to: {group['name']} ---")
                    await page.goto(group["url"], wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(4)

                    # Find "Write something..." box
                    create_box = await page.query_selector("div[aria-label='Write something...']")
                    if not create_box:
                        create_box = await page.query_selector("div[placeholder*='Write']")
                    if not create_box:
                        log("WARNING: Could not find post creation box")
                        continue

                    await create_box.click()
                    await asyncio.sleep(3)

                    # Find post input in modal
                    post_input = await page.query_selector("div[contenteditable='true'][role='textbox'][data-contents='true']")
                    if not post_input:
                        # Fallback: any contenteditable in the modal
                        post_input = await page.query_selector("div[role='dialog'] div[contenteditable='true']")
                    if not post_input:
                        log("WARNING: Could not find post input in modal")
                        continue

                    template = RESPONSE_TEMPLATES[posted_count % len(RESPONSE_TEMPLATES)]
                    full_post = (
                        "🏥 OPTIMUM CLINIC — PHARR, TX 🏥\n\n"
                        "Need a DOT physical or drug screen?\n\n"
                        "✅ DOT Physicals (CDL drivers)\n"
                        "✅ Drug Screening (pre-employment)\n"
                        "✅ Walk-in sick visits\n\n"
                        "💰 $75 cash pay\n"
                        "🕙 Open until 10 PM (perfect for night shift)\n"
                        "📍 Pharr, TX\n\n"
                        "No appointment needed. Walk in after your shift!"
                    )

                    await post_input.fill(full_post)
                    await asyncio.sleep(2)

                    # Click Post button
                    post_btn = await page.query_selector("div[aria-label='Post']")
                    if not post_btn:
                        post_btn = await page.query_selector("text='Post'")
                    if post_btn:
                        await post_btn.click()
                        await asyncio.sleep(5)
                        log(f"SUCCESS: Posted to {group['name']}")
                        posted_count += 1
                    else:
                        log("WARNING: Could not find Post button")

                    await asyncio.sleep(10)  # Rate limit

                except Exception as e:
                    log(f"ERROR posting to {group['name']}: {e}")
                    continue

            log(f"\n{'=' * 60}")
            log(f"MASS POST COMPLETE")
            log(f"Posts made: {posted_count}/{len(groups_to_post)}")
            log(f"{'=' * 60}")

        finally:
            await context.close()

# ─── Mode: Test ─────────────────────────────────────────────────────────────

async def mode_test():
    log("=" * 60)
    log("TEST MODE — Extracting posts from first group")
    log("=" * 60)

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await asyncio.sleep(5)

            if "login" in page.url.lower():
                log("Not logged in. Logging in...")
                input("Press Enter after logging in...")

            first_group = GROUPS[0]
            log(f"Testing with: {first_group['name']}")

            await page.goto(first_group["url"], wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            posts = await extract_recent_posts(page, max_posts=10)
            log(f"\nExtracted {len(posts)} posts:\n")

            for i, post in enumerate(posts, 1):
                preview = post["text"][:150].replace("\n", " ")
                has_kw = contains_keyword(post["text"])
                marker = "🎯 MATCH" if has_kw else "   --"
                log(f"  {marker} Post {i}: {preview}...")
                if has_kw:
                    log(f"       Keywords found!")

            input("\nPress Enter to close browser...")

        finally:
            await context.close()

# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Optimum Clinic FB Group Monitor")
    parser.add_argument("--monitor", action="store_true", help="Monitor and auto-respond")
    parser.add_argument("--post-all", action="store_true", help="Post to all groups (one-time)")
    parser.add_argument("--test", action="store_true", help="Test mode — extract posts only")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without posting")
    parser.add_argument("--max-groups", type=int, default=None, help="Limit groups to check")
    args = parser.parse_args()

    if args.test:
        asyncio.run(mode_test())
    elif args.post_all:
        asyncio.run(mode_post_all())
    elif args.monitor:
        asyncio.run(mode_monitor(max_groups=args.max_groups, dry_run=args.dry_run))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
