"""FB Comment Responder — scans all client pages for new comments and optionally
auto-replies using AI-generated responses via the Meta Graph API.

Usage:
  python fb_comment_responder.py              # scan + report only
  python fb_comment_responder.py --approve    # scan + auto-reply
  python fb_comment_responder.py --page sugar_shack  # single page
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
CREDS_PATH = ROOT / "fb_api_credentials.json"
STATE_PATH = ROOT / "fb_responder_state.json"
ENV_PATH = ROOT.parent.parent.parent / "scratch" / "gravity-claw" / ".env"

# ── Env helpers ──────────────────────────────────────────────────────────────

def _load_env() -> dict:
    env = {}
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    except (FileNotFoundError, OSError):
        pass
    return env

_ENV = _load_env()

def _env(key: str, default: str = "") -> str:
    return _ENV.get(key) or os.environ.get(key, default)

# ── Graph API helpers ────────────────────────────────────────────────────────

def _graph_call(page_token: str, endpoint: str, params: dict | None = None) -> dict:
    """Call Facebook Graph API v22.0 and return JSON."""
    url_params = {"access_token": page_token}
    if params:
        url_params.update(params)
    qs = urllib.parse.urlencode(url_params)
    url = f"https://graph.facebook.com/v22.0/{endpoint}?{qs}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"error": f"HTTP {e.code}: {body[:300]}"}

# ── AI reply generation ──────────────────────────────────────────────────────

def _generate_reply(comment_text: str, page_name: str) -> str | None:
    """Generate a friendly, short reply using OpenRouter / Claude."""
    api_key = _env("OPENROUTER_API_KEY")
    if not api_key:
        return None

    prompt = (
        "You are managing the Facebook page for a local business called "
        f"\"{page_name}\". A customer left this comment:\n\n"
        f"\"{comment_text}\"\n\n"
        "Write a short, friendly, professional reply (1-2 sentences max). "
        "Address the person by first name if visible. "
        "Be warm and grateful. Never offer discounts or prices. "
        "Reply only with the message text — no quotes, no signatures."
    )

    body = json.dumps({
        "model": "anthropic/claude-sonnet-4-6",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150,
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8787",
            "X-Title": "FB Comment Responder",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip().strip('"')
    except Exception:
        return None

# ── State management ─────────────────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_scan": None, "replied_to": {}}

def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))

# ── Notification ─────────────────────────────────────────────────────────────

def _notify_telegram(text: str) -> bool:
    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_USER_ID")
    if not token or not chat_id:
        return False
    try:
        data = urllib.parse.urlencode(
            {"chat_id": chat_id, "text": text[:4096], "parse_mode": "HTML"}
        ).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read()).get("ok", False)
    except Exception:
        return False

# ── Main logic ───────────────────────────────────────────────────────────────

def scan_comments(page_key: str, page_info: dict, since: str | None, approve: bool) -> list:
    """Scan one page for new comments. Returns list of (comment, reply) tuples."""
    page_token = page_info.get("page_token", "")
    page_id = page_info.get("page_id", "")
    page_name = page_info.get("page_name", page_key)
    if not page_token or not page_id:
        print(f"  SKIP {page_name}: no token or page_id")
        return []

    # Get recent posts (last 10)
    posts_resp = _graph_call(page_token, f"{page_id}/posts",
                             {"fields": "id,message,created_time", "limit": 10})
    if "error" in posts_resp:
        print(f"  ERROR fetching posts for {page_name}: {posts_resp['error']}")
        return []

    posts = posts_resp.get("data", [])
    results = []

    for post in posts:
        post_id = post.get("id", "")
        post_time = post.get("created_time", "")
        if since and post_time <= since:
            continue

        # Get comments on this post
        comments_resp = _graph_call(page_token, f"{post_id}/comments",
                                    {"fields": "id,message,created_time,from",
                                     "limit": 25, "order": "chronological"})
        if "error" in comments_resp:
            continue

        for comment in comments_resp.get("data", []):
            comment_id = comment.get("id", "")
            comment_text = comment.get("message", "")
            comment_time = comment.get("created_time", "")
            commenter = (comment.get("from") or {}).get("name", "Someone")

            if since and comment_time <= since:
                continue

            print(f"  [{page_name}] {commenter}: {comment_text[:100]}")
            results.append({
                "page": page_name,
                "page_id": page_id,
                "commenter": commenter,
                "comment_text": comment_text,
                "comment_id": comment_id,
                "comment_time": comment_time,
            })

            if approve:
                reply = _generate_reply(comment_text, page_name)
                if reply:
                    print(f"    → REPLY: {reply}")
                    _graph_call(page_token, f"{comment_id}/replies",
                                {"message": reply})
                    results[-1]["reply"] = reply
                    time.sleep(0.5)  # rate limit

    return results


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="FB Comment Responder")
    parser.add_argument("--approve", action="store_true", help="Auto-post AI replies")
    parser.add_argument("--page", help="Single page key to scan")
    parser.add_argument("--report", action="store_true", help="Generate report only")
    args = parser.parse_args()

    # Load creds
    if not CREDS_PATH.exists():
        print("ERROR: fb_api_credentials.json not found")
        sys.exit(1)
    creds = json.loads(CREDS_PATH.read_text())
    pages = creds.get("pages", {})

    # Filter
    if args.page:
        pages = {args.page: pages[args.page]} if args.page in pages else {}

    state = _load_state()
    since = state.get("last_scan")
    now = datetime.now(timezone.utc).isoformat()

    print(f"FB Comment Responder — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'approve & reply' if args.approve else 'scan & report'}")
    print(f"Pages: {len(pages)} | Since: {since or 'first run'}")
    print()

    all_results = []
    for key, info in pages.items():
        results = scan_comments(key, info, since, args.approve)
        all_results.extend(results)

    # Update state
    state["last_scan"] = now
    state.setdefault("replied_to", {})
    for r in all_results:
        if r.get("reply"):
            state["replied_to"][r["comment_id"]] = {
                "time": now, "reply": r["reply"],
                "page": r["page"], "commenter": r["commenter"],
            }
    _save_state(state)

    # Summary
    count = len(all_results)
    print(f"\n--- Done: {count} new comments found ---")

    # Telegram notification if comments found
    if count > 0:
        lines = [f"<b>FB Comment Responder</b> — {count} new comment(s)"]
        for r in all_results[:10]:
            icon = "✅" if r.get("reply") else "📩"
            lines.append(
                f"{icon} <b>{r['page']}</b> — {r['commenter']}: "
                f"{r['comment_text'][:120]}"
            )
            if r.get("reply"):
                lines.append(f"   ↳ <i>{r['reply'][:150]}</i>")
        _notify_telegram("\n".join(lines))

    if not all_results:
        print("No new comments since last scan.")


if __name__ == "__main__":
    main()
