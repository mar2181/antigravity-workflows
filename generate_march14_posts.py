#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate images for all 6 accounts — March 14, 2026 spring break posts.
Runs fal.ai generation, downloads images, then builds HTML previews.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import fal_client
except ImportError:
    os.system(f"{sys.executable} -m pip install fal_client -q")
    import fal_client

FAL_KEY = "39cee61b-1fb5-40ca-b489-7ff6bcec01ad:e223d38f3f0f8df11bff0b49cc46a73f"

# ── Ad definitions ─────────────────────────────────────────────────────────────
ADS = [
    {
        "key":      "sugar_shack",
        "name":     "The Sugar Shack",
        "avatar":   "SS",
        "color":    "#e91e63",
        "out_dir":  r"C:\Users\mario\sugar_shack_ad_images",
        "filename": "march14_spring_break.png",
        "prompt":   (
            "Massive colorful candy store display: overflowing bins of gummy bears, "
            "sour worms, rock candy, taffy, lollipops, and novelty sweets arranged in "
            "a rainbow of colors; bright white shelving, warm inviting store lighting, "
            "a paper bag filled with candies tipped over spilling treats, spring break "
            "vacation energy, South Padre Island gift shop feel, "
            "professional photography, 4k"
        ),
        "copy": (
            "Spring break just started — and we are READY for you. 🍭\n\n"
            "Pulling up to South Padre Island? Make The Sugar Shack your first stop. "
            "We've got the biggest candy selection on the Island — gummies, chocolates, "
            "saltwater taffy, novelty treats, and more than you can carry in one bag.\n\n"
            "Road trip fuel. Beach day rewards. Late-night sweet fix. Whatever the "
            "occasion, we've got what you're looking for.\n\n"
            "Come in, fill a bag, and make the week sweeter.\n\n"
            "📍 South Padre Island, TX\n\n"
            "#SpringBreak #SouthPadreIsland #SugarShackSPI"
        ),
    },
    {
        "key":      "island_arcade",
        "name":     "Island Arcade SPI",
        "avatar":   "IA",
        "color":    "#7c3aed",
        "out_dir":  r"C:\Users\mario\island_arcade_ad_images",
        "filename": "march14_spring_break.png",
        "prompt":   (
            "Vibrant indoor arcade filled with glowing game machines: claw machines, "
            "ticket-dispensing arcade cabinets, neon-lit racing games, and prize "
            "redemption counter overflowing with stuffed animals and prizes; colorful "
            "neon signs reflecting off polished floor, exciting and energetic atmosphere, "
            "no people visible, professional photography, 4k"
        ),
        "copy": (
            "Spring break is ON and the games are waiting. 🕹️\n\n"
            "Whether you're taking a break from the beach or looking for something to "
            "do after the sun goes down — Island Arcade has you covered. Compete with "
            "your crew, rack up tickets, and walk away with something to brag about.\n\n"
            "No rain required. Just walk in and start playing.\n\n"
            "📍 South Padre Island, TX\n\n"
            "#SpringBreak #IslandArcade #SouthPadreIsland"
        ),
    },
    {
        "key":      "spi",
        "name":     "SPI Fun Rentals",
        "avatar":   "SR",
        "color":    "#0ea5e9",
        "out_dir":  r"C:\Users\mario\spi_fun_rentals_ad_images",
        "filename": "march14_spring_break.png",
        "prompt":   (
            "Two shiny golf carts parked side by side on a wide South Padre Island "
            "beach road; bright blue sky, palm trees and Gulf of Mexico water visible "
            "in background, golden midday sunshine, road stretching ahead toward the "
            "horizon giving sense of freedom and adventure, vibrant vacation energy, "
            "professional photography, 4k"
        ),
        "copy": (
            "Spring break is here — and the best way to see South Padre Island is "
            "from the seat of a golf cart. 🛻\n\n"
            "Cruise every beach access. Find your favorite sunset spot. Explore the "
            "whole Island on your schedule.\n\n"
            "Golf carts, jeeps, and beach gear — all ready to roll. Availability goes "
            "fast this week, so don't wait.\n\n"
            "📞 (956) 761-9999 | 1314 Padre Blvd #A, South Padre Island\n"
            "spifunrentals.com\n\n"
            "#SpringBreak #SouthPadreIsland #SPIFunRentals"
        ),
    },
    {
        "key":      "island_candy",
        "name":     "Island Candy",
        "avatar":   "IC",
        "color":    "#f59e0b",
        "out_dir":  r"C:\Users\mario\island_candy_ad_images",
        "filename": "march14_spring_break.png",
        "prompt":   (
            "Two generous scoops of ice cream — one bright strawberry, one mint chip — "
            "in a waffle cone, slightly melting in bright beach sunlight; pastel "
            "background with soft turquoise tones evoking the Gulf of Mexico, colorful "
            "ice cream dripping down the sides, fresh and indulgent, summer heat energy, "
            "professional product photography, 4k"
        ),
        "copy": (
            "You've been out in the sun all day. You deserve this. 🍦\n\n"
            "Cool off with a scoop (or two) at Island Candy — right inside Island "
            "Arcade on South Padre Island. The perfect pick-me-up after a long beach day.\n\n"
            "Spring break goes by fast. Make every afternoon count.\n\n"
            "📍 Inside Island Arcade — South Padre Island, TX\n\n"
            "#SpringBreak #IslandCandy #SouthPadreIsland"
        ),
    },
    {
        "key":      "juan",
        "name":     "Juan Elizondo RE/MAX Elite",
        "avatar":   "JE",
        "color":    "#cc0000",
        "out_dir":  r"C:\Users\mario\juan_remax_ad_images",
        "filename": "march14_spring_market.png",
        "prompt":   (
            "Beautiful suburban Texas home exterior: single-story brick and stucco, "
            "lush green front lawn, blooming spring flower beds in red and yellow, "
            "wide driveway, mature shade tree in yard, clear blue South Texas sky, "
            "warm afternoon golden-hour lighting, neighborhood street visible, "
            "inviting and move-in ready, professional real estate photography, 4k"
        ),
        "copy": (
            "Spring is one of the best times to make a move in the Rio Grande Valley. 🏡\n\n"
            "Whether you've been thinking about buying, selling, or just want to know "
            "what your home is worth right now — this is the season when buyers are "
            "active and the market is moving.\n\n"
            "The RGV rewards those who act before summer. If you have questions about "
            "your neighborhood, your budget, or what's available — I'm here to help, "
            "no pressure, just answers.\n\n"
            "📱 DM me or call directly — Juan José Elizondo, RE/MAX Elite\n\n"
            "#RGV #McAllen #RealEstate"
        ),
    },
    {
        "key":      "optimum_clinic",
        "name":     "Optimum Health & Wellness Clinic",
        "avatar":   "OC",
        "color":    "#0f766e",
        "out_dir":  r"C:\Users\mario\optimum_clinic_ad_images",
        "filename": "march14_after_hours.png",
        "prompt":   (
            "Modern medical clinic exterior at dusk: clean contemporary architecture "
            "with warm interior lights glowing through large windows, welcoming entrance "
            "with glass doors, manicured landscaping, parking lot with a few cars, "
            "deep blue evening sky, professional signage illuminated, safe and "
            "accessible feel, professional photography, 4k"
        ),
        "copy": (
            "Spring break is great — until someone gets sick at 8 PM. 🏥\n\n"
            "We're Optimum Health & Wellness Clinic in Pharr, open every night until "
            "10 PM. No appointment needed. No insurance required. Walk right in.\n\n"
            "Sick visits starting at $75. Rapid flu, COVID, and strep tests available. "
            "100% bilingual staff.\n\n"
            "While every other clinic in the RGV closes at 6 or 8 PM — we're still "
            "here for you and your family.\n\n"
            "📍 3912 N Jackson Rd, Pharr, TX | 📞 (956) 627-3258\n"
            "Open 5–10 PM, 7 days a week\n\n"
            "#Pharr #McAllen #RGVHealth"
        ),
    },
]


