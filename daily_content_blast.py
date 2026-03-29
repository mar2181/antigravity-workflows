#!/usr/bin/env python3
"""
Daily Content Blast — Generate FB posts + images for all 8 clients, send to Telegram.
Bypasses Anthropic API by using pre-written copy passed via JSON.
"""

import json, os, sys, time, urllib.request, urllib.parse
from pathlib import Path

BASE = Path(__file__).parent
ENV_PATH = BASE.parent.parent / "scratch" / "gravity-claw" / ".env"

def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def notify_telegram(text: str, env: dict) -> bool:
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_USER_ID", "")
    if not token or not chat_id:
        print("  ⚠️  Telegram credentials missing")
        return False
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096], "parse_mode": "HTML"}).encode()
    try:
        resp = urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data),
            timeout=15
        )
        return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"  ⚠️  Telegram send failed: {e}")
        return False

def send_telegram_photo(photo_path: str, caption: str, env: dict) -> bool:
    """Send a photo with caption to Telegram."""
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_USER_ID", "")
    if not token or not chat_id:
        return False

    import io
    boundary = "----PythonBoundary"

    body = []
    # chat_id field
    body.append(f"--{boundary}".encode())
    body.append(b'Content-Disposition: form-data; name="chat_id"')
    body.append(b"")
    body.append(chat_id.encode())
    # caption field
    body.append(f"--{boundary}".encode())
    body.append(b'Content-Disposition: form-data; name="caption"')
    body.append(b"")
    body.append(caption[:1024].encode("utf-8"))
    # parse_mode
    body.append(f"--{boundary}".encode())
    body.append(b'Content-Disposition: form-data; name="parse_mode"')
    body.append(b"")
    body.append(b"HTML")
    # photo file
    fname = Path(photo_path).name
    with open(photo_path, "rb") as f:
        photo_data = f.read()
    body.append(f"--{boundary}".encode())
    body.append(f'Content-Disposition: form-data; name="photo"; filename="{fname}"'.encode())
    body.append(b"Content-Type: image/png")
    body.append(b"")
    body.append(photo_data)
    body.append(f"--{boundary}--".encode())

    payload = b"\r\n".join(body)

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"  ⚠️  Telegram photo send failed: {e}")
        return False


def generate_image(prompt: str, out_path: str, size: str = "landscape_16_9") -> bool:
    """Generate one image via fal.ai Flux Pro."""
    env = load_env()
    fal_key = env.get("FAL_KEY", "")
    if not fal_key:
        print("  ⚠️  FAL_KEY not found")
        return False

    os.environ["FAL_KEY"] = fal_key
    try:
        import fal_client
    except ImportError:
        os.system(f'"{sys.executable}" -m pip install fal_client -q')
        import fal_client

    try:
        handler = fal_client.submit(
            "fal-ai/flux-pro/v1.1-ultra",
            arguments={
                "prompt": prompt,
                "image_size": size,
                "num_images": 1,
            },
        )
        result = handler.get()
        img_url = result["images"][0]["url"]
        urllib.request.urlretrieve(img_url, out_path)
        return True
    except Exception as e:
        print(f"  ⚠️  fal.ai error: {e}")
        return False


def main():
    # Fix Windows console encoding
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    content_file = BASE / "daily_content_blast_posts.json"
    if not content_file.exists():
        print("ERROR: daily_content_blast_posts.json not found")
        sys.exit(1)

    posts = json.loads(content_file.read_text(encoding="utf-8"))
    env = load_env()
    img_dir = BASE / "daily_blast_images"
    img_dir.mkdir(exist_ok=True)

    total = len(posts)
    for i, post in enumerate(posts, 1):
        biz = post["business"]
        keyword = post["keyword"]
        copy_text = post["facebook_copy"]
        img_prompt = post["image_prompt"]

        print(f"\n[{i}/{total}] {biz} — \"{keyword}\"")

        # Generate image
        img_path = img_dir / f"{biz}_hero.png"
        print(f"  Generating image...", end=" ", flush=True)
        if generate_image(img_prompt, str(img_path)):
            print("✅")
        else:
            print("❌ (will send text only)")
            img_path = None

        # Send to Telegram
        header = f"<b>📢 {post['business_name']}</b>\n<i>Keyword: {keyword}</i>\n{'─' * 30}\n\n"

        if img_path and img_path.exists():
            ok = send_telegram_photo(str(img_path), header + copy_text, env)
        else:
            ok = notify_telegram(header + copy_text, env)

        status = "✅ Sent" if ok else "❌ Failed"
        print(f"  Telegram: {status}")

        # Small delay between sends
        if i < total:
            time.sleep(2)

    # Final summary
    print(f"\n{'='*50}")
    print(f"Done! {total} posts sent to Telegram for review.")
    notify_telegram(
        f"✅ <b>Daily Content Blast Complete</b>\n\n"
        f"{total} posts generated for all clients.\n"
        f"Review each post above. Reply 'APPROVE ALL' or specify which to post.",
        env
    )


if __name__ == "__main__":
    main()
