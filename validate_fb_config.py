import sys, os
sys.path.insert(0, r"C:\Users\mario\.gemini\antigravity\tools\execution")
os.chdir(r"C:\Users\mario\.gemini\antigravity\tools\execution")

# Load the BUSINESSES dict and MC_CLIENT_IDS from the runner
content = open("fb_campaign_runner.py").read()
exec(content.split("MARKETER_SCRIPT")[0])

tests = [
    ("island_candy", "island_candy", "facebook_mario_profile"),
    ("spi_fun_rentals", "spi_fun_rentals", "facebook_mario_profile"),
    ("sugar_shack", "sugar_shack", "facebook_mario_profile"),
]

import json
cfg = json.load(open("fb_pages_config.json"))

print("=== CAMPAIGN RUNNER VALIDATION ===\n")
all_ok = True
for biz_key, page_key, expected_profile in tests:
    biz = BUSINESSES.get(biz_key)
    if not biz:
        print(f"FAIL {biz_key}: not in BUSINESSES dict")
        all_ok = False
        continue
    page_cfg = cfg["pages"].get(page_key)
    if not page_cfg:
        print(f"FAIL {biz_key}: page '{page_key}' not in fb_pages_config.json")
        all_ok = False
        continue
    actual_profile = page_cfg.get("auth_profile", "facebook_mario_profile")
    profile_ok = actual_profile == expected_profile
    profile_exists = os.path.isdir(r"C:\Users\mario\.gemini\antigravity\tools\execution" + "\\" + actual_profile)
    status = "OK" if (profile_ok and profile_exists) else "FAIL"
    print(f"{status}  {biz_key}")
    print(f"     page_key   : {biz['page_key']}")
    print(f"     auth_profile: {actual_profile} (expected {expected_profile})")
    print(f"     profile dir exists: {profile_exists}")
    print()
    if not profile_ok or not profile_exists:
        all_ok = False

print("=== RESULT:", "ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED", "===")
