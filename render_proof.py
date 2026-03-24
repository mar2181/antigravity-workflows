from playwright.sync_api import sync_playwright
from pathlib import Path

html_path = Path(__file__).parent / "scheduled_posts_proof.html"
out_path  = Path(__file__).parent / "PROOF_scheduled_posts_final.png"
url = "file:///" + str(html_path).replace("\\", "/")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 650, "height": 900})
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(1000)
    page.screenshot(path=str(out_path), full_page=True)
    browser.close()

print("Screenshot saved:", out_path)
