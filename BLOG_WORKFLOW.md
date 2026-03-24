# Blog Writer Workflow — Antigravity Digital

## Pipeline Overview

```
keyword
  → intent triage (blog / maybe / skip)
  → competitor URL from keyword_rankings_state.json
  → scrape competitor (word count, H2s, title)
  → Claude Sonnet generates: blog + GBP post + FB post + 4 image prompts
  → Haiku scores blog (0-100) → auto-rewrite if < 70
  → fal.ai generates: hero (16:9) + 3 section images (square)
  → saves: .md + .html (review) + _PUBLISH.html (beautiful page) + _meta.json + images/
  → Telegram: 5 messages → review
  → approve → python blog_writer.py --publish → GBP + Facebook + website
```

---

## CLI Commands

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# See which keywords are worth blogging (triage only, no generation)
python blog_writer.py --client custom_designs_tx --list

# Generate everything for one keyword → send to Telegram
python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx"

# Generate + open _PUBLISH.html in browser immediately
python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --preview

# Generate without Telegram delivery
python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --no-telegram

# Generate even for transactional/skip keywords
python blog_writer.py --client sugar_shack --keyword "candy store spi" --force

# Process all blog-intent keywords for a client
python blog_writer.py --client optimum_clinic --all

# Publish previously generated content (all active channels)
python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --publish

# Publish to specific channels only
python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --publish --channels gbp
python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --publish --channels facebook
python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx" --publish --channels gbp,facebook
```

---

## Output Files

For each keyword, these files are created in `blog_posts/{client}/`:

| File | Purpose |
|---|---|
| `{date}_{slug}.md` | Markdown blog post with YAML frontmatter |
| `{date}_{slug}.html` | Internal review HTML (score breakdown, all 3 content pieces) |
| `{date}_{slug}_PUBLISH.html` | Beautiful publication page — hero + inline section images (self-contained, base64 images) |
| `{date}_{slug}_meta.json` | Metadata + publish state tracking (`published.gbp`, `published.facebook`, `published.website`) |
| `images/{date}_{slug}/hero.png` | Hero image (landscape 16:9) — also used as Facebook image |
| `images/{date}_{slug}/section_1.png` | Section image after H2 #1 (square) |
| `images/{date}_{slug}/section_2.png` | Section image after H2 #3 (square) |
| `images/{date}_{slug}/section_3.png` | Section image after H2 #5 / CTA (square) |

---

## Telegram Delivery (5 Messages)

1. **`_PUBLISH.html`** — Full publication page as a document. Open in browser to see the real layout with images.
2. **GBP post text** — Inline, ready to copy. Max 1,500 chars.
3. **Facebook post copy** — Inline with hero image prompt. Max 300 words.
4. **Hero image** — Sent as a photo for quick preview in Telegram.
5. **Publish command** — Copy-paste command to post to all active channels.

---

## Approval Gate

```
Generate → Review on Telegram → Run --publish

1. python blog_writer.py --client X --keyword "..."
   (sends to Telegram, 4-5 min for images)

2. Review the _PUBLISH.html in browser (hero + section images + article layout)
   Check: GBP text length, FB copy, image quality

3. python blog_writer.py --client X --keyword "..." --publish
   (posts to GBP + Facebook + website if configured)
```

---

## Business Coverage Matrix

| Client | GBP | Facebook | Website | Notes |
|---|---|---|---|---|
| `custom_designs_tx` | ✅ Active | ⚠️ Page URL unconfirmed | ✅ customdesignstx.com | GBP via `gbp_mario_profile` |
| `sugar_shack` | ✅ Active | ✅ Active | ❌ None | GBP via `gbp_sniffer_profile` |
| `island_candy` | ✅ Active | ✅ Active | ❌ None | GBP via `gbp_sniffer_profile` |
| `optimum_clinic` | ⚠️ Duplicate listing | ✅ Active | ✅ optimumhealthrx.com | GBP posting will fail — skip |
| `juan` | ⚠️ Suspended | ✅ Active | ✅ juanjoseelizondo.com | GBP posting will fail — skip |
| `island_arcade` | ⚠️ Duplicate listing | ✅ Active | ❌ None | No GBP key in config |
| `spi_fun_rentals` | ⚠️ Duplicate listing | ✅ Active | ❌ None | No GBP key in config |
| `optimum_foundation` | ❌ Not mapped | ❌ Not mapped | ❌ None | Skip for now |

---

## Image Generation Specs

- **Model:** `fal-ai/flux-pro/v1.1-ultra`
- **Hero:** `landscape_16_9` format (same image sent to Facebook)
- **Section images:** `square_hd` format (auto-inserted after H2 sections 1, 3, 5)
- **Credential:** `FAL_KEY` from `scratch/gravity-claw/.env`
- **Time:** ~30-60 seconds per image → ~2-4 minutes total for 4 images
- **Rules:** No text overlays, no logos, professional photography 4k, local RGV aesthetic where natural

---

## Scoring System

Haiku scores the blog post on 4 dimensions (0-25 each):

| Dimension | What it checks |
|---|---|
| `keyword_placement` | Keyword in title + first 100 words + H2 + meta description |
| `local_relevance` | City/region mentioned multiple times with local context |
| `depth_vs_competitor` | Word count ≥ target (30% more than competitor, min 800) |
| `cta_strength` | Clear CTA that matches the actual business offer |

**Auto-rewrite triggers:** Total < 70 OR any dimension < 15. Sonnet rewrites the weak section, Haiku re-scores.

---

## Content Type Routing

The keyword automatically determines what type of content is generated:

| Keyword pattern | Content type |
|---|---|
| `for sale`, `homes for`, `land for`, `commercial real` | Location Landing Page |
| `installation`, `clinic`, `walk in`, `urgent care`, `cash pay`, `after hours` | Service Page |
| Everything else (how to, guide, tips, cost, best, etc.) | Blog Post |

---

## Known Limitations

- **GBP posting:** Only works for `sugar_shack`, `island_candy`, `custom_designs_tx`. Others have duplicate/suspended listings.
- **Website publishing:** Stub only — finds GitHub repo but doesn't auto-commit. Manual step until repo structure is confirmed per client.
- **fal.ai cost:** Each image costs API credits. 4 images per post. Check balance before running `--all`.
- **Image generation time:** 2-4 minutes per keyword. Running `--all` for a client with 10+ keywords takes ~30 minutes.
- **Competitor scrape fails gracefully:** If the top competitor URL can't be scraped, content is still generated from keyword alone.

---

## File Locations

| Purpose | Path |
|---|---|
| Script | `tools/execution/blog_writer.py` |
| Blog output | `tools/execution/blog_posts/{client}/` |
| Image output | `tools/execution/blog_posts/{client}/images/{date}_{slug}/` |
| Keyword config | `tools/execution/keyword_rankings_config.json` |
| Rankings data | `tools/execution/keyword_rankings_state.json` |
| fal.ai key | `scratch/gravity-claw/.env` → `FAL_KEY` |
| Telegram creds | `scratch/gravity-claw/.env` → `TELEGRAM_BOT_TOKEN`, `TELEGRAM_USER_ID` |
