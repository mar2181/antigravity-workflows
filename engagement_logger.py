#!/usr/bin/env python3
"""
engagement_logger.py — Closes the autoresearch feedback loop.

After a post goes live on Facebook, log the real engagement numbers here.
The tool:
  1. Shows recent untracked posts from the business's program.md posting log
  2. Lets you enter likes, comments, shares, reach per post
  3. Updates the Posting Log table in program.md with the data
  4. Runs pattern analysis: which angles consistently outperform?
  5. Auto-updates the "What's Working" section with data-backed findings
  6. Saves structured history to {business}/engagement_history.json

This is what turns ad_copy_optimizer.py from "smart guessing" into
"learning from what actually works for THIS business."

Usage:
  # Log engagement for recent posts (interactive):
  python engagement_logger.py sugar_shack
  python engagement_logger.py optimum_clinic

  # Quick add a single post directly:
  python engagement_logger.py optimum_clinic --add "Skip the ER" --likes 87 --comments 23 --shares 14

  # Just run pattern analysis (no prompts):
  python engagement_logger.py sugar_shack --analyze

  # View full engagement history:
  python engagement_logger.py juan --history

Businesses: sugar_shack | island_arcade | island_candy | juan |
            spi_fun_rentals | custom_designs_tx | optimum_clinic | optimum_foundation
"""

import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent

BUSINESS_DIRS = {
    "sugar_shack": EXECUTION_DIR / "sugar_shack",
    "island_arcade": EXECUTION_DIR / "island_arcade",
    "island_candy": EXECUTION_DIR / "island_candy",
    "juan": EXECUTION_DIR / "juan",
    "spi_fun_rentals": EXECUTION_DIR / "spi_fun_rentals",
    "custom_designs_tx": EXECUTION_DIR / "custom_designs_tx",
    "optimum_clinic": EXECUTION_DIR / "optimum_clinic",
    "optimum_foundation": EXECUTION_DIR / "optimum_foundation",
}

BUSINESS_NAMES = {
    "sugar_shack": "The Sugar Shack",
    "island_arcade": "Island Arcade",
    "island_candy": "Island Candy",
    "juan": "Juan Elizondo RE/MAX Elite",
    "spi_fun_rentals": "SPI Fun Rentals",
    "custom_designs_tx": "Custom Designs TX",
    "optimum_clinic": "Optimum Health & Wellness Clinic",
    "optimum_foundation": "Optimum Health and Wellness Foundation",
}

# Engagement threshold to flag as "high performer" in What's Working
HIGH_PERFORMER_THRESHOLD = 50  # total engagement score

# ─── Engagement Score ─────────────────────────────────────────────────────────

def engagement_score(entry: dict) -> float:
    """Weighted engagement score. Shares > comments > likes (reach is reach, not action)."""
    likes = entry.get("likes", 0) or 0
    comments = entry.get("comments", 0) or 0
    shares = entry.get("shares", 0) or 0
    reach = entry.get("reach", 0) or 0
    # Weighted: shares=3, comments=2, likes=1, reach=0.01
    return (likes * 1) + (comments * 2) + (shares * 3) + (reach * 0.01)


def format_engagement(entry: dict) -> str:
    """Format engagement for display in tables."""
    parts = []
    if entry.get("likes"):
        parts.append(f"{entry['likes']}L")
    if entry.get("comments"):
        parts.append(f"{entry['comments']}C")
    if entry.get("shares"):
        parts.append(f"{entry['shares']}S")
    if entry.get("reach"):
        parts.append(f"{entry['reach']}R")
    score = engagement_score(entry)
    label = " ".join(parts) if parts else "—"
    return f"{label} [score:{score:.0f}]"

# ─── History ──────────────────────────────────────────────────────────────────

