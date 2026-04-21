"""Post one Facebook ad per client — downloads images, posts sequentially."""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

EXEC_DIR = Path(r"C:\Users\mario\.gemini\antigravity\tools\execution")
MARKETER = str(EXEC_DIR / "facebook_marketer.py")
TMP_DIR = EXEC_DIR / "tmp_post_images"
TMP_DIR.mkdir(exist_ok=True)

# ── Posts to make ──────────────────────────────────────────────────────────────
POSTS = [
    {
        "page_key": "juan",
        "name": "Juan - Real Estate Agent Edinburg TX",
        "image_local": str(EXEC_DIR / "blog_posts" / "juan" / "images" / "2026-03-27_real-estate-agent-edinburg-tx" / "hero.png"),
        "image_url": None,
        "message": (
            "Looking for a real estate agent in Edinburg, TX who actually knows the market?\n\n"
            "Edinburg is one of the fastest-growing cities in the Rio Grande Valley right now. "
            "With UTRGV driving demand, new master-planned communities going up near Trenton Road, "
            "and home values that are still more affordable than McAllen, this is the moment to make your move.\n\n"
            "Whether you're buying your first home, selling a property, or looking at investment opportunities, "
            "I bring 20+ years of RGV expertise and bilingual service to every transaction.\n\n"
            "What you get working with me:\n"
            "- Deep Edinburg neighborhood knowledge (Sugar Road, north Edinburg, Doctors Hospital area)\n"
            "- Honest market analysis before you commit\n"
            "- Bilingual service in English and Spanish\n\n"
            "Ready to explore Edinburg real estate? Call or text me at (956) 522-1481.\n\n"
            "#EdinburgTX #RGVRealEstate #JuanElizondoRemax"
        ),
    },
    {
        "page_key": "sugar_shack",
        "name": "Sugar Shack - Candy Paradise",
        "image_local": None,
        "image_url": "https://v3b.fal.media/files/b/0a934d04/P4NOQ49lbWvc1oOl_X4KY_f6d5ab8db59941df91a0a0c0b6d2faaf.png",
        "message": (
            "Rows and rows of bulk candy bins overflowing with every sweet you dreamed of as a kid.\n\n"
            "The Sugar Shack on South Padre Island is the candy store you wish existed in your hometown. "
            "Gummies, chocolate, sour belts, taffy, fudge, and more candy than you can fit in one bag "
            "(but you'll try anyway).\n\n"
            "Whether you're on spring break, a family beach trip, or just driving through SPI, "
            "this is your one stop for the best candy haul on the island.\n\n"
            "Open daily on South Padre Island. Come grab a bag and fill it up.\n\n"
            "#SouthPadreIsland #CandyStore #SPIVacation"
        ),
    },
    {
        "page_key": "island_arcade",
        "name": "Island Arcade - Fighter Showdown",
        "image_local": None,
        "image_url": "https://v3b.fal.media/files/b/0a934d07/LwOAaT0fooZ-NYCV-w3aw_a6b00ad5dc144af6a0cff2c17fac5d92.png",
        "message": (
            "Think you've got what it takes?\n\n"
            "Our classic fighting game cabinets are calling your name. "
            "Step up, pick your fighter, and see if you can hold the high score at Island Arcade.\n\n"
            "Whether you're reliving the golden age of arcades or introducing your kids to the classics, "
            "we've got the games, the tickets, and the prizes to make your SPI trip unforgettable.\n\n"
            "Rain or shine, Island Arcade is the spot on South Padre Island.\n\n"
            "Open daily. Bring the whole crew.\n\n"
            "#IslandArcade #SouthPadreIsland #ArcadeGames"
        ),
    },
    {
        "page_key": "island_candy",
        "name": "Island Candy - Tropical Swirl",
        "image_local": None,
        "image_url": "https://v3b.fal.media/files/b/0a934d14/vAGK077u15fT3myOWqIX8_f8c75a8cde1e4f3983bf4e0e0cbc7ebc.png",
        "message": (
            "Mango. Coconut. Passion fruit. Guava.\n\n"
            "Island Candy brings you tropical ice cream flavors you won't find anywhere else on "
            "South Padre Island. Every scoop is a vacation inside a vacation.\n\n"
            "We're inside Island Arcade, so grab your ice cream, play some games, "
            "and make it a full island afternoon.\n\n"
            "Come cool off with a scoop (or three). Open daily on SPI.\n\n"
            "#IslandCandy #SPIiceCream #SouthPadreIsland"
        ),
    },
    {
        "page_key": "spi_fun_rentals",
        "name": "SPI Fun Rentals - Island Cruiser",
        "image_local": None,
        "image_url": "https://v3b.fal.media/files/b/0a934d1a/snIbRDp8ccj7f8IL-j_E8_1e3ee6af26774f7c976cc4ea20e5eeff.png",
        "message": (
            "Skip the parking hassle. Grab a golf cart and cruise South Padre Island like a local.\n\n"
            "SPI Fun Rentals has the cleanest, most reliable golf carts on the island. "
            "Perfect for beach hopping, dinner runs, or just exploring with the family.\n\n"
            "We deliver to your rental. Easy pickup, easy return. "
            "Book ahead for spring break — carts go fast.\n\n"
            "Call or text to reserve yours today.\n\n"
            "#SPIFunRentals #GolfCartRentals #SouthPadreIsland"
        ),
    },
    {
        "page_key": "optimum_clinic",
        "name": "Optimum Clinic - Skip the ER",
        "image_local": None,
        "image_url": "https://v3b.fal.media/files/b/0a934d2b/Y9ocjCu52umHiErdJpQpp_73a49f7df46e4a6a951ea3e2951ede76.png",
        "message": (
            "Don't wait 4 hours in the ER for a non-emergency.\n\n"
            "Optimum Care Clinic sees you the same night. No long wait, no surprise bills. "
            "Walk-ins welcome, 5 PM to 10 PM nightly.\n\n"
            "Sick visits starting at $75. Cash-pay friendly. "
            "We treat colds, flu, infections, minor injuries, and more.\n\n"
            "Skip the ER. Get seen tonight.\n\n"
            "Call (956) 627-3258.\n\n"
            "#SkipTheER #CashPayClinic #OptimumCare"
        ),
    },
]

