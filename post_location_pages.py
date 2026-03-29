"""Post all 8 location pages to Facebook + GBP for Custom Designs."""

import json
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

EXEC_DIR = Path(r"C:\Users\mario\.gemini\antigravity\tools\execution")
MARKETER = EXEC_DIR / "facebook_marketer.py"
GBP_SCRIPT = EXEC_DIR / "_gbp_custom_designs_with_image.py"

# ── Collect posts ──────────────────────────────────────────────────────────────
POSTS = []

bases = {
    "custom_designs_tx": EXEC_DIR / "blog_posts" / "custom_designs_tx",
    "juan": EXEC_DIR / "blog_posts" / "juan",
}

for biz_key, blog_dir in bases.items():
    for meta_path in sorted(blog_dir.glob("2026-03-27*_meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        POSTS.append({
            "biz": biz_key,
            "keyword": meta["keyword"],
            "fb_copy": meta["fb_copy"],
            "gbp_copy": meta.get("gbp", ""),
            "hero": meta.get("images", {}).get("hero", ""),
            "page_key": "custom_designs_tx" if biz_key == "custom_designs_tx" else "juan",
        })

print(f"Ready to post {len(POSTS)} location pages\n")

# ── Facebook Posts ─────────────────────────────────────────────────────────────
print("=" * 60)
print("FACEBOOK POSTS")
print("=" * 60)

fb_success = 0
fb_fail = 0

for i, post in enumerate(POSTS, 1):
    print(f"\n[{i}/{len(POSTS)}] FB: {post['keyword']} → {post['page_key']}")

    # Kill Chrome between posts to avoid session conflicts
    subprocess.run(
        ["powershell", "-Command", "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"],
        capture_output=True
    )
    time.sleep(2)

    # Clear locks
    for profile in ["facebook_mario_profile", "facebook_sniffer_profile"]:
        lock = EXEC_DIR / profile / "SingletonLock"
        if lock.exists():
            lock.unlink()

    hero = post["hero"]
    if not hero or not Path(hero).exists():
        print(f"  SKIP — no hero image found at {hero}")
        fb_fail += 1
        continue

    cmd = [
        sys.executable, str(MARKETER),
        "--action", "image",
        "--page", post["page_key"],
        "--message", post["fb_copy"],
        "--media", hero,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                cwd=str(EXEC_DIR), encoding="utf-8", errors="replace")
        if result.returncode == 0 and "SUCCESS" in (result.stdout or ""):
            print(f"  OK — posted to Facebook")
            fb_success += 1
        else:
            print(f"  FAIL — returncode={result.returncode}")
            if result.stdout:
                # Print last 5 lines of stdout for debugging
                lines = result.stdout.strip().split("\n")
                for line in lines[-5:]:
                    print(f"    {line}")
            if result.stderr:
                lines = result.stderr.strip().split("\n")
                for line in lines[-3:]:
                    print(f"    ERR: {line}")
            fb_fail += 1
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT")
        fb_fail += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        fb_fail += 1

    # Brief pause between posts
    if i < len(POSTS):
        time.sleep(5)

print(f"\nFacebook: {fb_success} posted, {fb_fail} failed")

# ── GBP Posts (Custom Designs only) ───────────────────────────────────────────
print("\n" + "=" * 60)
print("GBP POSTS (Custom Designs TX only)")
print("=" * 60)

gbp_success = 0
gbp_fail = 0

cd_posts = [p for p in POSTS if p["biz"] == "custom_designs_tx"]

for i, post in enumerate(cd_posts, 1):
    print(f"\n[{i}/{len(cd_posts)}] GBP: {post['keyword']}")

    hero = post["hero"]
    if not hero or not Path(hero).exists():
        print(f"  SKIP — no hero image")
        gbp_fail += 1
        continue

    cmd = [
        sys.executable, str(GBP_SCRIPT),
        "--message", post["gbp_copy"],
        "--media", hero,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                                cwd=str(EXEC_DIR), encoding="utf-8", errors="replace")
        if result.returncode == 0:
            print(f"  OK — posted to GBP")
            gbp_success += 1
        else:
            print(f"  FAIL — returncode={result.returncode}")
            lines = (result.stdout or "").strip().split("\n")
            for line in lines[-5:]:
                print(f"    {line}")
            gbp_fail += 1
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT")
        gbp_fail += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        gbp_fail += 1

    if i < len(cd_posts):
        time.sleep(5)

print(f"\nGBP: {gbp_success} posted, {gbp_fail} failed")

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
print(f"Facebook: {fb_success}/{len(POSTS)} posted")
print(f"GBP:      {gbp_success}/{len(cd_posts)} posted")
print(f"Total:    {fb_success + gbp_success}/{len(POSTS) + len(cd_posts)} posted")
