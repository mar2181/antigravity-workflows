#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Campaign Runner — Generate → Preview → Approve → Post
==============================================================
Connected workflow for all 4 Facebook ad accounts.

Usage:
  python fb_campaign_runner.py --business sugar_shack --mode full
  python fb_campaign_runner.py --business island_arcade --mode generate
  python fb_campaign_runner.py --business island_candy --mode post
  python fb_campaign_runner.py --business juan --mode preview

Modes:
  generate  — Run fal.ai image generation script for this business
  preview   — Generate HTML preview files for each ad in the manifest
  post      — Show preview → wait for approval → post each ad
  full      — generate + preview + post in sequence

Manifest file (created by Claude when writing ADS_FINAL.md):
  Each business skill folder contains ads_manifest.json with ad copy + schedule + image paths.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# Asset resolver — uses real client photos when available, falls back to fal.ai
sys.path.insert(0, str(Path(__file__).parent))
try:
    from asset_resolver import resolve_asset, list_assets
    ASSET_RESOLVER_AVAILABLE = True
except ImportError:
    ASSET_RESOLVER_AVAILABLE = False

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── Business registry ──────────────────────────────────────────────────────────
BUSINESSES = {
    "sugar_shack": {
        "name":        "The Sugar Shack",
        "page_key":    "sugar_shack",
        "image_dir":   r"C:\Users\mario\sugar_shack_ad_images",
        "preview_dir": r"C:\Users\mario\sugar_shack_ad_images",
        "skill_dir":   r"C:\Users\mario\.gemini\antigravity\scratch\skills\sugar-shack-facebook",
        "color":       "#e91e63",   # pink
        "avatar_bg":   "#e91e63",
        "avatar_text": "SS",
    },
    "island_arcade": {
        "name":        "Island Arcade SPI",
        "page_key":    "island_arcade",
        "image_dir":   r"C:\Users\mario\island_arcade_ad_images",
        "preview_dir": r"C:\Users\mario\island_arcade_ad_images",
        "skill_dir":   r"C:\Users\mario\.gemini\antigravity\scratch\skills\island-arcade-facebook",
        "color":       "#7c3aed",   # purple
        "avatar_bg":   "#7c3aed",
        "avatar_text": "IA",
    },
    "island_candy": {
        "name":        "Island Candy",
        "page_key":    "island_candy",
        "image_dir":   r"C:\Users\mario\island_candy_ad_images",
        "preview_dir": r"C:\Users\mario\island_candy_ad_images",
        "skill_dir":   r"C:\Users\mario\.gemini\antigravity\scratch\skills\island-candy-facebook",
        "color":       "#f59e0b",   # amber
        "avatar_bg":   "#f59e0b",
        "avatar_text": "IC",
    },
    "juan": {
        "name":        "Juan Elizondo RE/MAX Elite",
        "page_key":    "juan",
        "image_dir":   r"C:\Users\mario\juan_remax_ad_images",
        "preview_dir": r"C:\Users\mario\juan_remax_ad_images",
        "skill_dir":   r"C:\Users\mario\.gemini\antigravity\scratch\skills\juan-elizondo-remax-elite-facebook",
        "color":       "#0ea5e9",   # RE/MAX blue
        "avatar_bg":   "#cc0000",   # RE/MAX red
        "avatar_text": "JE",
    },
}

MARKETER_SCRIPT = r"C:\Users\mario\.gemini\antigravity\tools\execution\facebook_marketer.py"
PYTHON          = sys.executable

# Mission Control — Supabase client UUIDs (matches project-config.ts clientDbId)
MC_CLIENT_IDS = {
    "sugar_shack":       "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
    "island_arcade":     "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
    "island_candy":      "d865037b-2552-4024-9db3-10e61e1419b4",
    "juan":              "a1000001-0000-0000-0000-000000000001",
    "spi_fun_rentals":   "f8693268-6abf-4401-8b2e-3795e326252b",
    "custom_designs_tx": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
    "optimum_clinic":    "a1000002-0000-0000-0000-000000000002",
    "optimum_foundation":"a1000003-0000-0000-0000-000000000003",
}
MC_IMPORT_URL  = "http://localhost:3001/api/ad-creatives/import"
MC_IMAGE_PROXY = "http://localhost:3001/api/local-image?path="


