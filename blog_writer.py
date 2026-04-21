#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blog_writer.py — SEO content pipeline: keyword triage → competitor scrape → generate → deliver.

Generates three content pieces per keyword:
  1. Blog post / service page / landing page (800-1200 words, Markdown + HTML)
  2. Google Business Profile post (max 1500 chars)
  3. Facebook post (max 300 words) + fal.ai image prompt

Usage:
  python blog_writer.py --client custom_designs_tx --list
  python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx"
  python blog_writer.py --client optimum_clinic --all
  python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --publish
  python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --publish --channels gbp,facebook
  python blog_writer.py --client sugar_shack --keyword "candy store south padre island" --force
  python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --preview
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import webbrowser
from datetime import date, datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import anthropic

# ── Paths ──────────────────────────────────────────────────────────────────────
EXECUTION_DIR = Path(__file__).parent
BLOG_DIR      = EXECUTION_DIR / "blog_posts"
CONFIG_PATH   = Path("C:/Users/mario/.gemini/antigravity/scratch/jack_automations_vault/skill_improver_config.json")

BLOG_DIR.mkdir(exist_ok=True)

# ── Models ─────────────────────────────────────────────────────────────────────
SCORE_MODEL = "claude-haiku-4-5-20251001"
WRITE_MODEL = "claude-sonnet-4-6"

# ── Intent Triage ──────────────────────────────────────────────────────────────
# Keywords matching these patterns have informational/research intent → worth a blog
BLOG_INTENT_SIGNALS = [
    "how to", "how do", "what is", "what are", "guide", "tips", "cost", "price",
    "vs", "versus", "difference", "best", "top", "why", "when to", "should i",
    "benefits", "types of", "checklist", "process", "steps", "installation",
    "after hours", "no insurance", "cash pay", "walk in", "open late", "night",
    "for sale", "land for sale", "homes for", "commercial real", "spring break rentals",
    "things to do", "urgent care", "community health", "free health", "affordable healthcare",
]

# Hard transactional/navigational → skip unless --force
SKIP_SIGNALS = [
    "spi fun rentals", "sugar shack spi", "island candy spi", "island arcade spi",
    "remax mcallen", "agente inmobiliario", "instalacion de alarmas",
    "camaras de seguridad", "helados ", "dulces ", "renta de",
    "consulta medica", "clinica nocturna", "clinica de urgencias",
]


def classify_keyword(keyword: str) -> str:
    """Returns 'blog', 'maybe', or 'skip'."""
    kw = keyword.lower()
    for sig in SKIP_SIGNALS:
        if sig in kw:
            return "skip"
    for sig in BLOG_INTENT_SIGNALS:
        if sig in kw:
            return "blog"
    return "maybe"


# ── Business Config ────────────────────────────────────────────────────────────
# Mirrors ad_copy_optimizer.py BUSINESSES dict — extended with GBP/FB publish info
BUSINESSES = {
    "sugar_shack": {
        "name": "The Sugar Shack",
        "type": "candy store",
        "location": "South Padre Island, TX",
        "phone": None,
        "hours": None,
        "voice": "Warm, playful, colorful, family-focused, high-energy. Speaks to spring break families and road trippers.",
        "audience": "Spring break families with kids, young groups, local SPI visitors",
        "offer_cta": "Stop in and see us — we're on the island!",
        "page_key": "sugar_shack",
        "gbp_key": "sugar_shack",
        "has_website": False,
        "website_url": None,
        "website_repo": None,
        "default_channels": ["gbp", "facebook"],  # GBP active (Yehuda), FB confirmed
        "image_guidance": "colorful assorted bulk candy — gummy bears, lollipops, candy jars, rainbow sweets — bright and fun, no storefront, no building exterior, no people",
    },
    "island_arcade": {
        "name": "Island Arcade SPI",
        "type": "arcade and family entertainment center",
        "location": "South Padre Island, TX",
        "phone": None,
        "hours": None,
        "voice": "Energetic, competitive, family-inclusive, nostalgic for retro gamers, exciting for first-timers.",
        "audience": "Spring break families, college groups, couples, locals",
        "offer_cta": "Come play — walk-ins welcome!",
        "page_key": "island_arcade",
        "gbp_key": None,
        "has_website": False,
        "website_url": None,
        "website_repo": None,
        "default_channels": ["facebook"],  # GBP duplicate issue — skip until resolved
        "image_guidance": "glowing arcade game screens, neon lighting, joysticks and buttons close-up, token coins, prize tickets — vibrant colors, no recognizable storefront, no specific interior that could misrepresent the location",
    },
    "island_candy": {
        "name": "Island Candy",
        "type": "ice cream and candy shop",
        "location": "South Padre Island, TX (inside Island Arcade)",
        "phone": None,
        "hours": None,
        "voice": "Sweet, playful, colorful, indulgent. 'You deserve this' energy. Instagram-worthy.",
        "audience": "Families at Island Arcade, SPI visitors, content creators",
        "offer_cta": "Come find your favorite flavor — no occasion needed.",
        "page_key": "island_candy",
        "gbp_key": "island_candy",
        "has_website": False,
        "website_url": None,
        "website_repo": None,
        "default_channels": ["gbp", "facebook"],  # GBP active (Yehuda/sniffer profile), FB confirmed (Mario profile)
        "image_guidance": "scoops of colorful ice cream, banana split, milkshake, waffle cone with melting ice cream — bright and indulgent, beach pastel tones, no storefront, no building exterior, no specific serving vessels that show the shop interior",
    },
    "spi_fun_rentals": {
        "name": "SPI Fun Rentals",
        "type": "beach vehicle and water sports rentals",
        "location": "South Padre Island, TX",
        "phone": None,
        "hours": None,
        "voice": "Fun, adventurous, island-life energy. Upbeat and laid-back — not corporate.",
        "audience": "Spring breakers, families, couples, groups",
        "offer_cta": "Reserve your ride — golf carts go fast during spring break!",
        "page_key": "spi_fun_rentals",
        "gbp_key": None,
        "has_website": False,
        "website_url": None,
        "website_repo": None,
        "default_channels": ["facebook"],  # GBP duplicate in Mario's account — skip until resolved
        "image_guidance": "golf cart on a paved road or parking lot near the beach, kayak on calm water, paddleboard on the Gulf — bright sunny day, no sand driving (illegal on SPI), no storefront, no building exterior",
    },
    "custom_designs_tx": {
        "name": "Custom Designs TX",
        "type": "home technology, security, and smart home installation",
        "location": "McAllen, TX (Rio Grande Valley — serving Hidalgo and Cameron County)",
        "phone": None,
        "hours": None,
        "voice": "Premium, confident, technical-but-accessible. 'We transform spaces.' Sophisticated — like a luxury concierge, not a handyman.",
        "audience": "RGV homeowners building or renovating, business owners wanting commercial security, high-end builders",
        "offer_cta": "Schedule your free on-site consultation — we come to you.",
        "page_key": None,  # Facebook page not yet confirmed — update when page URL is known
        "gbp_key": "custom_designs",
        "has_website": True,
        "website_url": "customdesignstx.com",
        "website_repo": None,  # Discovered on first publish
        "default_channels": ["gbp", "website"],  # FB pending page confirmation
        "image_guidance": "sleek home theater room with large screen and ambient lighting, security camera mounted on a wall, smart home control panel, professional cable installation — dark luxury aesthetic, no specific house exterior that could misrepresent a customer home",
    },
    "optimum_clinic": {
        "name": "Optimum Health & Wellness Clinic",
        "type": "cash-pay walk-in night clinic",
        "location": "3912 N Jackson Rd, Pharr, TX 78577 (serves all RGV)",
        "phone": None,
        "hours": "Monday–Sunday 5:00 PM – 10:00 PM",
        "voice": "Urgent, accessible, trustworthy. Warm but direct — 'We're open when no one else is.' Fully bilingual.",
        "audience": "RGV families without insurance, patients avoiding ER bills, Spanish-speaking community, working adults needing after-hours care",
        "offer_cta": "Walk in tonight — no appointment, no insurance needed.",
        "page_key": "optimum_clinic",
        "gbp_key": "optimum_clinic",  # GBP now VERIFIED — Business ID 16753182239006365635
        "has_website": True,
        "website_url": "optimumhealthrx.com",
        "website_repo": None,  # Lovable/React — confirm GitHub repo name on first publish
        "default_channels": ["gbp", "facebook", "website"],  # Full pipeline — all 3 channels active
        "image_guidance": "stethoscope on a clean white surface, doctor's hands with a patient, medical waiting room with warm lighting, prescription notepad — warm and trustworthy, no specific clinic exterior or signage that could misrepresent the location",
    },
    "juan": {
        "name": "Juan Elizondo RE/MAX Elite",
        "type": "real estate agent",
        "location": "Rio Grande Valley, TX",
        "phone": None,
        "hours": None,
        "voice": "Professional, data-driven, bilingual. Trustworthy expert — not pushy. Warm but authoritative.",
        "audience": "RGV homebuyers, sellers, investors, first-time buyers, bilingual community",
        "offer_cta": "Call or message Juan today for a free consultation.",
        "page_key": "juan",
        "gbp_key": None,  # GBP suspended — do not post until reinstated
        "has_website": True,
        "website_url": "juanjoseelizondo.com",
        "website_repo": None,  # Lovable/React — confirm GitHub repo name on first publish
        "default_channels": ["facebook"],  # GBP suspended, website repo TBD
        "image_guidance": "beautiful RGV home exterior with manicured lawn, modern kitchen interior, aerial view of a South Texas neighborhood, real estate keys on a desk — warm and aspirational, no specific house that could be misidentified as a listing, no agent photos",
    },
    "optimum_foundation": {
        "name": "Optimum Health and Wellness Foundation",
        "type": "501(c)(3) nonprofit community health organization",
        "location": "Pharr, TX / Rio Grande Valley",
        "phone": None,
        "hours": None,
        "voice": "Mission-driven, community-first, warm and hopeful. 'Together we build a healthier RGV.'",
        "audience": "RGV community, individual donors, volunteers, local businesses",
        "offer_cta": "Get involved — donate, volunteer, or share our mission.",
        "page_key": "optimum_foundation",
        "gbp_key": None,
        "has_website": False,
        "website_url": None,
        "website_repo": None,
        "default_channels": [],  # Hold — FB page URL not confirmed, no GBP
        "image_guidance": "diverse community members at a health fair, hands reaching together in solidarity, doctor speaking with a patient from an underserved community — warm and hopeful, no specific building or signage",
    },
}

