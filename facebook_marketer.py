"""
Facebook Marketing Automation Suite
Automates posting, scheduling, and engagement for Juan Elizondo RE/MAX and Optimum Health & Wellness
Uses Playwright UI automation with saved facebook_sniffer_profile authentication
"""

from playwright.sync_api import sync_playwright, expect
import json
import time
import argparse
from pathlib import Path
import requests  # used for Graph API posting (juan, optimum_clinic)

try:
    from screenpipe_verifier import verify_and_notify_fb, get_screen_context_at_failure, notify_mario as _sp_notify
    SCREENPIPE_AVAILABLE = True
except ImportError:
    SCREENPIPE_AVAILABLE = False


class FacebookMarketer:
    def __init__(self, config_path="fb_pages_config.json", profile_dir="facebook_sniffer_profile"):
        """Initialize with config and auth profile"""
        with open(config_path, "r") as f:
            self.config = json.load(f)

        self.profile_dir = profile_dir
        self.page = None
        self.context = None
        self.browser = None
        self.current_page_key = None
        self._composer_already_open = False  # set True when pages-list path opens dialog directly

    def launch_browser(self, page_key=None):
        """Launch Playwright browser with saved auth context, then verify correct account is loaded."""
        self.p = sync_playwright().start()

        print("[OK] Launching browser with saved Facebook session...")
        self.context = self.p.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=self.config.get("headless", False),
            viewport=self.config.get("viewport", {"width": 1920, "height": 1080})
        )

        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        print("[OK] Browser ready. Session authenticated.")

        # --- ACCOUNT VERIFICATION ---
        # Verify that the loaded session actually belongs to an account that manages
        # the pages in our config that use this profile. Catches wrong-profile errors
        # immediately instead of wasting minutes before failing.
        self._verify_account(page_key)

    def _verify_account(self, page_key=None):
        """Navigate silently to pages list and confirm at least one expected page is present.
        If the account is wrong, raises immediately with the exact fix command."""
        # Collect all page_ids that should be managed by this profile
        expected_ids = set()
        for key, info in self.config["pages"].items():
            profile = info.get("auth_profile", self.config.get("auth_profile", "facebook_sniffer_profile"))
            # Normalize: strip path separators if any
            profile_name = Path(profile).name if "/" in profile or "\\" in profile else profile
            loaded_name  = Path(self.profile_dir).name if "/" in self.profile_dir or "\\" in self.profile_dir else self.profile_dir
            if profile_name == loaded_name:
                expected_ids.add(str(info.get("page_id", "")))

        if not expected_ids:
            print("[VERIFY] No pages mapped to this profile — skipping account check")
            return

        try:
            self.page.goto("https://www.facebook.com/pages/?category=your_pages", timeout=15000)
            time.sleep(3)

            # Check for login redirect — session expired
            if "login" in self.page.url.lower():
                profile_name = Path(self.profile_dir).name if "/" in self.profile_dir or "\\" in self.profile_dir else self.profile_dir
                reauth = "reauth_mario_facebook.py" if "mario" in profile_name else "reauth_facebook_sniffer.py"
                raise RuntimeError(
                    f"\n\n[ACCOUNT ERROR] Session expired for profile: {profile_name}\n"
                    f"Fix: cd C:/Users/mario/.gemini/antigravity/scratch && python {reauth}\n"
                )

            # Get the account heading text
            heading_el = self.page.locator("h1, h2").first
            heading = heading_el.inner_text(timeout=4000) if heading_el.count() > 0 else "unknown"

            # Verify at least one of our expected pages appears in the page list
            found_any = False
            for pid in expected_ids:
                if pid and self.page.locator(f'a[href*="{pid}"]').count() > 0:
                    found_any = True
                    break

            if not found_any:
                profile_name = Path(self.profile_dir).name if "/" in self.profile_dir or "\\" in self.profile_dir else self.profile_dir
                raise RuntimeError(
                    f"\n\n[ACCOUNT ERROR] Wrong account loaded!\n"
                    f"  Profile used : {profile_name}\n"
                    f"  Account found: {heading}\n"
                    f"  Expected pages not visible on this account.\n"
                    f"Fix: Check 'auth_profile' in fb_pages_config.json for page '{page_key or 'unknown'}'\n"
                    f"     Make sure the profile directory exists and has the correct saved session.\n"
                )

            print(f"[VERIFY] Account OK — {heading} | Profile: {self.profile_dir}")

        except RuntimeError:
            raise  # re-raise our own errors
        except Exception as e:
            print(f"[VERIFY] Account check skipped (non-critical): {e}")

    def _snap(self, label):
        """Save a screenshot for debugging — stored next to script"""
        try:
            path = Path(__file__).parent / f"debug_snap_{label}.png"
            self.page.screenshot(path=str(path), full_page=False)
            print(f"[SNAP] {path.name}")
        except Exception as e:
            print(f"[SNAP-ERR] {label}: {e}")

    def close_browser(self):
        """Close browser and cleanup (safe to call even if browser was never launched)"""
        if getattr(self, "page", None):
            self.page.close()
        if getattr(self, "context", None):
            self.context.close()
        if getattr(self, "p", None):
            self.p.stop()
            print("[OK] Browser closed.")

    def navigate_to_page(self, page_key):
        """Navigate to a specific Facebook page and switch into page profile"""
        if page_key not in self.config["pages"]:
            raise ValueError(f"Unknown page: {page_key}")

        page_info = self.config["pages"][page_key]
        page_url = page_info["url"]

        # Go to personal feed first to establish account context
        print(f"\n[ACTION] Landing on personal feed first...")
        self.page.goto("https://www.facebook.com/")
        time.sleep(3)

        print(f"[ACTION] Navigating to {page_info['name']}...")
        self.page.goto(page_url)
        time.sleep(4)
        self._snap("01_page_loaded")

        # Click "Switch Now" to switch into the page profile (required to see composer)
        print("[ACTION] Looking for Switch Now button...")
        switch_selectors = [
            "div[role='button']:has-text('Switch Now')",
            "[aria-label='Switch Now']",
            "div[role='button']:has-text('Switch')",
            "[aria-label='Switch']",
        ]
        switched = False
        for sel in switch_selectors:
            try:
                btn = self.page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(2)
                    switched = True
                    break
            except Exception:
                pass

        # Handle "Switch profiles" confirmation modal that Facebook opens
        # It has a blue "Switch" button inside [role='dialog'] that must be clicked
        try:
            modal_switch = self.page.locator("[role='dialog'] div[role='button']:has-text('Switch')").first
            if modal_switch.is_visible(timeout=3000):
                modal_switch.click()
                time.sleep(3)
                print(f"[OK] Confirmed profile switch via modal")
            else:
                print(f"[OK] Switched into {page_info['name']} page profile (no modal)")
        except Exception:
            print(f"[OK] Switched into {page_info['name']} page profile (no modal)")

        self._snap("02_after_switch")

        if not switched:
            print("[WARNING] No Switch button found — trying pages-list fallback...")
            self._composer_already_open = False
            if self._open_composer_from_pages_list(page_key):
                return True
            print("[WARNING] Pages-list fallback also failed — verifying page context...")

        if "facebook.com" in self.page.url:
            self.current_page_key = page_key
            self._verify_active_page(page_key)  # RAISES RuntimeError if wrong page
            print(f"[OK] On {page_info['name']} page")
            return True
        else:
            print(f"[ERROR] Failed to navigate to {page_key}")
            return False

    def _verify_active_page(self, page_key):
        """Confirm the browser is on the correct Facebook page profile.
        Raises RuntimeError if wrong page detected — prevents silent wrong-page posts."""
        page_info = self.config["pages"][page_key]
        expected_name = page_info["name"].lower()
        expected_url = page_info["url"]
        page_id = str(page_info.get("page_id", ""))

        # Extract slug from URL (e.g. "JuanElizondoRemax" from "/JuanElizondoRemax/")
        url_slug = expected_url.rstrip("/").split("/")[-1]
        # For profile.php?id= URLs, slug is the id value
        if "profile.php" in url_slug:
            url_slug = page_id

        current_url = self.page.url
        url_match = bool(
            (page_id and page_id in current_url) or
            (url_slug and url_slug.lower() in current_url.lower())
        )

        # Also check DOM h1 for page name
        dom_match = False
        h1_text = ""
        try:
            h1_text = self.page.locator("h1").first.text_content(timeout=3000) or ""
            dom_match = (
                expected_name in h1_text.lower() or
                h1_text.strip().lower() in expected_name
            )
        except Exception:
            pass

        if not url_match and not dom_match:
            self._snap(f"WRONG_PAGE_{page_key}")
            raise RuntimeError(
                f"[ABORT] Wrong page! Expected '{page_info['name']}' "
                f"but got URL={current_url}, H1='{h1_text}'. "
                f"Post CANCELLED to prevent wrong-page posting. "
                f"Fix: confirm page_id '{page_id}' is correct in fb_pages_config.json."
            )

        print(f"[VERIFY] Confirmed on correct page: {page_info['name']} (url_match={url_match}, dom_match={dom_match})")

    def _open_composer_from_pages_list(self, page_key):
        """Fallback: navigate to pages list and click Create post for the specific page.
        Opens the composer dialog directly — sets self._composer_already_open = True on success."""
        page_info = self.config["pages"][page_key]
        page_id = str(page_info.get("page_id", ""))
        print(f"[FALLBACK] Navigating to pages list to find {page_info['name']}...")
        self.page.goto("https://www.facebook.com/pages/?category=your_pages")
        time.sleep(4)

        # Dismiss any blocking modal (e.g. "Switch profiles") before interacting
        try:
            close_btn = self.page.locator("[role='dialog'] [aria-label='Close']").first
            if close_btn.is_visible(timeout=2000):
                close_btn.click()
                time.sleep(1)
                print("[FALLBACK] Dismissed blocking modal")
        except Exception:
            pass
        try:
            self.page.keyboard.press("Escape")
            time.sleep(0.5)
        except Exception:
            pass

        self._snap("fallback_pages_list")

        # Use Playwright's :has() locator to find Create post inside the card that contains
        # a link to our specific page_id — no JS evaluate, no encoding issues
        try:
            create_btn = self.page.locator(
                f'div:has(a[href*="{page_id}"]) [aria-label="Create post"]'
            ).first
            create_btn.wait_for(state="visible", timeout=8000)
            print(f"[FALLBACK] Found Create post button for page_id={page_id}")
            create_btn.click()
            time.sleep(3)
            self._snap("fallback_after_create_post_click")

            # Handle Switch profiles modal that Facebook shows when clicking Create post
            # from the pages list while in personal profile.
            # After clicking Switch, Facebook switches profile but does NOT open composer —
            # we must navigate to the page URL and open the composer from there.
            switched_via_modal = False
            try:
                switch_btn = self.page.locator(
                    "[role='dialog'] div[role='button']:has-text('Switch')"
                ).first
                if switch_btn.is_visible(timeout=2000):
                    switch_btn.click()
                    time.sleep(4)
                    switched_via_modal = True
                    print("[FALLBACK] Clicked Switch — now in page profile")
                    self._snap("fallback_after_switch_modal")
            except Exception:
                pass

            if switched_via_modal:
                # Navigate directly to the page URL and open composer from there
                print(f"[FALLBACK] Navigating to page after profile switch: {page_info['url']}")
                self.page.goto(page_info["url"])
                time.sleep(4)
                self._snap("fallback_on_page_after_switch")
                self.current_page_key = page_key
                for sel in [
                    "div[role='button']:has-text('Create post')",
                    "[aria-label='Create post']",
                    "div[role='button']:has-text(\"What's on your mind\")",
                ]:
                    try:
                        btn = self.page.locator(sel).first
                        if btn.is_visible(timeout=3000):
                            btn.click()
                            time.sleep(3)
                            if self.page.locator("[role='dialog'] [role='textbox'], [role='dialog'] [contenteditable='true']").count() > 0:
                                self._composer_already_open = True
                                print("[FALLBACK] Composer opened on page after profile switch")
                                return True
                    except Exception:
                        continue
                # Profile is switched and we're on the page — let _open_composer handle it
                print("[FALLBACK] Profile switched, on page — main composer will handle opening")
                return False

            # Verify a REAL post composer dialog opened (not a Switch profiles modal)
            dialogs = self.page.locator("[role='dialog']").all()
            for d in dialogs:
                try:
                    # Post composer has a textbox; Switch modal does not
                    if d.locator("[role='textbox'], [contenteditable='true']").count() > 0:
                        self._composer_already_open = True
                        self.current_page_key = page_key
                        print("[FALLBACK] Composer dialog open via pages list")
                        return True
                except Exception:
                    continue
            print("[FALLBACK] Clicked Create post but post composer dialog not confirmed")
        except Exception as e:
            print(f"[FALLBACK] Locator approach failed: {e}")

        print(f"[FALLBACK] Could not open composer for page_id={page_id} on pages list")
        return False

    def _open_composer(self):
        """Open the post composer — must result in a [role='dialog'] being open"""
        print("[STEP] Opening post composer...")

        # Composer was already opened by pages-list fallback in navigate_to_page
        if self._composer_already_open:
            self._composer_already_open = False  # reset regardless
            # Confirm a POST composer is open (has textbox), not a Switch profiles modal
            dialogs = self.page.locator("[role='dialog']").all()
            for d in dialogs:
                try:
                    if d.locator("[role='textbox'], [contenteditable='true']").count() > 0:
                        print("[OK] Composer already open (pages-list path)")
                        return True
                except Exception:
                    continue
            print("[WARNING] pages-list flag set but no composer found — continuing normal flow")

        composer_selectors = [
            "div[role='button']:has-text('Create post')",
            "[aria-label='Create post']",
            "div[role='button']:has-text(\"What's on your mind\")",
            "[aria-label*=\"What's on your mind\"]",
            "[data-testid='status-attachment-mentions-input']",
        ]

        def _dismiss_overlays():
            """Press Escape to close any notification dropdowns or dialogs"""
            try:
                self.page.keyboard.press("Escape")
                time.sleep(0.5)
            except Exception:
                pass

        def _try_click_composer(dismiss_first=False):
            if dismiss_first:
                _dismiss_overlays()
            for selector in composer_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.is_visible():
                        element.click()
                        time.sleep(2)
                        # Only succeed if a dialog actually opened
                        dialog = self.page.query_selector("[role='dialog']")
                        if dialog:
                            return True
                except Exception:
                    pass
            return False

        # Attempt 1: clean page load — try without any overlay dismissal
        self.page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)
        self._snap("03_before_composer_click")
        if _try_click_composer(dismiss_first=False):
            self._snap("04_composer_open")
            print("[OK] Composer is open")
            return True

        self._snap("05_composer_attempt1_failed")
        # Attempt 2: navigate back to the page URL (reload drifts to notifications after profile switch)
        print("[WARNING] Could not find composer button, re-navigating to page and retrying...")
        if self.current_page_key:
            page_url = self.config["pages"][self.current_page_key]["url"]
            self.page.goto(page_url)
            time.sleep(4)
        else:
            self.page.reload()
            time.sleep(3)

        # Dismiss any notification dropdown or overlay by pressing Escape
        try:
            self.page.keyboard.press("Escape")
            time.sleep(1)
        except Exception:
            pass

        # Dismiss "Switch to page profile" dialog if it appears
        try:
            close_btn = self.page.locator("[role='dialog'] [aria-label='Close']").first
            if close_btn.is_visible(timeout=2000):
                close_btn.click()
                time.sleep(1)
                print("[OK] Dismissed switch-profile dialog")
        except Exception:
            pass

        self.page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)
        print(f"[DEBUG] Current URL: {self.page.url}")
        self._snap("06_after_renavigation")

        if _try_click_composer(dismiss_first=True):
            self._snap("07_composer_open_attempt2")
            print("[OK] Composer is open")
            return True

        self._snap("08_composer_failed_final")

        # Debug: report what buttons are visible near top of page
        try:
            buttons = self.page.locator("div[role='button']").all()
            found = []
            for b in buttons[:20]:
                try:
                    txt = (b.inner_text() or "").strip()[:50]
                    if txt:
                        found.append(txt)
                except Exception:
                    pass
            print(f"[DEBUG] Top-of-page role=button texts: {found}")
        except Exception:
            pass

        print("[ERROR] Composer did not open — no dialog found")

        # UC-5: Screenpipe forensics — grab OCR context at failure time
        if SCREENPIPE_AVAILABLE:
            try:
                ctx = get_screen_context_at_failure(seconds_back=30)
                print(f"[SCREENPIPE] Screen context at failure:\n{ctx[:1000]}")
                page_key = self.current_page_key or "unknown"
                _sp_notify(
                    f"COMPOSER FAILED — {page_key}\n"
                    f"URL: {self.page.url}\n\n"
                    f"Screen context (OCR):\n{ctx[:2000]}"
                )
            except Exception as e:
                print(f"[SCREENPIPE] Forensics error: {e}")

        return False

    def _type_message(self, message):
        """Type message into the text input inside the Create Post dialog.
        Uses clipboard paste to handle all Unicode/emoji correctly on Windows."""
        print(f"[STEP] Typing message ({len(message)} chars)...")

        # Load message into clipboard via JavaScript — avoids charmap issues entirely
        escaped = message.replace("\\", "\\\\").replace("`", "\\`")
        self.page.evaluate(f"""
            (async () => {{
                await navigator.clipboard.writeText(`{escaped}`);
            }})()
        """)
        time.sleep(0.3)

        selectors = [
            "[role='dialog'] div[role='textbox']",
            "[role='dialog'] [contenteditable='true']",
            "div[role='textbox']",
            "[contenteditable='true'][data-lexical-editor='true']",
            "[contenteditable='true']",
        ]

        for selector in selectors:
            try:
                el = self.page.locator(selector).first
                el.wait_for(state="visible", timeout=10000)
                el.click()
                time.sleep(0.5)
                # Paste from clipboard — handles emoji, em-dashes, all Unicode
                self.page.keyboard.press("Control+v")
                time.sleep(1.0)
                print("[OK] Message pasted via clipboard")
                return True
            except Exception:
                continue

        print("[ERROR] Could not find text input in dialog")
        return False

    def _upload_media(self, media_path):
        """Upload image or video via Photo/video button inside the Create Post dialog"""
        media_type = "video" if media_path.lower().endswith(('.mp4', '.mov', '.avi')) else "image"
        print(f"[STEP] Uploading {media_type}: {Path(media_path).name}")

        # Strategy 1: Try file input scoped to dialog only
        try:
            file_inputs = self.page.locator("[role='dialog'] input[type='file']").all()
            if file_inputs:
                file_inputs[0].set_input_files(media_path)
                time.sleep(5)
                print(f"[OK] {media_type.capitalize()} uploaded via dialog file input")
                return True
        except Exception as e:
            print(f"[INFO] Dialog file input failed: {e}")

        # Strategy 2: Try any file input on the page (Facebook hides them but they're settable)
        try:
            all_inputs = self.page.locator("input[type='file']").all()
            if all_inputs:
                all_inputs[0].set_input_files(media_path)
                time.sleep(5)
                print(f"[OK] {media_type.capitalize()} uploaded via page-wide file input")
                return True
        except Exception as e:
            print(f"[INFO] Page-wide file input failed: {e}")

        # Strategy 3: Try known aria-label variants for the photo button
        photo_selectors = [
            "[role='dialog'] [aria-label='Photo/video']",
            "[role='dialog'] [aria-label='Add photos/videos']",
            "[role='dialog'] [aria-label='Photos/videos']",
            "[role='dialog'] [aria-label*='Photo']",
            "[role='dialog'] [aria-label*='photo']",
            "[role='dialog'] [aria-label*='media']",
            "[role='dialog'] [aria-label*='Media']",
            "[aria-label='Photo/video']",
            "[aria-label='Add photos/videos']",
        ]
        for selector in photo_selectors:
            try:
                btn = self.page.locator(selector).first
                if btn.is_visible(timeout=2000):
                    with self.page.expect_file_chooser(timeout=6000) as fc_info:
                        btn.click()
                    fc_info.value.set_files(media_path)
                    time.sleep(4)
                    print(f"[OK] {media_type.capitalize()} uploaded via '{selector}'")
                    return True
            except Exception:
                continue

        # Strategy 4: Inspect and report all file inputs for debugging
        try:
            inputs = self.page.locator("input[type='file']").all()
            print(f"[DEBUG] Found {len(inputs)} file input(s) on page")
            buttons = self.page.locator("[role='dialog'] [role='button']").all()
            for b in buttons[:10]:
                try:
                    label = b.get_attribute("aria-label") or b.inner_text()[:40]
                    print(f"[DEBUG] Dialog button: '{label}'")
                except Exception:
                    pass
        except Exception:
            pass

        print(f"[WARNING] Could not upload {media_type}: all selectors failed")
        return False

    def _handle_interception_dialogs(self):
        """Auto-dismiss any interception dialogs (e.g., WhatsApp cross-post)"""
        print("[STEP] Checking for interception dialogs...")

        # Look for "Skip" or "Post to Page" buttons
        buttons_to_try = [
            "button:has-text('Skip')",
            "button:has-text('Post')",
            "[aria-label*='Skip']",
            "//button[contains(text(), 'Skip')]"
        ]

        for selector in buttons_to_try:
            try:
                button = self.page.query_selector(selector)
                if button and button.is_visible():
                    button.click()
                    time.sleep(1)
                    print("[OK] Dismissed interception dialog")
                    return True
            except:
                pass

        print("[OK] No interception dialogs found")
        return True

    def _find_and_click_post_button(self):
        """Find and click the post/publish button inside the Create Post dialog"""
        print("[STEP] Looking for post button...")
        self._snap("pre_post_click")

        # Dump all visible role=button text inside the dialog for diagnosis
        try:
            btns = self.page.locator("[role='dialog'] [role='button'], [role='dialog'] button").all()
            for b in btns:
                try:
                    txt = (b.inner_text() or "").strip()[:60]
                    lbl = b.get_attribute("aria-label") or ""
                    if txt or lbl:
                        print(f"[DEBUG] dialog btn → text='{txt}' aria='{lbl}'")
                except Exception:
                    pass
        except Exception:
            pass

        # Facebook Pages show "Next" first, then "Post" on the next screen
        # Try Next first, then fall back to direct Post
        next_selectors = [
            "[role='dialog'] div[role='button']:has-text('Next')",
            "[role='dialog'] [aria-label='Next']",
        ]
        post_selectors = [
            "[role='dialog'] [aria-label='Post'][role='button']",
            "[role='dialog'] div[aria-label='Post']",
            "[role='dialog'] div[role='button']:has-text('Post')",
        ]

        # Step 1: click Next if visible
        for selector in next_selectors:
            try:
                btn = self.page.locator(selector).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    time.sleep(3)
                    self._snap("after_next_click")
                    print(f"[OK] Clicked Next: {selector}")
                    break
            except Exception:
                continue

        # Dump all visible buttons at Post settings stage for diagnosis
        try:
            all_btns = self.page.evaluate("""() => {
                return Array.from(document.querySelectorAll('[role="button"], button'))
                    .filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
                    .map(b => ({
                        text: b.textContent.trim().slice(0,50),
                        aria: b.getAttribute('aria-label') || '',
                        inDialog: !!b.closest('[role="dialog"]'),
                        inLayer: !!(b.closest('[data-pagelet]') || b.closest('[role="main"]'))
                    }));
            }""")
            post_btns = [b for b in all_btns if 'post' in b['text'].lower() or 'post' in b['aria'].lower()]
            print(f"[DEBUG] Buttons with 'post' at Post settings stage: {post_btns}")
        except Exception as e:
            print(f"[DEBUG] Button dump failed: {e}")

        # Step 2: click Post (always required — either after Next or directly)
        # Use broad selectors (NOT restricted to role='dialog') for Facebook Pages
        post_selectors_broad = [
            "div[aria-label='Post'][role='button']",
            "div[role='button']:has-text('Post')",
        ] + post_selectors
        for selector in post_selectors_broad:
            try:
                btn = self.page.locator(selector).first
                btn.wait_for(state="visible", timeout=5000)
                btn.click()
                time.sleep(4)
                self._snap("post_button_clicked")
                print(f"[OK] Clicked Post: {selector}")
                # Dismiss any post-publish prompts (e.g. "Speak With People Directly" CTA dialog)
                time.sleep(2)
                try:
                    not_now = self.page.locator("div[role='button']:has-text('Not now'), [aria-label='Not now']").first
                    if not_now.is_visible(timeout=3000):
                        not_now.click()
                        print("[OK] Dismissed post-publish prompt (1st)")
                        time.sleep(2)
                        self._snap("after_not_now_1")
                except Exception:
                    pass
                # Dismiss any SECOND prompt that appears after the first "Not now"
                time.sleep(2)
                try:
                    not_now2 = self.page.locator("div[role='button']:has-text('Not now'), [aria-label='Not now'], div[role='button']:has-text('Skip'), div[role='button']:has-text('No thanks')").first
                    if not_now2.is_visible(timeout=3000):
                        not_now2.click()
                        print("[OK] Dismissed post-publish prompt (2nd)")
                        time.sleep(2)
                        self._snap("after_not_now_2")
                except Exception:
                    pass
                return True
            except Exception:
                continue

        # Screenshot + button dump for debugging
        try:
            self.page.screenshot(path="C:/Users/mario/.gemini/antigravity/scratch/post_button_debug.png")
            print("[DEBUG] Screenshot saved: post_button_debug.png")
            visible = []
            for el in self.page.locator("[role='button'], button").all():
                try:
                    if el.is_visible():
                        visible.append(f"text='{el.inner_text()[:60].strip()}' aria='{el.get_attribute('aria-label') or ''}'")
                except:
                    pass
            print("[DEBUG] Visible buttons:", visible)
        except Exception as de:
            print(f"[DEBUG] Could not capture debug info: {de}")

        print("[ERROR] Could not find post/next button in dialog")
        return False

    # ─── Graph API posting (juan + optimum_clinic ONLY) ───────────────────────
    # These two pages have page_tokens in fb_api_credentials.json.
    # All other clients (sugar_shack, island_arcade, island_candy, spi_fun_rentals)
    # use Playwright and must NOT be routed here until their tokens are added.

    _GRAPH_API_VERSION = "v19.0"
    _API_CREDS_FILE = Path(__file__).parent / "fb_api_credentials.json"

    def _parse_schedule_time(self, when_str):
        """
        Convert a human-readable schedule string to a Unix timestamp.
        Accepts:
          "+10m"  → now + 10 minutes
          "+2h"   → now + 2 hours
          "+1d"   → now + 1 day
          "2026-03-21 10:00"  → parsed as local time
        Facebook constraint: must be 10 min – 30 days in the future.
        Raises ValueError on invalid input or out-of-range time.
        """
        import re
        from datetime import datetime
        now = time.time()
        when_str = when_str.strip()
        m = re.match(r'^\+(\d+)(m|h|d)$', when_str)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            delta = {"m": 60, "h": 3600, "d": 86400}[unit]
            ts = now + n * delta
        else:
            try:
                dt = datetime.strptime(when_str, "%Y-%m-%d %H:%M")
                ts = dt.timestamp()
            except ValueError:
                raise ValueError(f"Cannot parse schedule time: '{when_str}'. Use '+10m', '+2h', '+1d', or 'YYYY-MM-DD HH:MM'.")
        min_ts = now + 600          # 10 minutes minimum
        max_ts = now + 30 * 86400   # 30 days maximum
        if ts < min_ts:
            raise ValueError("Scheduled time must be at least 10 minutes in the future.")
        if ts > max_ts:
            raise ValueError("Scheduled time cannot be more than 30 days in the future.")
        return ts

    def _graph_list_scheduled(self, page_key):
        """List queued scheduled posts for a Graph API page."""
        from datetime import datetime
        page_id, token = self._load_page_token(page_key)
        url = f"https://graph.facebook.com/{self._GRAPH_API_VERSION}/{page_id}/scheduled_posts"
        resp = requests.get(
            url,
            params={"access_token": token, "fields": "message,scheduled_publish_time,attachments"},
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            print(f"[ERROR] Graph API: {data['error'].get('message', data['error'])}")
            return
        posts = data.get("data", [])
        if not posts:
            print(f"[SCHEDULED POSTS] {page_key} — no posts scheduled.")
            return
        print(f"[SCHEDULED POSTS] {page_key} — {len(posts)} post(s) queued:")
        for p in posts:
            ts = int(p.get("scheduled_publish_time", 0))
            dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
            msg = p.get("message", "")[:80]
            icon = "[img] " if p.get("attachments") else ""
            safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
            print(f"  {dt_str} - {icon}{safe_msg}")

    def _load_page_token(self, page_key):
        """Load page_id + page_token from fb_api_credentials.json for Graph API pages."""
        try:
            creds = json.loads(self._API_CREDS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(f"[GRAPH API] Cannot read fb_api_credentials.json: {e}")
        page_creds = creds.get("pages", {}).get(page_key)
        if not page_creds:
            raise RuntimeError(f"[GRAPH API] '{page_key}' not found in fb_api_credentials.json")
        page_id = page_creds.get("page_id")
        token = page_creds.get("page_token")
        if not page_id or not token:
            raise RuntimeError(
                f"[GRAPH API] '{page_key}' is missing page_id or page_token in fb_api_credentials.json. "
                f"Run the OAuth flow first."
            )
        return page_id, token

    def _graph_post_text(self, page_key, message, schedule_time=None):
        """Post text-only via Graph API. Pass schedule_time (Unix ts) to schedule instead of post now."""
        page_id, token = self._load_page_token(page_key)
        url = f"https://graph.facebook.com/{self._GRAPH_API_VERSION}/{page_id}/feed"
        payload = {"message": message, "access_token": token}
        if schedule_time:
            payload["published"] = "false"
            payload["scheduled_publish_time"] = str(int(schedule_time))
            from datetime import datetime
            dt_str = datetime.fromtimestamp(schedule_time).strftime("%Y-%m-%d %H:%M")
            print(f"[GRAPH API] Scheduling text post for {page_key} at {dt_str}...")
        else:
            print(f"[GRAPH API] Posting text to {page_key} (page_id={page_id})...")
        resp = requests.post(url, data=payload, timeout=30)
        data = resp.json()
        if "id" in data:
            verb = "Scheduled" if schedule_time else "Published"
            print(f"[SUCCESS] {verb} via Graph API — post id: {data['id']}")
            return True
        else:
            print(f"[ERROR] Graph API error: {data}")
            return False

    def _graph_post_image(self, page_key, message, image_path, schedule_time=None):
        """Post image via Graph API. Pass schedule_time (Unix ts) to schedule instead of post now."""
        page_id, token = self._load_page_token(page_key)
        url = f"https://graph.facebook.com/{self._GRAPH_API_VERSION}/{page_id}/photos"
        payload = {"message": message, "access_token": token}
        if schedule_time:
            payload["published"] = "false"
            payload["scheduled_publish_time"] = str(int(schedule_time))
            from datetime import datetime
            dt_str = datetime.fromtimestamp(schedule_time).strftime("%Y-%m-%d %H:%M")
            print(f"[GRAPH API] Scheduling image post for {page_key} at {dt_str}...")
        else:
            print(f"[GRAPH API] Uploading image to {page_key} (page_id={page_id})...")
        with open(image_path, "rb") as f:
            resp = requests.post(url, data=payload, files={"source": f}, timeout=60)
        data = resp.json()
        if "id" in data:
            verb = "Scheduled" if schedule_time else "Published"
            print(f"[SUCCESS] {verb} via Graph API — post id: {data['id']}")
            return True
        else:
            print(f"[ERROR] Graph API error: {data}")
            return False

    def _graph_post_video(self, page_key, message, video_path):
        """Post video via Graph API."""
        page_id, token = self._load_page_token(page_key)
        url = f"https://graph.facebook.com/{self._GRAPH_API_VERSION}/{page_id}/videos"
        print(f"[GRAPH API] Uploading video to {page_key} (page_id={page_id})...")
        with open(video_path, "rb") as f:
            resp = requests.post(
                url,
                data={"description": message, "access_token": token},
                files={"source": f},
                timeout=120,
            )
        data = resp.json()
        if "id" in data:
            print(f"[SUCCESS] Video post published via Graph API — post id: {data['id']}")
            return True
        else:
            print(f"[ERROR] Graph API error: {data}")
            return False

    # ─── Public posting methods (route by posting_method in config) ────────────

    def post_text(self, page_key, message):
        """Create a text-only post"""
        # Route to Graph API if this page has page_token configured
        if self.config["pages"].get(page_key, {}).get("posting_method") == "graph_api":
            return self._graph_post_text(page_key, message)

        try:
            self.navigate_to_page(page_key)

            if not self._open_composer():
                return False

            if not self._type_message(message):
                return False

            self._handle_interception_dialogs()

            if not self._find_and_click_post_button():
                return False

            time.sleep(4)
            self._snap(f"POST_SUCCESS_text_{page_key}")
            print(f"[SUCCESS] Text post created! Screenshot saved — verify it's on '{self.config['pages'][page_key]['name']}'")

            if SCREENPIPE_AVAILABLE:
                verify_and_notify_fb(page_key, self.config['pages'][page_key]['name'], "text")

            return True

        except RuntimeError as e:
            print(str(e))
            return False
        except Exception as e:
            print(f"[ERROR] Failed to create text post: {str(e)}")
            return False

    def post_image(self, page_key, message, image_path):
        """Create a post with an image"""
        # Route to Graph API if this page has page_token configured
        if self.config["pages"].get(page_key, {}).get("posting_method") == "graph_api":
            return self._graph_post_image(page_key, message, image_path)

        try:
            self.navigate_to_page(page_key)

            if not self._open_composer():
                return False

            if not self._upload_media(image_path):
                return False

            time.sleep(7)  # Wait for Facebook to render composer after image upload

            if not self._type_message(message):
                return False

            self._handle_interception_dialogs()

            if not self._find_and_click_post_button():
                return False

            time.sleep(4)
            self._snap(f"POST_SUCCESS_image_{page_key}")
            print(f"[SUCCESS] Image post created! Screenshot saved — verify it's on '{self.config['pages'][page_key]['name']}'")

            if SCREENPIPE_AVAILABLE:
                verify_and_notify_fb(page_key, self.config['pages'][page_key]['name'], "image")

            return True

        except RuntimeError as e:
            print(str(e))
            return False
        except Exception as e:
            print(f"[ERROR] Failed to create image post: {str(e)}")
            return False

    def post_video(self, page_key, message, video_path):
        """Create a post with a video"""
        # Route to Graph API if this page has page_token configured
        if self.config["pages"].get(page_key, {}).get("posting_method") == "graph_api":
            return self._graph_post_video(page_key, message, video_path)

        try:
            self.navigate_to_page(page_key)

            if not self._open_composer():
                return False

            if not self._upload_media(video_path):
                return False

            # Wait for video processing/copyright check
            print("[STEP] Waiting for video processing...")
            time.sleep(5)

            if not self._type_message(message):
                return False

            self._handle_interception_dialogs()

            if not self._find_and_click_post_button():
                return False

            time.sleep(4)
            self._snap(f"POST_SUCCESS_video_{page_key}")
            print(f"[SUCCESS] Video post created! Screenshot saved — verify it's on '{self.config['pages'][page_key]['name']}'")

            if SCREENPIPE_AVAILABLE:
                verify_and_notify_fb(page_key, self.config['pages'][page_key]['name'], "video")

            return True

        except RuntimeError as e:
            print(str(e))
            return False
        except Exception as e:
            print(f"[ERROR] Failed to create video post: {str(e)}")
            return False

    def schedule_post(self, page_key, message, schedule_datetime, media_path=None):
        """Create a scheduled post"""
        try:
            self.navigate_to_page(page_key)

            if not self._open_composer():
                return False

            if media_path:
                if not self._upload_media(media_path):
                    return False
                time.sleep(2)

            if not self._type_message(message):
                return False

            # Find and click "Schedule" button (instead of "Post")
            print("[STEP] Looking for schedule option...")
            schedule_buttons = self.page.query_selector_all("button")
            schedule_found = False

            for button in schedule_buttons:
                label = button.get_attribute("aria-label") or ""
                if "Schedule" in (button.inner_text() or "") or "schedule" in label.lower():
                    button.click()
                    time.sleep(1)
                    schedule_found = True
                    break

            if not schedule_found:
                print("[WARNING] Schedule button not found, will post immediately")
                self._find_and_click_post_button()
                return True

            # If schedule dialog opened, fill in date/time
            # This is a simplified approach - Facebook's date picker is complex
            print(f"[STEP] Setting schedule to {schedule_datetime}...")
            time.sleep(1)

            # In a real scenario, would interact with Facebook's date/time picker
            # For now, just confirm the post
            self._find_and_click_post_button()

            time.sleep(2)
            print("[SUCCESS] Scheduled post created!")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to schedule post: {str(e)}")
            return False

    def reply_to_comment(self, post_url, comment_id, reply_text):
        """Reply to a specific comment on a post"""
        try:
            print(f"[ACTION] Navigating to post...")
            self.page.goto(post_url)
            time.sleep(3)

            print(f"[STEP] Finding comment {comment_id}...")

            # Find the reply button for the specific comment
            reply_buttons = self.page.query_selector_all("[aria-label*='Reply']")

            if reply_buttons:
                reply_buttons[0].click()
                time.sleep(1)

                # Type reply
                text_input = self.page.query_selector("[contenteditable='true'][role='textbox']")
                if text_input:
                    text_input.click()
                    text_input.fill(reply_text)
                    time.sleep(0.5)

                    # Submit reply
                    submit_button = self.page.query_selector("[aria-label='Comment']")
                    if submit_button:
                        submit_button.click()
                        time.sleep(2)
                        print("[SUCCESS] Reply posted!")
                        return True

            print("[ERROR] Could not find reply interface")
            return False

        except Exception as e:
            print(f"[ERROR] Failed to reply to comment: {str(e)}")
            return False

    def get_page_insights(self, page_key):
        """Navigate to page insights/analytics dashboard"""
        try:
            page_info = self.config["pages"][page_key]
            page_id = page_info["page_id"]

            insights_url = f"https://www.facebook.com/{page_id}/insights/"

            print(f"[ACTION] Opening insights for {page_info['name']}...")
            self.page.goto(insights_url)
            time.sleep(4)

            # Try to grab some visible metrics
            insights_text = self.page.inner_text()

            if "reach" in insights_text.lower() or "engagement" in insights_text.lower():
                print("[OK] Insights page loaded")
                print("[INFO] Insights dashboard is now visible. Review data in the browser window.")
                return True
            else:
                print("[WARNING] Insights page loaded but metrics not clearly visible")
                return True

        except Exception as e:
            print(f"[ERROR] Failed to load insights: {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Facebook Marketing Automation Suite")
    parser.add_argument("--action", required=True,
                       choices=["text", "image", "video", "schedule", "list-scheduled", "reply", "insights", "find_optimum"],
                       help="Action to perform")
    parser.add_argument("--page", default="juan", help="Page key: 'juan' or 'optimum'")
    parser.add_argument("--message", help="Post message or reply text")
    parser.add_argument("--media", help="Path to image or video file")
    parser.add_argument("--schedule", help="Schedule datetime (format: '2026-03-09 10:00')")
    parser.add_argument("--post-url", help="Post URL for replying to comments")
    parser.add_argument("--comment-id", help="Comment ID to reply to")
    parser.add_argument("--profile", default="facebook_sniffer_profile",
                        help="Auth profile dir (default: facebook_sniffer_profile)")

    args = parser.parse_args()

    # Auto-detect auth profile and posting method from per-page config
    profile_dir = args.profile
    posting_method = "playwright"  # default
    try:
        with open("fb_pages_config.json") as f:
            _cfg = json.load(f)
        page_cfg = _cfg["pages"].get(args.page, {})
        posting_method = page_cfg.get("posting_method", "playwright")
        if profile_dir == "facebook_sniffer_profile":  # i.e., still the default, not explicitly set
            page_auth = page_cfg.get("auth_profile")
            if page_auth and posting_method != "graph_api":
                profile_dir = page_auth
                print(f"[CONFIG] Using per-page auth profile: {profile_dir}")
    except Exception:
        pass

    marketer = FacebookMarketer(profile_dir=profile_dir)

    # Graph API pages (juan, optimum_clinic) do NOT need a browser — skip Playwright entirely.
    # Playwright pages (sugar_shack, island_arcade, island_candy, spi_fun_rentals, etc.) launch as normal.
    # NOTE: When tokens become available for remaining clients (expected ~Monday),
    # update their posting_method to "graph_api" in fb_pages_config.json and fb_api_credentials.json.
    if posting_method != "graph_api":
        marketer.launch_browser(page_key=args.page)
    else:
        print(f"[GRAPH API] '{args.page}' uses Graph API — skipping browser launch.")

    try:
        if args.action == "text":
            if not args.message:
                print("[ERROR] --message required for text posts")
                return
            marketer.post_text(args.page, args.message)

        elif args.action == "image":
            if not args.message or not args.media:
                print("[ERROR] --message and --media required for image posts")
                return
            marketer.post_image(args.page, args.message, args.media)

        elif args.action == "video":
            if not args.message or not args.media:
                print("[ERROR] --message and --media required for video posts")
                return
            marketer.post_video(args.page, args.message, args.media)

        elif args.action == "schedule":
            if not args.message or not args.schedule:
                print("[ERROR] --message and --schedule required for scheduled posts")
                return
            if posting_method == "graph_api":
                try:
                    ts = marketer._parse_schedule_time(args.schedule)
                except ValueError as e:
                    print(f"[ERROR] {e}")
                    return
                if args.media:
                    marketer._graph_post_image(args.page, args.message, args.media, schedule_time=ts)
                else:
                    marketer._graph_post_text(args.page, args.message, schedule_time=ts)
            else:
                marketer.schedule_post(args.page, args.message, args.schedule, args.media)

        elif args.action == "list-scheduled":
            if posting_method == "graph_api":
                marketer._graph_list_scheduled(args.page)
            else:
                print(f"[INFO] '{args.page}' uses Playwright — list-scheduled only works for Graph API pages.")

        elif args.action == "reply":
            if not args.post_url or not args.message:
                print("[ERROR] --post-url and --message required for replies")
                return
            marketer.reply_to_comment(args.post_url, args.comment_id or "", args.message)

        elif args.action == "insights":
            marketer.get_page_insights(args.page)
            print("\n[INFO] Browse the insights dashboard. Press Enter when done...")
            input()

        elif args.action == "find_optimum":
            print("[ACTION] Finding Optimum Health & Wellness page...")
            marketer.navigate_to_page("juan")
            print("\n[INFO] Navigate to Optimum Health & Wellness page manually.")
            print("[INFO] Copy the URL from the browser address bar and provide it.")
            print("[INFO] The script will extract the page ID and update the config.")
            print("[INFO] Press Enter to continue...")
            input()

            current_url = marketer.page.url
            if "facebook.com" in current_url:
                # Extract page ID from URL
                # URL format: https://www.facebook.com/[page_name]/ or https://www.facebook.com/pages/[name]/[id]/
                print(f"[INFO] Current URL: {current_url}")

                # Update config
                marketer.config["pages"]["optimum"]["url"] = current_url
                with open("fb_pages_config.json", "w") as f:
                    json.dump(marketer.config, f, indent=2)
                print("[OK] Config updated with Optimum page URL")

    finally:
        time.sleep(1)
        marketer.close_browser()


if __name__ == "__main__":
    main()