# ── Mission Control import hook ──────────────────────────────────────────────
def sync_to_mission_control(business_key: str, ads: list):
    """
    Push the campaign manifest to Mission Control's ad library (fire-and-forget).
    Silently skips if MC isn't running or business key is unknown.
    """
    client_id = MC_CLIENT_IDS.get(business_key)
    if not client_id:
        return

    entries = []
    for ad in ads:
        image_path = ad.get("image", "")
        # Serve through MC's local-image proxy so the browser can load it over HTTP
        fal_url = (MC_IMAGE_PROXY + image_path) if image_path and os.path.exists(image_path) else None
        entries.append({
            "name":          f"Ad #{ad.get('id', '?')} — {ad.get('angle', 'unknown')}",
            "url":           fal_url or "",
            "media_type":    "image",
            "copy_headline": ad.get("angle", "").replace("_", " ").title(),
            "copy_body":     ad.get("copy", ""),
            "copy_cta":      "",
            "ad_angle":      ad.get("angle", ""),
            "platform":      "facebook",
        })

    if not entries:
        return

    payload = json.dumps({"entries": entries, "clientId": client_id}).encode("utf-8")
    try:
        req = urllib.request.Request(
            MC_IMPORT_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            print(f"  [MC] Imported {result.get('imported', 0)} ads to Mission Control ad library.")
    except urllib.error.URLError:
        print("  [MC] Mission Control not running — skipping ad library sync.")
    except Exception as e:
        print(f"  [MC] Ad library sync failed: {e}")


# ── HTML preview generator ────────────────────────────────────────────────────
def generate_preview_html(ad: dict, biz: dict, output_path: str) -> str:
    """Generate a Facebook-style preview HTML for a single ad."""
    image_path = ad.get("image", "")
    copy_text  = ad.get("copy", "").replace("\n", "<br>")
    ad_id      = ad.get("id", "?")
    angle      = ad.get("angle", "unknown")
    schedule   = ad.get("schedule", "Immediate")
    name       = biz["name"]
    color      = biz["color"]
    avatar_bg  = biz["avatar_bg"]
    avatar_txt = biz["avatar_text"]

    # Convert Windows path to file:// URL for embedding
    img_url = Path(image_path).as_uri() if image_path and os.path.exists(image_path) else ""
    img_tag = f'<img src="{img_url}" style="width:100%;display:block;border-radius:0 0 8px 8px;">' if img_url else \
              '<div style="width:100%;height:300px;background:#e0e0e0;display:flex;align-items:center;justify-content:center;font-size:14px;color:#666;border-radius:0 0 8px 8px;">Image not yet generated</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Preview Ad #{ad_id} — {name}</title>
<style>
  body {{ margin: 0; padding: 24px; background: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  .preview-label {{ max-width: 520px; margin: 0 auto 12px; color: #65676b; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; }}
  .meta {{ max-width: 520px; margin: 0 auto 8px; color: #65676b; font-size: 12px; }}
  .card {{ max-width: 520px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,.15); overflow: hidden; }}
  .header {{ display: flex; align-items: center; padding: 12px 16px; gap: 10px; }}
  .avatar {{ width: 42px; height: 42px; border-radius: 50%; background: {avatar_bg}; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 15px; flex-shrink: 0; }}
  .page-name {{ font-weight: 700; font-size: 15px; color: #050505; line-height: 1.2; }}
  .sponsored {{ font-size: 12px; color: #65676b; }}
  .body {{ padding: 0 16px 12px; font-size: 15px; color: #050505; line-height: 1.5; }}
  .image-wrap {{ background: #000; }}
  .footer {{ padding: 10px 16px; border-top: 1px solid #e4e6eb; display: flex; gap: 8px; }}
  .reaction {{ flex: 1; text-align: center; padding: 6px; color: #65676b; font-size: 14px; font-weight: 600; cursor: pointer; border-radius: 4px; }}
  .reaction:hover {{ background: #f2f2f2; }}
  .approve-bar {{ max-width: 520px; margin: 16px auto 0; display: flex; gap: 12px; }}
  .btn {{ flex: 1; padding: 12px; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; }}
  .btn-approve {{ background: {color}; color: #fff; }}
  .btn-skip {{ background: #e4e6eb; color: #050505; }}
  .approved-msg {{ display:none; max-width:520px; margin:12px auto; padding:12px 16px; background:#d4edda; color:#155724; border-radius:8px; font-weight:600; font-size:14px; }}
</style>
</head>
<body>

<div class="preview-label">📋 Ad #{ad_id} Preview — {angle.replace('_', ' ').title()}</div>
<div class="meta">📅 Scheduled: {schedule} &nbsp;|&nbsp; 📄 Angle: {angle}</div>

<div class="card">
  <div class="header">
    <div class="avatar">{avatar_txt}</div>
    <div>
      <div class="page-name">{name}</div>
      <div class="sponsored">Sponsored · 🌐</div>
    </div>
  </div>
  <div class="body">{copy_text}</div>
  <div class="image-wrap">{img_tag}</div>
  <div class="footer">
    <div class="reaction">👍 Like</div>
    <div class="reaction">💬 Comment</div>
    <div class="reaction">↗️ Share</div>
  </div>
</div>

<div class="approve-bar">
  <button class="btn btn-approve" onclick="approve()">✅ APPROVED — Post this</button>
  <button class="btn btn-skip" onclick="skip()">⏭ Skip for now</button>
</div>
<div class="approved-msg" id="msg">✅ Marked as approved! Return to terminal and press Y.</div>

<script>
function approve() {{
  document.getElementById('msg').style.display = 'block';
  document.querySelector('.btn-approve').disabled = true;
  document.querySelector('.btn-approve').style.opacity = '0.5';
  document.querySelector('.btn-approve').textContent = '✅ Approved';
}}
function skip() {{
  document.querySelector('.btn-skip').textContent = '⏭ Skipped';
  document.querySelector('.btn-skip').disabled = true;
}}
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return Path(output_path).as_uri()


# ── Manifest loader ───────────────────────────────────────────────────────────
def load_manifest(biz: dict) -> list:
    manifest_path = os.path.join(biz["skill_dir"], "ads_manifest.json")
    if not os.path.exists(manifest_path):
        print(f"\n[ERROR] No ads_manifest.json found at:\n  {manifest_path}")
        print("\n[HELP] To create this file, ask Claude:")
        biz_name = biz["name"]
        print(f'  "Generate the {biz_name} ad campaign and save ads_manifest.json"')
        print("  Claude will write the JSON with ad copy, schedule dates, and image filenames.\n")
        sys.exit(1)
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("ads", [])


def save_manifest(biz: dict, ads: list):
    manifest_path = os.path.join(biz["skill_dir"], "ads_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(ads, f, indent=2, ensure_ascii=False)


# ── Mode: generate ────────────────────────────────────────────────────────────
def run_generate(biz: dict):
    gen_script = os.path.join(biz["skill_dir"], "generate_with_fal_v2.py")
    if not os.path.exists(gen_script):
        print(f"[ERROR] generate_with_fal_v2.py not found at: {gen_script}")
        sys.exit(1)
    print(f"\n[GENERATE] Starting fal.ai image generation for {biz['name']}...")
    result = subprocess.run([PYTHON, gen_script])
    if result.returncode == 0:
        print(f"[OK] Image generation complete.")
        # Sync generated ads to Mission Control ad library
        ads = load_manifest(biz)
        sync_to_mission_control(biz["page_key"], ads)
    else:
        print(f"[ERROR] Generation script exited with code {result.returncode}")
        sys.exit(result.returncode)


# ── Mode: preview ─────────────────────────────────────────────────────────────
def run_preview(biz: dict) -> list:
    ads = load_manifest(biz)
    os.makedirs(biz["preview_dir"], exist_ok=True)
    print(f"\n[PREVIEW] Generating HTML previews for {biz['name']} ({len(ads)} ads)...\n")
    for ad in ads:
        # Use real asset if image missing or file not found
        if ASSET_RESOLVER_AVAILABLE:
            img = ad.get("image", "")
            if not img or not os.path.exists(img):
                real = resolve_asset(biz["page_key"], ad.get("angle", ""))
                if real:
                    ad["image"] = real
        preview_file = os.path.join(biz["preview_dir"], f"preview_ad{ad['id']}.html")
        url = generate_preview_html(ad, biz, preview_file)
        status = "✅ POSTED" if ad.get("posted") else "⏳ pending"
        print(f"  Ad #{ad['id']:2d} [{status}] {ad.get('angle',''):<25s} → {url}")
    print()
    return ads


# ── Mode: post ────────────────────────────────────────────────────────────────
def run_post(biz: dict):
    ads = load_manifest(biz)
    os.makedirs(biz["preview_dir"], exist_ok=True)

    pending = [a for a in ads if not a.get("posted")]
    if not pending:
        print(f"\n[DONE] All ads for {biz['name']} are already marked as posted.")
        return

    print(f"\n[POST] Starting approval workflow for {biz['name']}")
    print(f"       {len(pending)} ads pending, {len(ads) - len(pending)} already posted\n")
    print("  Controls: y=post  n/skip=skip  q=quit\n")
    print("=" * 60)

    for ad in ads:
        if ad.get("posted"):
            print(f"  Ad #{ad['id']:2d} — ✅ already posted, skipping")
            continue

        # Use real asset if image missing or file not found
        if ASSET_RESOLVER_AVAILABLE:
            img = ad.get("image", "")
            if not img or not os.path.exists(img):
                real = resolve_asset(biz["page_key"], ad.get("angle", ""))
                if real:
                    ad["image"] = real
                    print(f"  [ASSET] Using real photo: {Path(real).name}")

        # Generate preview
        preview_file = os.path.join(biz["preview_dir"], f"preview_ad{ad['id']}.html")
        url = generate_preview_html(ad, biz, preview_file)

        print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  Ad #{ad['id']} — {ad.get('angle','').replace('_',' ').title()}")
        print(f"  Schedule: {ad.get('schedule', 'Immediate')}")
        print(f"  Image:    {ad.get('image', 'NOT SET')}")
        print(f"  Preview:  {url}")
        print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Approval prompt
        choice = input(f"\n  Post Ad #{ad['id']}? [y/n/q] → ").strip().lower()

        if choice == "q":
            print("\n[QUIT] Session ended. Progress saved. Run again to continue.")
            save_manifest(biz, ads)
            return

        if choice != "y":
            print(f"  [SKIP] Ad #{ad['id']} skipped.")
            continue

        # Build command
        image_path = ad.get("image", "")
        copy_text  = ad.get("copy", "")
        schedule   = ad.get("schedule", "")
        page_key   = biz["page_key"]

        if not copy_text:
            print(f"  [ERROR] No copy text for ad #{ad['id']} — check ads_manifest.json")
            continue

        if schedule and schedule.lower() != "immediate":
            action = "schedule"
            cmd = [PYTHON, MARKETER_SCRIPT,
                   "--action", "schedule",
                   "--page",   page_key,
                   "--message", copy_text,
                   "--schedule", schedule]
        else:
            action = "image" if image_path else "text"
            cmd = [PYTHON, MARKETER_SCRIPT,
                   "--action", action,
                   "--page",   page_key,
                   "--message", copy_text]

        if image_path and os.path.exists(image_path):
            cmd += ["--media", image_path]
        elif image_path:
            print(f"  [WARNING] Image not found: {image_path}")
            confirm = input("  Post without image? [y/n] → ").strip().lower()
            if confirm != "y":
                print(f"  [SKIP] Skipped ad #{ad['id']} (missing image)")
                continue
            cmd = [PYTHON, MARKETER_SCRIPT,
                   "--action", "text",
                   "--page",   page_key,
                   "--message", copy_text]

        print(f"\n  [POSTING] Ad #{ad['id']} via facebook_marketer.py...")
        result = subprocess.run(cmd)

        if result.returncode == 0:
            ad["posted"] = True
            ad["posted_at"] = time.strftime("%Y-%m-%d %H:%M")
            save_manifest(biz, ads)
            print(f"  [SUCCESS] Ad #{ad['id']} posted. Manifest updated.")
        else:
            print(f"  [ERROR] Posting failed (exit code {result.returncode}). Ad NOT marked posted.")

        # Brief pause between posts
        if ad["id"] < len(ads):
            print("  [WAIT] 15 seconds before next ad...")
            time.sleep(15)

    print(f"\n[COMPLETE] {biz['name']} campaign posting session done.")
    posted_count = sum(1 for a in ads if a.get("posted"))
    print(f"[STATUS] {posted_count}/{len(ads)} ads posted total.\n")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Facebook Campaign Runner")
    parser.add_argument("--business", required=True,
                        choices=list(BUSINESSES.keys()),
                        help="Which business to run")
    parser.add_argument("--mode", required=True,
                        choices=["generate", "preview", "post", "full"],
                        help="generate|preview|post|full")
    args = parser.parse_args()

    biz = BUSINESSES[args.business]

    print(f"\n{'='*60}")
    print(f"  Facebook Campaign Runner")
    print(f"  Business : {biz['name']}")
    print(f"  Mode     : {args.mode.upper()}")
    print(f"  Page Key : {biz['page_key']}")
    print(f"{'='*60}")

    if args.mode == "generate":
        run_generate(biz)

    elif args.mode == "preview":
        run_preview(biz)

    elif args.mode == "post":
        run_post(biz)

    elif args.mode == "full":
        run_generate(biz)
        run_preview(biz)
        run_post(biz)


if __name__ == "__main__":
    main()