BUSINESS_ORDER = list(BUSINESSES.keys())


# ── API Key ────────────────────────────────────────────────────────────────────
def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        key = cfg.get("anthropic_api_key", "")
        if key:
            return key
    print("❌ No ANTHROPIC_API_KEY found.")
    sys.exit(1)


# ── program.md Reader (reuse from ad_copy_optimizer) ──────────────────────────
def read_program_context(biz_key: str) -> str:
    program_path = EXECUTION_DIR / biz_key / "program.md"
    if not program_path.exists():
        return "(no program.md)"
    content = program_path.read_text(encoding="utf-8", errors="replace")
    priorities = re.search(r"## Current Priorities.*?(?=\n## |\Z)", content, re.DOTALL)
    listings   = re.search(r"## Active Listings.*?(?=\n## |\Z)", content, re.DOTALL)
    working    = re.search(r"## What's Working.*?(?=\n## |\Z)", content, re.DOTALL)
    parts = [m.group(0) for m in [priorities, listings, working] if m]
    ctx = "\n\n".join(parts) if parts else content[:800]
    ctx = re.sub(r"- \[ \] \*\*.*?\*\*: _\(fill in.*?\)_\n?", "", ctx)
    return ctx.strip() or "(program.md exists but sections not filled in)"


# ── Competitor Scrape ──────────────────────────────────────────────────────────
def scrape_top_result(url: str) -> dict:
    """Scrape a competitor URL and return structured data."""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Meta description
        meta = soup.find("meta", {"name": re.compile("description", re.I)})
        meta_desc = meta.get("content", "") if meta else ""

        # H2 headers
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2")][:8]

        # Word count from main content area
        body = soup.find("article") or soup.find("main") or soup.find("body")
        text = body.get_text(" ", strip=True) if body else ""
        word_count = len(text.split())

        return {
            "url": url,
            "title": title,
            "meta_desc": meta_desc,
            "h2_headers": h2s,
            "word_count": word_count,
            "scraped": True,
        }
    except Exception as e:
        return {"url": url, "scraped": False, "error": str(e)}


