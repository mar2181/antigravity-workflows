#!/usr/bin/env python3
"""
listing_optimizer.py — Autoresearch loop for MLS property listing descriptions.

Applies the same pattern as skill_improver.py and ad_copy_optimizer.py:
  1. Accept raw MLS description or property details
  2. Score 0-100 across 4 dimensions
  3. Rewrite targeting the weakest dimension — N iterations max
  4. Keep only if score improves
  5. Save winner to juan/listings/

Scoring rubric (0-25 each):
  - Lifestyle Appeal:  Does it sell the life, not the specs?
  - SEO Value:         Does it include location keywords, property type, natural search terms?
  - CTA Strength:      Clear, compelling call to action with contact info?
  - Accuracy / Info:   Beds, baths, price, key features, neighborhood — complete?

Usage:
  # From raw property details:
  python listing_optimizer.py --address "123 Main St, McAllen" --price 285000 --beds 3 --baths 2 --sqft 1800 --features "pool, new kitchen, corner lot"

  # From existing description (paste and optimize):
  python listing_optimizer.py --address "123 Main St" --description "Your existing MLS description here"

  # Spanish version:
  python listing_optimizer.py --address "123 Main St" --language es --beds 3 --baths 2 --price 285000

  # Dry-run (score only, no rewrite):
  python listing_optimizer.py --address "123 Main St" --description "..." --dry-run

  # Control iterations:
  python listing_optimizer.py --address "123 Main St" --beds 3 --baths 2 --price 285000 --iterations 5
"""

import sys
import json
import os
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import anthropic

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent
LISTINGS_DIR = EXECUTION_DIR / "juan" / "listings"
CONFIG_PATH = Path("C:/Users/mario/.gemini/antigravity/scratch/jack_automations_vault/skill_improver_config.json")
PROGRAM_MD = EXECUTION_DIR / "juan" / "program.md"

# ─── Agent Identity ───────────────────────────────────────────────────────────

JUAN_CONTEXT = """
Agent: Juan José Elizondo — RE/MAX Elite, Rio Grande Valley TX
Market: McAllen, Edinburg, Mission, San Juan, Pharr, Weslaco, Harlingen
Voice: Professional, warm, community-rooted. Bilingual (English/Spanish).
Style: Lead with lifestyle. Max 300 words. Include price, beds/baths, key feature, neighborhood, CTA with phone number.
Phone: (956) 266-xxxx  (use "Call Juan at (956) 266-xxxx" as CTA pattern)
Compliance: No specific ROI or appreciation claims without source. No unverified testimonials.
SEO targets: McAllen homes for sale, RGV real estate, Rio Grande Valley homes
"""

SCORING_RUBRIC = """
Score this real estate listing description 0-100 across exactly these 4 dimensions (0-25 each):

1. lifestyle_appeal (0-25): Does it sell the LIFE, not just the specs?
   - 25: Opens with a vivid lifestyle image, emotional pull throughout, buyer can picture themselves there
   - 15: Some lifestyle language but spec-heavy or flat
   - 5: Pure spec list (3BR/2BA, 1800 sqft) — zero emotional resonance

2. seo_value (0-25): Would this rank for RGV/McAllen real estate searches?
   - 25: Natural use of: city name, neighborhood, "homes for sale" variants, property type, key features
   - 15: City mentioned but weak keyword integration
   - 5: Generic — could be anywhere in the US

3. cta_strength (0-25): How clear and compelling is the call to action?
   - 25: Specific CTA ("Call Juan at XXX"), urgency or scarcity element, what buyer gains by acting
   - 15: Generic CTA ("Call today!") with no specifics
   - 5: No CTA or buried at the end with no energy

4. accuracy_completeness (0-25): Is the essential info present?
   - 25: Price, beds, baths, sqft (if available), key standout feature, neighborhood, agent contact
   - 15: Most info but missing 1-2 key fields
   - 5: Missing critical info (price, beds/baths, or location)

Return ONLY valid JSON, no markdown, no extra text:
{
  "lifestyle_appeal": <int 0-25>,
  "seo_value": <int 0-25>,
  "cta_strength": <int 0-25>,
  "accuracy_completeness": <int 0-25>,
  "total": <sum>,
  "weakest_dimension": "<one of: lifestyle_appeal | seo_value | cta_strength | accuracy_completeness>",
  "key_problem": "<one sentence — the single most important thing holding this description back>"
}
"""

