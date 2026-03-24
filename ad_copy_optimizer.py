#!/usr/bin/env python3
"""
ad_copy_optimizer.py — Autoresearch loop for Facebook ad copy.

Applies the same pattern as skill_improver.py, but for ad copy:
  1. Read program.md for current priorities, offer, and audience
  2. Generate initial copy (or accept existing copy via --copy)
  3. Score it 0-100 across 4 dimensions (Hook, Offer, CTA, Voice Match)
  4. Rewrite targeting the weakest dimension — 3 iterations max
  5. Keep only if score improves (autoresearch rule)
  6. Save the winning copy to {business}/ad_copy_{timestamp}.md

Usage:
  python ad_copy_optimizer.py sugar_shack
  python ad_copy_optimizer.py sugar_shack --angle "road trip families"
  python ad_copy_optimizer.py juan --language es
  python ad_copy_optimizer.py island_candy --copy "Your existing copy here"
  python ad_copy_optimizer.py island_arcade --iterations 5
  python ad_copy_optimizer.py sugar_shack --dry-run   (score only, no rewrite)

Businesses: sugar_shack | island_arcade | island_candy | juan
"""

import sys
import json
import os
import argparse
import re
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import anthropic

# ─── Business Config ──────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent
SKILL_BASE = Path("C:/Users/mario/.gemini/antigravity/scratch/skills")
CONFIG_PATH = Path("C:/Users/mario/.gemini/antigravity/scratch/jack_automations_vault/skill_improver_config.json")

