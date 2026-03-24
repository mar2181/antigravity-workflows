#!/usr/bin/env python3
"""
delta_tracker.py — Compute what changed since yesterday across all intel sources.

Reads:
  - keyword_rankings_state.json       (30-day rolling rankings per keyword per business)
  - competitor_reports/state.json     (GBP ratings + review counts per competitor)
  - competitor_reports/adlibrary_*.json  (Facebook ad counts per competitor)

Writes:
  - competitor_reports/delta_state.json     (snapshot of today — becomes "yesterday" tomorrow)
  - competitor_reports/delta_YYYY-MM-DD.json  (today's movements — read by morning_brief.py)

Usage:
  python delta_tracker.py            # compute deltas, write report
  python delta_tracker.py --dry-run  # print what changed, don't write files
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, date

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR   = Path(__file__).parent
REPORTS_DIR     = EXECUTION_DIR / "competitor_reports"
RANKINGS_STATE  = EXECUTION_DIR / "keyword_rankings_state.json"
GBP_STATE       = REPORTS_DIR / "state.json"
DELTA_STATE     = REPORTS_DIR / "delta_state.json"
REPORTS_DIR.mkdir(exist_ok=True)

# Business display names (mirrors morning_brief.py)
BUSINESS_NAMES = {
    "sugar_shack":       "The Sugar Shack",
    "island_arcade":     "Island Arcade",
    "island_candy":      "Island Candy",
    "juan":              "Juan Elizondo RE/MAX Elite",
    "spi_fun_rentals":   "SPI Fun Rentals",
    "custom_designs_tx": "Custom Designs TX",
    "optimum_clinic":    "Optimum Health & Wellness Clinic",
    "optimum_foundation":"Optimum Health and Wellness Foundation",
}

# ─── Loaders ─────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_rankings_state() -> dict:
    """Load keyword_rankings_state.json. Returns {} if missing."""
    return _load_json(RANKINGS_STATE) if RANKINGS_STATE.exists() else {}


def load_gbp_state() -> dict:
    """Load competitor_reports/state.json. Returns {} if missing."""
    return _load_json(GBP_STATE) if GBP_STATE.exists() else {}


def load_delta_state() -> dict:
    """Load yesterday's delta snapshot. Returns {} if no baseline yet."""
    return _load_json(DELTA_STATE) if DELTA_STATE.exists() else {}


def load_latest_adlibrary() -> dict:
    """Load most recent adlibrary_*.json."""
    candidates = sorted(REPORTS_DIR.glob("adlibrary_*.json"), reverse=True)
    for p in candidates:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


# ─── Keyword ranking deltas ───────────────────────────────────────────────────

def compute_keyword_movements(rankings_state: dict) -> list:
    """
    Compare the two most recent dates in keyword_rankings_state.json per keyword.
    Returns a list of movements where something actually changed.
    """
    movements = []

    for biz_key, keywords in rankings_state.items():
        biz_name = BUSINESS_NAMES.get(biz_key, biz_key)

        for kw_text, date_history in keywords.items():
            dates = sorted(date_history.keys())  # ascending
            if len(dates) < 2:
                continue  # need at least 2 data points

            prev_date = dates[-2]
            curr_date = dates[-1]

            prev = date_history[prev_date]
            curr = date_history[curr_date]

            if prev.get("error") or curr.get("error"):
                continue

            # Map pack position (lower number = better rank)
            mp_prev = prev.get("map_pack_position")
            mp_curr = curr.get("map_pack_position")

            # Organic position
            org_prev = prev.get("organic_position")
            org_curr = curr.get("organic_position")

            # Check if anything actually changed
            mp_changed  = (mp_prev != mp_curr)
            org_changed = (org_prev != org_curr)

            if not mp_changed and not org_changed:
                continue  # no movement — skip (zero noise)

            def pos_delta(prev_pos, curr_pos):
                if prev_pos is None and curr_pos is None:
                    return {"prev": None, "curr": None, "delta": 0, "direction": "same"}
                if prev_pos is None:
                    return {"prev": None, "curr": curr_pos, "delta": None, "direction": "new"}
                if curr_pos is None:
                    return {"prev": prev_pos, "curr": None, "delta": None, "direction": "lost"}
                delta = prev_pos - curr_pos  # positive = improved (lower rank # = better)
                direction = "up" if delta > 0 else ("down" if delta < 0 else "same")
                return {"prev": prev_pos, "curr": curr_pos, "delta": delta, "direction": direction}

            movements.append({
                "business":      biz_key,
                "business_name": biz_name,
                "keyword":       kw_text,
                "prev_date":     prev_date,
                "curr_date":     curr_date,
                "map_pack":      pos_delta(mp_prev, mp_curr),
                "organic":       pos_delta(org_prev, org_curr),
            })

    # Sort: biggest movers first (by abs delta on map_pack)
    def sort_key(m):
        d = m["map_pack"]["delta"]
        return abs(d) if d is not None else 0

    return sorted(movements, key=sort_key, reverse=True)


