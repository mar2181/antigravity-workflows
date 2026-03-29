"""Generate fal.ai images for all location pages created 2026-03-27."""

import json
import os
import sys
import urllib.request
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ENV_PATH = Path(r"C:\Users\mario\.gemini\antigravity\scratch\gravity-claw\.env")
BLOG_DIRS = {
    "custom_designs_tx": Path(r"C:\Users\mario\.gemini\antigravity\tools\execution\blog_posts\custom_designs_tx"),
    "juan": Path(r"C:\Users\mario\.gemini\antigravity\tools\execution\blog_posts\juan"),
}
DATE_PREFIX = "2026-03-27"

# ── Load FAL_KEY ───────────────────────────────────────────────────────────────
fal_key = None
for line in ENV_PATH.read_text().splitlines():
    if line.startswith("FAL_KEY"):
        fal_key = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

if not fal_key:
    print("ERROR: FAL_KEY not found")
    sys.exit(1)

os.environ["FAL_KEY"] = fal_key

try:
    import fal_client
except ImportError:
    os.system(f'"{sys.executable}" -m pip install fal_client -q')
    import fal_client

# ── Size map ───────────────────────────────────────────────────────────────────
SIZE_MAP = {
    "hero": "landscape_16_9",
    "section_1": "square_hd",
    "section_2": "square_hd",
    "section_3": "square_hd",
}

# ── Collect all meta files ─────────────────────────────────────────────────────
meta_files = []
for biz_key, blog_dir in BLOG_DIRS.items():
    for f in sorted(blog_dir.glob(f"{DATE_PREFIX}*_meta.json")):
        meta_files.append((biz_key, f))

print(f"Found {len(meta_files)} meta files to process\n")

total_generated = 0
total_skipped = 0

for biz_key, meta_path in meta_files:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    keyword = meta.get("keyword", "unknown")
    slug = meta_path.stem.replace("_meta", "")

    # Image output directory
    img_dir = meta_path.parent / "images" / slug
    img_dir.mkdir(parents=True, exist_ok=True)

    prompts = meta.get("image_prompts", {})
    if not prompts:
        print(f"  SKIP {keyword} — no image_prompts in meta")
        continue

    print(f"[{biz_key}] {keyword}")

    updated_images = meta.get("images", {})

    for key, prompt in prompts.items():
        fpath = img_dir / f"{key}.png"

        if fpath.exists() and fpath.stat().st_size > 10000:
            print(f"  {key}: already exists, skipping")
            total_skipped += 1
            continue

        print(f"  {key}: generating...", end=" ", flush=True)
        try:
            handler = fal_client.submit(
                "fal-ai/flux-pro/v1.1-ultra",
                arguments={
                    "prompt": prompt,
                    "image_size": SIZE_MAP.get(key, "square_hd"),
                    "num_images": 1,
                },
            )
            result = handler.get()
            img_url = result["images"][0]["url"]
            urllib.request.urlretrieve(img_url, str(fpath))
            updated_images[key] = str(fpath)
            total_generated += 1
            print("OK")
        except Exception as e:
            print(f"FAIL: {e}")

    # Update meta with image paths
    meta["images"] = updated_images
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print()

print(f"\nDone: {total_generated} generated, {total_skipped} skipped")