DIMENSION_INSTRUCTIONS = {
    "lifestyle_appeal": """REWRITE FOCUS: Lifestyle Appeal.
The description needs to make buyers FEEL the life they'd be living.
- Open with a sensory or emotional hook (morning light, neighborhood feel, what they'll enjoy)
- Weave lifestyle into specs: "3 spacious bedrooms" not "3 bedrooms"
- Use 'you' and 'your' language — buyer is already living there
- Keep all factual info (price, beds, baths, features) — just make it feel alive""",

    "seo_value": """REWRITE FOCUS: SEO Value.
Buyers searching Google and Zillow need to find this listing.
- Naturally include: the city name (McAllen / Mission / etc.), "Rio Grande Valley" or "RGV", property type
- Add neighborhood or submarket if known
- Include search-friendly phrases: "move-in ready", "new construction", "corner lot" etc. where accurate
- Don't keyword-stuff — integrate naturally into sentences""",

    "cta_strength": """REWRITE FOCUS: CTA Strength.
The ending needs to motivate action RIGHT NOW.
- Name Juan specifically: "Call or text Juan Elizondo at (956) 266-xxxx"
- Add urgency where honest: "Schedule your private tour before this one goes"
- Tell them what they GET by calling (a showing, an answer to questions, a no-pressure tour)
- The CTA should be the last thing they read and the thing that makes them reach for the phone""",

    "accuracy_completeness": """REWRITE FOCUS: Accuracy & Completeness.
Make sure all essential buyer information is present:
- Price (if not provided, use "Priced to sell — contact Juan for details")
- Beds and bathrooms
- Square footage (if known)
- The single most distinctive feature of this property
- City and neighborhood
- Agent contact: Juan Elizondo, RE/MAX Elite, (956) 266-xxxx
Do not invent details not in the original — flag with [confirm with client] if uncertain""",
}

# ─── API Key ──────────────────────────────────────────────────────────────────

def get_api_key(cli_key: str = "") -> str:
    if cli_key:
        return cli_key
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        return env_key
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if cfg.get("anthropic_api_key"):
                return cfg["anthropic_api_key"]
        except Exception:
            pass
    print("\nNo Anthropic API key found. Provide it one of three ways:")
    print("  1. CLI:     --api-key sk-ant-api03-...")
    print("  2. Env var: set ANTHROPIC_API_KEY=sk-ant-api03-...")
    print(f"  3. Config:  add 'anthropic_api_key' to {CONFIG_PATH}")
    sys.exit(1)

# ─── Score ────────────────────────────────────────────────────────────────────

def score_description(client: anthropic.Anthropic, description: str, property_context: str) -> dict:
    prompt = f"""You are a real estate listing expert for the Rio Grande Valley, TX market.

Property context:
{property_context}

Listing description to score:
---
{description}
---

{SCORING_RUBRIC}"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)

# ─── Rewrite ──────────────────────────────────────────────────────────────────

def rewrite_description(
    client: anthropic.Anthropic,
    description: str,
    score_result: dict,
    property_context: str,
    language: str,
) -> str:
    weakest = score_result["weakest_dimension"]
    key_problem = score_result.get("key_problem", "")
    focus_instruction = DIMENSION_INSTRUCTIONS[weakest]

    lang_note = ""
    if language == "es":
        lang_note = "\n\nIMPORTANT: Write the full rewrite in Spanish (Latin American, natural RGV bilingual tone). Do not translate word-for-word — adapt naturally."

    prompt = f"""You are a real estate listing writer for Juan Elizondo, RE/MAX Elite, Rio Grande Valley TX.

{JUAN_CONTEXT}

Property context:
{property_context}

Current listing description (score: {score_result['total']}/100):
---
{description}
---

Current problem: {key_problem}

{focus_instruction}
{lang_note}

Rules:
- Max 300 words
- Keep all accurate facts from the original
- Do not invent square footage, price, or features not mentioned
- Output ONLY the rewritten description — no intro, no commentary, no labels
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()

# ─── Main Loop ────────────────────────────────────────────────────────────────

def build_property_context(args) -> str:
    parts = []
    if args.address:
        parts.append(f"Address: {args.address}")
    if args.price:
        parts.append(f"Price: ${args.price:,}")
    if args.beds:
        parts.append(f"Bedrooms: {args.beds}")
    if args.baths:
        parts.append(f"Bathrooms: {args.baths}")
    if args.sqft:
        parts.append(f"Square Footage: {args.sqft:,}")
    if args.features:
        parts.append(f"Key Features: {args.features}")
    if args.neighborhood:
        parts.append(f"Neighborhood/City: {args.neighborhood}")
    if args.type:
        parts.append(f"Property Type: {args.type}")
    return "\n".join(parts) if parts else "(No structured property data provided — use what's in the description)"


def generate_initial_description(client: anthropic.Anthropic, property_context: str, language: str) -> str:
    lang_note = "Write in Spanish (natural RGV bilingual tone)." if language == "es" else "Write in English."
    prompt = f"""You are a real estate listing writer for Juan Elizondo, RE/MAX Elite, Rio Grande Valley TX.

{JUAN_CONTEXT}

Property details:
{property_context}

Write a compelling MLS listing description following these rules:
- Lead with lifestyle, not specs
- Include price, beds, baths, key feature, neighborhood, agent CTA
- Max 300 words
- {lang_note}
- End with: "Call or text Juan Elizondo at (956) 266-xxxx to schedule your private tour."
- Output ONLY the description — no intro, no labels
"""
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def print_score(score: dict, label: str = ""):
    tag = f" [{label}]" if label else ""
    print(f"\n--- Score{tag}: {score['total']}/100 ---")
    print(f"  Lifestyle Appeal:      {score['lifestyle_appeal']}/25")
    print(f"  SEO Value:             {score['seo_value']}/25")
    print(f"  CTA Strength:          {score['cta_strength']}/25")
    print(f"  Accuracy/Completeness: {score['accuracy_completeness']}/25")
    print(f"  Weakest:  {score['weakest_dimension']}")
    print(f"  Problem:  {score['key_problem']}")