def load_history(business_key: str) -> list:
    path = BUSINESS_DIRS[business_key] / "engagement_history.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_history(business_key: str, history: list):
    BUSINESS_DIRS[business_key].mkdir(parents=True, exist_ok=True)
    path = BUSINESS_DIRS[business_key] / "engagement_history.json"
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def add_to_history(business_key: str, angle: str, date_str: str, likes: int, comments: int, shares: int, reach: int, notes: str = ""):
    history = load_history(business_key)
    entry = {
        "date": date_str,
        "angle": angle,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "reach": reach,
        "score": engagement_score({"likes": likes, "comments": comments, "shares": shares, "reach": reach}),
        "notes": notes,
        "logged_at": datetime.now().isoformat(),
    }
    # Avoid duplicates: same angle + date
    existing = next((e for e in history if e["date"] == date_str and e["angle"].lower() == angle.lower()), None)
    if existing:
        existing.update(entry)
        print(f"  [Updated existing entry for {angle} on {date_str}]")
    else:
        history.append(entry)
    save_history(business_key, history)
    return entry

# ─── Pattern Analysis ─────────────────────────────────────────────────────────

def analyze_patterns(business_key: str) -> dict:
    """
    Groups history by angle, computes avg score.
    Returns: {angle: {count, avg_score, top_score, posts: [...]}}
    """
    history = load_history(business_key)
    if not history:
        return {}

    by_angle: dict = {}
    for entry in history:
        angle = entry.get("angle", "unknown")
        if angle not in by_angle:
            by_angle[angle] = []
        by_angle[angle].append(entry)

    analysis = {}
    for angle, posts in by_angle.items():
        scores = [p["score"] for p in posts]
        analysis[angle] = {
            "count": len(posts),
            "avg_score": sum(scores) / len(scores),
            "top_score": max(scores),
            "posts": posts,
        }

    return analysis


def print_analysis(business_key: str):
    analysis = analyze_patterns(business_key)
    if not analysis:
        print("  No engagement data logged yet for this business.")
        return

    name = BUSINESS_NAMES[business_key]
    print(f"\n=== Engagement Pattern Analysis: {name} ===")
    print(f"  {len(load_history(business_key))} posts logged\n")

    # Sort by avg score descending
    sorted_angles = sorted(analysis.items(), key=lambda x: x[1]["avg_score"], reverse=True)

    print(f"  {'Angle':<40} {'Posts':>5}  {'Avg Score':>9}  {'Top Score':>9}")
    print(f"  {'-'*40} {'-'*5}  {'-'*9}  {'-'*9}")
    for angle, stats in sorted_angles:
        flag = " <-- TOP" if stats["avg_score"] >= HIGH_PERFORMER_THRESHOLD else ""
        print(f"  {angle:<40} {stats['count']:>5}  {stats['avg_score']:>9.1f}  {stats['top_score']:>9.1f}{flag}")

    print()
    top = [a for a, s in sorted_angles if s["avg_score"] >= HIGH_PERFORMER_THRESHOLD and s["count"] >= 2]
    bottom = [a for a, s in sorted_angles if s["avg_score"] < 20 and s["count"] >= 2]

    if top:
        print("  What's Working (data-backed):")
        for angle in top:
            stats = analysis[angle]
            print(f"    - \"{angle}\" — avg score {stats['avg_score']:.0f} across {stats['count']} posts")
    if bottom:
        print("\n  Underperforming Angles (consider retiring or rewriting):")
        for angle in bottom:
            stats = analysis[angle]
            print(f"    - \"{angle}\" — avg score {stats['avg_score']:.0f} across {stats['count']} posts")
    print()
    return analysis

# ─── program.md Updater ───────────────────────────────────────────────────────

