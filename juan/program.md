# Juan Elizondo RE/MAX Elite — Agent Steering Document
> Read this before starting any Juan session. Update it after every session.
> For full campaign pipeline SOP, use skill: `juan-elizondo-remax-elite-facebook`

---

## Business Identity

- **Business:** Juan José Elizondo — RE/MAX Elite (real estate agent)
- **Market:** Rio Grande Valley, TX (McAllen, Edinburg, Mission, San Juan, Pharr)
- **Specialty:** Residential + commercial real estate, RGV market expert
- **Facebook Page:** https://www.facebook.com/JuanElizondoRemax/
- **Auth Account:** Mario (`marioelizondo81@gmail.com`) → profile: `facebook_mario_profile/`
- **Page Key:** `juan`
- **GBP:** ⚠️ Suspended — do not attempt GBP posting until resolved
- **Website:** juanjoseelizondo.com
- **Phone:** (956) 522-1481 — include in every post CTA

---

## Brand Voice

- Professional, knowledgeable, trustworthy — RGV's local expert
- Spanish and English content — bilingual audience
- Never aggressive sales — educational and helpful tone wins here
- Positions Juan as THE go-to agent for the RGV, not just another realtor
- Tone: confident, warm, community-rooted
- Hashtag limit: 3 max per post

---

## Current Priorities
> Update this section at the start of each session

- [ ] **Active listings to promote:** _(fill in — address, price, key features)_
- [ ] **Current market angle:** _(fill in — e.g., "interest rates dropping — buyers window opening")_
- [ ] **Target audience this week:** _(fill in — e.g., "first-time buyers", "investors", "sellers ready to list")_
- [ ] **Upcoming event / open house:** _(fill in — date, address)_
- [ ] **Commercial vs. residential focus:** _(fill in — which is priority this week)_

---

## Posting Log
> Add a row after every post.

| Date | Post Type | Property/Topic | Language | Engagement | Notes |
|------|-----------|---------------|----------|------------|-------|
| _(add after each post)_ | | | | | |

---

## Active Listings
> Update whenever a listing goes live or sells

| Address | Price | Type | Status | Notes |
|---------|-------|------|--------|-------|
| _(fill in)_ | | | | |

---

## What's Working

- _(add observations — e.g., "Market education posts (interest rate updates) get 3x the reach of listing posts")_
- _(e.g., "Spanish-language posts get higher engagement with organic RGV audience")_
- _(e.g., "Before/after renovation posts get strong save rates")_

---

## Competitors

> Watch these agents. Track their listings, social content, and market positioning.

| Competitor | Notes | Angle to Beat Them |
| ---------- | ----- | ------------------ |
| Deldi Ortegon Group | Keller Williams RGV, high-profile McAllen team | Beat with: personal touch, bilingual depth, commercial expertise |
| Maggie Harris Team | Keller Williams RGV, McAllen | Beat with: Juan's commercial + residential dual expertise |
| Coldwell Banker Commercial RGV | 508 E Dove Ave, McAllen | Beat with: local independent feel vs. corporate chain |
| Jinks Realty | Locally-owned RGV firm | Beat with: RE/MAX national network + local roots combination |
| Imperio Real Estate | Active in McAllen market | Beat with: track record, bilingual content volume |
| Realty Executives RGV | McAllen-area brokerage | Beat with: Juan's personal brand and market education content |

**Intelligence gaps to watch:** What listings are they promoting? What market angles are they hitting? Are they posting in Spanish? What's their Google review rating vs. Juan's?

---

## What to Avoid

- No text overlays in images
- No unverified testimonials — only use verified client reviews; flag as aspirational if unavailable
- Don't make specific ROI or appreciation claims without citing sources
- _(add as you learn)_

---

## Listing Description Standards
> For Juan's property listings (MLS, website, ads)

- Lead with lifestyle benefit, not specs ("Wake up to RGV sunrises" not "3BR/2BA")
- Always include: price, beds/baths, key feature, neighborhood, CTA with phone — **📞 (956) 522-1481**
- Spanish version: translate naturally — not word-for-word
- Max 300 words per listing description

---

## Market Context
> Update as market conditions change

- Current RGV market: _(fill in — buyer's/seller's market, avg days on market, etc.)_
- Interest rate environment: _(fill in)_
- Hot submarkets right now: _(fill in — e.g., "Mission is moving fast, Edinburg slower")_

---

## Best Posting Times

- Best days: _(fill in — e.g., "Thursday and Saturday perform best for listings")_
- Best times: _(fill in — e.g., "7–9pm after work crowd is scrolling")_
- Avoid: _(fill in)_

---

## Image Style Notes

- Format: `landscape_16_9` only
- Style: warm Texas light, professional real estate photography aesthetic
- End all image prompts with: `professional photography, 4k`
- For listings: exterior front shot angle works best
- No text, logos, or people's faces in generated images

---

## Quick Commands

```powershell
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# Full pipeline
python fb_campaign_runner.py --business juan --mode full

# Post only
python fb_campaign_runner.py --business juan --mode post

# Listing description optimizer (autoresearch loop)
# From raw property details:
python listing_optimizer.py --address "123 Main St, McAllen TX" --price 285000 --beds 3 --baths 2 --sqft 1800 --features "pool, corner lot, new kitchen"

# Optimize existing MLS description:
python listing_optimizer.py --address "123 Main St, McAllen TX" --description "Your existing description here"

# Spanish version:
python listing_optimizer.py --address "123 Main St, McAllen TX" --price 285000 --beds 3 --baths 2 --language es

# Score only (no rewrite):
python listing_optimizer.py --address "123 Main St" --description "..." --dry-run
```

---

## Target Keywords
> Content calendar — one keyword per blog session. Run: `python blog_writer.py --client juan --keyword "..." --publish`
> Channels: Facebook only (GBP suspended, website repo TBD — confirm GitHub repo to unlock website publish)

| Priority | Keyword | Intent | Status |
|----------|---------|--------|--------|
| 1 | homes for sale mcallen tx | Highest-volume local | ⬜ Not started |
| 2 | mcallen tx real estate market 2026 | Market report | ⬜ Not started |
| 3 | homes for sale edinburg tx | Secondary market | ⬜ Not started |
| 4 | how to sell your home in mcallen tx | Seller intent | ⬜ Not started |
| 5 | first time home buyer mcallen texas | Buyer intent | ⬜ Not started |
| 6 | commercial real estate mcallen tx | Commercial focus | ⬜ Not started |
| 7 | land for sale rio grande valley tx | Investment/land | ⬜ Not started |
| 8 | casas en venta mcallen tx | Spanish-language SEO | ⬜ Not started |
| 9 | agente de bienes raices mcallen tx | Spanish agent search | ⬜ Not started |
| 10 | mission tx homes for sale | Tertiary market | ⬜ Not started |
| **Location Pages** | | | |
| L1 | real estate agent edinburg tx | Location SEO | ✅ Generated 2026-03-27 |
| L2 | real estate agent mission tx | Location SEO | ✅ Generated 2026-03-27 |
| L3 | homes for sale pharr tx | Location SEO | ✅ Generated 2026-03-27 |
| L4 | homes for sale san juan tx | Location SEO | ✅ Generated 2026-03-27 |

---

## Session Notes

_(notes go here — clear after each session)_
