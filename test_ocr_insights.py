#!/usr/bin/env python3
"""
test_ocr_insights.py — Test Screenpipe OCR accuracy on Facebook Insights.

HOW TO USE:
  1. Open a Facebook page's Insights in Chrome (any client page)
  2. Navigate to the "Posts" section so you see engagement numbers
  3. Wait 10 seconds for Screenpipe to capture the screen
  4. Run this script:

     python test_ocr_insights.py                  # test last 2 minutes
     python test_ocr_insights.py --minutes 5      # test last 5 minutes
     python test_ocr_insights.py --dump            # raw OCR dump (debug)

  5. Compare printed numbers against what you see on screen

If numbers match → run: python engagement_logger.py <business> --screenpipe
If numbers are wrong → OCR is unreliable for Insights; keep manual entry.

This test only needs to run ONCE to decide whether UC-6 is viable.
"""

import sys
import json
import re
import argparse
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from screenpipe_verifier import screenpipe_healthy, screenpipe_search
except ImportError:
    print("[ERROR] screenpipe_verifier.py not found — run from tools/execution/")
    sys.exit(1)


# Keywords that appear on Facebook Insights pages
INSIGHTS_KEYWORDS = [
    "People reached",
    "Post engagements",
    "Engagements",
    "Post reach",
    "Likes",
    "Comments",
    "Shares",
    "reactions",
    "Reach",
    "Impressions",
    "Link clicks",
    "Post clicks",
    "Content distribution",
]

# Regex to find numbers near engagement keywords
NUMBER_NEAR_KEYWORD = re.compile(
    r'(?:(\d[\d,\.]*)\s*(?:people\s+reached|post\s+engagements?|engagements?|likes?|comments?|shares?|reactions?|reach|impressions|link\s+clicks|post\s+clicks))|'
    r'(?:(?:people\s+reached|post\s+engagements?|engagements?|likes?|comments?|shares?|reactions?|reach|impressions|link\s+clicks|post\s+clicks)\s*[:\-]?\s*(\d[\d,\.]*))',
    re.IGNORECASE,
)


def extract_metrics_from_text(text: str) -> list:
    """Try to extract engagement numbers from OCR text."""
    found = []
    for match in NUMBER_NEAR_KEYWORD.finditer(text):
        number_str = match.group(1) or match.group(2)
        if number_str:
            clean = number_str.replace(",", "").replace(".", "")
            try:
                value = int(clean)
                context = text[max(0, match.start()-20):match.end()+20].strip()
                found.append({"value": value, "raw": number_str, "context": context})
            except ValueError:
                pass
    return found


def test_ocr(minutes: int = 2, dump: bool = False):
    """Query Screenpipe for recent FB Insights data and attempt metric extraction."""
    if not screenpipe_healthy():
        print("[ERROR] Screenpipe is not running")
        return

    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Searching Screenpipe OCR from last {minutes} minutes...")
    print(f"Time range: {start} → {end}")
    print()

    # Search for each Insights keyword
    all_texts = []
    for keyword in INSIGHTS_KEYWORDS:
        results = screenpipe_search(keyword, content_type="ocr", limit=10,
                                     start_time=start, end_time=end)
        for r in results:
            text = r.get("content", {}).get("text", "")
            app = r.get("content", {}).get("app_name", "?")
            ts = r.get("content", {}).get("timestamp", "?")
            if text and text not in [t["text"] for t in all_texts]:
                all_texts.append({"text": text, "app": app, "ts": ts, "keyword": keyword})

    if not all_texts:
        print("NO Insights-related OCR text found in this time window.")
        print()
        print("Make sure you:")
        print("  1. Have Facebook Insights OPEN and VISIBLE on screen")
        print("  2. Wait 10+ seconds before running this script")
        print("  3. The Insights page shows numbers (not loading spinners)")
        return

    print(f"Found {len(all_texts)} OCR captures with Insights keywords")
    print("=" * 60)

    if dump:
        for i, item in enumerate(all_texts):
            print(f"\n--- Capture {i+1} ({item['app']}, keyword: {item['keyword']}) ---")
            print(item["text"][:500])
        return

    # Try to extract metrics
    all_metrics = []
    for item in all_texts:
        metrics = extract_metrics_from_text(item["text"])
        for m in metrics:
            m["app"] = item["app"]
            m["ts"] = item["ts"]
            all_metrics.append(m)

    if not all_metrics:
        print()
        print("OCR text found but COULD NOT extract numbers.")
        print("This suggests OCR is unreliable for Facebook Insights metrics.")
        print()
        print("Sample OCR text:")
        for item in all_texts[:3]:
            print(f"  [{item['app']}] {item['text'][:200]}")
        print()
        print("VERDICT: Keep manual engagement entry (--screenpipe mode NOT viable)")
        return

    print()
    print("EXTRACTED METRICS:")
    print(f"  {'Value':>10}  {'Raw':>10}  Context")
    print(f"  {'-'*10}  {'-'*10}  {'-'*40}")
    for m in all_metrics:
        print(f"  {m['value']:>10,}  {m['raw']:>10}  ...{m['context'][:50]}...")

    print()
    print(f"Total: {len(all_metrics)} numbers extracted from {len(all_texts)} OCR captures")
    print()
    print("COMPARE these numbers against what you see on the Facebook Insights page.")
    print("If they match → OCR is viable! Run: python engagement_logger.py <biz> --screenpipe")
    print("If they're wrong → OCR is unreliable; keep manual entry.")


def main():
    parser = argparse.ArgumentParser(description="Test Screenpipe OCR on Facebook Insights")
    parser.add_argument("--minutes", type=int, default=2, help="How far back to search (default: 2 min)")
    parser.add_argument("--dump", action="store_true", help="Dump raw OCR text instead of extracting")
    args = parser.parse_args()

    test_ocr(args.minutes, args.dump)


if __name__ == "__main__":
    main()
