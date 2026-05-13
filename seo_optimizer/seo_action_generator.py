#!/usr/bin/env python3
"""
seo_action_generator.py — Step 2: Generate SEO actions using Claude API.

For each (client, keyword) pair in the work queue:
  1. Reads {client}/program.md for brand voice and compliance rules
  2. Scores the current GBP state (0-100) across 4 signals:
     - Keyword presence in description
     - Keyword presence in recent posts
     - Q&A coverage for the keyword
     - Photo recency and alt-text optimization
  3. Identifies the weakest signal
  4. Generates one specific action targeting that weakness:
     - If weakest = post recency → 150-word GBP post
     - If weakest = Q&A → question + answer pair
     - If weakest = description → revised description variant
     - If weakest = photo → fal.ai image prompt + metadata

Uses Claude Haiku (scoring) and Claude Sonnet (action generation).

Usage:
  python seo_optimizer/seo_action_generator.py
  python seo_optimizer/seo_action_generator.py --dry-run
  python seo_optimizer/seo_action_generator.py --client sugar_shack

State file: seo_optimizer_state.json
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import anthropic
except ImportError:
    print("❌ anthropic library required: pip install anthropic")
    sys.exit(1)

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.parent
SEO_STATE_PATH = SCRIPT_DIR / "seo_optimizer" / "seo_optimizer_state.json"
EXECUTION_DIR = SCRIPT_DIR

# Client program files
CLIENT_DIRS = {
    "sugar_shack": SCRIPT_DIR / "sugar_shack",
    "island_arcade": SCRIPT_DIR / "island_arcade",
    "island_candy": SCRIPT_DIR / "island_candy",
    "juan": SCRIPT_DIR / "juan",
    "spi_fun_rentals": SCRIPT_DIR / "spi_fun_rentals",
    "custom_designs_tx": SCRIPT_DIR / "custom_designs_tx",
    "optimum_clinic": SCRIPT_DIR / "optimum_clinic",
    "optimum_foundation": SCRIPT_DIR / "optimum_foundation",
}

def load_program(client_name):
    """Load {client}/program.md for brand rules and voice."""
    program_path = CLIENT_DIRS.get(client_name, SCRIPT_DIR / client_name) / "program.md"

    if not program_path.exists():
        return {
            "brand_voice": "Professional and on-brand",
            "compliance_rules": [],
        }

    with open(program_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "brand_voice": content[:1000],  # First 1000 chars for context
        "compliance_rules": content,
    }

def score_gbp_state(client_name, keyword, program):
    """
    Use Claude Haiku to score the current GBP state.
    Returns: {description_score, posts_score, qa_score, photo_score, weakest_signal}
    """
    client = anthropic.Anthropic()

    prompt = f"""You are a Google Business Profile (GBP) SEO expert. Score the current state of {client_name}'s GBP listing for the keyword "{keyword}".

Brand voice: {program['brand_voice']}

Evaluate these 4 signals (0-100 each):
1. Description: How naturally is "{keyword}" present in the business description?
2. Posts: How recently and frequently has "{keyword}" appeared in recent GBP posts?
3. Q&A: Are there questions/answers that target "{keyword}" intent?
4. Photos: Are photos recent with keyword-rich alt text?

