"""Generate fresh fal.ai images for 4 SPI-area clients and post to Facebook."""

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

# Load FAL_KEY
env_path = Path(r"C:\Users\mario\.gemini\antigravity\scratch\gravity-claw\.env")
fal_key = None
for line in env_path.read_text().splitlines():
    if line.startswith("FAL_KEY"):
        fal_key = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
os.environ["FAL_KEY"] = fal_key

import fal_client

POSTS = [
    {
        "page_key": "sugar_shack",
        "name": "Sugar Shack",
        "image_prompt": "Colorful candy store interior with rows of bulk candy bins overflowing with gummies, chocolate, taffy, and sour belts, bright cheerful lighting, South Padre Island beach vacation candy shop vibes, warm inviting atmosphere, professional photography, 4k",
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
        "name": "Island Arcade",
        "image_prompt": "Vibrant neon-lit arcade interior with rows of classic arcade game cabinets glowing with colorful screens, exciting atmosphere, tokens and prize tickets, family entertainment center on a beach island, professional photography, 4k",
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
        "name": "Island Candy",
        "image_prompt": "Beautiful tropical ice cream display with vibrant scoops of mango, coconut, passion fruit, and guava ice cream in a bright cheerful shop setting, tropical beach town ice cream parlor, colorful and refreshing, professional photography, 4k",
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
        "page_key": "spi",
        "name": "SPI Fun Rentals",
        "image_prompt": "A row of clean colorful golf carts parked on a paved road near a tropical beach town, palm trees and blue sky, South Padre Island Texas vacation rental fleet, fun family transportation, professional photography, 4k",
        "message": (
            "Skip the parking hassle. Grab a golf cart and cruise South Padre Island like a local.\n\n"
            "SPI Fun Rentals has the cleanest, most reliable golf carts on the island. "
            "Perfect for beach hopping, dinner runs, or just exploring with the family.\n\n"
            "We deliver to your rental. Easy pickup, easy return. "
            "Book ahead for spring break - carts go fast.\n\n"
            "Call or text to reserve yours today.\n\n"
            "#SPIFunRentals #GolfCartRentals #SouthPadreIsland"
        ),
    },
]

# ── Generate images ────────────────────────────────────────────────────────────
print("Generating 4 images via fal.ai Flux Pro...\n")

for post in POSTS:
    img_path = TMP_DIR / f"{post['page_key']}_hero.png"
    post["image_path"] = str(img_path)

    if img_path.exists() and img_path.stat().st_size > 10000:
        print(f"  {post['name']}: image exists, skipping generation")
        continue

    print(f"  {post['name']}: generating...", end=" ", flush=True)
    try:
        handler = fal_client.submit(
            "fal-ai/flux-pro/v1.1-ultra",
            arguments={
                "prompt": post["image_prompt"],
                "image_size": "landscape_16_9",
                "num_images": 1,
            },
        )
        result = handler.get()
        img_url = result["images"][0]["url"]
        urllib.request.urlretrieve(img_url, str(img_path))
        print("OK")
    except Exception as e:
        print(f"FAIL: {e}")
        post["image_path"] = None

# ── Post to Facebook ───────────────────────────────────────────────────────────
print("\nPosting to Facebook...\n")

success = 0
fail = 0

for i, post in enumerate(POSTS, 1):
    print(f"[{i}/{len(POSTS)}] {post['name']} -> {post['page_key']}")

    if not post.get("image_path") or not Path(post["image_path"]).exists():
        print("  SKIP - no image")
        fail += 1
        continue

    # Kill Chrome between posts
    subprocess.run(
        ["powershell", "-Command", "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"],
        capture_output=True
    )
    time.sleep(2)
    for profile in ["facebook_mario_profile", "facebook_sniffer_profile"]:
        lock = EXEC_DIR / profile / "SingletonLock"
        if lock.exists():
            lock.unlink()

    cmd = [
        sys.executable, MARKETER,
        "--action", "image",
        "--page", post["page_key"],
        "--message", post["message"],
        "--media", post["image_path"],
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(EXEC_DIR), encoding="utf-8", errors="replace"
        )
        output = result.stdout or ""

        if "SUCCESS" in output:
            print(f"  POSTED")
            success += 1
        else:
            print(f"  FAILED (rc={result.returncode})")
            lines = output.strip().split("\n")
            for line in lines[-8:]:
                print(f"    {line}")
            fail += 1
    except subprocess.TimeoutExpired:
        print("  TIMEOUT")
        fail += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        fail += 1

    if i < len(POSTS):
        print("  Waiting 8s...")
        time.sleep(8)

print(f"\nDONE: {success}/{len(POSTS)} posted, {fail} failed")
