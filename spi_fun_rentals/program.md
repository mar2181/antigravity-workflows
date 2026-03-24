# SPI Fun Rentals — Agent Steering Document
> Read this before starting any SPI Fun Rentals session. Update it after every session.
> For posting SOP, use skill: `spi-fun-rentals-facebook`

---

## Business Identity

- **Business:** SPI Fun Rentals (golf carts, slingshots, mopeds, surfing equipment)
- **Location:** 1314 Padre Blvd #A, South Padre Island, TX 78597
- **Phone:** (956) 761-9999
- **Website:** spifunrentals.com
- **Season:** Peak = spring break (Feb–Apr), summer, holiday weekends
- **Facebook Page:** https://www.facebook.com/spifunrentals
- **Auth Account:** Yehuda (`quepadre@live.com`) → profile: `facebook_sniffer_profile/`
- **Page Key:** `spi` (in fb_pages_config.json)
- **GBP:** ⚠️ Duplicate listing in Mario's account (`gbp_mario_profile/`) | Business ID: `12018623800655095562` | Listed as "SPI Fun Rental & Island Surf Rental" — do not post until duplicate resolved
- **CRITICAL:** Two-step Switch flow required — see spi-fun-rentals-facebook SKILL.md

---

## What They Rent

- Golf carts (most popular — families, groups)
- Slingshots
- Mopeds
- Surfing equipment / water sports gear

> ⚠️ **NO JEEPS** — SPI Fun Rentals no longer rents Jeeps. Do NOT mention Jeeps in any ad copy, image prompts, or posts. Removed as of 2026-03-22.

---

## Brand Voice

- Fun, adventurous, island-life energy
- "Your vacation starts the moment you rent from us"
- Speaks to: spring breakers wanting freedom, families wanting convenience, couples wanting a memorable experience
- Tone: upbeat, laid-back island vibe — not corporate
- Hashtag limit: 3 max per post

---

## Current Priorities
> Update this section at the start of each session

- [ ] **Current campaign goal:** _(fill in — e.g., "spring break golf cart bookings", "summer water sports push")_
- [ ] **Active offer:** _(fill in — e.g., "Book 2 days, get 1 hour free")_
- [ ] **Target audience this week:** _(fill in — e.g., "spring break groups arriving March 15–22")_
- [ ] **Featured rental type:** _(fill in — e.g., "golf carts", "jeeps", "water sports")_
- [ ] **Deadline / event:** _(fill in)_

---

## Posting Log
> Add a row after every post.

| Date | Rental Type | Ad Angle | Offer | Engagement | Notes |
|------|------------|----------|-------|------------|-------|
| 2026-03-14 | Golf Cart | Family Connection | 15% off this week | Image (v2 — family in golf cart) | Pending | Family angle; 15% off offer included |
| 2026-03-14 | Golf Cart | Spring Break Here (march14) | Availability goes fast | Image (march14_spring_break) | Pending | Urgency + freedom angle |
| 2026-03-15 | Golf Cart | Golf Cart Spring Break (ad_1) | Carts go FAST on peak weekends | Image (Yehuda 6 Seater Golf Cart wNumber.jpg) | Pending | 6-seater crew angle; urgency + reservation CTA |

---

## What's Working

- _(add observations — e.g., "Golf cart posts outperform jeep posts 3:1 in spring break season")_
- _(e.g., "Group/friend photos get more tags and shares than couple shots")_
- _(e.g., "FOMO/availability scarcity works: 'Only X carts left this weekend'")_

---

## Competitors

> Watch these. Note their pricing, availability messaging, and seasonal offers.

| Competitor | Notes | Angle to Beat Them |
| ---------- | ----- | ------------------ |
| Paradise Fun Rentals | Golf carts + slingshots, 4 locations across SPI | Beat with: water sports breadth + beach gear combos |
| Isla Beach Rentals | Golf carts, beach transportation focus | Beat with: full experience (jeeps + water sports + gear) |
| Coast to Coast Rental | Golf carts + water sports combo | Most similar — beat with availability, faster booking, better social proof |
| PI Rentals | Multi-vehicle beach operation | Beat with: known brand, existing reviews, island-life brand voice |

**Intelligence gaps to watch:** Are they sold out on peak weekends (scarcity angle for us)? What's their pricing vs. ours? How fast do they respond to Facebook messages?

---

## What to Avoid

- No text overlays in images — all text in post copy only
- No unverified testimonials
- **NO JEEPS** — no longer offered. Never mention in copy or image prompts (2026-03-22)
- **Golf carts NEVER on sand** — driving on the beach is illegal in SPI. Always show carts on paved road or parking areas
- No images of surfboards stuck in sand (beach access rules)

---

## Best Posting Times

- Best days: _(fill in — e.g., "Wednesday–Thursday before weekend arrivals")_
- Best times: _(fill in — e.g., "7pm when people are planning next day activities")_
- Avoid: _(fill in)_

---

## Image Style Notes

- Format: `landscape_16_9` only
- Style: bright SPI beach photography — sunny skies, golf carts on the beach, happy people, open road
- End all image prompts with: `professional photography, 4k`
- No text, logos, or people's faces in generated images

---

## Quick Commands

```powershell
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# Optimize copy first
python ad_copy_optimizer.py spi_fun_rentals --angle "golf cart spring break"

# Post with existing script
python post_spi_ad1.py   # or copy and adapt for new ads
```

---

## Target Keywords
> Content calendar — one keyword per blog session. Run: `python blog_writer.py --client spi_fun_rentals --keyword "..." --publish`
> Channels: Facebook only (GBP duplicate — Mario's account, pending resolution)

| Priority | Keyword | Intent | Status |
|----------|---------|--------|--------|
| 1 | golf cart rental south padre island tx | Service SEO | ⬜ Not started |
| 2 | golf cart rental spi spring break | Seasonal | ⬜ Not started |
| 3 | how much does a golf cart rental cost south padre island | Cost/research | ⬜ Not started |
| 4 | slingshot rental south padre island | Service SEO | ⬜ Not started |
| 5 | water sports rentals south padre island | Service SEO | ⬜ Not started |
| 6 | beach vehicle rental south padre island | Broader service | ⬜ Not started |
| 7 | things to rent south padre island vacation | Tourism intent | ⬜ Not started |

---

## Session Notes

_(notes go here — clear after each session)_
