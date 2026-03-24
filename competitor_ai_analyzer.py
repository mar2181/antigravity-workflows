#!/usr/bin/env python3
"""
competitor_ai_analyzer.py — AI-powered analysis of competitor social activity.

Reads the latest competitor Facebook posts + Ad Library data and calls
OpenRouter (gpt-4o-mini) to produce per-client strategic analysis:
  - What themes/angles competitors are pushing this week
  - Which posts got high engagement (and why)
  - Competitor weaknesses visible in their content
  - 3 specific counter-angles for each client to use in their next ads

Cost: ~$0.001 per run (gpt-4o-mini, ~5-8K tokens total). Essentially free.

Usage:
    python competitor_ai_analyzer.py                          # all businesses
    python competitor_ai_analyzer.py --business island_candy  # one business
    python competitor_ai_analyzer.py --dry-run                # show prompts only

Output:
    competitor_reports/ai_analysis_YYYY-MM-DD.md
    competitor_reports/ai_analysis_YYYY-MM-DD.json
"""

import sys
import json
import os
import urllib.request
import urllib.parse
import argparse
from pathlib import Path
from datetime import date, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR  = Path(__file__).parent
REPORTS_DIR    = EXECUTION_DIR / "competitor_reports"
SCRATCH_DIR    = EXECUTION_DIR.parent.parent / "scratch"
ENV_PATH       = SCRATCH_DIR / "gravity-claw" / ".env"

# ─── Config ───────────────────────────────────────────────────────────────────

OPENROUTER_MODEL = "openai/gpt-4o-mini"

