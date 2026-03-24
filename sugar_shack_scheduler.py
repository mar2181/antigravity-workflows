#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sugar Shack Spring Break Campaign Scheduler
Posts ads 2-7, 9 at optimal spring break times over 3 days.

Schedule:
  Mar 12 11:00 AM → Ad #2 (Souvenir Play)
  Mar 12  6:00 PM → Ad #3 (Sweet Memories)
  Mar 13 10:00 AM → Ad #4 (Bulk Candy Budget)
  Mar 13  1:30 PM → Ad #5 (Cool Down From Beach)
  Mar 13  7:00 PM → Ad #6 (Kids Choice)
  Mar 14 11:00 AM → Ad #7 (Spring Break Fuel)
  Mar 14  5:00 PM → Ad #9 (Last Stop Before Home)
"""

import subprocess
import sys
import time
import json
import os
from datetime import datetime

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MARKETER = r"C:\Users\mario\.gemini\antigravity\tools\execution\facebook_marketer.py"
MANIFEST = r"C:\Users\mario\.gemini\antigravity\scratch\skills\sugar-shack-facebook\ads_manifest.json"
IMAGE_DIR = r"C:\Users\mario\sugar_shack_ad_images"
PYTHON = sys.executable

SCHEDULE = [
    {"ad_id": 2,  "post_at": "2026-03-12 11:00"},
    {"ad_id": 3,  "post_at": "2026-03-12 18:00"},
    {"ad_id": 4,  "post_at": "2026-03-13 10:00"},
    {"ad_id": 5,  "post_at": "2026-03-13 13:30"},
    {"ad_id": 6,  "post_at": "2026-03-13 19:00"},
    {"ad_id": 7,  "post_at": "2026-03-14 11:00"},
    {"ad_id": 9,  "post_at": "2026-03-14 17:00"},
]

def load_manifest():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)

def save_manifest(data):
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_ad(manifest, ad_id):
    for ad in manifest:
        if ad["id"] == ad_id:
            return ad
    return None

def post_ad(ad):
    image_path = ad["image"]
    copy = ad["copy"]
    cmd = [
        PYTHON, MARKETER,
        "--action", "image",
        "--page", "sugar_shack",
        "--message", copy,
        "--media", image_path,
    ]
    print(f"\n[POST] Ad #{ad['id']} — {ad['angle']}")
    print(f"       Image: {os.path.basename(image_path)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0

def wait_until(target_str):
    target = datetime.strptime(target_str, "%Y-%m-%d %H:%M")
    now = datetime.now()
    diff = (target - now).total_seconds()
    if diff <= 0:
        return  # Already past — post immediately
    hours = int(diff // 3600)
    mins = int((diff % 3600) // 60)
    print(f"[WAIT] Next post at {target_str} — sleeping {hours}h {mins}m...")
    # Sleep in chunks, printing status every 15 min
    chunk = 900  # 15 minutes
    while diff > 0:
        sleep_time = min(chunk, diff)
        time.sleep(sleep_time)
        diff -= sleep_time
        if diff > 0:
            remaining = datetime.strptime(target_str, "%Y-%m-%d %H:%M") - datetime.now()
            r_hours = int(remaining.total_seconds() // 3600)
            r_mins = int((remaining.total_seconds() % 3600) // 60)
            print(f"  [{datetime.now().strftime('%H:%M')}] Still waiting... {r_hours}h {r_mins}m until next post")

def main():
    print("=" * 60)
    print("SUGAR SHACK — SPRING BREAK CAMPAIGN SCHEDULER")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Ads to post: {len(SCHEDULE)}")
    print()

    for item in SCHEDULE:
        print(f"  Ad #{item['ad_id']:2d} → {item['post_at']}")
    print()

    manifest = load_manifest()
    posted_count = 0

    for item in SCHEDULE:
        ad_id = item["ad_id"]
        post_at = item["post_at"]
        ad = get_ad(manifest, ad_id)

        if not ad:
            print(f"[ERROR] Ad #{ad_id} not found in manifest — skipping")
            continue

        if ad.get("posted"):
            print(f"[SKIP] Ad #{ad_id} already marked as posted — skipping")
            continue

        # Wait until posting time
        wait_until(post_at)

        print(f"\n[{datetime.now().strftime('%H:%M')}] Posting Ad #{ad_id}...")
        success = post_ad(ad)

        if success:
            ad["posted"] = True
            ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_manifest(manifest)
            posted_count += 1
            print(f"[OK] Ad #{ad_id} posted and manifest updated")
        else:
            print(f"[ERROR] Ad #{ad_id} failed — will retry in 5 minutes")
            time.sleep(300)
            print(f"[RETRY] Retrying Ad #{ad_id}...")
            success = post_ad(ad)
            if success:
                ad["posted"] = True
                ad["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_manifest(manifest)
                posted_count += 1
                print(f"[OK] Ad #{ad_id} posted on retry")
            else:
                print(f"[FAIL] Ad #{ad_id} failed twice — moving on")

        # 30-second cooldown between posts (even if next one is far away)
        time.sleep(30)

    print("\n" + "=" * 60)
    print(f"CAMPAIGN COMPLETE: {posted_count}/{len(SCHEDULE)} ads posted")
    print("=" * 60)

if __name__ == "__main__":
    main()