def update_whats_working(business_key: str, analysis: dict):
    """
    Auto-updates the 'What's Working' section in program.md
    with data-backed findings (only for angles with 2+ posts and high scores).
    """
    program_path = BUSINESS_DIRS[business_key] / "program.md"
    if not program_path.exists():
        return

    content = program_path.read_text(encoding="utf-8")

    top_angles = sorted(
        [(a, s) for a, s in analysis.items() if s["avg_score"] >= HIGH_PERFORMER_THRESHOLD and s["count"] >= 2],
        key=lambda x: x[1]["avg_score"],
        reverse=True,
    )

    if not top_angles:
        return  # Not enough data yet to auto-update

    # Build the data-backed lines
    new_lines = []
    for angle, stats in top_angles[:3]:  # Top 3 only
        new_lines.append(
            f'- **"{angle}"** — avg engagement score {stats["avg_score"]:.0f} across {stats["count"]} posts _(data-backed)_'
        )

    # Find the "## What's Working" section and insert after the header + blockquote
    # Pattern: after "## What's Working" line + optional "> ..." line
    pattern = r'(## What\'s Working\n(?:>.*\n)?)'

    # Remove old data-backed lines first (to avoid duplicates)
    content_clean = re.sub(
        r'- \*\*".*?"\*\* — avg engagement score.*?_\(data-backed\)_\n',
        "",
        content,
    )

    # Inject new data-backed lines
    replacement = r'\1' + "\n".join(new_lines) + "\n"
    new_content = re.sub(pattern, replacement, content_clean, count=1)

    if new_content != content:
        program_path.write_text(new_content, encoding="utf-8")
        print(f"  [program.md updated: What's Working section refreshed with {len(new_lines)} data-backed findings]")

# ─── Interactive Logger ───────────────────────────────────────────────────────

def prompt_int(label: str, default: int = 0) -> int:
    val = input(f"    {label} [{default}]: ").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def interactive_log(business_key: str):
    """Walk through recent posts without engagement and prompt for numbers."""
    name = BUSINESS_NAMES[business_key]
    history = load_history(business_key)

    print(f"\n=== Log Engagement: {name} ===")
    print("Enter engagement numbers for your recent posts.")
    print("Press Enter to skip a field (uses 0). Type 'done' to finish.\n")

    today = date.today().isoformat()
    logged_count = 0

    while True:
        print(f"  Post date [{today}]: ", end="")
        date_input = input().strip()
        if date_input.lower() in ("done", "q", "quit", "exit", ""):
            if date_input == "":
                date_input = today
            else:
                break

        post_date = date_input if date_input else today

        print(f"  Ad angle / post topic: ", end="")
        angle = input().strip()
        if not angle or angle.lower() in ("done", "q"):
            break

        likes = prompt_int("Likes")
        comments = prompt_int("Comments")
        shares = prompt_int("Shares")
        reach = prompt_int("Reach (people reached)")

        print(f"  Notes (optional): ", end="")
        notes = input().strip()

        entry = add_to_history(business_key, angle, post_date, likes, comments, shares, reach, notes)
        score = entry["score"]
        print(f"\n  Logged. Engagement score: {score:.0f}")

        if score >= HIGH_PERFORMER_THRESHOLD:
            print(f"  HIGH PERFORMER — this angle is working well.")
        elif score < 15:
            print(f"  Low engagement — consider a different angle next time.")

        logged_count += 1
        print()

        print("  Log another post? [Enter = yes, 'done' = finish]: ", end="")
        cont = input().strip().lower()
        if cont in ("done", "q", "no", "n"):
            break

    if logged_count > 0:
        print(f"\n[{logged_count} post(s) logged to {business_key}/engagement_history.json]")
        analysis = analyze_patterns(business_key)
        if analysis:
            print_analysis(business_key)
            update_whats_working(business_key, analysis)
    else:
        print("\n[No posts logged]")

# ─── Screenpipe OCR Auto-Capture (UC-6) ──────────────────────────────────────

_INSIGHTS_NUMBER_RE = re.compile(
    r'(?:(\d[\d,\.]*)\s*(?:people\s+reached|post\s+engagements?|engagements?|likes?|comments?|shares?|reactions?|reach|impressions))|'
    r'(?:(?:people\s+reached|post\s+engagements?|engagements?|likes?|comments?|shares?|reactions?|reach|impressions)\s*[:\-]?\s*(\d[\d,\.]*))',
    re.IGNORECASE,
)

_KEYWORD_TO_FIELD = {
    "likes": "likes", "like": "likes", "reactions": "likes",
    "comments": "comments", "comment": "comments",
    "shares": "shares", "share": "shares",
    "people reached": "reach", "reach": "reach", "post reach": "reach",
    "impressions": "reach",
}