BUSINESS_PROFILES = {
    "sugar_shack": {
        "our_name":   "The Sugar Shack",
        "what_we_do": "Candy store at South Padre Island TX. Biggest candy selection on the island. Target: spring break families, tourists, kids.",
        "edge":       "Largest variety, novelty/experience factor, Instagram-worthy displays.",
    },
    "island_candy": {
        "our_name":   "Island Candy",
        "what_we_do": "Ice cream, candy, and sweets inside Island Arcade on South Padre Island. Target: families, content creators, beach tourists.",
        "edge":       "Unique location inside an arcade, Instagram moments, dole whip and specialty items.",
    },
    "island_arcade": {
        "our_name":   "Island Arcade",
        "what_we_do": "Arcade + games at South Padre Island. Only arcade on the island. Target: families with kids, spring break groups.",
        "edge":       "Only arcade on SPI — no direct competition.",
    },
    "spi_fun_rentals": {
        "our_name":   "SPI Fun Rentals",
        "what_we_do": "Water sports and beach rentals at South Padre Island. Jet skis, kayaks, paddleboards, more. Target: tourists, adventure seekers.",
        "edge":       "Widest menu of water activities, multiple rental types in one place.",
    },
    "juan": {
        "our_name":   "Juan Elizondo RE/MAX Elite",
        "what_we_do": "Real estate agent in Rio Grande Valley TX. Residential + commercial. Also markets to Mexican investors for US properties.",
        "edge":       "Bilingual, local expertise, investor network, commercial & residential.",
    },
    "custom_designs_tx": {
        "our_name":   "Custom Designs TX",
        "what_we_do": "Security cameras, alarms, home theater, audio/video, cable systems. McAllen TX, all of Hidalgo and Cameron County.",
        "edge":       "Full-service installation, B2B and B2C, local trusted brand.",
    },
    "optimum_clinic": {
        "our_name":   "Optimum Health & Wellness Clinic",
        "what_we_do": "Cash-pay night clinic in RGV. Open evenings when other clinics are closed. No insurance needed. Urgent care + wellness.",
        "edge":       "Open late, no insurance, fast in/out, affordable cash prices.",
    },
    "optimum_foundation": {
        "our_name":   "Optimum Health & Wellness Foundation",
        "what_we_do": "Non-profit health foundation in RGV providing community wellness programs.",
        "edge":       "Community trust, free/low-cost services, local impact.",
    },
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _load_env(path: Path) -> dict:
    env = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


def _call_openrouter(prompt: str, system: str, api_key: str) -> str:
    """Call OpenRouter gpt-4o-mini and return the text response."""
    payload = json.dumps({
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 1200,
        "temperature": 0.4,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://antigravity.local",
            "X-Title":       "Antigravity Competitor Analyzer",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        return f"[API ERROR {e.code}: {err[:300]}]"
    except Exception as e:
        return f"[ERROR: {e}]"


def load_latest_json(pattern: str) -> dict:
    """Load the most recent JSON report matching a glob pattern."""
    today_str = date.today().strftime("%Y-%m-%d")
    today_file = REPORTS_DIR / pattern.replace("*", today_str)
    candidates = [today_file] + sorted(REPORTS_DIR.glob(pattern), reverse=True)
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


# ─── Pre-Processing Intelligence ──────────────────────────────────────────────

def detect_winning_posts(fb_data: list) -> list:
    """
    Find posts with significantly higher engagement than the competitor's average.
    A post is a 'winner' if its engagement is 2x+ the competitor's mean engagement.
    Returns list of dicts: {competitor, post_excerpt, engagement, avg_engagement, multiple}
    """
    winners = []
    for comp in fb_data:
        name  = comp.get("name", "?")
        posts = comp.get("recent_posts", [])
        if not posts or not isinstance(posts[0], dict):
            continue

        engagements = []
        for p in posts:
            eng = p.get("likes", 0) + p.get("comments", 0) + p.get("shares", 0)
            engagements.append((eng, p.get("excerpt", "")))

        if len(engagements) < 2:
            continue

        values = [e[0] for e in engagements]
        avg    = sum(values) / len(values)
        if avg == 0:
            continue

        for eng, excerpt in engagements:
            multiple = eng / avg
            if multiple >= 2.0 and eng > 5:  # at least 2x average AND real engagement
                winners.append({
                    "competitor":      name,
                    "post_excerpt":    str(excerpt)[:200],
                    "engagement":      eng,
                    "avg_engagement":  round(avg, 1),
                    "multiple":        round(multiple, 1),
                })

    return sorted(winners, key=lambda x: x["multiple"], reverse=True)


def detect_trending_topics(fb_data: list) -> list:
    """
    Count keyword frequency across ALL competitor posts for the week.
    If 2+ competitors post about the same topic keyword, it's a trend.
    Returns list of (keyword, count, competitors_using_it).
    """
    import re as _re

    # Topic keywords to track — common marketing themes
    TOPIC_KEYWORDS = [
        "spring break", "easter", "spring", "summer", "holiday", "weekend",
        "discount", "sale", "off", "deal", "free", "special", "promo",
        "new", "grand opening", "open now", "hiring", "now hiring",
        "family", "kids", "couples", "groups",
        "open house", "sold", "listing", "price",
        "happy hour", "limited time", "last chance",
        "delivery", "pickup", "order online",
    ]

    keyword_hits: dict[str, set] = {}

    for comp in fb_data:
        name  = comp.get("name", "?")
        posts = comp.get("recent_posts", [])
        all_text = ""
        for p in posts:
            excerpt = p.get("excerpt", p) if isinstance(p, dict) else str(p)
            all_text += str(excerpt).lower() + " "

        for kw in TOPIC_KEYWORDS:
            if kw in all_text:
                keyword_hits.setdefault(kw, set()).add(name)

    trends = [
        (kw, len(comps), sorted(comps))
        for kw, comps in keyword_hits.items()
        if len(comps) >= 2
    ]
    return sorted(trends, key=lambda x: x[1], reverse=True)


# ─── Per-Business Analysis ────────────────────────────────────────────────────

def build_prompt(business_key: str, fb_data: list, adlib_data: dict,
                 winners: list = None, trends: list = None) -> str:
    """Build the analysis prompt for one business."""
    profile = BUSINESS_PROFILES.get(business_key, {})
    our_name = profile.get("our_name", business_key)
    what_we_do = profile.get("what_we_do", "")
    edge = profile.get("edge", "")

    # Gather competitor posts
    post_sections = []
    for comp in fb_data:
        name = comp.get("name", "Unknown")
        posts = comp.get("recent_posts", [])
        followers = comp.get("followers")
        posts_7d = comp.get("posts_last_7d", 0)

        section = [f"## Competitor: {name}"]
        if followers:
            section.append(f"Followers: {followers}")
        section.append(f"Posts in last 7 days: {posts_7d}")

        if posts:
            section.append("Recent posts:")
            for p in posts[:4]:
                excerpt = p.get("excerpt", p) if isinstance(p, dict) else str(p)
                likes = p.get("likes", 0) if isinstance(p, dict) else 0
                comments = p.get("comments", 0) if isinstance(p, dict) else 0
                shares = p.get("shares", 0) if isinstance(p, dict) else 0
                engagement = likes + comments + shares
                section.append(f"  - [{engagement} eng] {str(excerpt)[:200]}")
        else:
            section.append("  (no recent posts scraped)")

        post_sections.append("\n".join(section))

    # Gather ad library intel for this business
    ad_intel = []
    if adlib_data and business_key in adlib_data:
        for comp in adlib_data[business_key].get("competitors", []):
            name = comp.get("name", "")
            if comp.get("no_ads"):
                ad_intel.append(f"- {name}: ZERO paid ads running (gone dark)")
            elif comp.get("active_ad_count", 0) > 0:
                ad_intel.append(f"- {name}: {comp['active_ad_count']} active paid ads")
                for ad in comp.get("ads", [])[:2]:
                    ad_intel.append(f"  Ad copy: {ad['copy'][:150]}")

    # Winning posts section
    winners_text = ""
    if winners:
        lines = ["WINNING POSTS (2x+ avg engagement — proven content):"]
        for w in winners[:3]:
            lines.append(f"  - {w['competitor']}: {w['engagement']} eng ({w['multiple']}x their avg) → \"{w['post_excerpt'][:150]}\"")
        winners_text = "\n".join(lines)

    # Cross-competitor trending topics
    trends_text = ""
    if trends:
        lines = ["TRENDING TOPICS (2+ competitors posting about same thing):"]
        for kw, count, comps in trends[:5]:
            lines.append(f"  - \"{kw}\" — {count} competitors ({', '.join(comps[:3])})")
        trends_text = "\n".join(lines)

    prompt = f"""You are a sharp digital marketing strategist. Analyze the Facebook activity of competitors for a local business and provide actionable insights.

OUR BUSINESS: {our_name}
WHAT WE DO: {what_we_do}
OUR COMPETITIVE EDGE: {edge}

COMPETITOR FACEBOOK ACTIVITY (last 7 days):
{chr(10).join(post_sections) if post_sections else 'No competitor post data available.'}

PAID AD STATUS (Facebook Ad Library):
{chr(10).join(ad_intel) if ad_intel else 'No paid ad data available.'}
{(chr(10) + winners_text) if winners_text else ''}
{(chr(10) + trends_text) if trends_text else ''}

Provide a concise analysis with these exact sections:

**THEMES THIS WEEK**
(What are competitors posting about? Include any trending topics across multiple competitors. 2-3 bullet points)

**WINNING CONTENT**
(Which posts/angles got the most engagement and why? If winning posts are listed above, explain what made them work. 2-3 bullet points)

**COMPETITOR WEAKNESSES**
(What gaps, blind spots, or weaknesses do you see? 2-3 bullet points)

**3 COUNTER-ANGLES FOR {our_name.upper()}**
(Specific ad copy angles to run THIS WEEK. If competitors are trending on a topic, either counter-position or outdo them. Give actual headline/hook text.)
1.
2.
3.

Keep the entire response under 450 words. Be direct and actionable — no fluff."""

    return prompt


def analyze_business(business_key: str, fb_data: list, adlib_data: dict, api_key: str, dry_run: bool) -> dict:
    """Run AI analysis for one business. Returns structured result."""
    profile = BUSINESS_PROFILES.get(business_key, {})
    our_name = profile.get("our_name", business_key)

    # Filter out competitors with no data
    comps_with_data = [c for c in fb_data if c.get("recent_posts") or c.get("posts_last_7d", 0) > 0]

    if not comps_with_data and not (adlib_data and business_key in adlib_data):
        return {
            "our_name":    our_name,
            "business":    business_key,
            "status":      "no_data",
            "analysis":    "No competitor data available for this business.",
            "prompt_used": "",
        }

    # Pre-process: detect winning posts and trending topics before calling AI
    winners = detect_winning_posts(fb_data)
    trends  = detect_trending_topics(fb_data)

    if winners:
        log(f"  Winning posts detected: {len(winners)} ({', '.join(w['competitor'] for w in winners[:2])})")
    if trends:
        log(f"  Trending topics: {', '.join(t[0] for t in trends[:3])}")

    prompt = build_prompt(business_key, fb_data, adlib_data, winners=winners, trends=trends)

    if dry_run:
        log(f"  DRY RUN — prompt for {our_name} ({len(prompt)} chars):")
        print(prompt[:500] + "...\n")
        return {
            "our_name": our_name,
            "business": business_key,
            "status":   "dry_run",
            "analysis": "[dry run]",
        }

    log(f"  Calling {OPENROUTER_MODEL} for {our_name}...")
    system = (
        "You are a concise, direct marketing strategist. "
        "Give practical, specific advice. No generic marketing speak. "
        "Focus on what a small business can act on TODAY."
    )
    analysis = _call_openrouter(prompt, system, api_key)
    log(f"  Done ({len(analysis)} chars)")

    return {
        "our_name":      our_name,
        "business":      business_key,
        "status":        "ok",
        "analysis":      analysis,
        "winning_posts": winners,
        "trends":        [{"keyword": t[0], "count": t[1], "competitors": t[2]} for t in trends],
    }


# ─── Report Generation ────────────────────────────────────────────────────────

def generate_report(results: list, date_str: str) -> Path:
    """Write the AI analysis to markdown + JSON."""
    md_path   = REPORTS_DIR / f"ai_analysis_{date_str}.md"
    json_path = REPORTS_DIR / f"ai_analysis_{date_str}.json"

    lines = [
        f"# Competitor AI Analysis — {date_str}",
        "",
        f"> Generated by gpt-4o-mini via OpenRouter. Based on latest competitor Facebook posts + Ad Library data.",
        f"> Use these angles in your next ad session — they're calibrated against what competitors are doing RIGHT NOW.",
        "",
        "---",
        "",
    ]

    for r in results:
        if r.get("status") == "no_data":
            continue
        lines += [
            f"## {r['our_name']}",
            "",
            r.get("analysis", "[no analysis]"),
            "",
            "---",
            "",
        ]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    log(f"Analysis saved → {md_path}")
    return md_path


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI analysis of competitor social data")
    parser.add_argument("--business", help="Run for one business only")
    parser.add_argument("--dry-run",  action="store_true", help="Print prompts, don't call API")
    args = parser.parse_args()

    # Load API key
    env = _load_env(ENV_PATH)
    api_key = env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: OPENROUTER_API_KEY not found in gravity-claw/.env")
        sys.exit(1)

    # Load data
    fb_data     = load_latest_json("facebook_*.json")
    adlib_data  = load_latest_json("adlibrary_*.json")

    if not fb_data:
        print("No Facebook competitor data found.")
        print("Run: python competitor_facebook_monitor.py")
        sys.exit(1)

    log(f"FB data: {sum(len(v) for v in fb_data.values())} competitors across {len(fb_data)} businesses")
    log(f"Ad Library data: {'loaded' if adlib_data else 'not found (run competitor_fb_adlibrary.py)'}")

    # Filter to requested business
    businesses = (
        [args.business] if args.business and args.business in fb_data
        else list(fb_data.keys())
    )

    date_str = date.today().strftime("%Y-%m-%d")
    results  = []

    for biz_key in businesses:
        log(f"\nAnalyzing: {BUSINESS_PROFILES.get(biz_key, {}).get('our_name', biz_key)}")
        result = analyze_business(
            business_key=biz_key,
            fb_data=fb_data.get(biz_key, []),
            adlib_data=adlib_data,
            api_key=api_key,
            dry_run=args.dry_run,
        )
        results.append(result)

        if not args.dry_run:
            # Print analysis inline so you see it as it runs
            print(f"\n{'─'*60}")
            print(f"  {result['our_name']}")
            print(f"{'─'*60}")
            print(result.get("analysis", ""))

    if not args.dry_run:
        md_path = generate_report(results, date_str)
        print(f"\n{'='*60}")
        print(f"Full report: {md_path}")

    return results


if __name__ == "__main__":
    main()
