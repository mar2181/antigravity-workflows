"""
screenshot_scheduled_posts.py
Navigate to Facebook Publishing Tools to show scheduled posts for admins.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path(__file__).parent / "facebook_mario_profile")
OUT_DIR = Path(__file__).parent

PAGES = [
    {"key": "juan",          "page_id": "316634185463817",  "slug": "JuanElizondoRemax", "name": "Juan Elizondo"},
    {"key": "optimum_clinic","page_id": "1003933732800661", "slug": None,                 "name": "Optimum Clinic"},
]


def snap(page, label, clip=None):
    path = OUT_DIR / label
    kw = {"path": str(path), "full_page": False}
    if clip:
        kw["clip"] = clip
    try:
        page.screenshot(**kw)
        print(f"  [SNAP] {label}")
    except Exception as e:
        print(f"  [FAIL] {label}: {e}")


def dismiss(page):
    for sel in ["[aria-label='Close']", "div[role='dialog'] [aria-label='Close']"]:
        try:
            b = page.locator(sel).first
            if b.is_visible(timeout=800):
                b.click()
                page.wait_for_timeout(600)
                break
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    except Exception:
        pass


with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--start-maximized"],
        no_viewport=True,
    )
    page = browser.new_page()

    for pg in PAGES:
        key = pg["key"]
        page_id = pg["page_id"]
        name = pg["name"]
        print(f"\n== {name} ==")

        # Try Publishing Tools — the definitive place to see scheduled posts
        if pg["slug"]:
            pub_tools_url = f"https://www.facebook.com/{pg['slug']}/publishing_tools/"
        else:
            pub_tools_url = f"https://www.facebook.com/profile.php?id={page_id}&sk=publishing_tools"

        print(f"  Navigating to Publishing Tools...")
        try:
            page.goto(pub_tools_url, timeout=25000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"  [WARN] {e}")
        page.wait_for_timeout(5000)
        dismiss(page)
        snap(page, f"PROOF_{key}_A_pub_tools.png")

        # Click "Scheduled Posts" in the left sidebar or tabs
        clicked = False
        for txt in ["Scheduled Posts", "Scheduled posts", "Scheduled", "Publicaciones programadas"]:
            try:
                el = page.locator(f"text={txt}").first
                if el.is_visible(timeout=2000):
                    el.click()
                    page.wait_for_timeout(3000)
                    dismiss(page)
                    snap(page, f"PROOF_{key}_B_scheduled.png")
                    print(f"  [OK] Clicked '{txt}'")
                    clicked = True
                    break
            except Exception:
                pass

        if not clicked:
            # Try left nav links
            try:
                links = page.query_selector_all("a, [role='link']")
                for lnk in links:
                    try:
                        t = lnk.inner_text().strip()
                        if "sched" in t.lower():
                            print(f"    Found link: {t!r}")
                            lnk.click()
                            page.wait_for_timeout(3000)
                            snap(page, f"PROOF_{key}_B_scheduled.png")
                            clicked = True
                            break
                    except Exception:
                        pass
            except Exception:
                pass

        if not clicked:
            snap(page, f"PROOF_{key}_B_scheduled.png")

        # Final scroll-down to show list
        try:
            page.mouse.wheel(0, 300)
            page.wait_for_timeout(1500)
            snap(page, f"PROOF_{key}_C_scrolled.png")
        except Exception:
            pass

    browser.close()

print("\n[DONE]")
for f in sorted(OUT_DIR.glob("PROOF_*.png")):
    print(f"  {f.name}")