# ── fal.ai generation ──────────────────────────────────────────────────────────
def generate_image(ad: dict) -> str | None:
    os.makedirs(ad["out_dir"], exist_ok=True)
    filepath = os.path.join(ad["out_dir"], ad["filename"])

    print(f"\n[GEN] {ad['name']} — {ad['filename']}")
    print(f"      Prompt: {ad['prompt'][:80]}...")

    try:
        handler = fal_client.submit(
            "fal-ai/flux-pro/v1.1-ultra",
            arguments={
                "prompt":     ad["prompt"],
                "image_size": "landscape_16_9",
                "num_images": 1,
            },
        )
        result = handler.get()

        if "images" in result and result["images"]:
            url = result["images"][0]["url"]
            print(f"      Downloading from fal.ai...")
            urllib.request.urlretrieve(url, filepath)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"      [OK] Saved → {filepath} ({size_mb:.1f}MB)")
            return filepath
        else:
            print(f"      [FAIL] No images returned")
            return None
    except Exception as e:
        print(f"      [ERROR] {e}")
        return None


# ── HTML preview builder ───────────────────────────────────────────────────────
PREVIEW_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Preview — {name}</title>
<style>
  body {{ margin:0; padding:24px; background:#f0f2f5;
          font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
  .label {{ max-width:520px; margin:0 auto 12px; color:#65676b;
             font-size:13px; font-weight:600; letter-spacing:.5px;
             text-transform:uppercase; }}
  .card {{ max-width:520px; margin:0 auto; background:#fff;
           border-radius:8px; box-shadow:0 2px 12px rgba(0,0,0,.15);
           overflow:hidden; }}
  .header {{ display:flex; align-items:center; padding:12px 16px; gap:10px; }}
  .avatar {{ width:42px; height:42px; border-radius:50%;
             background:{color}; display:flex; align-items:center;
             justify-content:center; color:#fff; font-weight:700;
             font-size:15px; flex-shrink:0; }}
  .page-name {{ font-weight:700; font-size:15px; color:#050505; line-height:1.2; }}
  .sponsored {{ font-size:12px; color:#65676b; }}
  .body {{ padding:0 16px 12px; font-size:15px; color:#050505; line-height:1.5;
           white-space:pre-wrap; }}
  .image-wrap {{ background:#000; }}
  .image-wrap img {{ width:100%; display:block; border-radius:0 0 8px 8px; }}
  .no-img {{ width:100%; height:300px; background:#e0e0e0; display:flex;
             align-items:center; justify-content:center; font-size:14px;
             color:#666; }}
  .footer {{ padding:10px 16px; border-top:1px solid #e4e6eb;
             display:flex; gap:8px; }}
  .reaction {{ flex:1; text-align:center; padding:6px; color:#65676b;
               font-size:14px; font-weight:600; cursor:pointer;
               border-radius:4px; }}
  .reaction:hover {{ background:#f2f2f2; }}
</style>
</head>
<body>
<div class="label">📋 Preview — {name}</div>
<div class="card">
  <div class="header">
    <div class="avatar">{avatar}</div>
    <div>
      <div class="page-name">{name}</div>
      <div class="sponsored">March 14, 2026 · Spring Break Post</div>
    </div>
  </div>
  <div class="body">{copy}</div>
  <div class="image-wrap">{img_tag}</div>
  <div class="footer">
    <div class="reaction">👍 Like</div>
    <div class="reaction">💬 Comment</div>
    <div class="reaction">↗️ Share</div>
  </div>
</div>
</body>
</html>"""


def build_preview(ad: dict, image_path: str | None) -> str:
    if image_path and os.path.exists(image_path):
        uri = Path(image_path).as_uri()
        img_tag = f'<img src="{uri}" alt="ad image">'
    else:
        img_tag = '<div class="no-img">Image not generated</div>'

    html = PREVIEW_TEMPLATE.format(
        name=ad["name"],
        avatar=ad["avatar"],
        color=ad["color"],
        copy=ad["copy"],
        img_tag=img_tag,
    )

    preview_path = os.path.join(ad["out_dir"], f"preview_march14_{ad['key']}.html")
    os.makedirs(ad["out_dir"], exist_ok=True)
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html)
    return preview_path


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    os.environ["FAL_KEY"] = FAL_KEY

    print("=" * 60)
    print("  March 14 Post Generation — All 6 Accounts")
    print("  Model: fal-ai/flux-pro/v1.1-ultra")
    print("=" * 60)

    results = []
    for ad in ADS:
        img_path = generate_image(ad)
        preview  = build_preview(ad, img_path)
        uri      = Path(preview).as_uri()
        results.append({
            "account":  ad["name"],
            "key":      ad["key"],
            "image":    img_path or "FAILED",
            "preview":  preview,
            "uri":      uri,
        })

    print("\n" + "=" * 60)
    print("  PREVIEWS READY")
    print("=" * 60)
    for r in results:
        status = "✅" if r["image"] != "FAILED" else "❌"
        print(f"  {status} {r['account']}")
        print(f"     Preview: {r['uri']}")
        print()

    # Save manifest for posting later
    manifest_path = r"C:\Users\mario\.gemini\antigravity\tools\execution\march14_posts_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            [{"key": a["key"], "copy": a["copy"],
              "image": r["image"], "preview": r["preview"]}
             for a, r in zip(ADS, results)],
            f, indent=2, ensure_ascii=False
        )
    print(f"  Manifest saved → {manifest_path}")


if __name__ == "__main__":
    main()
