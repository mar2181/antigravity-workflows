#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fb_graph_poster.py — Post to Facebook Pages via Graph API v25.0
Replaces Playwright for pages that have API tokens (Juan, Optimum Clinic).
Usage:
    python fb_graph_poster.py --page juan --message "Your post text" --image path/to/image.png
    python fb_graph_poster.py --page optimum_clinic --message "Your post text"
    python fb_graph_poster.py --page juan --message "text" --image img.png --dry-run
"""

import argparse
import json
import sys
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
CREDS_FILE = SCRIPT_DIR / "fb_api_credentials.json"
API_BASE = "https://graph.facebook.com/v25.0"


def log(msg):
    print(f"[fb_graph] {msg}", flush=True)


def load_page_config(page_key: str) -> dict:
    with open(CREDS_FILE, encoding='utf-8') as f:
        creds = json.load(f)
    pages = creds.get("pages", {})
    if page_key not in pages:
        raise ValueError(f"Page '{page_key}' not found in fb_api_credentials.json")
    cfg = pages[page_key]
    if cfg.get("posting_method") != "graph_api":
        raise ValueError(f"Page '{page_key}' uses method '{cfg.get('posting_method')}', not graph_api")
    if not cfg.get("page_token"):
        raise ValueError(f"No page_token for '{page_key}'")
    return cfg


def post_photo(page_id: str, token: str, message: str, image_path: str) -> dict:
    """Upload a photo with caption to the page feed."""
    url = f"{API_BASE}/{page_id}/photos"
    log(f"Uploading photo to /{page_id}/photos ...")
    with open(image_path, "rb") as img:
        resp = requests.post(
            url,
            data={
                "message": message,
                "access_token": token,
            },
            files={"source": (Path(image_path).name, img, "image/png")},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()


def post_text(page_id: str, token: str, message: str) -> dict:
    """Post a text-only update to the page feed."""
    url = f"{API_BASE}/{page_id}/feed"
    log(f"Posting text to /{page_id}/feed ...")
    resp = requests.post(
        url,
        data={
            "message": message,
            "access_token": token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def verify_token(page_id: str, token: str) -> bool:
    """Check token is valid by attempting a harmless feed query."""
    url = f"{API_BASE}/{page_id}/feed"
    resp = requests.get(url, params={"access_token": token, "limit": "1", "fields": "id"}, timeout=15)
    if resp.status_code == 200:
        log(f"Token valid for page_id {page_id}")
        return True
    err = resp.json().get("error", {})
    # Code 200/190 = token expired/invalid. Code 100 with pages_manage_posts present = token OK for posting
    if err.get("code") == 190:
        log(f"Token expired: {err.get('message')}")
        return False
    # Any other error (e.g. missing read permission) — token may still post; warn and continue
    log(f"⚠️  Token read-check returned {resp.status_code} (code {err.get('code')}): {err.get('message','')[:120]}")
    log("Attempting post anyway — token may have write-only scope.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Post to Facebook via Graph API")
    parser.add_argument("--page", required=True, help="Page key: juan | optimum_clinic")
    parser.add_argument("--message", required=True, help="Post text")
    parser.add_argument("--image", default=None, help="Path to image file (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, don't post")
    args = parser.parse_args()

    cfg = load_page_config(args.page)
    page_id = cfg["page_id"]
    token = cfg["page_token"]
    page_name = cfg["page_name"]

    log(f"Target: {page_name} (id: {page_id})")

    # Verify token
    if not verify_token(page_id, token):
        log("❌ Token invalid or expired. Get a new one from Graph Explorer.")
        sys.exit(1)

    if args.dry_run:
        log("✅ Dry run complete — token valid, not posting.")
        return

    # Post
    if args.image:
        image_path = args.image
        if not Path(image_path).exists():
            log(f"❌ Image not found: {image_path}")
            sys.exit(1)
        result = post_photo(page_id, token, args.message, image_path)
    else:
        result = post_text(page_id, token, args.message)

    log(f"✅ Posted! Response: {result}")
    if "id" in result:
        post_id = result["id"]
        log(f"Post ID: {post_id}")
        log(f"View at: https://www.facebook.com/{post_id.split('_')[0]}/posts/{post_id.split('_')[-1]}")


if __name__ == "__main__":
    main()
