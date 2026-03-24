#!/usr/bin/env python3
"""
bulk_pool_uploader.py — Upload existing business images into Mission Control Image Pool

Usage:
  python bulk_pool_uploader.py                        # upload all clients
  python bulk_pool_uploader.py --client sugar_shack   # one client only
  python bulk_pool_uploader.py --dry-run              # preview only, no uploads
  python bulk_pool_uploader.py --vision-all           # force vision AI on ALL images
"""

import sys
import re
import os
import json
import base64
import argparse
import urllib.parse
import urllib.request
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

CLIENT_IDS = {
    "sugar_shack":       "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
    "island_arcade":     "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
    "island_candy":      "d865037b-2552-4024-9db3-10e61e1419b4",
    "spi_fun_rentals":   "f8693268-6abf-4401-8b2e-3795e326252b",
    "custom_designs_tx": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
    "juan":              "a1000001-0000-0000-0000-000000000001",
    "optimum_clinic":    "a1000002-0000-0000-0000-000000000002",
    "optimum_foundation":"a1000003-0000-0000-0000-000000000003",
}

CLIENT_LABELS = {
    "sugar_shack":       "Sugar Shack",
    "island_arcade":     "Island Arcade",
    "island_candy":      "Island Candy",
    "spi_fun_rentals":   "SPI Fun Rentals",
    "custom_designs_tx": "Custom Designs TX",
    "juan":              "Juan Elizondo",
    "optimum_clinic":    "Optimum Clinic",
    "optimum_foundation":"Optimum Foundation",
}

SOURCES = [
    ("sugar_shack",       "C:/Users/mario/sugar_shack_ad_images"),
    ("island_arcade",     "C:/Users/mario/island_arcade_ad_images"),
    ("island_candy",      "C:/Users/mario/island_candy_ad_images"),
    ("spi_fun_rentals",   "C:/Users/mario/spi_fun_rentals_ad_images"),
    ("spi_fun_rentals",   "C:/Users/mario/.gemini/antigravity/tools/execution/spi_fun_rentals/assets/images"),
    ("custom_designs_tx", "C:/Users/mario/custom_designs_ad_images"),
    ("juan",              "C:/Users/mario/juan_remax_ad_images"),
    ("optimum_clinic",    "C:/Users/mario/optimum_clinic_ad_images"),
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Patterns that mean the filename is NOT descriptive enough
NON_DESCRIPTIVE = re.compile(
    r"^(IMG|DSC|DSCN|P\d|image\d|photo\d|screenshot|bigstock|clip_|frame_|source_frame)",
    re.IGNORECASE,
)

API_URL = "http://localhost:3001"
ENV_PATH = Path("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env")

# ── Load env ──────────────────────────────────────────────────────────────────

def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

ENV = load_env()
OPENAI_KEY = ENV.get("OPENAI_API_KEY", "")
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = ENV.get("TELEGRAM_USER_ID", "")

# ── Helpers ───────────────────────────────────────────────────────────────────

def notify(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT, "text": text[:4096]}).encode()
        req = urllib.request.Request(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
            data=data,
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def clean_filename_description(filename, client_key):
    """Turn 'ad_3_spring_break_families.png' into 'Sugar Shack - Spring Break Families'"""
    name = Path(filename).stem
    name = re.sub(r"^ad_\d+_?", "", name)
    name = re.sub(r"_(debug|variant|v\d+|copy|final|test)$", "", name, flags=re.IGNORECASE)
    name = name.replace("_", " ").replace("-", " ")
    name = name.strip().title()
    if not name:
        name = "Photo"
    label = CLIENT_LABELS.get(client_key, client_key)
    return label + " - " + name


def vision_describe(image_path, client_key):
    """Use GPT-4o-mini vision to describe a non-descriptive image."""
    if not OPENAI_KEY:
        return clean_filename_description(image_path.name, client_key)

    try:
        img_bytes = image_path.read_bytes()
        ext = image_path.suffix.lower().lstrip(".")
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        mime = mime_map.get(ext, "image/jpeg")
        b64 = base64.b64encode(img_bytes).decode()

        label = CLIENT_LABELS.get(client_key, client_key)
        prompt_text = (
            "This is a marketing asset for " + label + ". "
            "Describe what is shown in 8 words or less. "
            "Be specific and factual. No feelings or adjectives. "
            "Examples: Golf cart on paved coastal road, Nurse holding clipboard, Candy bins with colorful sweets"
        )

        payload = json.dumps({
            "model": "gpt-4o-mini",
            "max_tokens": 60,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + b64, "detail": "low"}},
                    ],
                }
            ],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": "Bearer " + OPENAI_KEY,
                "Content-Type": "application/json",
            },
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        raw = data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        return label + " - " + raw
    except Exception as e:
        print("  [vision error] " + str(e) + " - using filename fallback")
        return clean_filename_description(image_path.name, client_key)