Return ONLY valid JSON:
{{
  "description_score": <0-100>,
  "posts_score": <0-100>,
  "qa_score": <0-100>,
  "photo_score": <0-100>,
  "weakest_signal": "<description|posts|qa|photo>",
  "reasoning": "<brief explanation>"
}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        result = json.loads(message.content[0].text)
        return result
    except (json.JSONDecodeError, IndexError):
        # Fallback if JSON parsing fails
        return {
            "description_score": 50,
            "posts_score": 40,
            "qa_score": 30,
            "photo_score": 50,
            "weakest_signal": "posts",
            "reasoning": "Could not parse scores, defaulting to posts as weakest",
        }

def generate_action(client_name, keyword, weakest_signal, program):
    """
    Use Claude Sonnet to generate one specific action targeting the weakest signal.
    """
    client = anthropic.Anthropic()

    signal_prompts = {
        "posts": f"""Generate a 150-word GBP post for "{keyword}".
The post should:
- Naturally include the keyword 1-2 times
- Have a clear call-to-action (e.g., "Book now", "Call today", "Learn more")
- Match this brand voice: {program['brand_voice'][:500]}
- Follow these rules: {program['compliance_rules'][:500]}
- Be warm, authentic, and specific to {client_name}

Return the post text ONLY (no quotes, no JSON).""",

        "qa": f"""Generate a Q&A pair targeting "{keyword}" for {client_name}'s GBP.
Format:
QUESTION: [customer question]
ANSWER: [business answer]

The Q&A should:
- Target "{keyword}" intent naturally
- Sound like a real customer and business owner
- Be 2-3 sentences each
- Follow brand rules: {program['brand_voice'][:500]}

Return ONLY the Q&A pair, no explanations.""",

        "description": f"""Rewrite {client_name}'s business description to naturally include "{keyword}".
Requirements:
- Max 750 characters
- Include the keyword 1-2 times naturally
- Maintain this brand voice: {program['brand_voice'][:500]}
- Follow compliance: {program['compliance_rules'][:500]}

Return ONLY the revised description, no explanations.""",

        "photo": f"""Generate a fal.ai image prompt and metadata for a {client_name} photo targeting "{keyword}".
Format:
PROMPT: [detailed image prompt, end with "professional photography, 4k"]
ALT_TEXT: [keyword-rich alt description for GBP]
GEO_TAG: [location hint if applicable]

Requirements:
- Prompt should relate to {client_name} and "{keyword}"
- Alt text should naturally include the keyword
- Keep prompt focused and specific

Return ONLY the prompt, alt text, and geo-tag, no explanations.""",
    }

    prompt = signal_prompts.get(weakest_signal, signal_prompts["posts"])

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    action_content = message.content[0].text.strip()

    return {
        "action_type": f"gbp_{weakest_signal}" if weakest_signal != "qa" else "gbp_qa",
        "action_content": action_content,
        "targeting_signal": weakest_signal,
    }

def main():
    parser = argparse.ArgumentParser(description="Generate SEO actions for weak keywords")
    parser.add_argument("--dry-run", action="store_true", help="Score only, don't generate actions")
    parser.add_argument("--client", help="Single client to process")
    args = parser.parse_args()

    print("🤖 SEO Action Generator — Scoring GBP state and generating actions...")

    # Load work queue
    if not SEO_STATE_PATH.exists():
        print("❌ Work queue not found. Run seo_ranking_analyzer.py first.")
        return

    with open(SEO_STATE_PATH, "r", encoding="utf-8") as f:
        seo_state = json.load(f)

    work_queue = seo_state.get("work_queue", [])

    if not work_queue:
        print("❌ No work queue. Run seo_ranking_analyzer.py first.")
        return

    # Filter by client if specified
    if args.client:
        work_queue = [w for w in work_queue if w["client"] == args.client]

    if not work_queue:
        print(f"❌ No keywords found for client: {args.client}")
        return

    print(f"\n📋 Processing {len(work_queue)} keywords...")

    for i, work_item in enumerate(work_queue, 1):
        client = work_item["client"]
        keyword = work_item["keyword"]

        print(f"\n[{i}/{len(work_queue)}] {client} → {keyword}")

        # Load program
        program = load_program(client)

        if args.dry_run:
            # In dry-run mode, skip all API calls and use mock data
            print("  Scoring GBP state (dry-run)...", end=" ", flush=True)
            scores = {
                "description_score": 45,
                "posts_score": 30,
                "qa_score": 40,
                "photo_score": 50,
                "weakest_signal": "posts",
                "reasoning": "DRY RUN - simulated scoring",
            }
            print(f"✓ Weakest: {scores['weakest_signal']}")
            print("  Action preview: [would generate gbp_post]")
            work_item["gbp_scores"] = scores
            work_item["action_type"] = f"gbp_{scores['weakest_signal']}"
            work_item["action_content"] = "[DRY RUN - not generated]"
            work_item["status"] = "READY"
        else:
            # Score GBP state
            print("  Scoring GBP state...", end=" ", flush=True)
            scores = score_gbp_state(client, keyword, program)
            print(f"✓ Weakest: {scores['weakest_signal']}")

            # Store scores
            work_item["gbp_scores"] = scores
            # Generate action
            print("  Generating action...", end=" ", flush=True)
            action = generate_action(client, keyword, scores["weakest_signal"], program)
            print("✓")

            # Store action
            work_item["action_type"] = action["action_type"]
            work_item["action_content"] = action["action_content"]
            work_item["status"] = "READY"

    # Save updated state (always, so executor can process)
    seo_state["work_queue"] = work_queue
    seo_state["last_generated"] = datetime.now().isoformat()

    with open(SEO_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(seo_state, f, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(f"\n📋 Dry run complete: {len(work_queue)} keywords scored (actions NOT generated)")
    else:
        print(f"\n✅ Actions generated: {len(work_queue)} ready to execute")

if __name__ == "__main__":
    main()