BUSINESSES = {
    "sugar_shack": {
        "name": "The Sugar Shack",
        "type": "candy store",
        "location": "South Padre Island, TX",
        "page_key": "sugar_shack",
        "skill_id": "sugar-shack-facebook",
        "voice": "Warm, playful, colorful, family-focused, high-energy. Speaks to spring break families and road trippers.",
        "audience": "Spring break families with kids, young groups, local SPI visitors",
        "rules": [
            "Max 3 hashtags",
            "Max 300 words",
            "No text overlays in images",
            "Testimonials: Variant B only (no verified reviews on file)",
        ],
    },
    "island_arcade": {
        "name": "Island Arcade",
        "type": "arcade and games",
        "location": "South Padre Island, TX",
        "page_key": "island_arcade",
        "skill_id": "island-arcade-facebook",
        "voice": "Energetic, competitive, family-inclusive, nostalgic for retro gamers, exciting for first-timers.",
        "audience": "Spring break families, college groups, couples, locals, people escaping beach heat or rain",
        "rules": [
            "Max 3 hashtags",
            "Max 300 words",
            "No text overlays in images",
            "Rainy day posts perform well — lean into indoor fun angle",
        ],
    },
    "island_candy": {
        "name": "Island Candy",
        "type": "ice cream and candy shop (inside Island Arcade)",
        "location": "South Padre Island, TX",
        "page_key": "island_candy",
        "skill_id": "island-candy-facebook",
        "voice": "Sweet, playful, colorful, indulgent. 'You deserve this' energy. Instagram-worthy.",
        "audience": "Families at Island Arcade, SPI visitors, content creators, late-night dessert seekers",
        "rules": [
            "Max 3 hashtags",
            "Max 300 words",
            "No text overlays in images",
            "Heat/sun relief angle works very well in summer",
        ],
    },
    "juan": {
        "name": "Juan Jose Elizondo — RE/MAX Elite",
        "type": "real estate agent",
        "location": "Rio Grande Valley, TX",
        "page_key": "juan",
        "skill_id": "juan-elizondo-remax-elite-facebook",
        "voice": "Professional, data-driven, bilingual (EN/ES). Trustworthy expert, not pushy. Warm but authoritative.",
        "audience": "RGV homebuyers, sellers, investors, first-time buyers, bilingual Spanish-speaking community",
        "rules": [
            "Max 3 hashtags",
            "Max 300 words",
            "No text overlays in images",
            "Bilingual posts perform strongly with organic RGV audience",
            "No ROI/appreciation claims without citing a source",
            "Only real verified testimonials — no aspirational testimonials",
        ],
    },
    "spi_fun_rentals": {
        "name": "SPI Fun Rentals",
        "type": "beach vehicle and water sports rentals",
        "location": "South Padre Island, TX",
        "page_key": "spi",
        "skill_id": "spi-fun-rentals-facebook",
        "voice": "Fun, adventurous, island-life energy. 'Your vacation starts the moment you rent from us.' Upbeat, laid-back — not corporate.",
        "audience": "Spring breakers wanting freedom, families wanting convenience, couples wanting a memorable SPI experience, groups looking for things to do",
        "rules": [
            "Max 3 hashtags",
            "Max 300 words",
            "No text overlays in images",
            "Golf carts are the most popular product — lead with them for spring break",
            "Scarcity/availability angle works well: 'Only X carts left this weekend'",
            "Testimonials: only real verified reviews — flag as aspirational if unavailable",
        ],
    },
    "custom_designs_tx": {
        "name": "Custom Designs TX",
        "type": "home technology, security, and smart home installation",
        "location": "McAllen, TX (Rio Grande Valley) and Houston",
        "page_key": "custom_designs",
        "skill_id": None,  # No Facebook skill yet — page URL needs to be confirmed first
        "voice": "Premium, confident, technical-but-accessible. 'We transform spaces.' Sophisticated and aspirational — like a luxury concierge, not a handyman.",
        "audience": "RGV homeowners earning $150k+ building or renovating, business owners wanting commercial security or display tech, high-end builders and contractors",
        "rules": [
            "Max 3 hashtags",
            "Max 300 words",
            "No text overlays in images",
            "Always luxury-tier language — never sound like a generic electrician",
            "No price guarantees or ROI claims without sourcing",
            "NOTE: Facebook page URL not yet confirmed — do not post until verified",
        ],
    },
    "optimum_clinic": {
        "name": "Optimum Health & Wellness Clinic",
        "type": "cash-pay walk-in night clinic",
        "location": "3912 N Jackson Rd, Pharr, TX 78577 (serves all RGV)",
        "page_key": "optimum_clinic",
        "skill_id": "optimum-clinic-facebook",
        "voice": "Urgent, accessible, and trustworthy. Speaks to families who need help NOW and can't afford the ER. Fully bilingual. Warm but direct — 'We're open when no one else is.'",
        "audience": "RGV families without insurance, cost-conscious patients avoiding ER bills, Spanish-speaking community, working adults needing after-hours care",
        "rules": [
            "Max 3 hashtags",
            "Max 300 words",
            "No text overlays in images",
            "Core offer must appear in every ad: 'Walk in tonight — no appointment, no insurance needed'",
            "Always use price RANGES — '$75 – $100' not '$75' — or 'starting at $X'",
            "NO treatment guarantees or cure claims — ever",
            "NO absolute superlatives ('best,' 'only') without documentation",
            "Testimonials: Variant B aspirational language only — no verified reviews on file yet",
            "Bilingual: post English version first, Spanish as a separate post same or next day",
        ],
    },
    "optimum_foundation": {
        "name": "Optimum Health and Wellness Foundation",
        "type": "501(c)(3) nonprofit community health organization",
        "location": "Pharr, TX / Rio Grande Valley",
        "page_key": "optimum_foundation",
        "skill_id": "optimum-foundation-facebook",
        "voice": "Mission-driven, community-first, warm and hopeful. 'Together we build a healthier RGV.' Uses 'your neighbors' and 'your community' language. Never clinical — always human.",
        "audience": "RGV community members, individual donors, volunteers, local businesses and employers, parents concerned about community health",
        "rules": [
            "Max 3 hashtags",
            "Max 300 words",
            "No text overlays in images",
            "Every post must have a CTA: Donate / Volunteer / Share / Register / Learn more",
            "NEVER include medical service offers or pricing — wrong entity",
            "Include EIN in any donation-request post (confirm EIN number from owner first)",
            "Lead with community impact — not organization features",
            "Testimonials: Variant B only — 'Families across the RGV benefit from...'",
            "NOTE: Facebook page URL PENDING — confirm with owner before any posting",
        ],
    },
}

# ─── Models ───────────────────────────────────────────────────────────────────

SCORE_MODEL = "claude-haiku-4-5-20251001"
WRITE_MODEL = "claude-sonnet-4-6"

# ─── Prompts ──────────────────────────────────────────────────────────────────

