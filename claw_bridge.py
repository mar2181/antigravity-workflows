#!/usr/bin/env python3
"""
claw_bridge.py — Bridge between Genspark CLAW cloud and local machine via Supabase.

CLAW pushes pending items (review responses, ad copy, blog drafts, images) to the
`claw_pending_items` Supabase table. This script polls that table and lets Mario
review, approve, or reject items from the command line or morning brief.

Usage:
  python claw_bridge.py                     # show all pending items
  python claw_bridge.py --count             # just show count (for morning brief)
  python claw_bridge.py --approve 5         # approve item #5
  python claw_bridge.py --reject 5          # reject item #5
  python claw_bridge.py --approve-all       # approve all pending
  python claw_bridge.py --client sugar_shack  # filter by client
  python claw_bridge.py --telegram          # send pending count to Telegram
  python claw_bridge.py --push              # push test items (for testing)
  python claw_bridge.py --export            # export approved items to local files

Supabase table: claw_pending_items
Credentials: reads from gravity-claw/.env (SUPABASE_URL, SUPABASE_KEY)
"""

import sys
import json
import argparse
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXECUTION_DIR = Path(__file__).parent
ENV_PATH = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
EXPORT_DIR = EXECUTION_DIR / "claw_exports"

BUSINESS_NAMES = {
    "sugar_shack": "The Sugar Shack",
    "island_arcade": "Island Arcade",
    "island_candy": "Island Candy",
    "juan": "Juan Elizondo RE/MAX",
    "spi_fun_rentals": "SPI Fun Rentals",
    "custom_designs_tx": "Custom Designs TX",
    "optimum_clinic": "Optimum Clinic",
    "optimum_foundation": "Optimum Foundation",
}


# ─── Config ─────────────────────────────────────────────────────────────────

def _load_env() -> dict:
    """Load SUPABASE_URL and SUPABASE_KEY from gravity-claw .env."""
    env = {}
    if not ENV_PATH.exists():
        print(f"  [ERROR] .env not found at {ENV_PATH}")
        sys.exit(1)
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _supabase_request(method: str, endpoint: str, body: dict = None,
                      url: str = None, key: str = None) -> dict:
    """Make a request to the Supabase REST API."""
    if not url or not key:
        env = _load_env()
        url = url or env.get("SUPABASE_URL", "")
        key = key or env.get("SUPABASE_KEY", "")

    api_url = f"{url}/rest/v1/{endpoint}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(api_url, data=data, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"  [Supabase error {e.code}]: {error_body}")
        return []
    except Exception as e:
        print(f"  [Request error]: {e}")
        return []


def _notify_mario(text: str) -> bool:
    try:
        from screenpipe_verifier import notify_mario
        return notify_mario(text)
    except ImportError:
        return False


# ─── Core Operations ────────────────────────────────────────────────────────

def get_pending(client_filter: str = None) -> list:
    """Fetch all pending items from Supabase."""
    endpoint = "claw_pending_items?status=eq.pending&order=created_at.asc"
    if client_filter:
        endpoint += f"&client_key=eq.{client_filter}"
    return _supabase_request("GET", endpoint)


def get_all(status_filter: str = None, client_filter: str = None) -> list:
    """Fetch items with optional filters."""
    endpoint = "claw_pending_items?order=created_at.desc"
    if status_filter:
        endpoint += f"&status=eq.{status_filter}"
    if client_filter:
        endpoint += f"&client_key=eq.{client_filter}"
    return _supabase_request("GET", endpoint)