def screenpipe_capture(business_key: str, minutes: int = 5) -> dict:
    """Query Screenpipe OCR for recent Facebook Insights engagement metrics.

    Returns dict with keys: likes, comments, shares, reach (all int, 0 if not found).
    Returns empty dict if Screenpipe unavailable or no data found.
    """
    try:
        sys.path.insert(0, str(EXECUTION_DIR))
        from screenpipe_verifier import screenpipe_healthy, screenpipe_search
    except ImportError:
        print("[screenpipe] screenpipe_verifier.py not found")
        return {}

    if not screenpipe_healthy():
        print("[screenpipe] Screenpipe not running")
        return {}

    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    name = BUSINESS_NAMES.get(business_key, business_key)
    print(f"[screenpipe] Searching OCR for {name} engagement data (last {minutes} min)...")

    search_terms = [name, "People reached", "Engagements", "Post reach"]
    all_texts = set()
    for term in search_terms:
        results = screenpipe_search(term, content_type="ocr", limit=20,
                                     start_time=start, end_time=end)
        for r in results:
            text = r.get("content", {}).get("text", "")
            if text:
                all_texts.add(text)

    if not all_texts:
        print("[screenpipe] No Insights-related OCR text found")
        return {}

    metrics = {"likes": 0, "comments": 0, "shares": 0, "reach": 0}
    found_any = False

    for text in all_texts:
        for match in _INSIGHTS_NUMBER_RE.finditer(text):
            number_str = match.group(1) or match.group(2)
            if not number_str:
                continue
            clean = number_str.replace(",", "").replace(".", "")
            try:
                value = int(clean)
            except ValueError:
                continue

            context = match.group(0).lower()
            for keyword, field in _KEYWORD_TO_FIELD.items():
                if keyword in context:
                    if value > metrics[field]:
                        metrics[field] = value
                        found_any = True
                    break

    if not found_any:
        print("[screenpipe] OCR text found but could not extract engagement numbers")
        print("[screenpipe] Run: python test_ocr_insights.py --dump  to debug")
        return {}

    print(f"[screenpipe] Captured: {metrics['likes']}L {metrics['comments']}C {metrics['shares']}S {metrics['reach']}R")
    return metrics


def screenpipe_log(business_key: str, angle: str = "", minutes: int = 5):
    """Auto-capture engagement from Screenpipe OCR and log it."""
    metrics = screenpipe_capture(business_key, minutes)
    if not metrics:
        print("[screenpipe] No metrics captured -- try manual entry instead")
        return

    if not angle:
        program = BUSINESS_DIRS[business_key] / "program.md"
        if program.exists():
            text = program.read_text(encoding="utf-8", errors="replace")
            in_log = False
            recent_angle = None
            for line in text.splitlines():
                if "## Posting Log" in line or "## posting log" in line.lower():
                    in_log = True
                    continue
                if in_log and line.startswith("##"):
                    break
                if in_log and "|" in line and line.strip().startswith("|"):
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 2 and len(parts[0]) >= 10 and parts[0][:4].isdigit():
                        recent_angle = parts[1]
            if recent_angle:
                angle = recent_angle
                print(f"[screenpipe] Auto-matched to most recent post: \"{angle}\"")

    if not angle:
        print("[screenpipe] Could not determine post angle -- provide with --add ANGLE")
        return

    today = date.today().isoformat()
    entry = add_to_history(
        business_key, angle, today,
        metrics["likes"], metrics["comments"],
        metrics["shares"], metrics["reach"],
        notes="auto-captured via Screenpipe OCR"
    )
    print(f"[screenpipe] Logged. Score: {entry['score']:.0f}")

    analysis = analyze_patterns(business_key)
    if analysis:
        update_whats_working(business_key, analysis)


# ─── Attention ↔ Engagement Correlation ──────────────────────────────────────