def save_result(address: str, description: str, score: dict, language: str, iterations_run: int):
    LISTINGS_DIR.mkdir(parents=True, exist_ok=True)
    slug = address.lower().replace(" ", "_").replace(",", "").replace("/", "-")[:40]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lang_suffix = f"_{language}" if language != "en" else ""
    filename = f"{slug}{lang_suffix}_{timestamp}.md"
    path = LISTINGS_DIR / filename

    content = f"""# Listing: {address}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Language: {"Spanish" if language == "es" else "English"}
Iterations run: {iterations_run}
Final score: {score['total']}/100

---

## Description

{description}

---

## Score Breakdown

| Dimension | Score |
|-----------|-------|
| Lifestyle Appeal | {score['lifestyle_appeal']}/25 |
| SEO Value | {score['seo_value']}/25 |
| CTA Strength | {score['cta_strength']}/25 |
| Accuracy/Completeness | {score['accuracy_completeness']}/25 |
| **Total** | **{score['total']}/100** |
"""
    path.write_text(content, encoding="utf-8")
    return path


def optimize_listing(args):
    api_key = get_api_key(args.api_key if hasattr(args, "api_key") else "")
    client = anthropic.Anthropic(api_key=api_key)
    property_context = build_property_context(args)
    language = args.language if hasattr(args, "language") and args.language else "en"
    iterations = args.iterations if hasattr(args, "iterations") and args.iterations else 3
    dry_run = args.dry_run if hasattr(args, "dry_run") else False

    print(f"\n=== Listing Optimizer — Juan Elizondo RE/MAX Elite ===")
    print(f"Address: {args.address}")
    print(f"Language: {'Spanish' if language == 'es' else 'English'}")
    print(f"Mode: {'DRY RUN (score only)' if dry_run else f'{iterations} iterations'}")

    # Step 1: Get initial description
    if hasattr(args, "description") and args.description:
        current = args.description
        print("\n[Using provided description]")
    else:
        print("\n[Generating initial description...]")
        current = generate_initial_description(client, property_context, language)
        print("\n--- Initial Description ---")
        print(current)

    # Step 2: Score it
    print("\n[Scoring...]")
    best_score = score_description(client, current, property_context)
    best_description = current
    print_score(best_score, "baseline")

    if dry_run:
        print("\n[Dry run — skipping rewrites]")
    else:
        # Step 3: Iterate
        for i in range(1, iterations + 1):
            if best_score["total"] >= 95:
                print(f"\n[Score {best_score['total']}/100 — stopping early, already excellent]")
                break

            print(f"\n[Iteration {i}/{iterations} — targeting: {best_score['weakest_dimension']}]")
            candidate = rewrite_description(client, best_description, best_score, property_context, language)
            candidate_score = score_description(client, candidate, property_context)
            print_score(candidate_score, f"iteration {i}")

            if candidate_score["total"] > best_score["total"]:
                delta = candidate_score["total"] - best_score["total"]
                print(f"  [+{delta} points — keeping this version]")
                best_description = candidate
                best_score = candidate_score
            else:
                delta = best_score["total"] - candidate_score["total"]
                print(f"  [-{delta} points — discarding, keeping previous best]")

    # Step 4: Print winner
    print(f"\n=== WINNER ({best_score['total']}/100) ===")
    print(best_description)

    # Step 5: Save
    if not dry_run:
        saved_path = save_result(args.address, best_description, best_score, language, iterations)
        print(f"\n[Saved: {saved_path}]")

    return best_description, best_score


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Autoresearch loop for MLS listing descriptions — Juan Elizondo RE/MAX Elite"
    )
    parser.add_argument("--address", required=True, help="Property address (e.g. '123 Main St, McAllen TX')")
    parser.add_argument("--price", type=int, help="Listing price (e.g. 285000)")
    parser.add_argument("--beds", type=int, help="Number of bedrooms")
    parser.add_argument("--baths", type=float, help="Number of bathrooms (e.g. 2.5)")
    parser.add_argument("--sqft", type=int, help="Square footage")
    parser.add_argument("--features", help="Key features (comma-separated, e.g. 'pool, corner lot, new kitchen')")
    parser.add_argument("--neighborhood", help="Neighborhood or city submarket")
    parser.add_argument("--type", help="Property type (e.g. 'single-family', 'commercial', 'land')")
    parser.add_argument("--description", help="Existing MLS description to optimize (instead of generating new)")
    parser.add_argument("--language", choices=["en", "es"], default="en", help="Output language (default: en)")
    parser.add_argument("--iterations", type=int, default=3, help="Max rewrite iterations (default: 3)")
    parser.add_argument("--dry-run", action="store_true", help="Score only — skip rewrites")
    parser.add_argument("--api-key", default="", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    args = parser.parse_args()
    optimize_listing(args)


if __name__ == "__main__":
    main()