def update_status(item_id: int, status: str, notes: str = None) -> list:
    """Update an item's status (approve/reject)."""
    body = {
        "status": status,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if notes:
        body["notes"] = notes
    endpoint = f"claw_pending_items?id=eq.{item_id}"
    return _supabase_request("PATCH", endpoint, body)


def push_item(item_type: str, client_key: str, title: str,
              content: str = None, metadata: dict = None, source: str = "claw") -> list:
    """Push a new pending item (used by CLAW or for testing)."""
    body = {
        "item_type": item_type,
        "client_key": client_key,
        "title": title,
        "content": content,
        "metadata": json.dumps(metadata or {}),
        "source": source,
        "status": "pending",
    }
    return _supabase_request("POST", "claw_pending_items", body)


def export_approved(client_filter: str = None) -> int:
    """Export approved items to local files."""
    items = get_all(status_filter="approved", client_filter=client_filter)
    if not items:
        print("  No approved items to export.")
        return 0

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in items:
        client = item.get("client_key", "unknown")
        item_type = item.get("item_type", "unknown")
        item_id = item.get("id")
        title = item.get("title", "untitled").replace(" ", "_")[:50]

        client_dir = EXPORT_DIR / client
        client_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{item_type}_{item_id}_{title}.md"
        filepath = client_dir / filename

        content = f"# {item.get('title', 'Untitled')}\n\n"
        content += f"**Type:** {item_type}\n"
        content += f"**Client:** {BUSINESS_NAMES.get(client, client)}\n"
        content += f"**Created:** {item.get('created_at', 'unknown')}\n"
        content += f"**Source:** {item.get('source', 'unknown')}\n\n"
        content += "---\n\n"
        content += item.get("content", "(no content)")

        filepath.write_text(content, encoding="utf-8")
        count += 1
        print(f"  Exported: {filepath}")

    print(f"\n  {count} items exported to {EXPORT_DIR}")
    return count


# ─── Display ────────────────────────────────────────────────────────────────

def display_items(items: list):
    """Pretty-print pending items."""
    if not items:
        print("  No pending items.")
        return

    print(f"\n  {'ID':>4}  {'Type':<18}  {'Client':<20}  {'Title':<40}  {'Created'}")
    print(f"  {'─'*4}  {'─'*18}  {'─'*20}  {'─'*40}  {'─'*20}")

    for item in items:
        item_id = item.get("id", "?")
        item_type = item.get("item_type", "?")[:18]
        client = BUSINESS_NAMES.get(item.get("client_key", ""), item.get("client_key", "?"))[:20]
        title = (item.get("title", "?"))[:40]
        created = item.get("created_at", "?")[:16]
        print(f"  {item_id:>4}  {item_type:<18}  {client:<20}  {title:<40}  {created}")

    print(f"\n  Total: {len(items)} pending items")
    print(f"  Approve: python claw_bridge.py --approve <ID>")
    print(f"  Reject:  python claw_bridge.py --reject <ID>")


def display_count(items: list):
    """Show just the count (for morning brief integration)."""
    by_client = {}
    by_type = {}
    for item in items:
        client = item.get("client_key", "unknown")
        itype = item.get("item_type", "unknown")
        by_client[client] = by_client.get(client, 0) + 1
        by_type[itype] = by_type.get(itype, 0) + 1

    print(f"CLAW Pending Items: {len(items)}")
    if by_client:
        for client, count in sorted(by_client.items(), key=lambda x: -x[1]):
            name = BUSINESS_NAMES.get(client, client)
            print(f"  {name}: {count}")
    if by_type:
        print(f"  By type: {', '.join(f'{t}={c}' for t, c in sorted(by_type.items(), key=lambda x: -x[1]))}")


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CLAW Bridge — manage pending approval items from Genspark CLAW")
    parser.add_argument("--count", action="store_true", help="Show pending count only (for morning brief)")
    parser.add_argument("--approve", type=int, metavar="ID", help="Approve an item by ID")
    parser.add_argument("--reject", type=int, metavar="ID", help="Reject an item by ID")
    parser.add_argument("--approve-all", action="store_true", help="Approve all pending items")
    parser.add_argument("--client", choices=list(BUSINESS_NAMES.keys()), help="Filter by client")
    parser.add_argument("--status", choices=["pending", "approved", "rejected", "posted"], help="Filter by status")
    parser.add_argument("--telegram", action="store_true", help="Send pending count to Telegram")
    parser.add_argument("--export", action="store_true", help="Export approved items to local files")
    parser.add_argument("--push", action="store_true", help="Push test items (for testing the bridge)")
    parser.add_argument("--notes", type=str, help="Notes when approving/rejecting")

    args = parser.parse_args()

    # Push test items
    if args.push:
        print("Pushing test items to Supabase...")
        test_items = [
            ("review_response", "sugar_shack", "Reply to 5-star review from Sarah M.",
             "Thank you so much Sarah! We're so glad you loved our homemade fudge. Come visit us again next time you're on the island!",
             {"review_rating": 5, "platform": "google"}),
            ("ad_copy", "island_arcade", "Spring Break Family Fun angle",
             "Spring Break is HERE and Island Arcade is the place to be! 🎮 Bring the whole family for hours of fun...",
             {"angle": "spring_break_family", "target": "tourists_with_kids"}),
            ("blog_draft", "custom_designs_tx", "5 Signs Your Security Camera System Needs an Upgrade",
             "Is your security camera system keeping up? Here are 5 signs it might be time for an upgrade...",
             {"keyword": "security camera upgrade mcallen", "word_count": 850}),
        ]
        for item_type, client, title, content, meta in test_items:
            result = push_item(item_type, client, title, content, meta)
            if result:
                print(f"  Pushed: [{client}] {title}")
            else:
                print(f"  FAILED: [{client}] {title}")
        return

    # Approve
    if args.approve:
        result = update_status(args.approve, "approved", args.notes)
        if result:
            print(f"  Approved item #{args.approve}")
        return

    # Reject
    if args.reject:
        result = update_status(args.reject, "rejected", args.notes)
        if result:
            print(f"  Rejected item #{args.reject}")
        return

    # Approve all
    if args.approve_all:
        items = get_pending(client_filter=args.client)
        if not items:
            print("  No pending items to approve.")
            return
        for item in items:
            update_status(item["id"], "approved", args.notes or "bulk approved")
        print(f"  Approved {len(items)} items")
        return

    # Export
    if args.export:
        export_approved(client_filter=args.client)
        return

    # Count (for morning brief)
    if args.count:
        items = get_pending(client_filter=args.client)
        display_count(items)
        if args.telegram and items:
            msg = f"CLAW Bridge: {len(items)} items pending approval\n"
            by_client = {}
            for item in items:
                c = BUSINESS_NAMES.get(item.get("client_key", ""), "?")
                by_client[c] = by_client.get(c, 0) + 1
            for name, count in sorted(by_client.items(), key=lambda x: -x[1]):
                msg += f"  {name}: {count}\n"
            _notify_mario(msg)
        return

    # Default: show all pending items
    if args.status:
        items = get_all(status_filter=args.status, client_filter=args.client)
    else:
        items = get_pending(client_filter=args.client)
    display_items(items)

    if args.telegram and items:
        _notify_mario(f"CLAW Bridge: {len(items)} items pending your approval")


if __name__ == "__main__":
    main()