GENERATE_PROMPT = """You are a Facebook ad copywriter for {business_name} ({business_type}) in {location}.

BRAND VOICE: {voice}
TARGET AUDIENCE: {audience}

CURRENT CONTEXT (from program.md):
{program_context}

RULES:
{rules}

Write ONE Facebook ad post for this business. The angle is: {angle}

Requirements:
- Post text only (no image description)
- Natural, human — not corporate
- Max 300 words
- Max 3 hashtags (or fewer if they feel forced)
- Include the offer naturally if one is active

Output ONLY the post text. No labels, no explanation."""

SCORE_PROMPT = """You are a Facebook ad performance expert scoring copy for {business_name}.

BRAND VOICE: {voice}
TARGET AUDIENCE: {audience}
LANGUAGE REQUIREMENT: {language_note}

Score this Facebook ad copy on EXACTLY these 4 dimensions, 0-25 each (total 0-100):

1. HOOK (0-25)
   - The first 1-2 lines stop scrolling and create immediate desire or curiosity
   - Specific and concrete — not "Come visit us!" but a compelling reason to stop
   - Works for the specific audience of this business

2. OFFER CLARITY (0-25)
   - The value proposition or deal is crystal clear within 3 seconds
   - Reader knows exactly what they get and how to get it
   - Specific beats vague ("50% off gummies this weekend" beats "great deals")

3. CTA SHARPNESS (0-25)
   - Exactly ONE clear action is requested (not three)
   - Has urgency or a reason to act now (limited time, event, season)
   - The action is frictionless — easy to do immediately

4. VOICE MATCH (0-25)
   - Sounds like THIS specific business, not a generic local business template
   - Tone matches the brand voice exactly
   - Feels written by a real person who loves this business — not marketing copy

---

AD COPY TO SCORE:
{copy}

---

Respond with ONLY this JSON (no markdown, no explanation):
{{
  "hook": <0-25>,
  "offer_clarity": <0-25>,
  "cta_sharpness": <0-25>,
  "voice_match": <0-25>,
  "total": <sum>,
  "weakest_dimension": "<hook|offer_clarity|cta_sharpness|voice_match>",
  "key_problem": "<one sentence describing the single most impactful fix>"
}}"""

REWRITE_PROMPT = """You are a Facebook ad copywriter improving copy for {business_name}.

BRAND VOICE: {voice}
TARGET AUDIENCE: {audience}
LANGUAGE: {language_note}

RULES:
{rules}

This copy scored {score}/100. Its main weakness: {key_problem}
Weakest dimension: {weakest_dimension}

Fix ONLY the weakest dimension. Keep everything that already works.

ORIGINAL COPY:
{copy}

Output ONLY the improved copy. No labels, no explanation, no "Here's the improved version:"."""

# ─── API Key ──────────────────────────────────────────────────────────────────

def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        key = cfg.get("anthropic_api_key", "")
        if key:
            return key
    print("\n[ad_copy_optimizer] No API key found.")
    print("Set ANTHROPIC_API_KEY or add it to skill_improver_config.json")
    sys.exit(1)

# ─── program.md Reader ────────────────────────────────────────────────────────

def read_program_context(business_key: str) -> str:
    """Extract current priorities, offer, and audience from program.md."""
    program_path = EXECUTION_DIR / business_key / "program.md"
    if not program_path.exists():
        return "(no program.md found — using defaults)"

    content = program_path.read_text(encoding="utf-8", errors="replace")

    # Extract the Current Priorities section
    priorities_match = re.search(
        r"## Current Priorities.*?(?=\n## |\Z)", content, re.DOTALL
    )
    priorities = priorities_match.group(0) if priorities_match else ""

    # Extract Active Listings for Juan
    listings_match = re.search(
        r"## Active Listings.*?(?=\n## |\Z)", content, re.DOTALL
    )
    listings = listings_match.group(0) if listings_match else ""

    # Extract What's Working
    working_match = re.search(
        r"## What's Working.*?(?=\n## |\Z)", content, re.DOTALL
    )
    working = working_match.group(0) if working_match else ""

    context_parts = [p for p in [priorities, listings, working] if p.strip()]
    context = "\n\n".join(context_parts) if context_parts else content[:800]

    # Strip uncompleted checkboxes noise for cleaner context
    context = re.sub(r"- \[ \] \*\*.*?\*\*: _\(fill in.*?\)_\n?", "", context)
    context = context.strip()

    return context if context else "(program.md exists but Current Priorities not yet filled in)"

# ─── Scorer ───────────────────────────────────────────────────────────────────

