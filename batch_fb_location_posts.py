"""Batch post all 8 location pages to Facebook, one at a time with verification."""

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
MARKETER = str(EXEC_DIR / "facebook_marketer.py")

# Page key mapping
PAGE_KEYS = {
    "custom_designs_tx": "custom_designs_tx",
    "juan": "juan",
}

# Collect all meta files from today
posts = []
for biz_key in ["custom_designs_tx", "juan"]:
    blog_dir = EXEC_DIR / "blog_posts" / biz_key
    for meta_path in sorted(blog_dir.glob("2026-03-27*_meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        hero = meta.get("images", {}).get("hero", "")
        if not hero or not Path(hero).exists():
            print(f"SKIP {meta['keyword']} — no hero image")
            continue
        posts.append({
            "biz": biz_key,
            "keyword": meta["keyword"],
            "fb_copy": meta["fb_copy"],
            "hero": hero,
            "page_key": PAGE_KEYS[biz_key],
        })

# Skip first post (Edinburg CD TX — already posted)
skip_keyword = "security camera installation edinburg tx"
posts = [p for p in posts if p["keyword"] != skip_keyword]

print(f"Posting {len(posts)} remaining Facebook posts\n")

success = 0
fail = 0

for i, post in enumerate(posts, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/{len(posts)}] {post['keyword']} → {post['page_key']}")
    print(f"{'='*60}")

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

    cmd = [
        sys.executable, MARKETER,
        "--action", "image",
        "--page", post["page_key"],
        "--message", post["fb_copy"],
        "--media", post["hero"],
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(EXEC_DIR), encoding="utf-8", errors="replace"
        )
        output = result.stdout or ""

        if "SUCCESS" in output:
            print(f"  ✅ POSTED — {post['keyword']}")
            success += 1
        else:
            print(f"  ❌ FAILED — returncode={result.returncode}")
            # Print last 10 lines
            lines = output.strip().split("\n")
            for line in lines[-10:]:
                print(f"    {line}")
            fail += 1
    except subprocess.TimeoutExpired:
        print(f"  ❌ TIMEOUT")
        fail += 1
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        fail += 1

    # Pause between posts
    if i < len(posts):
        print("  Waiting 8s before next post...")
        time.sleep(8)

print(f"\n{'='*60}")
print(f"DONE: {success} posted, {fail} failed out of {len(posts)}")
print(f"{'='*60}")
