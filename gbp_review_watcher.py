#!/usr/bin/env python3
"""
gbp_review_watcher.py — Real-time GBP review monitor & Telegram notifier

Polls all 4 active GBP locations every 60 seconds.
When a new review is detected:
  1. Generates AI draft response (Claude API)
  2. Sends Telegram alert with review + draft + inline buttons
  3. Mario taps [✅ Post Reply] or [✏️ Edit] in Telegram

Usage:
    python gbp_review_watcher.py              # run daemon (Ctrl+C to stop)
    python gbp_review_watcher.py --dry-run    # list all current reviews, no Telegram
    python gbp_review_watcher.py --test       # simulate a new review (Telegram test)
    python gbp_review_watcher.py --once       # one poll cycle then exit

Background:
    start /b python gbp_review_watcher.py > gbp_watcher.log 2>&1
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
EXECUTION_DIR = Path(__file__).parent
ENV_PATH      = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
STATE_FILE    = EXECUTION_DIR / "gbp_review_state.json"
SUPABASE_URL  = "https://svgsbaahxiaeljmfykzp.supabase.co"

# ── Account & location config ─────────────────────────────────────────────
# accountId and locationId are fetched dynamically after auth,
# but we pre-configure business keys and token files here.
# Run --verify-locations once after auth to populate account_name + location_name.

LOCATIONS_CONFIG = {
    "sugar_shack": {
        "account":       "yehuda",
        "token_file":    EXECUTION_DIR / "token_yehuda_gbp.json",
        "business_name": "The Sugar Shack",
        "account_name":  None,   # populated by --verify-locations
        "location_name": None,   # e.g. "accounts/123/locations/456"
        "gbp_business_id": "13038061471302579308",
    },
    "island_candy": {
        "account":       "yehuda",
        "token_file":    EXECUTION_DIR / "token_yehuda_gbp.json",
        "business_name": "Island Candy",
        "account_name":  None,
        "location_name": None,
        "gbp_business_id": "4798477906868509722",
    },
    "custom_designs_tx": {
        "account":       "mario",
        "token_file":    EXECUTION_DIR / "token_mario_gbp.json",
        "business_name": "Custom Designs TX",
        "account_name":  None,
        "location_name": None,
        "gbp_business_id": "13185634142027650449",
    },
    "optimum_clinic": {
        "account":       "mario",
        "token_file":    EXECUTION_DIR / "token_mario_gbp.json",
        "business_name": "Optimum Health & Wellness Clinic",
        "account_name":  None,
        "location_name": None,
        "gbp_business_id": "16753182239006365635",
    },
}

POLL_INTERVAL = 60  # seconds


# ── Env / credentials ─────────────────────────────────────────────────────
def _load_env() -> dict:
    env = {}
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env

_env = _load_env()
TELEGRAM_TOKEN = _env.get("TELEGRAM_BOT_TOKEN") or ""
TELEGRAM_UID   = _env.get("TELEGRAM_USER_ID") or ""
SUPABASE_KEY   = _env.get("SUPABASE_KEY") or ""


# ── State management ──────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"reviews": {}, "locations": {}}

def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def _is_seen(state: dict, review_id: str) -> bool:
    return review_id in state.get("reviews", {})

def _mark_seen(state: dict, review_id: str, data: dict) -> None:
    state.setdefault("reviews", {})[review_id] = data


# ── GBP API helpers ───────────────────────────────────────────────────────
def _get_token(token_file: Path) -> str:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import logging
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

    SCOPES = ["https://www.googleapis.com/auth/business.manage"]
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
    return creds.token


def fetch_reviews(location_name: str, token: str, page_size: int = 20) -> list:
    """Fetch reviews for a location via GBP Reviews API v1."""
    url = (
        f"https://mybusinessreviews.googleapis.com/v1/{location_name}/reviews"
        f"?pageSize={page_size}&orderBy=updateTime%20desc"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data.get("reviews", [])
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"[api] reviews.list error {e.code}: {err[:200]}")
        return []
    except Exception as e:
        print(f"[api] fetch_reviews error: {e}")
        return []


def post_reply(location_name: str, review_id: str, reply_text: str, token: str) -> bool:
    """Post a reply to a GBP review via API."""
    url = f"https://mybusinessreviews.googleapis.com/v1/{location_name}/reviews/{review_id}/reply"
    payload = json.dumps({"comment": reply_text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        return True
    except urllib.error.HTTPError as e:
        print(f"[api] reply error {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"[api] reply error: {e}")
        return False


# ── Supabase logging ──────────────────────────────────────────────────────
def _supabase_upsert(review_id: str, row: dict) -> None:
    if not SUPABASE_KEY:
        return
    url = f"{SUPABASE_URL}/rest/v1/gbp_reviews"
    payload = json.dumps({**row, "id": review_id}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[supabase] upsert warning: {e}")


# ── Telegram helpers ──────────────────────────────────────────────────────
TGBASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def _tg(method: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"{TGBASE}/{method}", data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"[telegram] {method} error: {e}")
        return {"ok": False}

def send_review_alert(review_id: str, business_key: str, business_name: str,
                      stars: int, reviewer: str, review_text: str, draft: str) -> None:
    stars_str = "⭐" * stars + "☆" * (5 - stars)
    date_str  = datetime.now(timezone.utc).strftime("%B %d, %Y")
    short_text = (review_text[:300] + "...") if len(review_text) > 300 else review_text
    short_draft = (draft[:400] + "...") if len(draft) > 400 else draft

    msg = (
        f"{stars_str} NEW REVIEW — {business_name}\n\n"
        f"👤 {reviewer}\n"
        f"📅 {date_str}\n\n"
        f"\"{short_text}\"\n\n"
        f"─────────────────────\n"
        f"💬 Draft response:\n"
        f"{short_draft}"
    )

    # Inline keyboard with review_id encoded in callback_data
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Post This Reply",  "callback_data": f"gbp_post|{review_id}|{business_key}"},
            {"text": "✏️ Edit Reply",        "callback_data": f"gbp_edit|{review_id}|{business_key}"},
            {"text": "❌ Skip",             "callback_data": f"gbp_skip|{review_id}|{business_key}"},
        ]]
    }

    _tg("sendMessage", {
        "chat_id":      TELEGRAM_UID,
        "text":         msg,
        "reply_markup": keyboard,
        "parse_mode":   "",
    })


def send_msg(text: str) -> None:
    _tg("sendMessage", {"chat_id": TELEGRAM_UID, "text": text})


# ── Core pipeline ─────────────────────────────────────────────────────────
def process_new_review(review: dict, business_key: str, location_name: str,
                       state: dict, dry_run: bool = False) -> None:
    from gbp_review_responder import generate_response

    review_id    = review["reviewId"]
    stars_map    = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
    stars        = stars_map.get(review.get("starRating", "FIVE"), 5)
    reviewer     = review.get("reviewer", {}).get("displayName", "Guest")
    review_text  = review.get("comment", "(no text)")
    cfg          = LOCATIONS_CONFIG[business_key]
    business_name = cfg["business_name"]

    print(f"[NEW] {business_name} | {stars}★ | {reviewer}: {review_text[:80]}...")

    # Generate AI draft
    draft = generate_response(business_key, stars, reviewer, review_text)
    print(f"[draft] {draft[:100]}...")

    # Save to state
    entry = {
        "business":      business_key,
        "business_name": business_name,
        "location_name": location_name,
        "stars":         stars,
        "reviewer":      reviewer,
        "text":          review_text,
        "draft":         draft,
        "seen_at":       datetime.now(timezone.utc).isoformat(),
        "replied":       False,
        "skipped":       False,
        "notified":      not dry_run,
    }
    _mark_seen(state, review_id, entry)
    save_state(state)

    # Log to Supabase
    _supabase_upsert(review_id, {
        "business_name":   business_name,
        "reviewer_name":   reviewer,
        "star_rating":     stars,
        "review_text":     review_text,
        "draft_response":  draft,
        "status":          "draft_ready",
        "review_date":     review.get("createTime", datetime.now(timezone.utc).isoformat()),
    })

    if dry_run:
        print(f"[dry-run] Would send Telegram for: {reviewer} ({stars}★)")
        return

    send_review_alert(review_id, business_key, business_name, stars, reviewer, review_text, draft)
    print(f"[telegram] Alert sent for review {review_id[:12]}...")


def poll_once(state: dict, dry_run: bool = False) -> int:
    """Poll all locations. Returns count of new reviews found."""
    new_count = 0
    for biz_key, cfg in LOCATIONS_CONFIG.items():
        location_name = cfg.get("location_name")
        if not location_name:
            print(f"[{biz_key}] WARNING: No location_name -- run: python gbp_auth_setup.py --account {cfg['account']}, then --setup-locations")
            continue

        token_file = cfg["token_file"]
        if not token_file.exists():
            print(f"[{biz_key}] Token missing: {token_file.name} — run gbp_auth_setup.py")
            continue

        try:
            token = _get_token(token_file)
        except Exception as e:
            print(f"[{biz_key}] Token error: {e}")
            continue

        reviews = fetch_reviews(location_name, token)
        if dry_run:
            print(f"[{biz_key}] {cfg['business_name']}: {len(reviews)} review(s) found")
            for r in reviews:
                stars_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
                stars = stars_map.get(r.get("starRating", "FIVE"), 5)
                reviewer = r.get("reviewer", {}).get("displayName", "?")
                text = r.get("comment", "")[:60]
                rid  = r.get("reviewId", "?")[:12]
                seen = "✓" if _is_seen(state, r.get("reviewId","")) else "NEW"
                print(f"  [{seen}] {stars}★ {reviewer}: {text}...")
        else:
            for review in reviews:
                rid = review.get("reviewId", "")
                if rid and not _is_seen(state, rid):
                    process_new_review(review, biz_key, location_name, state, dry_run)
                    new_count += 1

    return new_count


def handle_callback(callback_data: str, state: dict) -> None:
    """Handle Telegram inline button presses (called by telegram_bot.py integration)."""
    parts = callback_data.split("|")
    if len(parts) < 3:
        return
    action, review_id, business_key = parts[0], parts[1], parts[2]

    review_state = state.get("reviews", {}).get(review_id)
    if not review_state:
        send_msg(f"⚠️ Review {review_id[:12]} not found in state.")
        return

    cfg           = LOCATIONS_CONFIG.get(business_key, {})
    location_name = review_state.get("location_name") or cfg.get("location_name")
    token_file    = cfg.get("token_file")
    draft         = review_state.get("draft", "")
    business_name = review_state.get("business_name", business_key)

    if action == "gbp_post":
        if not token_file or not token_file.exists():
            send_msg(f"⚠️ Token missing for {business_key}. Cannot post reply.")
            return
        token = _get_token(token_file)
        ok = post_reply(location_name, review_id, draft, token)
        if ok:
            review_state["replied"]    = True
            review_state["replied_at"] = datetime.now(timezone.utc).isoformat()
            save_state(state)
            _supabase_upsert(review_id, {"status": "replied", "final_response": draft,
                                          "replied_at": review_state["replied_at"]})
            send_msg(f"✅ Reply posted to {business_name}!")
        else:
            send_msg(f"❌ Failed to post reply to {business_name}. Check logs.")

    elif action == "gbp_edit":
        # Bot will prompt for custom text — handled in telegram_bot.py
        send_msg(
            f"✏️ Send me your custom reply for {business_name}.\n\n"
            f"(Review ID: `{review_id[:16]}`)\n\n"
            f"Original draft:\n{draft}"
        )

    elif action == "gbp_skip":
        review_state["skipped"] = True
        save_state(state)
        _supabase_upsert(review_id, {"status": "skipped"})
        send_msg(f"⬜ Review skipped for {business_name}.")


def setup_locations(state: dict) -> None:
    """
    Fetch real account + location names from GBP API and update LOCATIONS_CONFIG.
    Also saves location_name to state for persistence.
    Run once after auth to populate the config.
    """
    import requests

    SCOPES = ["https://www.googleapis.com/auth/business.manage"]
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    for account_name in ["mario", "yehuda"]:
        token_file = EXECUTION_DIR / f"token_{account_name}_gbp.json"
        if not token_file.exists():
            print(f"[{account_name}] Token not found — skipping")
            continue

        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())

        headers = {"Authorization": f"Bearer {creds.token}"}

        # List accounts
        r = requests.get("https://mybusinessaccountmanagement.googleapis.com/v1/accounts", headers=headers)
        if r.status_code != 200:
            print(f"[{account_name}] accounts.list failed: {r.status_code}")
            continue

        for acct in r.json().get("accounts", []):
            acct_resource = acct["name"]  # e.g. "accounts/112345678"

            # List locations
            loc_url = (
                f"https://mybusinessbusinessinformation.googleapis.com/v1/"
                f"{acct_resource}/locations?readMask=name,title"
            )
            lr = requests.get(loc_url, headers=headers)
            if lr.status_code != 200:
                continue

            for loc in lr.json().get("locations", []):
                loc_resource = loc["name"]  # e.g. "accounts/.../locations/..."
                loc_title    = loc.get("title", "").lower()

                # Match to our config by partial name
                for biz_key, cfg in LOCATIONS_CONFIG.items():
                    if cfg["account"] != account_name:
                        continue
                    if cfg.get("location_name"):
                        continue  # already set
                    biz_words = set(cfg["business_name"].lower().split())
                    match_words = set(loc_title.split())
                    if len(biz_words & match_words) >= 1:
                        cfg["account_name"]  = acct_resource
                        cfg["location_name"] = loc_resource
                        print(f"[setup] Matched '{loc_title}' → {biz_key}: {loc_resource}")

    # Persist to state
    state.setdefault("locations", {})
    for biz_key, cfg in LOCATIONS_CONFIG.items():
        if cfg.get("location_name"):
            state["locations"][biz_key] = {
                "account_name":  cfg["account_name"],
                "location_name": cfg["location_name"],
            }
    save_state(state)
    print("\n[setup] Location mapping saved to gbp_review_state.json")


def _load_locations_from_state(state: dict) -> None:
    """Restore location_name / account_name from saved state."""
    for biz_key, loc_data in state.get("locations", {}).items():
        if biz_key in LOCATIONS_CONFIG:
            LOCATIONS_CONFIG[biz_key]["account_name"]  = loc_data.get("account_name")
            LOCATIONS_CONFIG[biz_key]["location_name"] = loc_data.get("location_name")


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="GBP Review Watcher")
    parser.add_argument("--dry-run",         action="store_true", help="List reviews, no Telegram")
    parser.add_argument("--once",            action="store_true", help="One poll cycle then exit")
    parser.add_argument("--test",            action="store_true", help="Send fake Telegram alert")
    parser.add_argument("--setup-locations", action="store_true", help="Discover location IDs from API")
    args = parser.parse_args()

    state = load_state()
    _load_locations_from_state(state)

    if args.setup_locations:
        setup_locations(state)
        return

    if args.test:
        print("[test] Sending fake review alert to Telegram...")
        send_review_alert(
            review_id="test_review_001",
            business_key="sugar_shack",
            business_name="The Sugar Shack",
            stars=5,
            reviewer="Jane Doe",
            review_text="Amazing candy selection! My kids absolutely loved picking their own treats. We'll definitely be back every spring break!",
            draft="Thank you so much, Jane! Hearing that your kids had that magical candy-picking experience means everything to us — that joy is exactly what we're here for. We can't wait to see you back on the island! 🍬 — The Sugar Shack Team",
        )
        print("[test] Telegram alert sent!")
        return

    if args.dry_run:
        print("=== DRY RUN — listing all current reviews ===\n")
        poll_once(state, dry_run=True)
        return

    # Daemon mode
    print(f"[watcher] Starting GBP review watcher (poll every {POLL_INTERVAL}s)...")
    print(f"[watcher] Monitoring {sum(1 for c in LOCATIONS_CONFIG.values() if c.get('location_name'))} location(s)")
    configured = [k for k, c in LOCATIONS_CONFIG.items() if c.get("location_name")]
    unconfigured = [k for k, c in LOCATIONS_CONFIG.items() if not c.get("location_name")]
    if configured:
        print(f"[watcher] Active: {', '.join(configured)}")
    if unconfigured:
        print(f"[watcher] ⚠️  No location_name: {', '.join(unconfigured)} — run --setup-locations")

    if args.once:
        count = poll_once(state)
        print(f"[watcher] Done. {count} new review(s) found.")
        return

    send_msg("🔍 GBP Review Watcher online — monitoring all active locations.")
    while True:
        try:
            count = poll_once(state)
            if count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {count} new review(s) processed")
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            send_msg("🔴 GBP Review Watcher going offline.")
            print("\n[watcher] Stopped.")
            break
        except Exception as e:
            print(f"[watcher] Poll error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
