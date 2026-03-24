#!/usr/bin/env python3
"""
gbp_review_responder.py — AI-powered Google review response generator

Uses Claude API (claude-sonnet-4-6) with each client's brand voice.
Called by gbp_review_watcher.py when a new review is detected.

Usage (standalone):
    python gbp_review_responder.py --business sugar_shack --stars 5 --reviewer "Jane" --text "Amazing candy!"
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

EXECUTION_DIR = Path(__file__).parent
CONFIG_PATH   = EXECUTION_DIR.parent.parent / "scratch" / "jack_automations_vault" / "skill_improver_config.json"

# ── Client brand voice config ─────────────────────────────────────────────
BRAND_VOICES = {
    "sugar_shack": {
        "business_name": "The Sugar Shack",
        "voice": "Warm, fun, playful, island-casual. We're a small candy shop on South Padre Island. Speak like a friendly local who genuinely loves their customers.",
        "signature": "The Sugar Shack Team",
    },
    "island_candy": {
        "business_name": "Island Candy",
        "voice": "Warm, sweet, casual, island vibes. We're a homemade ice cream shop inside Island Arcade on South Padre Island. Friendly and genuine.",
        "signature": "The Island Candy Team",
    },
    "custom_designs_tx": {
        "business_name": "Custom Designs TX",
        "voice": "Professional, premium, sophisticated — like a luxury concierge service. We install home theaters, smart home systems, and security in McAllen TX. Warm but elevated.",
        "signature": "The Custom Designs TX Team",
    },
    "optimum_clinic": {
        "business_name": "Optimum Health & Wellness Clinic",
        "voice": "Caring, warm, professional, medically competent. We're a cash-pay walk-in clinic open late nights in the RGV. Empathetic and reassuring.",
        "signature": "The Optimum Clinic Team",
    },
}

# Stars → tone guidance
STAR_GUIDANCE = {
    5: "This is a 5-star review. Be enthusiastic and warm. Thank them by name. Reference the specific thing they mentioned. Invite them back.",
    4: "This is a 4-star review. Thank them sincerely. Acknowledge the positive. If they mentioned any concern, briefly note you'd love to hear more to improve.",
    3: "This is a 3-star review. Thank them for honest feedback. Acknowledge their experience. Invite them to contact you directly so you can make it right.",
    2: "This is a 2-star review. Apologize that their experience didn't meet expectations. Take ownership (do NOT be defensive or make excuses). Provide a way to contact you to resolve it. Invite them back.",
    1: "This is a 1-star review. Express genuine concern and apology. Do NOT argue or be defensive. Take responsibility. Provide direct contact info to resolve the situation offline. Show you care.",
}


def _load_anthropic_key() -> str:
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return cfg.get("anthropic_api_key", "")
    except Exception:
        pass
    import os
    return os.environ.get("ANTHROPIC_API_KEY", "")


def generate_response(business_key: str, stars: int, reviewer_name: str, review_text: str) -> str:
    """Generate a professional review response using Claude API."""
    api_key = _load_anthropic_key()
    if not api_key:
        return f"[Manual response needed] Thank you for your review, {reviewer_name}!"

    brand = BRAND_VOICES.get(business_key, {
        "business_name": business_key.replace("_", " ").title(),
        "voice": "Professional and warm.",
        "signature": "The Team",
    })

    star_note = STAR_GUIDANCE.get(stars, STAR_GUIDANCE[3])
    first_name = reviewer_name.split()[0] if reviewer_name else "there"

    system = (
        f"You are writing Google Business Profile review responses on behalf of {brand['business_name']}.\n"
        f"Brand voice: {brand['voice']}\n"
        f"Sign off with: {brand['signature']}\n\n"
        "Rules:\n"
        "- Use the reviewer's first name naturally\n"
        "- 2-4 sentences maximum\n"
        "- Reference something SPECIFIC from their review (not generic)\n"
        "- Never copy-paste generic templates\n"
        "- Never be defensive or argumentative\n"
        "- Follow Google's best practices for review responses\n"
        "- Do NOT include quotation marks around the response\n"
        "- Do NOT add any preamble or explanation — just the response text"
    )

    user_msg = (
        f"{star_note}\n\n"
        f"Reviewer first name: {first_name}\n"
        f"Star rating: {stars}/5\n"
        f"Review text: \"{review_text}\"\n\n"
        "Write the review response now:"
    )

    payload = json.dumps({
        "model":      "claude-sonnet-4-6",
        "max_tokens": 300,
        "system":     system,
        "messages":   [{"role": "user", "content": user_msg}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        resp   = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        return result["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"[responder] Anthropic error {e.code}: {err[:200]}", file=sys.stderr)
        return f"Thank you for your feedback, {first_name}! We appreciate you taking the time to share your experience."
    except Exception as e:
        print(f"[responder] Error: {e}", file=sys.stderr)
        return f"Thank you so much, {first_name}! We really appreciate your kind words."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GBP review response")
    parser.add_argument("--business", required=True, choices=list(BRAND_VOICES.keys()))
    parser.add_argument("--stars",    required=True, type=int, choices=[1,2,3,4,5])
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--text",     required=True)
    args = parser.parse_args()

    response = generate_response(args.business, args.stars, args.reviewer, args.text)
    print("\n=== Generated Response ===")
    print(response)
    print(f"\n[{args.stars} stars | {args.business} | reviewer: {args.reviewer}]")