def score_copy(client: anthropic.Anthropic, copy: str, biz: dict, language_note: str) -> dict:
    prompt = SCORE_PROMPT.format(
        business_name=biz["name"],
        voice=biz["voice"],
        audience=biz["audience"],
        language_note=language_note,
        copy=copy,
    )
    response = client.messages.create(
        model=SCORE_MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw)
    result["total"] = result["hook"] + result["offer_clarity"] + result["cta_sharpness"] + result["voice_match"]
    return result

# ─── Generator ────────────────────────────────────────────────────────────────

def generate_copy(client: anthropic.Anthropic, biz: dict, program_context: str, angle: str, language_note: str) -> str:
    rules_str = "\n".join(f"- {r}" for r in biz["rules"])
    prompt = GENERATE_PROMPT.format(
        business_name=biz["name"],
        business_type=biz["type"],
        location=biz["location"],
        voice=biz["voice"],
        audience=biz["audience"],
        program_context=program_context,
        rules=rules_str,
        angle=angle,
    )
    if language_note and "spanish" in language_note.lower():
        prompt += "\n\nWRITE IN SPANISH."

    response = client.messages.create(
        model=WRITE_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()

# ─── Rewriter ─────────────────────────────────────────────────────────────────

def rewrite_copy(client: anthropic.Anthropic, copy: str, biz: dict, score_result: dict, language_note: str) -> str:
    rules_str = "\n".join(f"- {r}" for r in biz["rules"])
    prompt = REWRITE_PROMPT.format(
        business_name=biz["name"],
        voice=biz["voice"],
        audience=biz["audience"],
        language_note=language_note,
        rules=rules_str,
        score=score_result["total"],
        key_problem=score_result["key_problem"],
        weakest_dimension=score_result["weakest_dimension"],
        copy=copy,
    )
    response = client.messages.create(
        model=WRITE_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()

# ─── Save Output ──────────────────────────────────────────────────────────────

def save_result(business_key: str, copy: str, iterations: list[dict], angle: str):
    output_dir = EXECUTION_DIR / business_key
    output_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"ad_copy_{ts}.md"

    baseline = iterations[0]["score"]
    best = max(it["score"] for it in iterations)

    lines = [
        f"# Ad Copy — {business_key} — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n",
        f"**Angle:** {angle}\n",
        f"**Score:** {baseline} → {best}/100 (+{best - baseline})\n\n",
        f"---\n\n",
        f"## Winning Copy\n\n",
        copy,
        f"\n\n---\n\n",
        f"## Iteration Log\n\n",
        f"| Iter | Score | Hook | Offer | CTA | Voice | Key Problem |\n",
        f"|------|-------|------|-------|-----|-------|-------------|\n",
    ]
    for it in iterations:
        s = it["scores"]
        lines.append(
            f"| {it['iteration']} | {it['score']} | {s['hook']} | {s['offer_clarity']} | "
            f"{s['cta_sharpness']} | {s['voice_match']} | {s.get('key_problem','')[:55]} |\n"
        )
    lines.append(f"\n*Generated by ad_copy_optimizer.py — ready to paste into fb_campaign_runner.py*\n")

    output_path.write_text("".join(lines), encoding="utf-8")
    return output_path

# ─── Main Loop ────────────────────────────────────────────────────────────────

def optimize_copy(
    business_key: str,
    angle: str = "",
    existing_copy: str = "",
    language: str = "en",
    iterations: int = 3,
    dry_run: bool = False,
):
    if business_key not in BUSINESSES:
        print(f"Unknown business: '{business_key}'")
        print(f"Valid options: {', '.join(BUSINESSES.keys())}")
        sys.exit(1)

    biz = BUSINESSES[business_key]
    language_note = "Spanish (write in Spanish)" if language == "es" else "English"

    print(f"\n{'='*60}")
    print(f"  ad_copy_optimizer — {biz['name']}")
    print(f"  Language: {language_note} | Iterations: {iterations} | Dry run: {dry_run}")
    print(f"{'='*60}\n")

    api_key = get_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    # Read current context from program.md
    print("[context] Reading program.md...")
    program_context = read_program_context(business_key)
    context_preview = program_context[:120].replace("\n", " ")
    print(f"[context] {context_preview}...\n")

    # Determine angle
    if not angle:
        angle = f"general promotional post for {biz['type']}"

    # Get initial copy
    if existing_copy:
        print(f"[init] Using provided copy ({len(existing_copy)} chars)")
        current_copy = existing_copy
    else:
        print(f"[init] Generating initial copy for angle: '{angle}'...")
        current_copy = generate_copy(client, biz, program_context, angle, language_note)
        print(f"[init] Generated ({len(current_copy)} chars)\n")

    # Score baseline
    print("[score] Scoring baseline...")
    baseline_scores = score_copy(client, current_copy, biz, language_note)
    baseline_total = baseline_scores["total"]

    print(f"[score] Baseline: {baseline_total}/100")
    print(f"        Hook={baseline_scores['hook']} | Offer={baseline_scores['offer_clarity']} | "
          f"CTA={baseline_scores['cta_sharpness']} | Voice={baseline_scores['voice_match']}")
    print(f"        Weakest: {baseline_scores['weakest_dimension']}")
    print(f"        Problem: {baseline_scores['key_problem']}\n")

    print("--- BASELINE COPY ---")
    print(current_copy)
    print("---------------------\n")

    if dry_run:
        print("[dry-run] Score only — no rewriting performed.")
        return

    # Iteration log
    run_log = [{"iteration": 0, "score": baseline_total, "scores": baseline_scores}]
    best_copy = current_copy
    best_score = baseline_total
    best_scores = baseline_scores

    for i in range(1, iterations + 1):
        print(f"[iter {i}/{iterations}] Rewriting — fixing '{best_scores['weakest_dimension']}'...")
        candidate = rewrite_copy(client, best_copy, biz, best_scores, language_note)

        print(f"[iter {i}/{iterations}] Scoring candidate...")
        candidate_scores = score_copy(client, candidate, biz, language_note)
        candidate_total = candidate_scores["total"]
        delta = candidate_total - best_score
        kept = candidate_total > best_score

        print(f"[iter {i}/{iterations}] Score: {candidate_total}/100 (delta: {delta:+d}) — {'KEPT' if kept else 'DISCARDED'}")

        run_log.append({"iteration": i, "score": candidate_total, "scores": candidate_scores})

        if kept:
            best_copy = candidate
            best_score = candidate_total
            best_scores = candidate_scores
        else:
            print(f"             Reverting to previous best ({best_score}/100)")

        print()

    # Final
    total_gain = best_score - baseline_total
    print(f"{'─'*60}")
    print(f"  FINAL: {baseline_total} -> {best_score}/100  ({total_gain:+d} points)")
    print(f"{'─'*60}\n")

    print("--- WINNING COPY ---")
    print(best_copy)
    print("--------------------\n")

    # Save
    output_path = save_result(business_key, best_copy, run_log, angle)
    print(f"[saved] {output_path}")
    print(f"\n[next]  Paste into fb_campaign_runner.py or use with facebook_marketer.py")
    print(f"[next]  Update Posting Log in: {EXECUTION_DIR / business_key / 'program.md'}\n")

    return best_score, baseline_total, best_copy

# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Autoresearch loop for Facebook ad copy"
    )
    parser.add_argument("business", nargs="?",
                        help="Business key: sugar_shack | island_arcade | island_candy | juan")
    parser.add_argument("--angle", default="",
                        help="Ad angle hint (e.g. 'road trip families', 'rainy day escape')")
    parser.add_argument("--copy", default="",
                        help="Existing copy to improve instead of generating fresh")
    parser.add_argument("--language", default="en", choices=["en", "es"],
                        help="Language for copy (en or es, default: en)")
    parser.add_argument("--iterations", type=int, default=3,
                        help="Max improvement iterations (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score only — no rewriting")

    args = parser.parse_args()

    if not args.business:
        parser.print_help()
        print("\nExamples:")
        print("  python ad_copy_optimizer.py sugar_shack")
        print("  python ad_copy_optimizer.py juan --language es --angle 'new listing alert'")
        print("  python ad_copy_optimizer.py island_arcade --angle 'rainy day escape'")
        print("  python ad_copy_optimizer.py island_candy --dry-run")
        return

    optimize_copy(
        business_key=args.business,
        angle=args.angle,
        existing_copy=args.copy,
        language=args.language,
        iterations=args.iterations,
        dry_run=args.dry_run,
    )

if __name__ == "__main__":
    main()
