#!/usr/bin/env python3
"""
spi_3d_video_ad.py — Generate a cinematic golf cart video ad for SPI Fun Rentals

Pipeline:
1. Upload real golf cart photo to fal.ai storage
2. Animate via Kling Video v2.1 Pro (image-to-video, 5 seconds)
3. Download video + royalty-free music
4. Mix with ffmpeg
5. Output final video ready for Facebook + Mission Control
"""

import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).resolve().parent
ENV_FILE = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
OUTPUT_DIR = EXECUTION_DIR / "spi_fun_rentals" / "video_ads"

# Source image — real 8-seater blue golf cart on SPI pavement
SOURCE_IMAGE = EXECUTION_DIR / "spi_fun_rentals" / "assets" / "images" / "golf_cart_8seater_resized.jpg"

# fal.ai endpoints
KLING_I2V_ENDPOINT = "fal-ai/kling-video/v2.1/pro/image-to-video"
FAL_QUEUE_BASE = "https://queue.fal.run"
FAL_UPLOAD_URL = "https://fal.ai/api/storage/upload"

# Royalty-free music (Energetic Pop — fun, catchy, social media vibe)
MUSIC_URL = "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946b17b244.mp3"
MUSIC_NAME = "Energetic Pop"

# ffmpeg path
FFMPEG = "C:/Users/mario/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.0.1-full_build/bin/ffmpeg.exe"

# Animation prompt
VIDEO_PROMPT = (
    "Slow cinematic camera orbit around a blue 8-seater golf cart parked on a clean paved road "
    "on South Padre Island. Palm trees sway gently in the warm breeze. Golden hour sunlight. "
    "The camera smoothly glides from a low front-quarter angle to a side profile view, "
    "showcasing the spacious seating and chrome wheels. Tropical vacation atmosphere. "
    "Professional commercial footage, 4K quality, no text overlays."
)


def load_env():
    env = {}
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


ENV = load_env()
FAL_KEY = os.environ.get("FAL_KEY") or ENV.get("FAL_KEY", "")

if not FAL_KEY:
    print("ERROR: FAL_KEY not found")
    sys.exit(1)


def fal_headers():
    return {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}


def notify_mario(text):
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


def send_telegram_video(video_path, caption=""):
    """Send video file to Mario via Telegram."""
    import requests
    token = ENV.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = ENV.get("TELEGRAM_USER_ID", "")
    if not token or not chat_id:
        return False
    try:
        with open(video_path, "rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendVideo",
                data={"chat_id": chat_id, "caption": caption[:1024]},
                files={"video": f},
                timeout=120,
            )
        return resp.json().get("ok", False)
    except Exception as e:
        print(f"  Telegram video send failed: {e}")
        return False


# ─── STEP 1: Upload image to fal.ai ─────────────────────────────────────────

def upload_image():
    import requests

    print(f"\n[1/4] Uploading golf cart photo to fal.ai...")
    print(f"  Source: {SOURCE_IMAGE.name} ({SOURCE_IMAGE.stat().st_size / (1024*1024):.1f} MB)")

    content_type = "image/jpeg" if SOURCE_IMAGE.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    with open(SOURCE_IMAGE, "rb") as f:
        resp = requests.put(
            FAL_UPLOAD_URL,
            headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": content_type},
            data=f.read(),
            timeout=60,
        )

    if resp.status_code == 200:
        data = resp.json()
        url = data.get("url") or data.get("file_url")
        print(f"  Uploaded: {url[:80]}...")
        return url
    else:
        print(f"  Upload failed: {resp.status_code} {resp.text[:200]}")
        return None


# ─── STEP 2: Animate with Kling image-to-video ──────────────────────────────

def submit_video_job(image_url):
    import requests

    print(f"\n[2/4] Submitting image-to-video job (Kling v2.1 Pro)...")
    print(f"  Prompt: {VIDEO_PROMPT[:80]}...")

    payload = {
        "image_url": image_url,
        "prompt": VIDEO_PROMPT,
        "duration": "5",
    }

    resp = requests.post(
        f"{FAL_QUEUE_BASE}/{KLING_I2V_ENDPOINT}",
        headers=fal_headers(),
        json=payload,
        timeout=30,
    )

    if resp.status_code == 200:
        data = resp.json()
        request_id = data.get("request_id")
        print(f"  Job submitted: {request_id}")
        return request_id
    else:
        print(f"  Submit failed: {resp.status_code} {resp.text[:300]}")
        return None


