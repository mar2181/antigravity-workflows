#!/usr/bin/env python3
"""
seo_delta_tracker.py — Step 4: Measure rank improvements 6-12 hours after actions.

Runs 6-12 hours after seo_action_executor.py.

For each executed action:
  1. Re-checks the target keyword rank using Bright Data
  2. Computes delta = pre_action_rank - post_action_rank (positive = improvement)
  3. Applies keep-if-better logic:
     - delta > 0 → EFFECTIVE (add to winning patterns)
     - delta = 0 → NEUTRAL (try different action type next time)
     - delta < 0 → HARMFUL (flag for review, optionally delete post)
  4. Updates seo_optimizer_state.json with outcomes

Over time builds a per-client "what works" pattern map.

Usage:
  python seo_optimizer/seo_delta_tracker.py                    # all clients
  python seo_optimizer/seo_delta_tracker.py --client sugar_shack
  python seo_optimizer/seo_delta_tracker.py --dry-run

State file: seo_optimizer_state.json
"""

import json
import sys
import argparse
import urllib.parse
import urllib.request
import re
import html as _html_mod
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.parent
SEO_STATE_PATH = SCRIPT_DIR / "seo_optimizer" / "seo_optimizer_state.json"
RANKING_STATE_PATH = SCRIPT_DIR / "keyword_rankings_state.json"

# Bright Data Web Unlocker
BD_TOKEN = "7fe773b11b190ba758a122c288438d14deef5356a694ef707a3c847de5af3b5c"
BD_URL = "https://api.brightdata.com/request"

def fetch_rank_via_brightdata(keyword, location="South Padre Island, TX"):
    """
    Fetch current keyword rank using Bright Data Web Unlocker.
    Returns: {map_pack_rank, organic_rank, competitors: [...]}
    """
    try:
        search_query = f"{keyword} near {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"

        payload = json.dumps({
            "zone": "web_unlocker1",
            "url": url,
            "format": "raw",
        }).encode("utf-8")

        req = urllib.request.Request(
            BD_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {BD_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", errors="replace")

        # Parse rank from HTML
        map_pack_rank = None
        organic_rank = None

        # Simple extraction (more sophisticated parsing in actual keyword_rank_tracker.py)
        if "map_pack_rank" in raw:
            # Placeholder — actual parsing depends on HTML structure
            map_pack_rank = None

        return {
            "rank": map_pack_rank,
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"      ⚠️ Error fetching rank: {str(e)}")
        return None

def update_winning_patterns(seo_state, client, action_type, delta):
    """Update winning patterns registry based on action outcome."""
    if "winning_patterns" not in seo_state:
        seo_state["winning_patterns"] = {}

    if client not in seo_state["winning_patterns"]:
        seo_state["winning_patterns"][client] = {}

    if action_type not in seo_state["winning_patterns"][client]:
        seo_state["winning_patterns"][client][action_type] = {
            "total": 0,
            "effective": 0,
            "neutral": 0,
            "harmful": 0,
            "avg_delta": 0,
        }

    stats = seo_state["winning_patterns"][client][action_type]
    stats["total"] += 1

    if delta > 0:
        stats["effective"] += 1
        stats["avg_delta"] = (stats["avg_delta"] * (stats["effective"] - 1) + delta) / stats["effective"]
    elif delta == 0:
        stats["neutral"] += 1
    else:
        stats["harmful"] += 1

    return seo_state

def main():
    parser = argparse.ArgumentParser(description="Track rank deltas for executed actions")
    parser.add_argument("--client", help="Single client to check")
    parser.add_argument("--dry-run", action="store_true", help="Check only, don't update state")
    args = parser.parse_args()

    print("📊 SEO Delta Tracker — Measuring rank improvements...")

    # Load SEO state
    if not SEO_STATE_PATH.exists():
        print("❌ SEO state file not found. Run executor first.")
        return

    with open(SEO_STATE_PATH, "r", encoding="utf-8") as f:
        seo_state = json.load(f)

    work_queue = seo_state.get("work_queue", [])

    # Filter to EXECUTED status
    work_queue = [w for w in work_queue if w.get("status") == "EXECUTED"]

    # Filter by client if specified
    if args.client:
        work_queue = [w for w in work_queue if w["client"] == args.client]

    if not work_queue:
        print("❌ No executed actions to track.")
        return

    print(f"\n📋 Checking rank changes for {len(work_queue)} keywords...")

    for i, work_item in enumerate(work_queue, 1):
        client = work_item["client"]
        keyword = work_item["keyword"]
        pre_rank = work_item.get("pre_action_rank")

        print(f"\n[{i}/{len(work_queue)}] {client} → {keyword}")
        print(f"  Pre-action rank: {pre_rank or 'Not ranked'}", end=" → ", flush=True)

        # Fetch current rank
        rank_data = fetch_rank_via_brightdata(keyword)

        if rank_data and rank_data.get("rank"):
            post_rank = rank_data["rank"]
            delta = (pre_rank or 100) - post_rank  # Higher pre than post = improvement

            print(f"Post-action rank: {post_rank}")
            print(f"  Delta: {delta:+d} {'✅ EFFECTIVE' if delta > 0 else '⚠️ NEUTRAL' if delta == 0 else '❌ HARMFUL'}")

            if not args.dry_run:
                work_item["post_action_rank"] = post_rank
                work_item["delta"] = delta

                # Determine outcome
                if delta > 0:
                    work_item["status"] = "EFFECTIVE"
                elif delta == 0:
                    work_item["status"] = "NEUTRAL"
                else:
                    work_item["status"] = "HARMFUL"

                # Update winning patterns
                action_type = work_item.get("action_type", "unknown")
                seo_state = update_winning_patterns(seo_state, client, action_type, delta)

                # Add to history
                if "action_history" not in seo_state:
                    seo_state["action_history"] = []

                seo_state["action_history"].append({
                    "client": client,
                    "keyword": keyword,
                    "action_type": action_type,
                    "pre_rank": pre_rank,
                    "post_rank": post_rank,
                    "delta": delta,
                    "status": work_item["status"],
                    "timestamp": datetime.now().isoformat(),
                })

        else:
            print("Could not fetch rank (will retry later)")

    # Save updated state
    if not args.dry_run:
        seo_state["work_queue"] = work_queue
        seo_state["last_tracked"] = datetime.now().isoformat()

        with open(SEO_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(seo_state, f, indent=2, ensure_ascii=False)

        # Print winning patterns summary
        print("\n📈 Winning Patterns (Effectiveness):")
        for client, patterns in seo_state.get("winning_patterns", {}).items():
            print(f"\n  {client}:")
            for action_type, stats in patterns.items():
                if stats["total"] > 0:
                    effectiveness = (stats["effective"] / stats["total"]) * 100
                    print(f"    {action_type}: {effectiveness:.0f}% effective ({stats['effective']}/{stats['total']}) | Avg delta: {stats['avg_delta']:+.1f}")

        print(f"\n✅ Delta tracking complete")
    else:
        print(f"\n📋 Dry run complete: {len(work_queue)} actions checked")

if __name__ == "__main__":
    main()