# ─── Competitor GBP rating deltas ─────────────────────────────────────────────

def compute_gbp_changes(gbp_state: dict, prev_snapshot: dict) -> list:
    """
    Compare current GBP state.json against the previous delta_state.json snapshot.
    Returns list of competitors where rating or review_count changed.
    """
    changes = []

    for state_key, curr in gbp_state.items():
        # state_key format: "sugar_shack__Sugar Kingdom"
        if "__" not in state_key:
            continue
        biz_key, competitor = state_key.split("__", 1)
        biz_name = BUSINESS_NAMES.get(biz_key, biz_key)

        prev = prev_snapshot.get("gbp", {}).get(state_key, {})
        if not prev:
            continue  # no baseline for this competitor yet

        curr_rating = curr.get("rating")
        prev_rating = prev.get("rating")
        curr_reviews = curr.get("review_count")
        prev_reviews = prev.get("review_count")

        rating_changed  = (curr_rating != prev_rating) and curr_rating and prev_rating
        reviews_changed = False
        review_delta    = 0

        # Review count delta (convert to int where possible)
        try:
            cr = int(str(curr_reviews).replace(",", "")) if curr_reviews else None
            pr = int(str(prev_reviews).replace(",", "")) if prev_reviews else None
            if cr and pr and cr != pr:
                reviews_changed = True
                review_delta = cr - pr
        except (ValueError, TypeError):
            pass

        if not rating_changed and not reviews_changed:
            continue

        # Compute rating delta
        rating_delta = 0.0
        try:
            if rating_changed:
                rating_delta = round(float(curr_rating) - float(prev_rating), 2)
        except (ValueError, TypeError):
            pass

        change = {
            "business":       biz_key,
            "business_name":  biz_name,
            "competitor":     competitor,
            "rating": {
                "prev":  prev_rating,
                "curr":  curr_rating,
                "delta": rating_delta,
                "changed": rating_changed,
            },
            "review_count": {
                "prev":  prev_reviews,
                "curr":  curr_reviews,
                "delta": review_delta,
                "changed": reviews_changed,
            },
        }

        # Flag if competitor is dropping (alert)
        if rating_changed and rating_delta < 0:
            change["alert"] = "RATING_DROP"
        elif reviews_changed and review_delta > 10:
            change["alert"] = "REVIEW_SURGE"

        changes.append(change)

    return changes


# ─── Facebook Ad Library deltas ───────────────────────────────────────────────

def compute_ad_changes(adlib_data: dict, prev_snapshot: dict) -> list:
    """
    Compare current adlibrary data against previous snapshot.
    Returns list of competitors where ad count changed.
    """
    changes = []

    for biz_key, biz_data in adlib_data.items():
        biz_name = BUSINESS_NAMES.get(biz_key, biz_key)

        for comp in biz_data.get("competitors", []):
            name        = comp.get("name", "")
            snap_key    = f"{biz_key}__{name}"
            curr_count  = comp.get("active_ad_count", 0)
            no_ads_curr = comp.get("no_ads", False)

            prev_entry = prev_snapshot.get("ads", {}).get(snap_key, {})
            if not prev_entry:
                continue

            prev_count = prev_entry.get("active_ad_count", 0)
            if curr_count == prev_count:
                continue

            delta = curr_count - prev_count
            alert = None
            if prev_count == 0 and curr_count > 0:
                alert = "STARTED_ADS"
            elif curr_count == 0 and prev_count > 0:
                alert = "STOPPED_ADS"
            elif delta > 2:
                alert = "ADS_INCREASED"

            changes.append({
                "business":      biz_key,
                "business_name": biz_name,
                "competitor":    name,
                "active_ads": {
                    "prev":  prev_count,
                    "curr":  curr_count,
                    "delta": delta,
                },
                "alert": alert,
            })

    return changes


# ─── Snapshot builder ─────────────────────────────────────────────────────────

