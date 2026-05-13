#!/usr/bin/env python3
"""
seo_ranking_analyzer.py — Step 1: Identify weak keywords by opportunity score.

Reads keyword_rankings_state.json (time-series data from keyword_rank_tracker.py).
For each client, scores every keyword by opportunity:
  - Opportunity score = rank_weight × search_volume_weight × 100
  - Keywords ranked 4–10 in Map Pack get highest weight (easiest to push into top 3)
  - Keywords with no ranking get medium weight
  - Keywords in 1–3 are skipped (already winning)

Outputs a work queue: top 3 opportunity keywords per client per run.
Writes to seo_optimizer_state.json.

Usage:
  python seo_optimizer/seo_ranking_analyzer.py                    # all clients
  python seo_optimizer/seo_ranking_analyzer.py --dry-run
  python seo_optimizer/seo_ranking_analyzer.py --client sugar_shack

State file: seo_optimizer_state.json
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.parent
RANKING_STATE_PATH = SCRIPT_DIR / "keyword_rankings_state.json"
SEO_STATE_PATH = SCRIPT_DIR / "seo_optimizer" / "seo_optimizer_state.json"

# Keyword opportunity weights
SEARCH_VOLUME_MAP = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}

RANK_WEIGHTS = {
    1: 0.0,    # Already winning
    2: 0.0,
    3: 0.0,
    4: 1.0,    # Highest opportunity (just outside 3-pack)
    5: 0.95,
    6: 0.90,
    7: 0.85,
    8: 0.80,
    9: 0.75,
    10: 0.70,
    11: 0.60,
    20: 0.40,
    None: 0.50,  # Not ranked (medium opportunity)
}

def load_ranking_state():
    """Load keyword rankings from keyword_rank_tracker output (time-series data)."""
    if not RANKING_STATE_PATH.exists():
        print(f"❌ Ranking state file not found: {RANKING_STATE_PATH}")
        return {}

    with open(RANKING_STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_seo_state():
    """Load existing SEO optimizer state."""
    if not SEO_STATE_PATH.exists():
        return {
            "work_queue": [],
            "winning_patterns": {},
            "action_history": [],
        }

    with open(SEO_STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_latest_rank(keyword_timeseries):
    """
    Extract the latest map_pack_position from time-series keyword data.

    Data structure: {YYYY-MM-DD: {map_pack_position, maps_position, ...}, ...}
    Returns: (current_rank, latest_date) or (None, None) if no data
    """
    if not keyword_timeseries or not isinstance(keyword_timeseries, dict):
        return None, None

    # Get latest date (dict keys are date strings, sort them)
    dates = sorted(keyword_timeseries.keys(), reverse=True)
    if not dates:
        return None, None

    latest_date = dates[0]
    latest_data = keyword_timeseries[latest_date]

    # Extract map_pack_position (may be None if not ranked)
    current_rank = latest_data.get("map_pack_position")

    return current_rank, latest_date

def estimate_search_volume(current_rank):
    """
    Estimate search volume category based on current rank.
    Higher rank (lower number) suggests higher search volume.
    Not ranked = unknown volume (assume medium).
    """
    if current_rank is None:
        return "medium"

    if current_rank <= 3:
        return "high"
    elif current_rank <= 10:
        return "high"
    elif current_rank <= 20:
        return "medium"
    else:
        return "low"

def compute_opportunity_score(current_rank, search_volume):
    """
    Compute opportunity score for a keyword.
    Higher score = more opportunity to move the ranking.
    """
    # Skip keywords already in top 3
    if current_rank and current_rank <= 3:
        return 0.0

    # Weight for rank position
    rank_weight = RANK_WEIGHTS.get(current_rank, RANK_WEIGHTS[None])

    # Weight for search volume
    volume_weight = SEARCH_VOLUME_MAP.get(search_volume, 0.3)

    # Combined opportunity score (0-100)
    opportunity = rank_weight * volume_weight * 100

    return opportunity

def analyze_client(client_name, ranking_data):
    """Analyze all keywords for a client and return top 3 opportunities."""
    opportunities = []

    if client_name not in ranking_data:
        return []

    client_keywords = ranking_data[client_name]

    for keyword, timeseries_data in client_keywords.items():
        # Extract latest rank from time-series
        current_rank, latest_date = get_latest_rank(timeseries_data)

        # Estimate search volume from rank
        search_volume = estimate_search_volume(current_rank)

        # Compute opportunity score
        score = compute_opportunity_score(current_rank, search_volume)

        if score > 0:  # Only include keywords with opportunity
            opportunities.append({
                "keyword": keyword,
                "current_rank": current_rank,
                "search_volume": search_volume,
                "opportunity_score": round(score, 2),
                "latest_date": latest_date,
            })

    # Sort by opportunity score (descending)
    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

    # Return top 3
    return opportunities[:3]

def main():
    parser = argparse.ArgumentParser(description="Identify weak keywords for SEO optimization")
    parser.add_argument("--client", help="Single client to analyze (e.g., sugar_shack)")
    parser.add_argument("--dry-run", action="store_true", help="Print analysis without saving")
    args = parser.parse_args()

    print("📊 SEO Ranking Analyzer — Identifying weak keywords...\n")

    ranking_state = load_ranking_state()
    seo_state = load_seo_state()

    if not ranking_state:
        print("❌ No ranking data found. Run keyword_rank_tracker.py first.")
        return

    work_queue = []

    # Analyze selected client(s)
    clients = sorted([args.client] if args.client else ranking_state.keys())

    for client_name in clients:
        opportunities = analyze_client(client_name, ranking_state)

        if not opportunities:
            print(f"{client_name.upper()} — No opportunities (all keywords already top 3 or unranked)")
            continue

        print(f"{client_name.upper()} — Top {len(opportunities)} Opportunities:\n")

        for i, opp in enumerate(opportunities, 1):
            work_queue.append({
                "client": client_name,
                "keyword": opp["keyword"],
                "current_rank": opp["current_rank"],
                "search_volume": opp["search_volume"],
                "opportunity_score": opp["opportunity_score"],
                "status": "PENDING",
                "action_type": None,
                "action_content": None,
                "pre_action_rank": opp["current_rank"],
                "post_action_rank": None,
                "delta": None,
                "gbp_scores": None,
                "created_at": datetime.now().isoformat(),
            })

            rank_display = f"#{opp['current_rank']}" if opp['current_rank'] else "Unranked"
            print(f"  {i}. {opp['keyword']}")
            print(f"     Rank: {rank_display} | Volume: {opp['search_volume'].upper()} | Score: {opp['opportunity_score']}")
            print()

    if not work_queue:
        print("⚠️  No opportunities found. All keywords may already be top 3.")
        return

    # Save work queue (even in dry-run, so subsequent steps can process it)
    seo_state["work_queue"] = work_queue
    seo_state["last_analyzed"] = datetime.now().isoformat()
    seo_state["dry_run"] = args.dry_run

    with open(SEO_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(seo_state, f, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(f"📋 Dry run: {len(work_queue)} keywords queued (will not execute posts)")
    else:
        print(f"✅ Work queue saved: {len(work_queue)} keywords identified for optimization")

if __name__ == "__main__":
    main()