def get_existing_descriptions(client_id):
    """Fetch existing asset descriptions to deduplicate."""
    try:
        url = API_URL + "/api/assets?clientId=" + client_id + "&type=photo&limit=200"
        resp = urllib.request.urlopen(url, timeout=15)
        data = json.loads(resp.read())
        return {a.get("description", "").lower() for a in data.get("assets", [])}
    except Exception:
        return set()


def upload_image(image_path, client_id, description):
    """POST image to /api/assets via multipart/form-data."""
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    img_bytes = image_path.read_bytes()
    ext_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime = ext_map.get(image_path.suffix.lower(), "application/octet-stream")

    def field(name, value):
        return (
            "--" + boundary + "\r\n"
            "Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n"
            + value + "\r\n"
        ).encode("utf-8")

    body = b""
    body += field("clientId", client_id)
    body += field("type", "photo")
    body += field("source", "uploaded")
    body += field("description", description)
    body += (
        "--" + boundary + "\r\n"
        "Content-Disposition: form-data; name=\"file\"; filename=\"" + image_path.name + "\"\r\n"
        "Content-Type: " + mime + "\r\n\r\n"
    ).encode("utf-8")
    body += img_bytes
    body += ("\r\n--" + boundary + "--\r\n").encode("utf-8")

    req = urllib.request.Request(
        API_URL + "/api/assets",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    return "asset" in result or "id" in result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bulk upload images to Mission Control Image Pool")
    parser.add_argument("--client", help="Upload one client only (e.g. sugar_shack)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no uploads")
    parser.add_argument("--vision-all", action="store_true", help="Force vision AI on all images")
    args = parser.parse_args()

    sources = SOURCES
    if args.client:
        if args.client not in CLIENT_IDS:
            print("Unknown client '" + args.client + "'. Valid: " + ", ".join(CLIENT_IDS))
            sys.exit(1)
        sources = [(k, d) for k, d in SOURCES if k == args.client]

    total_ok = 0
    total_skip = 0
    total_err = 0
    total_vision = 0

    mode = "DRY RUN - " if args.dry_run else ""
    print("\n" + mode + "Bulk Image Pool Uploader")
    print("=" * 60)

    for client_key, dir_path in sources:
        directory = Path(dir_path)
        if not directory.exists():
            print("\n[SKIP] " + dir_path + " - directory not found")
            continue

        images = sorted([f for f in directory.iterdir() if f.suffix.lower() in IMAGE_EXTS])
        if not images:
            print("\n[SKIP] " + dir_path + " - no images found")
            continue

        client_id = CLIENT_IDS[client_key]
        label = CLIENT_LABELS[client_key]

        print("\n" + label + " (" + str(len(images)) + " images)")
        print("  Dir: " + str(dir_path))

        existing = get_existing_descriptions(client_id) if not args.dry_run else set()

        for img in images:
            needs_vision = args.vision_all or bool(NON_DESCRIPTIVE.match(img.name))

            if needs_vision:
                if not args.dry_run:
                    desc = vision_describe(img, client_key)
                    total_vision += 1
                else:
                    desc = "[VISION WOULD RUN] " + img.name
            else:
                desc = clean_filename_description(img.name, client_key)

            if desc.lower() in existing:
                print("  SKIP  " + img.name + " (already in pool)")
                total_skip += 1
                continue

            if args.dry_run:
                flag = "[V] " if needs_vision else "    "
                print("  " + flag + img.name)
                print("       -> " + desc)
                total_ok += 1
                continue

            try:
                ok = upload_image(img, client_id, desc)
                if ok:
                    flag = "[V] " if needs_vision else "    "
                    print("  OK " + flag + img.name + " -> " + desc)
                    total_ok += 1
                    existing.add(desc.lower())
                else:
                    print("  ERR  " + img.name + " - unexpected response")
                    total_err += 1
            except Exception as e:
                print("  ERR  " + img.name + " - " + str(e))
                total_err += 1

    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN complete: " + str(total_ok) + " would upload, " + str(total_skip) + " would skip")
    else:
        print("Done: " + str(total_ok) + " uploaded, " + str(total_skip) + " skipped, " + str(total_err) + " errors")
        if total_vision > 0:
            print("      " + str(total_vision) + " images described via GPT-4o-mini vision")
        notify(
            "Image Pool Upload complete\n"
            "Uploaded: " + str(total_ok) + "\n"
            "Skipped: " + str(total_skip) + "\n"
            "Errors: " + str(total_err) + "\n"
            "Vision-described: " + str(total_vision)
        )

if __name__ == "__main__":
    main()
