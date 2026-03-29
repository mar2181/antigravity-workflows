#!/usr/bin/env python3
"""Generate images and send Optimum Clinic occupational health ads to Telegram."""

import json, os, sys, time, urllib.request, urllib.parse
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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

def send_telegram_photo(photo_path, caption, env):
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_USER_ID", "")
    if not token or not chat_id:
        return False
    boundary = "----PythonBoundary"
    body = []
    body.append(f"--{boundary}".encode())
    body.append(b'Content-Disposition: form-data; name="chat_id"')
    body.append(b""); body.append(chat_id.encode())
    body.append(f"--{boundary}".encode())
    body.append(b'Content-Disposition: form-data; name="caption"')
    body.append(b""); body.append(caption[:1024].encode("utf-8"))
    body.append(f"--{boundary}".encode())
    body.append(b'Content-Disposition: form-data; name="parse_mode"')
    body.append(b""); body.append(b"HTML")
    fname = Path(photo_path).name
    with open(photo_path, "rb") as f:
        photo_data = f.read()
    body.append(f"--{boundary}".encode())
    body.append(f'Content-Disposition: form-data; name="photo"; filename="{fname}"'.encode())
    body.append(b"Content-Type: image/png"); body.append(b""); body.append(photo_data)
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
        print(f"  Telegram error: {e}")
        return False

def notify_telegram(text, env):
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_USER_ID", "")
    if not token or not chat_id: return False
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096], "parse_mode": "HTML"}).encode()
    try:
        resp = urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data), timeout=15)
        return json.loads(resp.read()).get("ok", False)
    except: return False

def generate_image(prompt, out_path, size="landscape_16_9"):
    env = load_env()
    fal_key = env.get("FAL_KEY", "")
    if not fal_key: return False
    os.environ["FAL_KEY"] = fal_key
    try:
        import fal_client
    except ImportError:
        os.system(f'"{sys.executable}" -m pip install fal_client -q')
        import fal_client
    try:
        handler = fal_client.submit("fal-ai/flux-pro/v1.1-ultra",
            arguments={"prompt": prompt, "image_size": size, "num_images": 1})
        result = handler.get()
        img_url = result["images"][0]["url"]
        urllib.request.urlretrieve(img_url, out_path)
        return True
    except Exception as e:
        print(f"  fal.ai error: {e}")
        return False

def main():
    ads_file = BASE / "optimum_clinic_occupational_ads.json"
    ads = json.loads(ads_file.read_text(encoding="utf-8"))
    env = load_env()
    img_dir = BASE / "optimum_clinic_occupational_images"
    img_dir.mkdir(exist_ok=True)

    # Send header
    notify_telegram(
        "<b>OPTIMUM CLINIC — 10 OCCUPATIONAL HEALTH ADS</b>\n"
        "<i>DOT Physicals | Refinery Testing | Employment Physicals</i>\n"
        "<i>Key angle: ONLY clinic open after 5 PM</i>\n\n"
        "Reviewing 10 ad variations below...", env)
    time.sleep(1)

    for ad in ads:
        num = ad["ad_number"]
        angle = ad["angle"]
        copy = ad["facebook_copy"]
        prompt = ad["image_prompt"]

        print(f"\n[Ad #{num}/10] {angle}")

        # Generate image
        img_path = img_dir / f"ad_{num}.png"
        print(f"  Generating image...", end=" ", flush=True)
        if generate_image(prompt, str(img_path)):
            print("OK")
        else:
            print("FAILED")
            img_path = None

        # Send to Telegram
        header = f"<b>Ad #{num}/10 — {angle}</b>\n{'─'*30}\n\n"
        if img_path and img_path.exists():
            ok = send_telegram_photo(str(img_path), header + copy[:900], env)
        else:
            ok = notify_telegram(header + copy, env)

        print(f"  Telegram: {'OK' if ok else 'FAILED'}")
        time.sleep(2)

    # Send completion
    notify_telegram(
        "<b>All 10 Optimum Clinic occupational health ads sent.</b>\n\n"
        "Reply which ads to post, or 'APPROVE ALL' to go live.\n\n"
        "Ads 1-8: English | Ad 9: Spanish | Ad 10: General employment", env)
    print(f"\nDone! 10 ads sent to Telegram.")

if __name__ == "__main__":
    main()