# ── Post loop ──────────────────────────────────────────────────────────────────
success = 0
fail = 0

for i, post in enumerate(POSTS, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/{len(POSTS)}] {post['name']} -> {post['page_key']}")
    print(f"{'='*60}")

    # Kill Chrome between posts
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

    # Get image file
    if post["image_local"] and Path(post["image_local"]).exists():
        img_path = post["image_local"]
    elif post["image_url"]:
        img_path = str(TMP_DIR / f"{post['page_key']}_hero.png")
        print(f"  Downloading image...", end=" ", flush=True)
        try:
            urllib.request.urlretrieve(post["image_url"], img_path)
            print("OK")
        except Exception as e:
            print(f"FAIL: {e}")
            fail += 1
            continue
    else:
        print("  SKIP - no image available")
        fail += 1
        continue

    # Post to Facebook
    cmd = [
        sys.executable, MARKETER,
        "--action", "image",
        "--page", post["page_key"],
        "--message", post["message"],
        "--media", img_path,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(EXEC_DIR), encoding="utf-8", errors="replace"
        )
        output = result.stdout or ""

        if "SUCCESS" in output:
            print(f"  POSTED to {post['page_key']}")
            success += 1
        else:
            print(f"  FAILED (rc={result.returncode})")
            lines = output.strip().split("\n")
            for line in lines[-8:]:
                print(f"    {line}")
            fail += 1
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT")
        fail += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        fail += 1

    # Pause between posts
    if i < len(POSTS):
        print("  Waiting 8s...")
        time.sleep(8)

print(f"\n{'='*60}")
print(f"RESULTS: {success}/{len(POSTS)} posted, {fail} failed")
print(f"{'='*60}")