def build_snapshot(gbp_state: dict, adlib_data: dict) -> dict:
    """
    Build today's snapshot — saved as delta_state.json (becomes "yesterday" tomorrow).
    """
    snapshot = {
        "date": date.today().isoformat(),
        "gbp":  {},
        "ads":  {},
    }

    # GBP snapshot — key per competitor
    for state_key, data in gbp_state.items():
        snapshot["gbp"][state_key] = {
            "rating":       data.get("rating"),
            "review_count": data.get("review_count"),
        }

    # Ad Library snapshot — key per competitor
    for biz_key, biz_data in adlib_data.items():
        for comp in biz_data.get("competitors", []):
            name     = comp.get("name", "")
            snap_key = f"{biz_key}__{name}"
            snapshot["ads"][snap_key] = {
                "active_ad_count": comp.get("active_ad_count", 0),
                "no_ads":          comp.get("no_ads", False),
            }

    return snapshot


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compute daily movement deltas")
    parser.add_argument("--dry-run", action="store_true", help="Print output, don't write files")
    args = parser.parse_args()

    today_str   = date.today().isoformat()
    out_path    = REPORTS_DIR / f"delta_{today_str}.json"

    print(f"Delta Tracker — {today_str}")

    # Load all sources
    rankings_state = load_rankings_state()
    gbp_state      = load_gbp_state()
    adlib_data     = load_latest_adlibrary()
    prev_snapshot  = load_delta_state()

    has_baseline = bool(prev_snapshot)
    if has_baseline:
        print(f"  Baseline from: {prev_snapshot.get('date', 'unknown')}")
    else:
        print("  No baseline yet — this run creates it. Deltas will appear tomorrow.")

    # Compute all deltas
    keyword_movements = compute_keyword_movements(rankings_state)
    gbp_changes       = compute_gbp_changes(gbp_state, prev_snapshot) if has_baseline else []
    ad_changes        = compute_ad_changes(adlib_data, prev_snapshot)  if has_baseline else []

    print(f"  Keyword movements:    {len(keyword_movements)}")
    print(f"  GBP rating changes:   {len(gbp_changes)}")
    print(f"  Ad activity changes:  {len(ad_changes)}")

    # Print summary
    if keyword_movements:
        print("\n  KEYWORD MOVEMENTS:")
        for m in keyword_movements[:10]:
            mp  = m["map_pack"]
            org = m["organic"]
            parts = []
            if mp["direction"] not in ("same", "new", "lost"):
                arrow = "UP" if mp["direction"] == "up" else "DOWN"
                parts.append(f"Map Pack #{mp['prev']} -> #{mp['curr']} ({arrow} {abs(mp['delta'])})")
            elif mp["direction"] == "new":
                parts.append(f"Map Pack: NEW ENTRY #{mp['curr']}")
            elif mp["direction"] == "lost":
                parts.append(f"Map Pack: DROPPED OUT (was #{mp['prev']})")
            if org["changed"] if isinstance(org.get("changed"), bool) else (org["prev"] != org["curr"]):
                if org["direction"] not in ("same",):
                    parts.append(f"Organic #{org.get('prev','?')} -> #{org.get('curr','?')}")
            if parts:
                print(f"    {m['business_name']}: \"{m['keyword'][:50]}\" — {', '.join(parts)}")

    if gbp_changes:
        print("\n  GBP CHANGES:")
        for c in gbp_changes:
            r  = c["rating"]
            rv = c["review_count"]
            parts = []
            if r["changed"]:
                sign = "+" if r["delta"] > 0 else ""
                parts.append(f"Rating {r['prev']} -> {r['curr']} ({sign}{r['delta']})")
            if rv["changed"]:
                sign = "+" if rv["delta"] > 0 else ""
                parts.append(f"Reviews {rv['prev']} -> {rv['curr']} ({sign}{rv['delta']})")
            alert = f" [{c['alert']}]" if c.get("alert") else ""
            print(f"    {c['business_name']} — {c['competitor']}: {', '.join(parts)}{alert}")

    if ad_changes:
        print("\n  AD ACTIVITY:")
        for c in ad_changes:
            ads = c["active_ads"]
            sign = "+" if ads["delta"] > 0 else ""
            alert = f" [{c['alert']}]" if c.get("alert") else ""
            print(f"    {c['business_name']} — {c['competitor']}: {ads['prev']} -> {ads['curr']} ads ({sign}{ads['delta']}){alert}")

    if not keyword_movements and not gbp_changes and not ad_changes and has_baseline:
        print("  Nothing changed since yesterday.")

    if args.dry_run:
        print("\n  [DRY RUN — no files written]")
        return 0

    # Build today's snapshot for tomorrow's comparison
    new_snapshot = build_snapshot(gbp_state, adlib_data)

    # has_baseline = True if we have any data to show (keywords always available from history)
    has_data = bool(keyword_movements or gbp_changes or ad_changes)

    # Build delta output file
    delta_output = {
        "date":                  today_str,
        "generated_at":          datetime.now().isoformat(),
        "has_baseline":          has_data,   # True as long as we have something to show
        "gbp_baseline_ready":    has_baseline,  # GBP/ad deltas only available after 2nd run
        "baseline_date":         prev_snapshot.get("date") if has_baseline else "ranking history",
        "keyword_movements":     keyword_movements,
        "competitor_rating_changes": gbp_changes,
        "ad_activity_changes":   ad_changes,
    }

    # Write files
    out_path.write_text(json.dumps(delta_output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Delta report: {out_path}")

    DELTA_STATE.write_text(json.dumps(new_snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Baseline snapshot updated: {DELTA_STATE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