def correlate_attention_engagement(days_back: int = 7) -> dict:
    """Correlate Screenpipe client attention (screen time) with engagement scores.

    Returns: {
        "period_days": int,
        "clients": {
            client_key: {
                "name": str,
                "attention_mentions": int,
                "posts_count": int,
                "avg_engagement": float,
                "attention_rank": int,
                "engagement_rank": int,
                "correlation": "aligned" | "over-indexed" | "under-indexed" | "no-data"
            }
        },
        "insight": str  # one-line summary
    }
    """
    try:
        import urllib.request as _req
        from screenpipe_verifier import screenpipe_healthy, SCREENPIPE_BASE
    except ImportError:
        return {}
    if not screenpipe_healthy():
        return {}

    from datetime import timezone as _tz
    now = datetime.now(_tz.utc)
    start = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    end = now.strftime("%Y-%m-%dT23:59:59Z")

    # Gather screen attention per client from Screenpipe OCR
    search_terms = {
        "sugar_shack": "Sugar Shack",
        "island_arcade": "Island Arcade",
        "island_candy": "Island Candy",
        "juan": "Juan Elizondo",
        "spi_fun_rentals": "SPI Fun Rentals",
        "custom_designs_tx": "Custom Designs",
        "optimum_clinic": "Optimum",
        "optimum_foundation": "Optimum Foundation",
    }

    attention = {}
    for biz_key, term in search_terms.items():
        try:
            import urllib.parse as _parse
            params = _parse.urlencode({
                "q": term, "content_type": "ocr", "limit": "500",
                "start_time": start, "end_time": end,
            })
            resp = _req.urlopen(f"{SCREENPIPE_BASE}/search?{params}", timeout=10)
            data = json.loads(resp.read())
            attention[biz_key] = len(data.get("data", []))
        except Exception:
            attention[biz_key] = 0

    # Gather engagement per client from history (same period)
    cutoff = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
    engagement = {}
    for biz_key in BUSINESS_DIRS:
        history = load_history(biz_key)
        recent = [e for e in history if e.get("date", "") >= cutoff]
        if recent:
            avg = sum(e.get("score", 0) for e in recent) / len(recent)
            engagement[biz_key] = {"count": len(recent), "avg": avg}
        else:
            engagement[biz_key] = {"count": 0, "avg": 0}

    # Rank both dimensions
    attn_ranked = sorted(attention.items(), key=lambda x: -x[1])
    eng_ranked = sorted(engagement.items(), key=lambda x: -x[1]["avg"])
    attn_rank = {k: i + 1 for i, (k, _) in enumerate(attn_ranked)}
    eng_rank = {k: i + 1 for i, (k, _) in enumerate(eng_ranked)}

    clients = {}
    for biz_key in BUSINESS_DIRS:
        a_rank = attn_rank.get(biz_key, 8)
        e_rank = eng_rank.get(biz_key, 8)
        eng_data = engagement.get(biz_key, {"count": 0, "avg": 0})

        if eng_data["count"] == 0:
            corr = "no-data"
        elif abs(a_rank - e_rank) <= 2:
            corr = "aligned"
        elif a_rank < e_rank:
            corr = "over-indexed"   # lots of attention, low engagement
        else:
            corr = "under-indexed"  # low attention, high engagement

        clients[biz_key] = {
            "name": BUSINESS_NAMES.get(biz_key, biz_key),
            "attention_mentions": attention.get(biz_key, 0),
            "posts_count": eng_data["count"],
            "avg_engagement": round(eng_data["avg"], 1),
            "attention_rank": a_rank,
            "engagement_rank": e_rank,
            "correlation": corr,
        }

    # Build insight
    over = [c["name"] for c in clients.values() if c["correlation"] == "over-indexed"]
    under = [c["name"] for c in clients.values() if c["correlation"] == "under-indexed"]
    if over:
        insight = f"Over-indexed (high attention, low engagement): {', '.join(over)}. Consider changing content angles."
    elif under:
        insight = f"Under-indexed (low attention, high engagement): {', '.join(under)}. Double down on what's working."
    else:
        insight = "Attention and engagement are generally aligned across clients."

    return {
        "period_days": days_back,
        "clients": clients,
        "insight": insight,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Log post engagement and close the autoresearch feedback loop"
    )
    parser.add_argument(
        "business",
        choices=list(BUSINESS_DIRS.keys()),
        help="Which business to log engagement for",
    )
    parser.add_argument(
        "--add",
        metavar="ANGLE",
        help="Angle/topic name for a direct add (non-interactive)",
    )
    parser.add_argument("--date", default=date.today().isoformat(), help="Post date (YYYY-MM-DD)")
    parser.add_argument("--likes", type=int, default=0)
    parser.add_argument("--comments", type=int, default=0)
    parser.add_argument("--shares", type=int, default=0)
    parser.add_argument("--reach", type=int, default=0)
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run pattern analysis only (no prompts)",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show full engagement history for this business",
    )
    parser.add_argument(
        "--screenpipe",
        action="store_true",
        help="Auto-capture engagement from Screenpipe OCR (open FB Insights first)",
    )
    parser.add_argument(
        "--screenpipe-minutes",
        type=int, default=5,
        help="How far back Screenpipe should search (default: 5 min)",
    )
    parser.add_argument(
        "--correlate",
        action="store_true",
        help="Run attention ↔ engagement correlation analysis (requires Screenpipe)",
    )
    parser.add_argument(
        "--correlate-days",
        type=int, default=7,
        help="Days to look back for correlation analysis (default: 7)",
    )
    args = parser.parse_args()

    if args.correlate:
        result = correlate_attention_engagement(days_back=args.correlate_days)
        if not result:
            print("Correlation unavailable (Screenpipe not running or no data).")
            return
        print(f"\n=== Attention ↔ Engagement Correlation ({result['period_days']}d) ===\n")
        print(f"{'Client':<30} {'Attention':>9} {'Posts':>5} {'Avg Eng':>8} {'A-Rank':>6} {'E-Rank':>6} {'Status':<15}")
        print("-" * 90)
        for biz_key, c in sorted(result["clients"].items(), key=lambda x: x[1]["attention_rank"]):
            print(f"{c['name']:<30} {c['attention_mentions']:>9} {c['posts_count']:>5} "
                  f"{c['avg_engagement']:>8.1f} {c['attention_rank']:>6} {c['engagement_rank']:>6} {c['correlation']:<15}")
        print(f"\nInsight: {result['insight']}")
        return

    if args.screenpipe:
        angle = args.add or ""
        screenpipe_log(args.business, angle=angle, minutes=args.screenpipe_minutes)
        return

    if args.history:
        history = load_history(args.business)
        if not history:
            print(f"No history yet for {args.business}.")
            return
        print(f"\n=== Engagement History: {BUSINESS_NAMES[args.business]} ===")
        print(f"{'Date':<12} {'Angle':<40} {'Likes':>5} {'Cmts':>5} {'Shrs':>5} {'Reach':>6} {'Score':>6}")
        print("-" * 85)
        for e in sorted(history, key=lambda x: x.get("date", ""), reverse=True):
            print(
                f"{e.get('date','?'):<12} {e.get('angle','?')[:40]:<40} "
                f"{e.get('likes',0):>5} {e.get('comments',0):>5} "
                f"{e.get('shares',0):>5} {e.get('reach',0):>6} "
                f"{e.get('score',0):>6.0f}"
            )
        return

    if args.analyze:
        analysis = analyze_patterns(args.business)
        if analysis:
            print_analysis(args.business)
            update_whats_working(args.business, analysis)
        else:
            print(f"No engagement data logged yet for {args.business}.")
        return

    if args.add:
        entry = add_to_history(
            args.business, args.add, args.date,
            args.likes, args.comments, args.shares, args.reach, args.notes
        )
        print(f"Logged: {args.add} | Score: {entry['score']:.0f}")
        analysis = analyze_patterns(args.business)
        if analysis:
            update_whats_working(args.business, analysis)
        return

    # Default: interactive
    interactive_log(args.business)


if __name__ == "__main__":
    main()
