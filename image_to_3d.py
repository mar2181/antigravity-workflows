#!/usr/bin/env python3
"""
image_to_3d.py — Convert 2D images to 3D models via fal.ai Tripo3D

Uses the same FAL_KEY as the ad image pipeline. Outputs GLB files.

Usage:
    # From URL
    python image_to_3d.py --url "https://example.com/photo.jpg"

    # From local file (uploads to fal first)
    python image_to_3d.py --file "C:/Users/mario/photo.jpg"

    # From text prompt (generates 2D image via Flux Pro, then converts to 3D)
    python image_to_3d.py --prompt "modern security camera on a wall bracket"

    # Options
    python image_to_3d.py --url "..." --texture HD --output ./my_models/
    python image_to_3d.py --prompt "..." --name "camera_model" --notify
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).resolve().parent
ENV_FILE = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
OUTPUT_DIR = EXECUTION_DIR / "3d_models"

TRIPO_ENDPOINT = "https://fal.run/tripo3d/tripo/v2.5/image-to-3d"
FLUX_ENDPOINT = "https://fal.run/fal-ai/flux-pro"


def load_env():
    """Load env vars from .env file."""
    env = {}
    try:
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


ENV = load_env()
FAL_KEY = os.environ.get("FAL_KEY") or ENV.get("FAL_KEY", "")

if not FAL_KEY:
    print("❌ FAL_KEY not found in environment or .env file")
    sys.exit(1)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def fal_headers():
    return {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json",
    }


def notify_mario(text: str) -> bool:
    """Send Telegram notification."""
    token = ENV.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = ENV.get("TELEGRAM_USER_ID", "")
    if not token or not chat_id:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read()).get("ok", False)
    except Exception:
        return False


def upload_to_fal(filepath: Path) -> str | None:
    """Upload a local file to fal.ai storage and return the URL."""
    import requests

    url = "https://fal.run/fal-ai/any-llm/storage/upload"
    headers = {"Authorization": f"Key {FAL_KEY}"}

    content_type = "image/png"
    ext = filepath.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        content_type = "image/jpeg"
    elif ext == ".webp":
        content_type = "image/webp"

    with open(filepath, "rb") as f:
        resp = requests.put(
            "https://fal.ai/api/storage/upload",
            headers={**headers, "Content-Type": content_type},
            data=f.read(),
            timeout=60,
        )
    if resp.status_code == 200:
        data = resp.json()
        return data.get("url") or data.get("file_url")
    print(f"  ⚠️ Upload failed: {resp.status_code} {resp.text[:200]}")
    return None


def generate_2d_image(prompt: str) -> str | None:
    """Generate a 2D image via Flux Pro, return the image URL."""
    import requests

    print(f"  🎨 Generating 2D image from prompt...")
    payload = {
        "prompt": prompt + ", clean white background, product photography, studio lighting, 4k",
        "image_size": "square",
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "num_images": 1,
        "safety_tolerance": "2",
        "output_format": "png",
    }
    for attempt in range(2):
        try:
            resp = requests.post(FLUX_ENDPOINT, headers=fal_headers(), json=payload, timeout=90)
            if resp.status_code == 200:
                images = resp.json().get("images", [])
                if images:
                    url = images[0].get("url")
                    print(f"  ✅ 2D image generated")
                    return url
            print(f"  ⚠️ Flux Pro {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  ⚠️ Flux Pro error: {e}")
        if attempt == 0:
            time.sleep(3)
    return None


def convert_to_3d(image_url: str, texture: str = "standard") -> dict | None:
    """Convert a 2D image URL to a 3D model via Tripo3D."""
    import requests

    print(f"  🔮 Converting to 3D (texture: {texture})...")
    payload = {
        "image_url": image_url,
        "texture": texture,
        "texture_alignment": "original_image",
        "orientation": "default",
        "pbr": True,
    }
    try:
        resp = requests.post(TRIPO_ENDPOINT, headers=fal_headers(), json=payload, timeout=300)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  ✅ 3D model generated")
            return data
        print(f"  ❌ Tripo3D {resp.status_code}: {resp.text[:300]}")
    except Exception as e:
        print(f"  ❌ Tripo3D error: {e}")
    return None


def download_file(url: str, filepath: Path) -> bool:
    """Download a file from URL."""
    import requests

    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(resp.content)
            return True
    except Exception as e:
        print(f"  ⚠️ Download failed: {e}")
    return False


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Convert 2D images to 3D models")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="URL of the image to convert")
    group.add_argument("--file", help="Local file path of the image")
    group.add_argument("--prompt", help="Text prompt (generates 2D first, then 3D)")

    parser.add_argument("--texture", default="standard", choices=["no", "standard", "HD"],
                        help="Texture quality (default: standard)")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--name", default=None, help="Output filename (without extension)")
    parser.add_argument("--notify", action="store_true", help="Send Telegram notification when done")

    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp for unique naming
    ts = time.strftime("%Y%m%d_%H%M%S")
    name = args.name or f"model_{ts}"

    print(f"\n🔲 Image → 3D Converter (Tripo3D via fal.ai)")
    print(f"   Output: {output_dir / name}.glb\n")

    # Step 1: Get the image URL
    image_url = None

    if args.url:
        image_url = args.url
        print(f"  📎 Using URL: {image_url[:80]}...")

    elif args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"  ❌ File not found: {filepath}")
            sys.exit(1)
        print(f"  📤 Uploading {filepath.name}...")
        image_url = upload_to_fal(filepath)
        if not image_url:
            print("  ❌ Upload failed")
            sys.exit(1)

    elif args.prompt:
        image_url = generate_2d_image(args.prompt)
        if not image_url:
            print("  ❌ 2D generation failed")
            sys.exit(1)
        # Save the 2D image too
        img_path = output_dir / f"{name}_2d.png"
        if download_file(image_url, img_path):
            print(f"  💾 2D image saved: {img_path}")
            saved_2d = str(img_path)
        else:
            saved_2d = None
    else:
        saved_2d = None

    # Step 2: Convert to 3D
    result = convert_to_3d(image_url, args.texture)
    if not result:
        print("\n❌ 3D conversion failed")
        sys.exit(1)

    # Step 3: Download outputs
    saved_files = []
    if saved_2d:
        saved_files.append(saved_2d)

    # Debug: save full response to see actual keys
    debug_path = output_dir / f"{name}_response.json"
    debug_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"  📋 Response keys: {list(result.keys())}")

    # Main mesh (GLB) — try multiple known response formats
    mesh = result.get("model_mesh") or result.get("base_model") or result.get("model") or {}
    if isinstance(mesh, str):
        # Sometimes the URL is returned directly
        mesh_url = mesh
    else:
        mesh_url = mesh.get("url") if mesh else None

    # Fallback: scan all top-level keys for a URL ending in .glb/.fbx/.obj
    if not mesh_url:
        for k, v in result.items():
            if isinstance(v, str) and any(v.endswith(ext) for ext in (".glb", ".fbx", ".obj")):
                mesh_url = v
                break
            if isinstance(v, dict) and v.get("url"):
                url = v["url"]
                if any(ext in url for ext in (".glb", ".fbx", ".obj", "model")):
                    mesh_url = url
                    break
    if mesh_url:
        ext = ".glb"
        ct = mesh.get("content_type", "")
        if "fbx" in ct:
            ext = ".fbx"
        elif "obj" in ct:
            ext = ".obj"
        mesh_path = output_dir / f"{name}{ext}"
        if download_file(mesh_url, mesh_path):
            size_mb = mesh_path.stat().st_size / (1024 * 1024)
            print(f"  💾 3D model saved: {mesh_path} ({size_mb:.1f} MB)")
            saved_files.append(str(mesh_path))

    # PBR model (if available)
    pbr = result.get("pbr_model", {})
    pbr_url = pbr.get("url")
    if pbr_url:
        pbr_path = output_dir / f"{name}_pbr.glb"
        if download_file(pbr_url, pbr_path):
            print(f"  💾 PBR model saved: {pbr_path}")
            saved_files.append(str(pbr_path))

    # Rendered preview
    rendered = result.get("rendered_image", {})
    render_url = rendered.get("url")
    if render_url:
        render_path = output_dir / f"{name}_preview.webp"
        if download_file(render_url, render_path):
            print(f"  💾 Preview saved: {render_path}")
            saved_files.append(str(render_path))

    # Save metadata
    meta = {
        "name": name,
        "source": args.url or args.file or args.prompt,
        "source_type": "url" if args.url else ("file" if args.file else "prompt"),
        "image_url": image_url,
        "texture": args.texture,
        "task_id": result.get("task_id"),
        "files": saved_files,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    meta_path = output_dir / f"{name}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    # Summary
    cost = {"no": 0.20, "standard": 0.30, "HD": 0.40}.get(args.texture, 0.30)
    if args.prompt:
        cost += 0.05  # Flux Pro cost estimate
    print(f"\n✅ Done! Estimated cost: ${cost:.2f}")
    print(f"   Files: {output_dir}")

    # Telegram notification — send actual files, not just text
    if args.notify:
        source = args.prompt or args.url or args.file
        try:
            import requests as _req
            token = ENV.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = ENV.get("TELEGRAM_USER_ID", "")
            tg_base = f"https://api.telegram.org/bot{token}"

            # Send preview/2D images as photos
            for fpath in saved_files:
                fp = Path(fpath)
                if fp.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    label = "2D Reference" if "_2d" in fp.name else "3D Preview"
                    with open(fp, "rb") as fh:
                        _req.post(f"{tg_base}/sendPhoto",
                                  data={"chat_id": chat_id, "caption": f"🔮 {label} — {source[:80]}"},
                                  files={"photo": fh}, timeout=30)

            # Send GLB/model files as documents
            for fpath in saved_files:
                fp = Path(fpath)
                if fp.suffix.lower() in (".glb", ".fbx", ".obj"):
                    size_mb = fp.stat().st_size / (1024 * 1024)
                    with open(fp, "rb") as fh:
                        _req.post(f"{tg_base}/sendDocument",
                                  data={"chat_id": chat_id, "caption": f"📦 3D Model ({size_mb:.1f} MB) — Cost: ~${cost:.2f}"},
                                  files={"document": (fp.name, fh, "model/gltf-binary")}, timeout=60)

            print("  📱 Telegram: images + model files sent")
        except Exception as e:
            # Fallback to text-only
            notify_mario(f"🔮 3D Model Ready!\n\nSource: {source[:100]}\nTexture: {args.texture}\nFiles: {len(saved_files)}\nCost: ~${cost:.2f}")
            print(f"  📱 Telegram: text notification sent (file send failed: {e})")


if __name__ == "__main__":
    main()
