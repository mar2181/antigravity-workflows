#!/usr/bin/env python3
"""
Parallel batch runner for the no-website lead scraper.
Splits categories across multiple worker processes for speed.

Usage:
    python batch_runner.py                  # all categories, 4 workers
    python batch_runner.py --workers 2      # 2 parallel workers
    python batch_runner.py --limit 10       # only first 10 categories
"""

import sys
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from config import CATEGORIES, CITIES, QUERY_TEMPLATES, SCORING, OUTPUT_DIR


def run_batch(batch_categories: list[str], batch_id: int) -> list[dict]:
    """Run a batch of categories through the scraper. Returns lead dicts."""
    from scraper import run_search, _score_lead, _lead_tier, _dedup_key

    all_leads = []
    total_cats = len(batch_categories)

    for ci, cat in enumerate(batch_categories):
        queries = [t.format(cat, city) for city in CITIES for t in QUERY_TEMPLATES]
        # Flatten: run all city queries for this category
        cat_leads = []
        seen = set()

        for city in CITIES:
            city_queries = [t.format(cat, city) for t in QUERY_TEMPLATES]
            results = run_search(cat, city, city_queries)
            for b in results:
                key = _dedup_key(b)
                if key not in seen:
                    seen.add(key)
                    b["category"] = cat
                    b["city"] = city
                    cat_leads.append(b)

        for b in cat_leads:
            b["score"] = _score_lead(b)
            b["tier"] = _lead_tier(b["score"])

        all_leads.extend(cat_leads)
        if (ci + 1) % 3 == 0 or ci == total_cats - 1:
            print(f"  [Batch {batch_id}] {ci+1}/{total_cats} categories done, "
                  f"{len(all_leads)} leads so far", flush=True)

    return all_leads


def main():
    parser = argparse.ArgumentParser(description="Parallel lead gen batch runner")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers (default: 4)")
    parser.add_argument("--limit", type=int, default=0, help="Limit total categories")
    parser.add_argument("--output", type=str, default="", help="Output CSV name")
    args = parser.parse_args()

    categories = CATEGORIES[:args.limit] if args.limit else CATEGORIES
    workers = min(args.workers, len(categories))

    # Split categories across workers
    batches = [[] for _ in range(workers)]
    for i, cat in enumerate(categories):
        batches[i % workers].append(cat)

    print(f"{'='*60}")
    print(f"PARALLEL LEAD GEN SWEEP")
    print(f"{'='*60}")
    print(f"Categories: {len(categories)}  |  Cities: {len(CITIES)}  |  "
          f"Queries per city: {len(QUERY_TEMPLATES)}")
    print(f"Workers: {workers}  |  Batches: {[len(b) for b in batches]}")
    print(f"Total queries: {len(categories) * len(CITIES) * len(QUERY_TEMPLATES)}")
    print(f"{'='*60}\n")

    all_leads = []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_batch, batch, i): i
            for i, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            batch_id = futures[future]
            try:
                leads = future.result()
                all_leads.extend(leads)
                print(f"[Batch {batch_id}] COMPLETE — {len(leads)} leads", flush=True)
            except Exception as e:
                print(f"[Batch {batch_id}] FAILED: {e}", flush=True)

    # Deduplicate across batches
    seen = set()
    unique = []
    for l in sorted(all_leads, key=lambda x: x.get("score", 0), reverse=True):
        from scraper import _dedup_key
        key = _dedup_key(l)
        if key not in seen:
            seen.add(key)
            unique.append(l)

    unique = [l for l in unique if l.get("score", 0) >= SCORING["min_score"]]

    # Output
    out_dir = SCRIPT_DIR / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_name = args.output or f"rgv_full_sweep_{ts}.csv"
    out_path = out_dir / out_name

    fields = ["tier", "score", "name", "category", "city", "rating", "reviews",
              "has_website", "website_type", "website_url", "address", "phone",
              "rank_pos", "search_query"]

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique)

    # Summary
    no_site = [l for l in unique if not l["has_website"]]
    social = [l for l in unique if l.get("website_type") == "social"]
    hot = [l for l in unique if l["tier"] == "HOT"]

    print(f"\n{'='*60}")
    print(f"FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Total businesses scanned:   {len(unique)}")
    print(f"No website at all:         {len(no_site)}  <- PRIMARY TARGETS")
    print(f"Social media only:         {len(social)}  <- upgrade to real site")
    print(f"HOT leads (score 75+):     {len(hot)}")
    print(f"Output: {out_path}")

    # Top 15 preview
    print(f"\n{'-'*60}")
    print(f"TOP 15 LEADS (no-website only)")
    print(f"{'-'*60}")
    shown = 0
    for l in unique:
        if not l["has_website"] and shown < 15:
            shown += 1
            print(f"  {shown:2}. [{l['tier']:4}] {l['name'][:45]}")
            print(f"       {l['category']} | {l['city']} | {l.get('rating','?')}* "
                  f"({l.get('reviews',0)} reviews) | Score: {l['score']}")
            if l.get("phone"):
                print(f"       Phone: {l['phone']}")
    if shown == 0:
        print("  (no no-website leads found in this sweep)")

    print(f"\nDone. Full list -> {out_path}")


if __name__ == "__main__":
    main()