def poll_video_job(request_id):
    import requests

    print(f"  Polling for completion (this takes 2-4 minutes)...")
    max_polls = 80  # 80 * 5s = ~6.5 minutes max
    for i in range(max_polls):
        time.sleep(5)
        try:
            resp = requests.get(
                f"{FAL_QUEUE_BASE}/{KLING_I2V_ENDPOINT}/requests/{request_id}/status",
                headers=fal_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                status_data = resp.json()
                status = status_data.get("status", "UNKNOWN")
                if i % 6 == 0:  # Print every 30 seconds
                    print(f"  [{i*5}s] Status: {status}")

                if status == "COMPLETED":
                    # Fetch the result
                    result_resp = requests.get(
                        f"{FAL_QUEUE_BASE}/{KLING_I2V_ENDPOINT}/requests/{request_id}",
                        headers=fal_headers(),
                        timeout=15,
                    )
                    if result_resp.status_code == 200:
                        result = result_resp.json()
                        video_url = (
                            result.get("video", {}).get("url")
                            or result.get("data", {}).get("video", {}).get("url")
                            or result.get("output", {}).get("video", {}).get("url")
                        )
                        # Fallback: scan for any URL ending in .mp4
                        if not video_url:
                            for k, v in result.items():
                                if isinstance(v, dict) and v.get("url", "").endswith(".mp4"):
                                    video_url = v["url"]
                                    break
                                if isinstance(v, str) and v.endswith(".mp4"):
                                    video_url = v
                                    break
                        # Save full response for debugging
                        debug_path = OUTPUT_DIR / "kling_response.json"
                        debug_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

                        if video_url:
                            print(f"  Video ready: {video_url[:80]}...")
                            return video_url
                        else:
                            print(f"  Completed but no video URL found. Keys: {list(result.keys())}")
                            return None

                elif status == "FAILED":
                    error = status_data.get("error", "Unknown error")
                    print(f"  Video generation FAILED: {error}")
                    return None
        except Exception as e:
            if i % 6 == 0:
                print(f"  [{i*5}s] Poll error: {e}")

    print(f"  Timed out after {max_polls * 5}s")
    return None


# ─── STEP 3: Download video + music, mix with ffmpeg ────────────────────────

def download_file(url, filepath):
    import requests
    resp = requests.get(url, timeout=120, stream=True)
    if resp.status_code == 200:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    print(f"  Download failed: {resp.status_code}")
    return False


def mix_audio(video_path, music_path, output_path):
    print(f"\n[3/4] Mixing video + music ({MUSIC_NAME})...")

    # Replace audio with music track (video has no audio from Kling)
    cmd = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-i", str(music_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-shortest",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  Final video: {output_path.name} ({size_mb:.1f} MB)")
            return True
        else:
            print(f"  ffmpeg error: {result.stderr[:300]}")
            return False
    except Exception as e:
        print(f"  ffmpeg exception: {e}")
        return False


# ─── STEP 4: Generate preview HTML ──────────────────────────────────────────

def create_preview_html(video_path, output_dir):
    html_path = output_dir / "preview_spi_video_ad.html"
    rel_video = video_path.name

    ad_copy = (
        "Cruise South Padre Island in style! Our 8-seater golf carts "
        "are perfect for the whole crew. Explore the island at your own pace "
        "-- beaches, restaurants, shops, all just a ride away.\n\n"
        "Book yours today at SPI Fun Rentals!\n\n"
        "#SPIFunRentals #SouthPadreIsland #GolfCartRentals"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SPI Fun Rentals — Video Ad Preview</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #1a1a2e; color: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }}
  .card {{
    max-width: 520px; margin: 30px auto; background: #fff; border-radius: 12px;
    overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.3); color: #1c1e21;
  }}
  .header {{ display: flex; align-items: center; padding: 12px 16px; gap: 10px; }}
  .avatar {{
    width: 40px; height: 40px; border-radius: 50%; background: #0066cc;
    display: flex; align-items: center; justify-content: center;
    font-weight: bold; color: #fff; font-size: 14px;
  }}
  .header-text {{ font-weight: 600; font-size: 14px; }}
  .header-sub {{ color: #65676b; font-size: 12px; }}
  .post-text {{ padding: 0 16px 12px; font-size: 14px; line-height: 1.5; white-space: pre-line; }}
  video {{ width: 100%; display: block; }}
  .actions {{ display: flex; justify-content: space-around; padding: 8px 16px; border-top: 1px solid #e4e6eb; }}
  .action-btn {{ color: #65676b; font-size: 14px; font-weight: 600; padding: 8px 12px; cursor: pointer; }}
  .badge {{ text-align: center; padding: 16px; color: #8892b0; font-size: 0.85rem; }}
  .badge span {{ background: #e94560; color: #fff; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; }}
  h2 {{ text-align: center; margin: 20px 0 0; color: #e94560; font-size: 1.2rem; }}
  .approve {{ text-align: center; margin: 20px; }}
  .approve a {{
    display: inline-block; padding: 12px 32px; background: #0066cc; color: #fff;
    border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;
  }}
</style>
</head>
<body>
<h2>SPI Fun Rentals — Video Ad Preview</h2>
<div class="badge"><span>DRAFT — Awaiting Approval</span></div>

<div class="card">
  <div class="header">
    <div class="avatar">SPI</div>
    <div>
      <div class="header-text">SPI Fun Rentals</div>
      <div class="header-sub">Sponsored</div>
    </div>
  </div>
  <div class="post-text">{ad_copy}</div>
  <video controls autoplay muted loop>
    <source src="{rel_video}" type="video/mp4">
  </video>
  <div class="actions">
    <div class="action-btn">Like</div>
    <div class="action-btn">Comment</div>
    <div class="action-btn">Share</div>
  </div>
</div>

<div class="badge" style="margin-top: 20px; color: #ccc; font-size: 0.8rem;">
  Video: {rel_video} | Music: {MUSIC_NAME} (royalty-free)
</div>
</body>
</html>"""

    html_path.write_text(html, encoding="utf-8")
    print(f"  Preview HTML: {html_path}")
    return html_path, ad_copy


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("SPI Fun Rentals — 3D Golf Cart Video Ad Generator")
    print("=" * 60)

    # Step 1: Upload image
    image_url = upload_image()
    if not image_url:
        print("\nFAILED: Could not upload image")
        sys.exit(1)

    # Step 2: Generate video
    request_id = submit_video_job(image_url)
    if not request_id:
        print("\nFAILED: Could not submit video job")
        sys.exit(1)

    video_url = poll_video_job(request_id)
    if not video_url:
        print("\nFAILED: Video generation did not complete")
        sys.exit(1)

    # Download video
    raw_video = OUTPUT_DIR / f"spi_golf_cart_raw_{ts}.mp4"
    print(f"\n  Downloading raw video...")
    if not download_file(video_url, raw_video):
        print("\nFAILED: Could not download video")
        sys.exit(1)
    print(f"  Raw video: {raw_video.name} ({raw_video.stat().st_size / (1024*1024):.1f} MB)")

    # Download music
    music_path = OUTPUT_DIR / "energetic_pop.mp3"
    if not music_path.exists():
        print(f"  Downloading music ({MUSIC_NAME})...")
        if not download_file(MUSIC_URL, music_path):
            print("  WARNING: Music download failed, using raw video")
            final_video = raw_video
        else:
            final_video = None
    else:
        print(f"  Music already cached: {music_path.name}")
        final_video = None

    # Step 3: Mix audio
    if final_video is None:
        final_video = OUTPUT_DIR / f"spi_golf_cart_final_{ts}.mp4"
        if not mix_audio(raw_video, music_path, final_video):
            print("  WARNING: Audio mix failed, using raw video")
            final_video = raw_video

    # Step 4: Create preview HTML
    html_path, ad_copy = create_preview_html(final_video, OUTPUT_DIR)

    # Save metadata
    meta = {
        "client": "spi_fun_rentals",
        "type": "video_ad",
        "source_image": str(SOURCE_IMAGE),
        "image_url": image_url,
        "video_url": video_url,
        "raw_video": str(raw_video),
        "final_video": str(final_video),
        "music": MUSIC_NAME,
        "prompt": VIDEO_PROMPT,
        "ad_copy": ad_copy,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cost_estimate": "$0.50 (Kling v2.1 Pro)",
    }
    meta_path = OUTPUT_DIR / f"spi_golf_cart_{ts}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Send to Telegram
    print(f"\n[4/4] Sending to Telegram...")
    notify_mario(
        f"Video Ad Ready! SPI Fun Rentals\n\n"
        f"8-Seater Golf Cart — Cinematic Video\n"
        f"Duration: 5 seconds + {MUSIC_NAME} music\n"
        f"Cost: ~$0.50\n\n"
        f"Preview the video and approve for posting!"
    )
    send_telegram_video(
        final_video,
        caption="SPI Fun Rentals — Golf Cart Video Ad (DRAFT)\nApprove to post to Facebook"
    )

    print(f"\n{'=' * 60}")
    print(f"DONE!")
    print(f"  Final video: {final_video}")
    print(f"  Preview:     {html_path}")
    print(f"  Cost:        ~$0.50")
    print(f"{'=' * 60}")

    return str(final_video), str(html_path), ad_copy, video_url


if __name__ == "__main__":
    main()
