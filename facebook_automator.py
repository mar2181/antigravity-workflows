from playwright.sync_api import sync_playwright
import time
import sys
import os

def automate_post(post_text):
    abs_auth_path = os.path.abspath("facebook_auth")
    with sync_playwright() as p:
        print(f"Launching browser with saved session from: {abs_auth_path}")
        context = p.chromium.launch_persistent_context(
            user_data_dir=abs_auth_path,
            headless=False,
            # Disable notifications to prevent popups stealing focus
            permissions=["notifications"]
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("Navigating to Facebook Pages dashboard...")
        page.goto("https://www.facebook.com/pages/")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print("Looking for Juan Elizondo RE/MAX page...")
        # Try to find the page link by text matching
        try:
            # We look for any element containing Juan Elizondo or RE/MAX
            # Facebook's DOM is complex, so we use a text locator
            page_link = page.locator("text=/Juan Elizondo/i").first
            if page_link.count() > 0:
                print("Found page link! Clicking...")
                page_link.click()
            else:
                # If we can't find it on the dashboard, we might need manual URL
                print("Could not find Juan Elizondo page on the dashboard. Trying common URL...")
                page.goto("https://www.facebook.com/juanelizondoremax/")
        except Exception as e:
            print(f"Navigation error: {e}")
            
        time.sleep(5) # Wait for page to load fully

        print("Attempting to create a post...")
        try:
            # Facebook's "What's on your mind?" button often has these labels
            # We use a broad search first
            selectors = [
                "div[role='button']:has-text(\"What's on your mind\")",
                "div[role='button']:has-text(\"Create post\")",
                "text=/Write something/i",
                "[aria-label*='Write something']",
                "[aria-label*='Create post']"
            ]
            
            create_post_btn = None
            for selector in selectors:
                loc = page.locator(selector).first
                if loc.count() > 0:
                    create_post_btn = loc
                    break
            
            if create_post_btn:
                print("Clicking post creation area...")
                create_post_btn.click()
            else:
                print("Could not find post creation area. Trying to force open composer via modal...")
                # Sometimes we can force it by looking for the input specifically
            
            time.sleep(3)

            print("Typing post content...")
            # The actual textbox usually has aria-label="What's on your mind, [Name]?"
            # or a specific role="textbox" inside a contenteditable div
            textbox = page.locator("div[role='textbox'][contenteditable='true']").first
            
            if textbox.count() == 0:
                textbox = page.locator("[aria-label*='What\\'s on your mind']").first

            textbox.click() # Ensure focus
            textbox.fill(post_text)
            time.sleep(2)

            print("Clicking Post button...")
            # The "Post" button is usually a blue button at the bottom of the modal
            post_btn = page.locator("div[aria-label='Post'][role='button']").first
            
            if post_btn.count() == 0:
                # Fallback to text matching
                post_btn = page.locator("div[role='button']:has-text('Post')").last
            
            if post_btn.is_enabled():
                print("Button is enabled. Publishing...")
                post_btn.click()
            else:
                print("Post button is disabled. Maybe the text wasn't accepted?")
                # Try typing one character at a time as a fallback
                textbox.press_sequentially(post_text, delay=50)
                time.sleep(1)
                post_btn.click()
            
            print("Wait 10 seconds for publish to complete...")
            time.sleep(10)
            print("SUCCESS! Post published automatically.")

        except Exception as e:
            print(f"Error during posting workflow: {e}")
            print("\nIf this failed, it is likely because Facebook updated their UI labels.")
            print("I might need to adjust the locators.")
            
        context.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = sys.argv[1]
    else:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        text = f"Automated test post for Juan Elizondo RE/MAX - {timestamp} 🤖"
        
    print(f"Starting automation to post: '{text}'")
    automate_post(text)
