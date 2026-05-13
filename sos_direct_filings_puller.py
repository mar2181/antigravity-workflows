"""
SOSDirect Filings Puller — pulls full Texas SOS filings for any entity list.

USAGE:
    cd C:/Users/mario/.gemini/antigravity/tools/execution
    python sos_direct_filings_puller.py

What it does:
    1. Opens a Chromium browser (persistent profile: sos_direct_profile/)
    2. Navigates to https://direct.sos.state.tx.us/
    3. Waits for you to log in (one-time — session is saved)
    4. Walks through each entity in ENTITIES (below)
    5. For each: opens the entity-name search, you click results + buy docs
    6. After each entity, saves the page HTML + a screenshot to property_research/hugo_dig/sos_filings/

Notes on SOSDirect:
    - $1 per name search, $1 per filing image (PDF) — pay-as-you-go via deposit
    - You'll need an account funded with at least $10 (covers all 5 entities + buffer)
    - Login URL: https://direct.sos.state.tx.us/acct/acct-login.asp
    - To register: click "Register" — needs name/email/CC, $10 minimum deposit
"""
import os, sys, time, json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

# === CONFIGURATION =========================================================

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "sos_direct_profile")
OUTPUT_DIR = "C:/Users/mario/property_research/hugo_dig/sos_filings"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Entities to research, in priority order
ENTITIES = [
    {
        "slug": "ms_estate_ltd",
        "search_name": "M & S ESTATE",
        "comptroller_taxpayer": "32053592377",
        "context": "Real-estate holding LP — owns 12 parcels (~64 acres + 1527 S Jackson)",
        "wishlist": "Certificate of Formation, all amendments, names of all limited partners",
    },
    {
        "slug": "ms_estate_management_llc",
        "search_name": "M & S ESTATE MANAGEMENT",
        "comptroller_taxpayer": "32053592401",
        "context": "GP/manager LLC for the LP above",
        "wishlist": "Certificate of Formation, members/managers list",
    },
    {
        "slug": "center_medical_ridge_llc",
        "search_name": "CENTER MEDICAL RIDGE",
        "comptroller_taxpayer": "32076095366",
        "context": "Holds 1401 + 1519 S Jackson plazas ($4.14M)",
        "wishlist": "Certificate of Formation, current managers/members",
    },
    {
        "slug": "member_construction_llc",
        "search_name": "MEMBER CONSTRUCTION",
        "comptroller_taxpayer": "32056537072",
        "context": "Hugo's GC firm (a.k.a. MC Developers) — 23 yrs in business",
        "wishlist": "Certificate of Formation, members/managers, registered agent",
    },
    {
        "slug": "mc_heavy_equipment_llc",
        "search_name": "MC HEAVY EQUIPMENT",
        "comptroller_taxpayer": "32079115997",
        "context": "Heavy equipment LLC at 1527 S Jackson",
        "wishlist": "Certificate of Formation, members",
    },
]

# === SCRIPT ================================================================

def banner(msg):
    print("\n" + "=" * 72)
    print(msg)
    print("=" * 72)

def wait_for_user(prompt):
    """Pause for Mario to do something manual. He hits ENTER when ready."""
    print(f"\n>>> {prompt}")
    input(">>> Press ENTER when ready to continue (or Ctrl+C to abort): ")

banner("SOS DIRECT FILINGS PULLER — Texas Secretary of State")
print(f"\nOutput dir : {OUTPUT_DIR}")
print(f"Profile dir: {PROFILE_DIR}")
print(f"Entities   : {len(ENTITIES)} to research")
print(f"\nSetup needed (once, ~5 min):")
print(f"  1. Have a SOSDirect account at https://direct.sos.state.tx.us/")
print(f"  2. Account must have $10+ deposit on file (covers all 5 + buffer)")
print(f"  3. To register: visit the URL above, click 'Register', $10 min deposit")
print(f"\nDuring the run:")
print(f"  - For each entity, the browser will open the search page")
print(f"  - You click the entity result, then 'Order Filing' on each doc you want")
print(f"  - When done with that entity, return to terminal and press ENTER")
print(f"  - Script saves screenshots + HTML automatically before moving on\n")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        viewport={"width": 1400, "height": 900},
        accept_downloads=True,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Step 1: Login
    banner("STEP 1 — LOG IN TO SOSDIRECT")
    page.goto("https://direct.sos.state.tx.us/acct/acct-login.asp")
    time.sleep(2)
    print("  Browser opened to login page.")
    print("  If you're not logged in, log in now (or register if first time).")
    print("  After login you should see the Account/Welcome page.")
    wait_for_user("Log in, then press ENTER here.")

    # Step 2: Cycle each entity
    for i, ent in enumerate(ENTITIES, 1):
        banner(f"ENTITY {i}/{len(ENTITIES)} — {ent['search_name']}")
        print(f"  Context : {ent['context']}")
        print(f"  Wishlist: {ent['wishlist']}")
        print(f"  Comptroller taxpayer ID: {ent['comptroller_taxpayer']}")

        # Navigate to entity name search
        # SOSDirect main menu → Business Organizations → Find Entity
        page.goto("https://direct.sos.state.tx.us/corp_inquiry/corp_inquiry-entity.asp")
        time.sleep(2)

        slug_dir = os.path.join(OUTPUT_DIR, ent["slug"])
        os.makedirs(slug_dir, exist_ok=True)

        # Try to fill in entity name automatically
        try:
            # The form field for entity name is typically named 'Filing_Name' or similar
            page.fill("input[name='Filing_Name']", ent["search_name"])
            print(f"  [auto] Filled in '{ent['search_name']}'.")
        except Exception as e:
            print(f"  [manual] Could not autofill; type '{ent['search_name']}' yourself.")
            print(f"  ({e})")

        wait_for_user(
            f"In the browser:\n"
            f"    1. Click 'Search' (or press Enter in the form)\n"
            f"    2. Find '{ent['search_name']}' in the results\n"
            f"    3. Click the entity name link to open its detail page\n"
            f"    4. On the detail page: click 'Order' next to each filing you want\n"
            f"       (Certificate of Formation = most important; amendments next)\n"
            f"    5. After each $1 charge, the filing PDF will download — save it to:\n"
            f"       {slug_dir}\n"
            f"    6. When you've ordered all the filings you want for this entity,\n"
            f"       come back here."
        )

        # Save evidence: screenshot + HTML of whatever page is currently shown
        try:
            ts = time.strftime("%Y%m%d-%H%M%S")
            screenshot = os.path.join(slug_dir, f"final_state_{ts}.png")
            html = os.path.join(slug_dir, f"final_state_{ts}.html")
            page.screenshot(path=screenshot, full_page=True)
            with open(html, "w", encoding="utf-8") as f:
                f.write(page.content())
            print(f"  [saved] {screenshot}")
            print(f"  [saved] {html}")
        except Exception as e:
            print(f"  [warn] Could not save evidence: {e}")

    banner("ALL ENTITIES PROCESSED")
    print(f"\nFiles saved under: {OUTPUT_DIR}/<entity_slug>/")
    print("Browser stays open. Close it manually when done.\n")
    wait_for_user("Press ENTER to close the browser.")
    ctx.close()

print("\n[DONE] Session saved. Re-run anytime — it will remember your login.")