def get_competitor_url(biz_key: str, keyword: str) -> str | None:
    """Get top organic URL from keyword rankings state."""
    try:
        spec = importlib.util.spec_from_file_location(
            "keyword_rank_tracker",
            EXECUTION_DIR / "keyword_rank_tracker.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        summary = mod.load_rankings_summary()
        biz_data = summary.get(biz_key, {})
        kw_data = biz_data.get(keyword, {})
        top3 = kw_data.get("top3_organic", [])
        for entry in top3:
            url = entry.get("url", "")
            if url and not entry.get("is_ours") and url.startswith("http"):
                return url
    except Exception:
        pass
    return None


# ── Content Generation ─────────────────────────────────────────────────────────
GENERATE_PROMPT = """You are an expert SEO content writer for {business_name} — a {business_type} in {location}.

BRAND VOICE: {voice}
TARGET AUDIENCE: {audience}
CURRENT BUSINESS CONTEXT:
{program_context}

KEYWORD TO TARGET: "{keyword}"
CONTENT TYPE: {content_type}
TARGET WORD COUNT: {target_words} words (minimum)

COMPETITOR ANALYSIS:
{competitor_analysis}

RULES:
- Include the exact keyword naturally in: title, first 100 words, one H2, meta description
- Write with a strong local angle — mention {location} and nearby areas throughout
- End with a clear CTA: {cta}
- Use proper H1/H2/H3 hierarchy
- No keyword stuffing — write for humans first
- Be specific and useful — not generic filler content
- Outperform the competitor in depth, examples, and local relevance

Generate ALL THREE of the following in one response. Use these EXACT section markers:

===BLOG_START===
---
title: "<SEO title with keyword>"
meta_description: "<150-160 char meta desc with keyword>"
keyword: "{keyword}"
content_type: "{content_type}"
date: {today}
business: {biz_key}
---

<full blog/page content in Markdown — minimum {target_words} words>
===BLOG_END===

===GBP_START===
<Google Business Profile post — max 1500 characters, text only, include phone/hours if available, 1-2 hashtags, CTA>
===GBP_END===

===FB_START===
POST COPY:
<Facebook post — max 300 words, hook + 3 bullet points + CTA, max 3 hashtags>

IMAGE PROMPT:
<fal.ai Flux Pro image prompt — professional photography, 4k, no text overlays, landscape 16:9 format, captures the service/business atmosphere>
===FB_END===

===IMAGES_START===
IMAGE GUIDANCE: {image_guidance}
HERO: <landscape 16:9 hero image — must follow IMAGE GUIDANCE above, vivid and eye-catching, professional photography 4k, no text overlays, no logos, NO invented storefronts or building exteriors>
SECTION_1: <square image for H2 section 1 — follows IMAGE GUIDANCE, specific to that section's subject matter, professional photography 4k, no text>
SECTION_2: <square image for H2 section 3 — follows IMAGE GUIDANCE, mid-article visual, different angle or setting from SECTION_1, professional photography 4k, no text>
SECTION_3: <square image for H2 section 5 or the CTA section — follows IMAGE GUIDANCE, professional photography 4k, no text, warm and action-inspiring tone>
===IMAGES_END===

Rules for image prompts:
- All prompts must end with "professional photography, 4k"
- No text overlays, no logos, no branded elements
- STRICTLY follow the IMAGE GUIDANCE — generate product/concept shots, never invented storefronts or building exteriors
- Use South Texas / Rio Grande Valley local aesthetic where natural (landscapes, architecture, people)
- HERO doubles as the Facebook image — make it the strongest, most scroll-stopping image
- Section images should illustrate the specific topic of that section (not generic stock photo energy)"""

SCORE_PROMPT = """Score this SEO blog post for "{keyword}" on 4 dimensions (0-25 each):

1. KEYWORD_PLACEMENT (0-25): Keyword in title + first 100 words + at least one H2 + meta description
2. LOCAL_RELEVANCE (0-25): City/region mentioned multiple times, local context throughout
3. DEPTH_VS_COMPETITOR (0-25): Word count >= {min_words} words, covers topic thoroughly
4. CTA_STRENGTH (0-25): Clear, specific CTA that matches the business's actual offer

BLOG CONTENT:
{blog_content}

Respond with ONLY this JSON (no markdown, no explanation):
{{"keyword_placement": <0-25>, "local_relevance": <0-25>, "depth_vs_competitor": <0-25>, "cta_strength": <0-25>, "total": <sum>, "weakest_dimension": "<dimension_name>", "key_problem": "<one sentence fix>"}}"""

REWRITE_SECTION_PROMPT = """You are improving a section of an SEO blog post for "{keyword}".

The blog scored low on: {weakest_dimension}
Problem: {key_problem}

FULL BLOG:
{blog_content}

Rewrite the blog to fix ONLY the weak dimension. Keep everything else identical.
Output ONLY the improved blog content (Markdown, starting with the title). No explanation."""


def parse_image_prompts(raw: str) -> dict:
    """Extract HERO/SECTION_1/SECTION_2/SECTION_3 from ===IMAGES_START=== block."""
    match = re.search(r"===IMAGES_START===\n?(.*?)===IMAGES_END===", raw, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    prompts = {}
    for key in ["HERO", "SECTION_1", "SECTION_2", "SECTION_3"]:
        m = re.search(rf"^{key}:\s*(.+)$", block, re.MULTILINE)
        if m:
            prompts[key.lower()] = m.group(1).strip()
    return prompts


def generate_content(client: anthropic.Anthropic, biz_key: str, keyword: str,
                     competitor: dict) -> dict:
    """Generate blog + GBP + FB content for a keyword. Returns dict with all three."""
    biz = BUSINESSES[biz_key]
    program_context = read_program_context(biz_key)

    # Determine content type
    kw = keyword.lower()
    if any(w in kw for w in ["for sale", "homes for", "land for", "commercial real", "listings"]):
        content_type = "Location Landing Page"
    elif any(w in kw for w in ["installation", "clinic", "walk in", "urgent care", "after hours",
                                 "cash pay", "no insurance", "consultation"]):
        content_type = "Service Page"
    else:
        content_type = "Blog Post"

    # Target word count: 30% more than competitor (min 800)
    comp_words = competitor.get("word_count", 0) if competitor.get("scraped") else 0
    target_words = max(800, int(comp_words * 1.30)) if comp_words > 300 else 900

    # Build competitor analysis section
    if competitor.get("scraped"):
        comp_analysis = (
            f"Top-ranking page: {competitor['url']}\n"
            f"Their title: {competitor.get('title', 'N/A')}\n"
            f"Their word count: {comp_words} words\n"
            f"Their H2 headers: {', '.join(competitor.get('h2_headers', [])) or 'none detected'}\n"
            f"Beat them by: adding local RGV context they lack, going deeper on specifics, "
            f"writing at least {target_words} words."
        )
    else:
        comp_analysis = "No competitor data available — write a comprehensive, locally-focused piece that covers the topic better than average."

    prompt = GENERATE_PROMPT.format(
        business_name=biz["name"],
        business_type=biz["type"],
        location=biz["location"],
        voice=biz["voice"],
        audience=biz["audience"],
        program_context=program_context,
        keyword=keyword,
        content_type=content_type,
        target_words=target_words,
        competitor_analysis=comp_analysis,
        cta=biz["offer_cta"],
        today=date.today().isoformat(),
        biz_key=biz_key,
        image_guidance=biz.get("image_guidance", "product or service related imagery — no invented storefronts or building exteriors"),
    )

    print("  [1/2] Generating content (Sonnet)...")
    response = client.messages.create(
        model=WRITE_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text

    # Parse sections
    blog_match = re.search(r"===BLOG_START===\n?(.*?)===BLOG_END===", raw, re.DOTALL)
    gbp_match  = re.search(r"===GBP_START===\n?(.*?)===GBP_END===", raw, re.DOTALL)
    fb_match   = re.search(r"===FB_START===\n?(.*?)===FB_END===", raw, re.DOTALL)

    blog_content = blog_match.group(1).strip() if blog_match else raw
    gbp_content  = gbp_match.group(1).strip() if gbp_match else ""
    fb_content   = fb_match.group(1).strip() if fb_match else ""

    # Parse FB into post copy + image prompt
    fb_copy = fb_content
    image_prompt = ""
    if "IMAGE PROMPT:" in fb_content:
        parts = fb_content.split("IMAGE PROMPT:", 1)
        fb_copy = parts[0].replace("POST COPY:", "").strip()
        image_prompt = parts[1].strip()

    # Parse structured image prompts block
    image_prompts = parse_image_prompts(raw)
    # Hero overrides the FB image prompt if available (same image, dual use)
    if image_prompts.get("hero"):
        image_prompt = image_prompts["hero"]

    # Score blog
    print("  [2/2] Scoring content (Haiku)...")
    blog_text_only = re.sub(r"^---.*?---\n", "", blog_content, flags=re.DOTALL)
    word_count = len(blog_text_only.split())
    min_words = max(int(comp_words * 1.25), 700) if comp_words > 300 else 700

    score_prompt = SCORE_PROMPT.format(
        keyword=keyword,
        min_words=min_words,
        blog_content=blog_content[:3000],
    )
    score_resp = client.messages.create(
        model=SCORE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": score_prompt}],
    )
    score_raw = score_resp.content[0].text.strip()
    if score_raw.startswith("```"):
        score_raw = score_raw.split("```")[1]
        if score_raw.startswith("json"):
            score_raw = score_raw[4:]
    try:
        score = json.loads(score_raw)
        score["total"] = (score.get("keyword_placement", 0) + score.get("local_relevance", 0) +
                          score.get("depth_vs_competitor", 0) + score.get("cta_strength", 0))
    except Exception:
        score = {"total": 75, "weakest_dimension": "none", "key_problem": "Could not parse score"}

    print(f"  Score: {score['total']}/100 — weak: {score.get('weakest_dimension','—')}")

    # Rewrite if any dimension < 15
    if score["total"] < 70 or any(
        score.get(d, 25) < 15 for d in ["keyword_placement", "local_relevance", "depth_vs_competitor", "cta_strength"]
    ):
        print("  [Rewrite] Improving weak section...")
        rewrite_prompt = REWRITE_SECTION_PROMPT.format(
            keyword=keyword,
            weakest_dimension=score.get("weakest_dimension", "overall quality"),
            key_problem=score.get("key_problem", "Improve depth and local relevance"),
            blog_content=blog_content,
        )
        rw_resp = client.messages.create(
            model=WRITE_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": rewrite_prompt}],
        )
        blog_content = rw_resp.content[0].text.strip()
        blog_text_only = re.sub(r"^---.*?---\n", "", blog_content, flags=re.DOTALL)
        word_count = len(blog_text_only.split())

    return {
        "keyword": keyword,
        "content_type": content_type,
        "blog": blog_content,
        "gbp": gbp_content,
        "fb_copy": fb_copy,
        "image_prompt": image_prompt,
        "image_prompts": image_prompts,  # {hero, section_1, section_2, section_3}
        "images": {},                    # populated by save_content() after fal.ai generation
        "word_count": word_count,
        "score": score,
        "target_words": target_words,
        "competitor": competitor,
    }


# ── Real Photos Check ──────────────────────────────────────────────────────────
REAL_PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def find_real_photo(biz_key: str) -> Path | None:
    """Return a real business photo from {biz_key}/photos/ if one exists, else None."""
    photos_dir = EXECUTION_DIR / biz_key / "photos"
    if not photos_dir.exists():
        return None
    candidates = [f for f in photos_dir.iterdir() if f.suffix.lower() in REAL_PHOTO_EXTS]
    if not candidates:
        return None
    # Prefer files named 'hero*' first, then any
    heroes = [f for f in candidates if f.stem.lower().startswith("hero")]
    return heroes[0] if heroes else candidates[0]


# ── Image Generation (fal.ai) ──────────────────────────────────────────────────
def _load_fal_key() -> str:
    env_path = Path(__file__).parent.parent.parent / "scratch" / "gravity-claw" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("FAL_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    return os.environ.get("FAL_KEY", "")


def generate_blog_images(image_prompts: dict, out_dir: Path, biz_key: str = "") -> dict:
    """Generate hero + section images via fal.ai SDK. Returns {key: Path}.

    If a real business photo exists in {biz_key}/photos/, it is copied as the
    hero image instead of generating an invented one via fal.ai.
    """
    if not image_prompts:
        return {}

    fal_key = _load_fal_key()
    if not fal_key:
        print("  ⚠️  FAL_KEY not found — skipping image generation")
        return {}

    os.environ["FAL_KEY"] = fal_key

    try:
        import fal_client
    except ImportError:
        print("  Installing fal_client...")
        os.system(f'"{sys.executable}" -m pip install fal_client -q')
        import fal_client

    import shutil
    import urllib.request as _urlreq

    out_dir.mkdir(parents=True, exist_ok=True)
    size_map = {
        "hero":      "landscape_16_9",
        "section_1": "square_hd",
        "section_2": "square_hd",
        "section_3": "square_hd",
    }
    results = {}

    # Check for a real business photo to use as hero
    real_photo = find_real_photo(biz_key) if biz_key else None

    for key, prompt in image_prompts.items():
        fpath = out_dir / f"{key}.png"

        # Use real photo as hero if available
        if key == "hero" and real_photo:
            dest = out_dir / f"hero{real_photo.suffix}"
            shutil.copy2(real_photo, dest)
            results[key] = dest
            print(f"  📷  hero — using real business photo: {real_photo.name} ✅")
            continue

        print(f"  🖼  Generating {key}...", end=" ", flush=True)
        try:
            handler = fal_client.submit(
                "fal-ai/flux-pro/v1.1-ultra",
                arguments={
                    "prompt": prompt,
                    "image_size": size_map.get(key, "square_hd"),
                    "num_images": 1,
                },
            )
            result = handler.get()
            img_url = result["images"][0]["url"]
            _urlreq.urlretrieve(img_url, str(fpath))
            results[key] = fpath
            print(f"✅")
        except Exception as e:
            print(f"⚠️  {e}")

    return results


# ── File Saving ────────────────────────────────────────────────────────────────
def keyword_to_slug(keyword: str) -> str:
    slug = keyword.lower()
    slug = re.sub(r"[^a-z0-9 ]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug[:60]


def build_html(biz_key: str, content: dict) -> str:
    biz = BUSINESSES[biz_key]
    today = date.today().strftime("%B %d, %Y")
    title_match = re.search(r'^# (.+)$', content["blog"], re.MULTILINE)
    page_title = title_match.group(1) if title_match else content["keyword"].title()
    # Simple markdown→HTML for H2/H3/paragraphs
    body_md = content["blog"]
    body_md = re.sub(r"^---.*?---\n?", "", body_md, flags=re.DOTALL)  # strip frontmatter
    body_html = body_md
    body_html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', body_html, flags=re.MULTILINE)
    body_html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', body_html, flags=re.MULTILINE)
    body_html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', body_html, flags=re.MULTILINE)
    body_html = re.sub(r'^\*\*(.+)\*\*$', r'<strong>\1</strong>', body_html, flags=re.MULTILINE)
    body_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', body_html)
    body_html = re.sub(r'^\- (.+)$', r'<li>\1</li>', body_html, flags=re.MULTILINE)
    body_html = re.sub(r'(<li>.*?</li>)(\n<li>)', r'\1\2', body_html)
    body_html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', body_html)
    body_html = re.sub(r'\n\n', '</p><p>', body_html)
    body_html = f"<p>{body_html}</p>"
    body_html = re.sub(r'<p>(<h[1-3]>)', r'\1', body_html)
    body_html = re.sub(r'(</h[1-3]>)</p>', r'\1', body_html)
    body_html = re.sub(r'<p>(<ul>)', r'\1', body_html)
    body_html = re.sub(r'(</ul>)</p>', r'\1', body_html)
    body_html = re.sub(r'<p>\s*</p>', '', body_html)

    score = content["score"]
    score_bar = f"{score.get('total', 0)}/100"

    gbp_escaped = content["gbp"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    fb_escaped  = content["fb_copy"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    img_escaped = content["image_prompt"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DRAFT: {page_title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; }}
  .header {{ background: linear-gradient(135deg, #1a2a5e 0%, #2d4a8a 100%); color: white; padding: 28px 32px; }}
  .header h1 {{ font-size: 20px; font-weight: 700; }}
  .header .sub {{ font-size: 13px; opacity: 0.8; margin-top: 6px; }}
  .badge {{ display: inline-block; background: rgba(255,255,255,0.2); border-radius: 4px; padding: 3px 10px; font-size: 12px; margin-top: 8px; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 24px 20px; }}
  .section {{ background: white; border-radius: 10px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .section h2 {{ font-size: 15px; font-weight: 700; color: #1a2a5e; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #e2e8f0; }}
  .score-bar {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }}
  .score-item {{ background: #f1f5f9; border-radius: 6px; padding: 8px 14px; font-size: 12px; }}
  .score-item strong {{ display: block; font-size: 18px; color: #1a2a5e; }}
  .blog-content h1 {{ font-size: 22px; font-weight: 800; color: #1e293b; margin: 20px 0 12px; }}
  .blog-content h2 {{ font-size: 17px; font-weight: 700; color: #1a2a5e; margin: 20px 0 10px; }}
  .blog-content h3 {{ font-size: 15px; font-weight: 600; color: #374151; margin: 16px 0 8px; }}
  .blog-content p {{ font-size: 14px; line-height: 1.7; margin-bottom: 12px; color: #374151; }}
  .blog-content ul {{ margin: 10px 0 14px 20px; }}
  .blog-content li {{ font-size: 14px; line-height: 1.6; margin-bottom: 4px; color: #374151; }}
  .copy-block {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-size: 13px; line-height: 1.6; white-space: pre-wrap; color: #374151; }}
  .word-count {{ font-size: 12px; color: #64748b; margin-top: 8px; }}
  .footer {{ text-align: center; padding: 20px; color: #94a3b8; font-size: 12px; }}
</style>
</head>
<body>

<div class="header">
  <h1>DRAFT — {biz["name"]}</h1>
  <div class="sub">{content["content_type"]} for keyword: <em>"{content["keyword"]}"</em></div>
  <span class="badge">SEO Score: {score_bar} &nbsp;·&nbsp; {content["word_count"]} words &nbsp;·&nbsp; {today}</span>
</div>

<div class="container">

  <div class="section">
    <h2>Score Breakdown</h2>
    <div class="score-bar">
      <div class="score-item"><strong>{score.get("keyword_placement", "—")}/25</strong>Keyword Placement</div>
      <div class="score-item"><strong>{score.get("local_relevance", "—")}/25</strong>Local Relevance</div>
      <div class="score-item"><strong>{score.get("depth_vs_competitor", "—")}/25</strong>Depth vs. Competitor</div>
      <div class="score-item"><strong>{score.get("cta_strength", "—")}/25</strong>CTA Strength</div>
    </div>
    <p style="font-size:13px;color:#64748b">{score.get("key_problem", "")}</p>
  </div>

  <div class="section">
    <h2>Blog / {content["content_type"]} (Website)</h2>
    <div class="blog-content">{body_html}</div>
    <div class="word-count">{content["word_count"]} words &nbsp;·&nbsp; Target was {content["target_words"]}</div>
  </div>

  <div class="section">
    <h2>Google Business Profile Post</h2>
    <div class="copy-block">{gbp_escaped}</div>
    <div class="word-count">{len(content["gbp"])} characters (max 1,500)</div>
  </div>

  <div class="section">
    <h2>Facebook Post</h2>
    <div class="copy-block">{fb_escaped}</div>
    <div style="margin-top:14px">
      <strong style="font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Image Prompt</strong>
      <div class="copy-block" style="margin-top:6px;font-style:italic;color:#475569">{img_escaped}</div>
    </div>
  </div>

</div>

<div class="footer">
  Draft generated by <strong>Antigravity Blog Writer</strong> &nbsp;·&nbsp; {today}<br>
  <em>Review on Telegram, then run: python blog_writer.py --client {biz_key} --keyword "{content["keyword"]}" --publish</em>
</div>

</body>
</html>"""


def build_publication_html(biz_key: str, content: dict, images: dict) -> str:
    """Build a beautiful publication-ready HTML page with hero + inline section images."""
    import base64

    biz  = BUSINESSES[biz_key]
    today = date.today().strftime("%B %d, %Y")

    # ── Extract frontmatter meta ───────────────────────────────────────────────
    fm_title = content["keyword"].title()
    fm_meta  = ""
    fm_match = re.search(r"^---\n(.*?)\n---", content["blog"], re.DOTALL)
    if fm_match:
        fm_block = fm_match.group(1)
        t = re.search(r'^title:\s*"?(.+?)"?\s*$', fm_block, re.MULTILINE)
        d = re.search(r'^meta_description:\s*"?(.+?)"?\s*$', fm_block, re.MULTILINE)
        if t:
            fm_title = t.group(1).strip()
        if d:
            fm_meta = d.group(1).strip()

    # ── Markdown → HTML (with section image injection) ────────────────────────
    body_md = re.sub(r"^---.*?---\n?", "", content["blog"], flags=re.DOTALL).strip()

    def img_tag(key: str, caption: str) -> str:
        p = images.get(key)
        if not p or not Path(p).exists():
            return ""
        b64 = base64.b64encode(Path(p).read_bytes()).decode()
        return (
            f'<figure style="margin:28px 0;text-align:center">'
            f'<img src="data:image/png;base64,{b64}" alt="{caption}" '
            f'style="max-width:100%;border-radius:10px;box-shadow:0 4px 18px rgba(0,0,0,0.12)">'
            f'<figcaption style="font-size:13px;color:#64748b;margin-top:8px;font-style:italic">{caption}</figcaption>'
            f'</figure>'
        )

    h2_count = [0]

    def replace_h2(m):
        h2_count[0] += 1
        title = m.group(1)
        n = h2_count[0]
        html = f'<h2 style="font-size:22px;font-weight:700;color:#1a2a5e;margin:36px 0 12px;border-left:4px solid #1a2a5e;padding-left:14px">{title}</h2>'
        if n == 1:
            html += img_tag("section_1", title)
        elif n == 3:
            html += img_tag("section_2", title)
        elif n == 5:
            html += img_tag("section_3", title)
        return html

    body_html = body_md
    body_html = re.sub(r'^### (.+)$', r'<h3 style="font-size:18px;font-weight:600;color:#334155;margin:24px 0 8px">\1</h3>', body_html, flags=re.MULTILINE)
    body_html = re.sub(r'^## (.+)$', replace_h2, body_html, flags=re.MULTILINE)
    body_html = re.sub(r'^# (.+)$', r'<h1 style="font-size:30px;font-weight:800;color:#0f172a;line-height:1.25;margin:0 0 24px">\1</h1>', body_html, flags=re.MULTILINE)
    body_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', body_html)
    body_html = re.sub(r'^\- (.+)$', r'<li>\1</li>', body_html, flags=re.MULTILINE)
    body_html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul style="margin:12px 0 18px 22px;line-height:1.8">\1</ul>', body_html)
    body_html = re.sub(r'\n\n', '</p><p>', body_html)
    body_html = f'<p style="font-size:18px;line-height:1.78;color:#334155;margin-bottom:18px">{body_html}</p>'
    # Clean up block-level elements wrapped in <p>
    for tag in ["h1", "h2", "h3", "ul", "figure"]:
        body_html = re.sub(rf'<p[^>]*>(<{tag})', r'\1', body_html)
        body_html = re.sub(rf'(</{tag}>)</p>', r'\1', body_html)
    body_html = re.sub(r'<p[^>]*>\s*</p>', '', body_html)

    # ── Hero image (base64) ────────────────────────────────────────────────────
    hero_tag = ""
    hero_path = images.get("hero")
    if hero_path and Path(hero_path).exists():
        b64 = base64.b64encode(Path(hero_path).read_bytes()).decode()
        hero_tag = (
            f'<div style="width:100%;max-height:420px;overflow:hidden;margin-bottom:0">'
            f'<img src="data:image/png;base64,{b64}" alt="{fm_title}" '
            f'style="width:100%;max-height:420px;object-fit:cover;display:block">'
            f'</div>'
        )

    # ── CTA block ──────────────────────────────────────────────────────────────
    cta_html = (
        f'<div style="background:#1a2a5e;color:white;border-radius:14px;padding:36px 40px;'
        f'margin:48px 0 32px;text-align:center">'
        f'<h3 style="font-size:22px;font-weight:700;margin:0 0 12px;color:white">{biz["name"]}</h3>'
        f'<p style="font-size:16px;color:rgba(255,255,255,0.88);margin:0 0 24px;line-height:1.5">'
        f'{biz["offer_cta"]}</p>'
        f'<a href="tel:+1" style="display:inline-block;background:white;color:#1a2a5e;'
        f'font-weight:700;font-size:15px;padding:14px 34px;border-radius:50px;'
        f'text-decoration:none;letter-spacing:0.3px">Contact Us Today</a>'
        f'</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{fm_title}</title>
<meta name="description" content="{fm_meta}">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Georgia,serif;background:#f8f9fb;color:#1e293b}}
  .site-header{{background:#1a2a5e;padding:18px 32px;display:flex;align-items:center;gap:14px}}
  .site-header .biz-name{{color:white;font-size:17px;font-weight:700;letter-spacing:0.2px}}
  .site-header .badge{{background:rgba(255,255,255,0.18);color:rgba(255,255,255,0.9);font-size:11px;padding:3px 10px;border-radius:20px;margin-left:auto}}
  .article-wrap{{max-width:760px;margin:40px auto;padding:0 20px 60px}}
  .article-meta{{font-size:13px;color:#64748b;margin-bottom:28px}}
  figure img{{border-radius:10px}}
  footer{{text-align:center;padding:24px;color:#94a3b8;font-size:12px;border-top:1px solid #e2e8f0;margin-top:20px}}
  @media(max-width:600px){{.article-wrap{{padding:0 14px 40px}}.site-header{{padding:14px 18px}}}}
</style>
</head>
<body>

<div class="site-header">
  <span class="biz-name">{biz["name"]}</span>
  <span class="badge">{content["content_type"]} &nbsp;·&nbsp; {today}</span>
</div>

{hero_tag}

<div class="article-wrap">
  <p class="article-meta">{content["content_type"]} &nbsp;·&nbsp; {content["word_count"]} words &nbsp;·&nbsp; {today}</p>
  {body_html}
  {cta_html}
</div>

<footer>
  Prepared by <strong>Antigravity Digital</strong> &nbsp;·&nbsp; {today}<br>
  <em>Draft for review — run <code>python blog_writer.py --client {biz_key} --keyword "{content["keyword"]}" --publish</code> to go live</em>
</footer>

</body>
</html>"""


def save_content(biz_key: str, content: dict) -> dict:
    """Save .md + .html + _PUBLISH.html + images. Returns paths dict."""
    today_str = date.today().strftime("%Y-%m-%d")
    slug = keyword_to_slug(content["keyword"])
    out_dir = BLOG_DIR / biz_key
    out_dir.mkdir(exist_ok=True)

    md_path      = out_dir / f"{today_str}_{slug}.md"
    html_path    = out_dir / f"{today_str}_{slug}.html"
    publish_path = out_dir / f"{today_str}_{slug}_PUBLISH.html"
    meta_path    = out_dir / f"{today_str}_{slug}_meta.json"

    # Save markdown
    md_path.write_text(content["blog"], encoding="utf-8")

    # Generate images via fal.ai
    img_dir = BLOG_DIR / biz_key / "images" / f"{today_str}_{slug}"
    image_prompts = content.get("image_prompts", {})
    images = {}
    if image_prompts:
        print("  Generating images...")
        images = generate_blog_images(image_prompts, img_dir, biz_key=biz_key)
        content["images"] = images

    # Internal review HTML (unchanged — score breakdown, all 3 pieces)
    html_path.write_text(build_html(biz_key, content), encoding="utf-8")

    # Beautiful publication HTML (hero + section images inline)
    publish_path.write_text(build_publication_html(biz_key, content, images), encoding="utf-8")

    # Save meta (include image paths as strings for --publish flow)
    meta_path.write_text(json.dumps({
        "keyword": content["keyword"],
        "content_type": content["content_type"],
        "gbp": content["gbp"],
        "fb_copy": content["fb_copy"],
        "image_prompt": content["image_prompt"],
        "image_prompts": content.get("image_prompts", {}),
        "images": {k: str(v) for k, v in images.items()},
        "word_count": content["word_count"],
        "score": content["score"],
        "competitor_url": content["competitor"].get("url", ""),
        "generated": today_str,
        "published": {"gbp": False, "facebook": False, "website": False},
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  📄 Blog:     {md_path.name}")
    print(f"  🌐 Review:   {html_path.name}")
    print(f"  ✨ Publish:  {publish_path.name}")
    if images:
        print(f"  🖼  Images:  {len(images)} saved to {img_dir.name}/")

    return {"md": md_path, "html": html_path, "publish": publish_path, "meta": meta_path, "images": images}


# ── Telegram Delivery ──────────────────────────────────────────────────────────
def _load_telegram_creds() -> dict:
    env_path = Path(__file__).parent.parent.parent / "scratch" / "gravity-claw" / ".env"
    creds = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                creds[k.strip()] = v.strip().strip('"')
    return creds


def send_to_telegram(biz_key: str, keyword: str, paths: dict, content: dict) -> bool:
    try:
        import requests
    except ImportError:
        print("  ❌ Telegram: install requests (pip install requests)")
        return False

    creds  = _load_telegram_creds()
    token  = creds.get("TELEGRAM_BOT_TOKEN")
    chat_id = creds.get("TELEGRAM_USER_ID")
    if not token or not chat_id:
        print("  ❌ Telegram credentials not found in .env")
        return False

    base_url = f"https://api.telegram.org/bot{token}"
    biz   = BUSINESSES[biz_key]
    today = date.today().strftime("%B %d, %Y")
    images = paths.get("images", {})
    sent  = 0

    # 1. _PUBLISH.html — beautiful publication page
    publish_path = paths.get("publish") or paths.get("html")
    try:
        with open(publish_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/sendDocument",
                data={"chat_id": chat_id,
                      "caption": (f"✨ PUBLICATION DRAFT — {biz['name']}\n"
                                  f"\"{keyword}\"\n{today}\n\n"
                                  f"Open in browser — images are embedded.\n"
                                  f"SEO score: {content['score'].get('total', 0)}/100 "
                                  f"| {content['word_count']} words")},
                files={"document": (publish_path.name, f, "text/html")},
                timeout=30,
            )
        if resp.ok:
            sent += 1
        else:
            print(f"  ⚠️  Telegram HTML failed: {resp.text[:80]}")
    except Exception as e:
        print(f"  ⚠️  Telegram HTML error: {e}")

    # 2. GBP post text
    gbp_msg = (f"📍 *GBP POST — {biz['name']}*\n_{keyword}_\n\n"
               f"{content['gbp']}\n\n"
               f"_{len(content['gbp'])} chars (max 1,500)_")
    try:
        requests.post(f"{base_url}/sendMessage",
                      json={"chat_id": chat_id, "text": gbp_msg, "parse_mode": "Markdown"},
                      timeout=10)
        sent += 1
    except Exception:
        pass

    # 3. Facebook post copy
    fb_msg = (f"📱 *FACEBOOK POST — {biz['name']}*\n_{keyword}_\n\n"
              f"{content['fb_copy']}\n\n"
              f"🖼 *Hero image prompt:*\n_{content['image_prompt']}_")
    try:
        requests.post(f"{base_url}/sendMessage",
                      json={"chat_id": chat_id, "text": fb_msg, "parse_mode": "Markdown"},
                      timeout=10)
        sent += 1
    except Exception:
        pass

    # 4. Hero image as photo (if generated)
    hero_path = images.get("hero")
    if hero_path and Path(hero_path).exists():
        try:
            with open(hero_path, "rb") as f:
                resp = requests.post(
                    f"{base_url}/sendPhoto",
                    data={"chat_id": chat_id,
                          "caption": f"🖼 Hero image — {biz['name']} · \"{keyword}\""},
                    files={"photo": ("hero.png", f, "image/png")},
                    timeout=30,
                )
            if resp.ok:
                sent += 1
        except Exception as e:
            print(f"  ⚠️  Hero photo send failed: {e}")
    else:
        print("  ℹ️  No hero image to send (generation may have failed)")

    # 5. Publish command reminder
    cmd_msg = (f"✅ *Review complete? Run to publish:*\n"
               f"`python blog_writer.py --client {biz_key} --keyword \"{keyword}\" --publish`\n\n"
               f"Or specific channels:\n"
               f"`--publish --channels gbp,facebook`")
    try:
        requests.post(f"{base_url}/sendMessage",
                      json={"chat_id": chat_id, "text": cmd_msg, "parse_mode": "Markdown"},
                      timeout=10)
        sent += 1
    except Exception:
        pass

    print(f"  ✅ Telegram: {sent}/5 messages sent")
    return sent >= 3


# ── Publishing ─────────────────────────────────────────────────────────────────
def find_latest_meta(biz_key: str, keyword: str) -> dict | None:
    slug = keyword_to_slug(keyword)
    out_dir = BLOG_DIR / biz_key
    if not out_dir.exists():
        return None
    pattern = f"*_{slug}_meta.json"
    matches = sorted(out_dir.glob(pattern), reverse=True)
    if not matches:
        return None
    meta = json.loads(matches[0].read_text(encoding="utf-8"))
    meta["_meta_path"] = matches[0]
    meta["_md_path"]   = matches[0].with_name(matches[0].name.replace("_meta.json", ".md"))
    return meta


def publish_gbp(biz_key: str, meta: dict) -> bool:
    biz = BUSINESSES[biz_key]
    gbp_key = biz.get("gbp_key")
    if not gbp_key:
        print(f"  ⚠️  GBP: no GBP key configured for {biz_key} — skipping")
        return False

    gbp_poster = EXECUTION_DIR / "gbp_post_custom_designs.py"
    if not gbp_poster.exists():
        print("  ❌ GBP: gbp_post_custom_designs.py not found")
        return False

    print(f"  📍 GBP: posting for {biz['name']}...")
    gbp_text = meta["gbp"]
    temp_script = EXECUTION_DIR / "_gbp_blog_post_temp.py"

    # Build search terms from business name + known GBP aliases
    gbp_name_upper = biz["name"].upper()
    gbp_aliases = {
        "optimum_clinic": ["OPTIMUM", "CASH NIGHT CLINIC"],
        "sugar_shack": ["SUGAR SHACK"],
        "island_candy": ["ISLAND CANDY"],
        "custom_designs": ["CUSTOM DESIGNS"],
    }
    search_terms = gbp_aliases.get(gbp_key, [gbp_name_upper[:12].upper()])
    js_search = " || ".join(f'txt.includes("{t}")' for t in search_terms)

    # JS strings stored as Python variables to avoid brace-escaping inside f-string
    js_find_btn = (
        "() => {"
        "  const rows = Array.from(document.querySelectorAll('tr'));"
        "  for (let row of rows) {"
        "    const txt = row.textContent.toUpperCase();"
        f"    if ({js_search}) {{"
        "      const btns = row.querySelectorAll('a, button, [role=\"button\"]');"
        "      for (let btn of btns) {"
        "        const aria = (btn.getAttribute('aria-label') || '').toLowerCase();"
        "        const title = (btn.getAttribute('title') || '').toLowerCase();"
        "        const text = btn.textContent.trim().toLowerCase();"
        "        if (aria === 'create post' || title === 'create post' ||"
        "            aria.includes('add update') || title.includes('add update')) {"
        "          btn.click(); return aria || title || text || 'clicked';"
        "        }"
        "      }"
        "      const ab = Array.from(row.querySelectorAll('button, [role=\"button\"]'))"
        "        .filter(b => !b.textContent.includes('See your profile') && !b.textContent.includes('Manage profile'));"
        "      if (ab.length >= 3) { ab[2].click(); return '3rd-icon-clicked'; }"
        "    }"
        "  }"
        "  const all = Array.from(document.querySelectorAll('button, [role=\"button\"]'));"
        "  for (let btn of all) {"
        "    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();"
        "    if (aria.includes('add update') || aria.includes('create post')) { btn.click(); return 'global-' + aria; }"
        "  }"
        "  return null;"
        "}"
    )
    js_click_post = (
        "() => {"
        "  const btns = Array.from(document.querySelectorAll('button'));"
        "  for (let b of btns) { if (b.textContent.trim() === 'Post') { b.click(); return true; } }"
        "  return false;"
        "}"
    )

    temp_script.write_text(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path({repr(str(EXECUTION_DIR))})
POST_TEXT = {repr(gbp_text)}
JS_FIND_BTN = {repr(js_find_btn)}
JS_CLICK_POST = {repr(js_click_post)}

async def post():
    from playwright.async_api import async_playwright
    profile_map = {{
        "sugar_shack":   str(SCRIPT_DIR / "gbp_sniffer_profile"),
        "island_candy":  str(SCRIPT_DIR / "gbp_sniffer_profile"),
        "custom_designs": str(SCRIPT_DIR / "gbp_mario_profile"),
    }}
    profile = profile_map.get({repr(gbp_key)}, str(SCRIPT_DIR / "gbp_mario_profile"))
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=profile, headless=False,
            args=["--start-maximized"], no_viewport=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://business.google.com/locations", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(SCRIPT_DIR / "gbp_{gbp_key}_step1_locations.png"))

        post_clicked = await page.evaluate(JS_FIND_BTN)
        print(f"GBP find-btn result: {{post_clicked}}")
        if not post_clicked:
            print("GBP_POST_FAIL: Could not find post button")
            await ctx.close()
            return

        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(SCRIPT_DIR / "gbp_{gbp_key}_step2_modal.png"))

        modal_frame = page
        for frame in page.frames:
            try:
                content = await frame.content()
                if "Description" in content or "Add post" in content or "Select images" in content:
                    modal_frame = frame
                    break
            except Exception:
                pass

        filled = False
        try:
            desc = modal_frame.locator('textarea[placeholder="Description"]').first
            await desc.wait_for(timeout=5000)
            await desc.click()
            await page.wait_for_timeout(300)
            await desc.fill(POST_TEXT)
            filled = True
        except Exception:
            pass
        if not filled:
            try:
                desc = modal_frame.locator('textarea').first
                await desc.wait_for(timeout=10000)
                await desc.click()
                await desc.fill(POST_TEXT)
                filled = True
            except Exception as e:
                print(f"GBP_POST_FAIL: textarea error: {{e}}")
                await ctx.close()
                return

        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCRIPT_DIR / "gbp_{gbp_key}_step3_filled.png"))
        published = False
        try:
            post_btn = modal_frame.locator('button:has-text("Post")').last
            await post_btn.wait_for(timeout=5000)
            await post_btn.click()
            published = True
        except Exception:
            for frame in page.frames:
                try:
                    if await frame.evaluate(JS_CLICK_POST):
                        published = True
                        break
                except Exception:
                    pass

        await page.wait_for_timeout(4000)
        await page.screenshot(path=str(SCRIPT_DIR / "gbp_{gbp_key}_step4_result.png"))
        print("GBP_POST_OK" if published else "GBP_POST_FAIL: Post button not clicked")
        await ctx.close()

asyncio.run(post())
""", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(temp_script)],
        capture_output=True, text=True, timeout=60, encoding="utf-8"
    )
    temp_script.unlink(missing_ok=True)
    if "GBP_POST_OK" in result.stdout:
        print("  ✅ GBP: posted successfully")
        return True
    else:
        print(f"  ❌ GBP: {result.stderr.strip()[-200:] or result.stdout.strip()[-200:]}")
        return False


def publish_facebook(biz_key: str, meta: dict) -> bool:
    biz = BUSINESSES[biz_key]
    page_key = biz.get("page_key")
    if not page_key:
        print(f"  ⚠️  Facebook: no page key for {biz_key}")
        return False

    fb_copy = meta["fb_copy"]
    image_prompt = meta.get("image_prompt", "")

    # Use pre-generated hero image if available (generated at blog creation time)
    image_path = None
    hero_str = meta.get("images", {}).get("hero", "")
    if hero_str and Path(hero_str).exists():
        image_path = Path(hero_str)
        print(f"  🖼  Facebook: using pre-generated hero image")
    elif image_prompt:
        # Fall back: generate now via fal_client SDK
        print("  🖼  Facebook: generating image via fal.ai...")
        slug = keyword_to_slug(meta["keyword"])
        out_dir = BLOG_DIR / biz_key
        image_path = out_dir / f"{meta['generated']}_{slug}_hero.png"
        try:
            prompts = {"hero": image_prompt}
            results = generate_blog_images(prompts, out_dir, biz_key=biz_key)
            if results.get("hero"):
                image_path = results["hero"]
                # Rename to expected name
                target = out_dir / f"{meta['generated']}_{slug}_hero.png"
                image_path.rename(target)
                image_path = target
        except Exception as e:
            print(f"  ⚠️  Image generation failed: {e} — posting text only")
            image_path = None

    fb_script = EXECUTION_DIR / "facebook_marketer.py"
    if not fb_script.exists():
        print("  ❌ Facebook: facebook_marketer.py not found")
        return False

    print(f"  📱 Facebook: posting to {page_key}...")
    if image_path and image_path.exists():
        cmd = [sys.executable, str(fb_script), "--action", "image",
               "--page", page_key, "--message", fb_copy, "--media", str(image_path)]
    else:
        cmd = [sys.executable, str(fb_script), "--action", "text",
               "--page", page_key, "--message", fb_copy]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                            encoding="utf-8", errors="replace")
    if result.returncode == 0:
        print("  ✅ Facebook: posted")
        return True
    else:
        print(f"  ❌ Facebook: {result.stderr.strip()[-200:]}")
        return False


def _slug_to_component(slug: str) -> str:
    """Convert kebab-case slug to PascalCase component name."""
    return "".join(w.capitalize() for w in slug.replace("-", "_").split("_"))


def _pick_blog_image(keyword: str) -> str:
    """Select the most relevant existing blog asset image for a keyword."""
    kw = keyword.lower()
    mapping = [
        (["security camera", "cctv", "surveillance"], "security-camera-rgv-home.jpg"),
        (["security alarm", "alarm system", "home security"], "security-panel-hero.jpg"),
        (["commercial security"], "commercial-security-cameras-building.jpg"),
        (["home theater", "theater", "cinema"], "home-theater-luxury-room.jpg"),
        (["outdoor entertainment", "outdoor tv", "patio"], "outdoor-entertainment-luxury-patio.jpg"),
        (["multi room audio", "multiroom", "whole home audio", "speakers"], "multiroom-audio-living-room.jpg"),
        (["lighting", "smart light"], "outdoor-landscape-lighting.jpg"),
        (["fiber optic", "networking", "network", "wifi", "internet"], "fiber-optic-installation.jpg"),
        (["motorized shade", "window shade", "blind"], "motorized-shades-living-room.jpg"),
        (["tv mount", "tv wall", "display"], "outdoor-tv-patio-mount.jpg"),
        (["intercom", "doorbell", "video doorbell"], "video-doorbell-front-door.jpg"),
        (["smart lock", "keyless", "access control"], "smart-lock-front-door.jpg"),
        (["gate", "electric gate", "gate automation"], "automatic-gate-driveway.jpg"),
        (["smart home", "home automation", "automation"], "smart-home-control-panel.jpg"),
        (["thermostat", "climate", "hvac"], "smart-thermostat-living-room.jpg"),
        (["structured wiring", "prewire", "wiring"], "structured-wiring-panel.jpg"),
        (["commercial av", "conference", "boardroom"], "commercial-conference-av-system.jpg"),
    ]
    for keywords_list, image in mapping:
        if any(k in kw for k in keywords_list):
            return image
    return "security-camera-rgv-home.jpg"


def _parse_md_sections(md_content: str) -> list:
    """Parse H2 sections from markdown. Returns list of {heading, body}."""
    # Strip YAML frontmatter
    if md_content.startswith("---"):
        end = md_content.find("---", 3)
        if end != -1:
            md_content = md_content[end + 3:].strip()
    sections = []
    current_heading = None
    current_body = []
    for line in md_content.splitlines():
        if line.startswith("## "):
            if current_heading:
                sections.append({"heading": current_heading, "body": "\n".join(current_body).strip()})
            current_heading = line[3:].strip()
            current_body = []
        elif not line.startswith("# "):
            current_body.append(line)
    if current_heading:
        sections.append({"heading": current_heading, "body": "\n".join(current_body).strip()})
    return sections


def _md_body_to_jsx(body: str) -> str:
    """Convert simple markdown body text to JSX paragraphs and lists."""
    lines = body.splitlines()
    jsx_parts = []
    in_list = False
    list_items = []
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                items_jsx = "\n".join(f'            <li key={{i}} className="flex gap-2 text-slate-300"><span className="text-red-400 mt-1">•</span>{li}</li>'
                                      for i, li in enumerate(list_items))
                jsx_parts.append(f'          <ul className="space-y-2 mb-4">\n{items_jsx}\n          </ul>')
                list_items = []
                in_list = False
            continue
        if line.startswith("- ") or line.startswith("* "):
            in_list = True
            item = line[2:].replace("**", "").strip()
            list_items.append(item)
        elif line.startswith("| ") or line.startswith("|---"):
            continue  # skip tables
        elif not line.startswith("#"):
            if in_list:
                items_jsx = "\n".join(f'            <li key={{i}} className="flex gap-2 text-slate-300"><span className="text-red-400 mt-1">•</span>{li}</li>'
                                      for i, li in enumerate(list_items))
                jsx_parts.append(f'          <ul className="space-y-2 mb-4">\n{items_jsx}\n          </ul>')
                list_items = []
                in_list = False
            # Convert **bold** to <strong>
            text = re.sub(r"\*\*(.+?)\*\*", r'<strong className="text-white">\1</strong>', line)
            jsx_parts.append(f'          <p className="text-slate-300 text-lg leading-relaxed mb-4">{text}</p>')
    if in_list and list_items:
        items_jsx = "\n".join(f'            <li key={{i}} className="flex gap-2 text-slate-300"><span className="text-red-400 mt-1">•</span>{li}</li>'
                              for i, li in enumerate(list_items))
        jsx_parts.append(f'          <ul className="space-y-2 mb-4">\n{items_jsx}\n          </ul>')
    return "\n".join(jsx_parts)


def _generate_blog_tsx(meta: dict, md_content: str, component_name: str) -> str:
    """Generate a React TSX blog component following the Lovable.dev Custom Designs pattern."""
    keyword = meta["keyword"]
    slug = keyword_to_slug(keyword)

    # Extract frontmatter fields
    title = ""
    meta_desc = ""
    fm_match = re.match(r"^---\n(.*?)\n---", md_content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        t = re.search(r'^title:\s*(.+)$', fm, re.MULTILINE)
        d = re.search(r'^meta_description:\s*(.+)$', fm, re.MULTILINE)
        if t:
            title = t.group(1).strip().strip('"')
        if d:
            meta_desc = d.group(1).strip().strip('"')

    if not title:
        title = " ".join(w.capitalize() for w in keyword.split()) + " | Custom Designs TX"
    if not meta_desc:
        meta_desc = f"Professional {keyword} services in the Rio Grande Valley. Free consultation from Custom Designs TX."

    sections = _parse_md_sections(md_content)
    hero_image_file = _pick_blog_image(keyword)
    # Use a secondary image for section breaks
    secondary_images = {
        "security camera": ("security-install-outdoor.jpg", "security-app-phone.jpg"),
        "home theater": ("family-home-theater.jpg", "hidden-audio-speakers.jpg"),
        "outdoor entertainment": ("outdoor-kitchen-entertainment.jpg", "outdoor-landscape-speakers.jpg"),
    }
    sec_imgs = ("security-install-outdoor.jpg", "security-smartphone-app.jpg")
    for k, imgs in secondary_images.items():
        if k in keyword.lower():
            sec_imgs = imgs
            break

    # Build info cards from first 4 sections
    card_icons = ["Shield", "CheckCircle", "Zap", "Award", "MapPin", "Phone"]
    info_cards_jsx = ""
    for i, sec in enumerate(sections[:4]):
        icon = card_icons[i % len(card_icons)]
        heading = sec["heading"][:40]
        # First sentence of body as description
        first_sent = sec["body"].split(".")[0].replace("**", "").strip()[:80] + "."
        info_cards_jsx += f"""    {{
      title: "{heading}",
      description: "{first_sent}",
      icon: <{icon} className="w-6 h-6" />
    }},
"""

    # Build content sections JSX
    content_sections_jsx = ""
    for i, sec in enumerate(sections):
        body_jsx = _md_body_to_jsx(sec["body"])
        # Insert section image after sections 1 and 3
        img_jsx = ""
        if i == 1:
            img_jsx = f"""
        <div className="my-8 rounded-2xl overflow-hidden">
          <img src={{img1}} alt="{sec['heading']}" className="w-full h-64 object-cover" />
        </div>"""
        elif i == 3:
            img_jsx = f"""
        <div className="my-8 rounded-2xl overflow-hidden">
          <img src={{img2}} alt="{sec['heading']}" className="w-full h-64 object-cover" />
        </div>"""

        content_sections_jsx += f"""
        <motion.section className="mb-12" {{...fadeIn}}>
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-6">
            {sec['heading']}
          </h2>
{body_jsx}{img_jsx}
        </motion.section>
"""

    # Service areas — pre-built JSX spans to avoid {} escaping inside f-string
    cities = ["McAllen", "Brownsville", "Harlingen", "Edinburg", "Mission", "Pharr", "Weslaco", "South Padre Island"]
    cities_jsx = "\n".join(
        f'              <span className="px-4 py-2 bg-slate-800/50 rounded-full text-slate-300 border border-slate-700/50">{c}</span>'
        for c in cities
    )

    today = datetime.today().strftime("%B %d, %Y")

    return f"""import React from 'react';
import {{ Helmet }} from 'react-helmet';
import {{ Link }} from 'react-router-dom';
import {{ motion }} from 'framer-motion';
import {{ Phone, CheckCircle, Shield, Zap, Award, MapPin }} from 'lucide-react';
import {{ Button }} from '@/components/ui/button';
import BlogHeroTemplate from '@/components/blog/BlogHeroTemplate';

import heroImage from '@/assets/blog/{hero_image_file}';
import img1 from '@/assets/blog/{sec_imgs[0]}';
import img2 from '@/assets/blog/{sec_imgs[1]}';

const fadeIn = {{
  initial: {{ opacity: 0, y: 20 }},
  whileInView: {{ opacity: 1, y: 0 }},
  viewport: {{ once: true }},
  transition: {{ duration: 0.5 }}
}};

const {component_name} = () => {{
  const infoCards = [
{info_cards_jsx}  ];

  return (
    <>
      <Helmet>
        <title>{title}</title>
        <meta name="description" content="{meta_desc}" />
        <link rel="canonical" href="https://www.customdesignstx.com/blog/{slug}" />
        <meta property="og:title" content="{title}" />
        <meta property="og:description" content="{meta_desc}" />
        <meta property="og:image" content={{heroImage}} />
        <meta property="og:type" content="article" />
        <script type="application/ld+json">
          {{JSON.stringify({{
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "{title}",
            "image": heroImage,
            "author": {{ "@type": "Organization", "name": "Custom Designs TX" }},
            "publisher": {{ "@type": "Organization", "name": "Custom Designs TX" }},
            "datePublished": "{today}",
            "description": "{meta_desc}"
          }})}}
        </script>
      </Helmet>

      <article className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900">
        <BlogHeroTemplate
          title="{' '.join(keyword.title().split()[:3])}"
          titleHighlight="{' '.join(keyword.title().split()[3:]) or 'McAllen TX'}"
          subtitle="{meta_desc[:120]}"
          heroImage={{heroImage}}
          infoCards={{infoCards}}
          ctaText="Get a FREE Consultation!"
          publishDate="{today}"
          readTime="8 min read"
        />

        <div className="container mx-auto max-w-4xl px-4 py-12">
{content_sections_jsx}
          {{/* Service Areas */}}
          <motion.section className="mb-12" {{...fadeIn}}>
            <h2 className="text-2xl font-bold text-white mb-6 text-center">
              Serving the <span className="text-red-400">Rio Grande Valley</span>
            </h2>
            <div className="flex flex-wrap justify-center gap-3">
{cities_jsx}
            </div>
          </motion.section>

          {{/* CTA */}}
          <motion.section {{...fadeIn}}>
            <div className="bg-gradient-to-r from-red-600 to-rose-700 rounded-3xl p-8 md:p-12 text-center">
              <h2 className="text-3xl font-bold text-white mb-4">Ready to Get Started?</h2>
              <p className="text-white/90 text-lg mb-8 max-w-xl mx-auto">
                Schedule your free consultation today. We come to you, assess your space, and recommend the right solution.
              </p>
              <div className="flex flex-wrap justify-center gap-4">
                <Button asChild size="lg" className="bg-white text-red-700 hover:bg-slate-100">
                  <a href="tel:9569727673">
                    <Phone className="w-5 h-5 mr-2" />
                    Call (956) 972-7673
                  </a>
                </Button>
                <Button asChild size="lg" variant="outline" className="border-white text-white hover:bg-white/10">
                  <Link to="/contact">Get Free Quote</Link>
                </Button>
              </div>
            </div>
          </motion.section>
        </div>
      </article>
    </>
  );
}};

export default {component_name};
"""


def publish_website(biz_key: str, meta: dict) -> bool:
    biz = BUSINESSES[biz_key]
    if not biz.get("has_website"):
        print(f"  ⚠️  Website: {biz_key} has no website configured — skipping")
        return False

    # Per-business GitHub repo mapping (Lovable.dev React + Vite projects)
    github_repos = {
        "custom_designs_tx": ("mar2181/custom-designs", "https://www.customdesignstx.com"),
    }
    if biz_key not in github_repos:
        print(f"  ⚠️  Website: no GitHub repo mapped for {biz_key} — manual publish needed")
        print(f"  📋 Content saved to {BLOG_DIR / biz_key}/")
        return False

    github_repo, site_url = github_repos[biz_key]
    slug = keyword_to_slug(meta["keyword"])
    blog_url = f"{site_url}/blog/{slug}"
    component_name = _slug_to_component(slug)
    print(f"  🌐 Website: publishing to {blog_url}...")

    import tempfile, shutil
    tmp_dir = Path(tempfile.mkdtemp(prefix="blog_publish_"))
    try:
        # Clone the repo
        r = subprocess.run(
            ["git", "clone", f"https://github.com/{github_repo}.git", str(tmp_dir), "--depth=1"],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode != 0:
            print(f"  ❌ Website: git clone failed — {r.stderr.strip()[:150]}")
            return False

        router_path = tmp_dir / "src" / "pages" / "blog" / "StaticBlogRouter.tsx"
        static_blogs_path = tmp_dir / "src" / "data" / "staticBlogs.ts"
        static_dir = tmp_dir / "src" / "pages" / "blog" / "static"

        router_content = router_path.read_text(encoding="utf-8")

        # Check if slug already exists AND component file is present
        component_file = static_dir / f"{component_name}.tsx"
        if f"'{slug}'" in router_content and component_file.exists():
            print(f"  ✅ Website: page already live → {blog_url}")
            return True
        elif f"'{slug}'" in router_content and not component_file.exists():
            print(f"  ⚠️  Website: slug in router but component file missing — republishing...")

        # Read generated markdown content
        md_path = BLOG_DIR / biz_key / f"{meta['generated']}_{slug}.md"
        if not md_path.exists():
            print(f"  ❌ Website: markdown file not found at {md_path}")
            return False
        md_content = md_path.read_text(encoding="utf-8")

        # 1. Generate the TSX component file
        tsx_content = _generate_blog_tsx(meta, md_content, component_name)
        tsx_path = static_dir / f"{component_name}.tsx"
        tsx_path.write_text(tsx_content, encoding="utf-8")
        print(f"  📝 Generated: src/pages/blog/static/{component_name}.tsx")

        # 2. Patch StaticBlogRouter.tsx — add import + slug map entry
        # Add lazy import after the last existing import
        last_import_pos = router_content.rfind("React.lazy(() => import('./static/")
        if last_import_pos != -1:
            line_end = router_content.find("\n", last_import_pos) + 1
            new_import = f"const {component_name} = React.lazy(() => import('./static/{component_name}'));\n"
            router_content = router_content[:line_end] + new_import + router_content[line_end:]
        # Add slug map entry before the closing }; of blogComponents
        map_entry = f"  '{slug}': {component_name},\n"
        close_pos = router_content.rfind("};")
        router_content = router_content[:close_pos] + map_entry + router_content[close_pos:]
        router_path.write_text(router_content, encoding="utf-8")
        print(f"  🔗 Registered in StaticBlogRouter.tsx")

        # 3. Patch staticBlogs.ts — add metadata entry
        blogs_content = static_blogs_path.read_text(encoding="utf-8")
        # Extract title and excerpt from markdown frontmatter
        fm_match = re.match(r"^---\n(.*?)\n---", md_content, re.DOTALL)
        post_title = meta["keyword"].title() + " | Custom Designs TX"
        post_excerpt = meta.get("gbp", "")[:160].replace('"', "'").replace("\n", " ")
        if fm_match:
            fm = fm_match.group(1)
            t = re.search(r'^title:\s*(.+)$', fm, re.MULTILINE)
            d = re.search(r'^meta_description:\s*(.+)$', fm, re.MULTILINE)
            if t:
                post_title = t.group(1).strip().strip('"')
            if d:
                post_excerpt = d.group(1).strip().strip('"')[:160]

        today_long = datetime.today().strftime("%B %d, %Y")
        image_file = _pick_blog_image(meta["keyword"])
        image_var = image_file.replace("-", "_").replace(".jpg", "").replace(".png", "")
        # Check if image var is already imported
        if f"import {image_var} from" not in blogs_content:
            # Find a good insertion point (after last import statement)
            last_import = blogs_content.rfind("import ")
            import_end = blogs_content.find("\n", last_import) + 1
            blogs_content = blogs_content[:import_end] + f'import {image_var} from "@/assets/blog/{image_file}";\n' + blogs_content[import_end:]

        new_entry = f"""  {{
    id: "{slug}",
    slug: "{slug}",
    title: "{post_title}",
    excerpt: "{post_excerpt}",
    author: "Custom Designs",
    category: "Security",
    date: "{today_long}",
    image: {image_var},
    images: [
      {{ url: {image_var}, caption: "{meta['keyword'].title()}" }},
    ],
    component: "{component_name}"
  }},
"""
        # Insert at start of staticBlogs array
        array_start = blogs_content.find("export const staticBlogs: StaticBlogPost[] = [")
        insert_pos = blogs_content.find("\n", array_start) + 1
        blogs_content = blogs_content[:insert_pos] + new_entry + blogs_content[insert_pos:]
        static_blogs_path.write_text(blogs_content, encoding="utf-8")
        print(f"  📋 Registered in staticBlogs.ts")

        # 4. Commit and push
        git_cmds = [
            ["git", "-C", str(tmp_dir), "config", "user.email", "hssolutions2181@gmail.com"],
            ["git", "-C", str(tmp_dir), "config", "user.name", "Antigravity Digital"],
            ["git", "-C", str(tmp_dir), "add", "."],
            ["git", "-C", str(tmp_dir), "commit", "-m",
             f"Add {slug} blog\n\nGenerated by Antigravity Digital blog writer.\nKeyword: {meta['keyword']}"],
            ["git", "-C", str(tmp_dir), "push", "origin", "main"],
        ]
        for cmd in git_cmds:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if r.returncode != 0 and "commit" in " ".join(cmd):
                print(f"  ❌ Website: git {cmd[-2]} failed — {r.stderr.strip()[:120]}")
                return False

        print(f"  ✅ Website: pushed to GitHub → Vercel deploying (~1-2 min)")
        print(f"  🌐 Live URL: {blog_url}")
        return True

    except Exception as e:
        print(f"  ❌ Website: {e}")
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def publish_all(biz_key: str, keyword: str, channels: list[str]) -> None:
    meta = find_latest_meta(biz_key, keyword)
    if not meta:
        print(f"❌ No generated content found for {biz_key} / \"{keyword}\"")
        print(f"   Run first: python blog_writer.py --client {biz_key} --keyword \"{keyword}\"")
        sys.exit(1)

    print(f"\n[publish] {BUSINESSES[biz_key]['name']} — \"{keyword}\"")

    published = meta.get("published", {})
    if not channels or "gbp" in channels:
        ok = publish_gbp(biz_key, meta)
        if ok:
            published["gbp"] = True
    if not channels or "facebook" in channels:
        ok = publish_facebook(biz_key, meta)
        if ok:
            published["facebook"] = True
    if not channels or "web" in channels or "website" in channels:
        ok = publish_website(biz_key, meta)
        if ok:
            published["website"] = True

    # Update meta
    meta["published"] = published
    meta_path = meta.get("_meta_path")
    if meta_path:
        clean = {k: v for k, v in meta.items() if not k.startswith("_")}
        Path(meta_path).write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────────────
def process_keyword(biz_key: str, keyword: str, preview: bool = False,
                    send_telegram: bool = True) -> None:
    print(f"\n[{biz_key}] \"{keyword}\"")

    # Scrape competitor
    print("  Fetching competitor URL from rankings...")
    comp_url = get_competitor_url(biz_key, keyword)
    competitor = {}
    if comp_url:
        print(f"  Scraping: {comp_url[:70]}...")
        competitor = scrape_top_result(comp_url)
        if competitor.get("scraped"):
            print(f"  Competitor: {competitor['word_count']} words, {len(competitor.get('h2_headers',[]))} H2s")
        else:
            print(f"  Scrape failed ({competitor.get('error','')[:60]}) — generating from keyword only")
    else:
        print("  No competitor URL in rankings — generating from keyword only")

    # Generate
    client = anthropic.Anthropic(api_key=get_api_key())
    content = generate_content(client, biz_key, keyword, competitor)
    print(f"  Generated: {content['word_count']} words, score {content['score'].get('total',0)}/100")

    # Save
    paths = save_content(biz_key, content)

    # Telegram
    if send_telegram:
        send_to_telegram(biz_key, keyword, paths, content)

    # Preview — open the beautiful publication page, not the internal review
    if preview:
        preview_target = paths.get("publish") or paths.get("html")
        webbrowser.open(preview_target.as_uri())
        print("  🌐 Opened _PUBLISH.html in browser")


def main():
    parser = argparse.ArgumentParser(description="SEO Blog Writer — Generate + Publish")
    parser.add_argument("--client",   help="Business key (e.g. custom_designs_tx)")
    parser.add_argument("--keyword",  help="Keyword to target")
    parser.add_argument("--all",      action="store_true", help="Process all blog-intent keywords")
    parser.add_argument("--list",     action="store_true", help="List blog-intent keywords (dry run)")
    parser.add_argument("--force",    action="store_true", help="Generate even for transactional keywords")
    parser.add_argument("--publish",  action="store_true", help="Publish previously generated content")
    parser.add_argument("--channels", help="Comma-separated: gbp,facebook,web (default: all active)")
    parser.add_argument("--preview",  action="store_true", help="Open HTML in browser after generation")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram delivery")
    args = parser.parse_args()

    if not args.client:
        parser.print_help()
        sys.exit(1)
    if args.client not in BUSINESSES:
        print(f"Unknown client: {args.client}")
        print(f"Valid: {', '.join(BUSINESS_ORDER)}")
        sys.exit(1)

    biz_key = args.client
    cfg_path = EXECUTION_DIR / "keyword_rankings_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    keywords = cfg["businesses"].get(biz_key, {}).get("keywords", [])
    channels = [c.strip() for c in args.channels.split(",")] if args.channels else []
    send_tg = not args.no_telegram

    # --list
    if args.list:
        print(f"\nKeyword intent triage for {BUSINESSES[biz_key]['name']}:")
        for kw in keywords:
            intent = classify_keyword(kw)
            icon = {"blog": "✅", "maybe": "🟡", "skip": "⛔"}[intent]
            print(f"  {icon} [{intent}] {kw}")
        return

    # --publish
    if args.publish:
        if not args.keyword:
            print("❌ --publish requires --keyword")
            sys.exit(1)
        publish_all(biz_key, args.keyword, channels)
        return

    # --keyword
    if args.keyword:
        intent = classify_keyword(args.keyword)
        if intent == "skip" and not args.force:
            print(f"⚠️  \"{args.keyword}\" looks transactional — blog content unlikely to rank.")
            print("   Use --force to generate anyway.")
            sys.exit(0)
        process_keyword(biz_key, args.keyword, preview=args.preview, send_telegram=send_tg)
        return

    # --all
    if args.all:
        blog_keywords = [kw for kw in keywords if classify_keyword(kw) == "blog"]
        if not blog_keywords:
            print(f"No blog-intent keywords found for {biz_key}. Use --list to see all, --keyword + --force to override.")
            sys.exit(0)
        print(f"\nProcessing {len(blog_keywords)} blog-intent keywords for {BUSINESSES[biz_key]['name']}...")
        for kw in blog_keywords:
            process_keyword(biz_key, kw, preview=False, send_telegram=send_tg)
        print(f"\n✅ Done. {len(blog_keywords)} posts generated → {BLOG_DIR / biz_key}/")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
