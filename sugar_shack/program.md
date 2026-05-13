# The Sugar Shack — Agent Steering Document
> Read this before starting any Sugar Shack session. Update it after every session.
> For full campaign pipeline SOP, use skill: `sugar-shack-facebook`

---

## Business Identity

- **Business:** The Sugar Shack (candy store + snacks)
- **Location:** South Padre Island, TX
- **Season:** Peak = spring break (Feb–Apr), summer families, holiday weekends
- **Facebook Page:** https://www.facebook.com/profile.php?id=61557735298128
- **Auth Account:** Yehuda (`quepadre@live.com`) → profile: `facebook_sniffer_profile/`
- **Page Key:** `sugar_shack`
- **GBP:** ✅ Active | Profile: `gbp_sniffer_profile/` | Script: `gbp_post_sugar_shack.py`

---

## Brand Voice

- Fun, colorful, family-friendly
- Speaks to road-tripping families and spring breakers
- Never corporate — sounds like the local shop owner talking
- Tone: excited, warm, playful
- Hashtag limit: 3 max per post

---

## Current Priorities
> Update this section at the start of each session

- [ ] **Current campaign goal:** _(fill in — e.g., "spring break foot traffic", "new product launch")_
- [ ] **Active offer:** _(fill in — e.g., "Buy 2 get 1 free on gummies this weekend")_
- [ ] **Target audience this week:** _(fill in — e.g., "families driving to SPI for spring break")_
- [ ] **Deadline / event:** _(fill in — e.g., "Spring break March 15–22")_

---

## Posting Log
> Add a row after every post. Helps prevent repetition and track what works.

| Date | Ad Angle | Offer Mentioned | Format | Engagement | Notes |
|------|----------|----------------|--------|------------|-------|
| 2026-03-29 | Road Trip Fuel | "Your road trip isn't complete without a stop" | Image (mission_control_road_trip_fuel.png) | Posting | ✅ LIVE — Posted from Mission Control library at 3:55 PM |
| 2026-03-14 | Sweet Memories / childhood candy wonder | "Come in, fill a bag" | Image (v2 — dad+daughter in store) | Pending | Spring break family angle; v2 image regenerated |
| 2026-03-14 | Spring Break Ready (march14) | "Come in, fill a bag" | Image (march14_spring_break) | Pending | Bulk candy + road trip energy |
| 2026-03-15 | Bulk Candy Budget (ad_4) | "Stop by, fill a bag" | Image (ad_4_bulk_candy_budget.png) | Pending | Family budget angle; per-piece pricing callout |
| 2026-03-15 | Last Stop Home (gbp_ad9) — **GBP** | "Don't leave the island without this stop" | Image (ad_9_last_stop_home.png) | Pending | GBP post; end-of-vacation angle |

---

## What's Working
> Update when you see good engagement (keep doing these)

- _(add observations — e.g., "Road trip angle gets more shares than beach angle")_
- _(e.g., "Posts with a specific price get more link clicks than vague discount language")_

---

## Competitors

> Watch these. Note what they're posting, their offers, and any gaps you can exploit.

| Competitor | Notes | Angle to Beat Them |
| ---------- | ----- | ------------------ |
| Sugar Kingdom | 2,500+ candy types — quantity is their pitch | Beat with: local personality, better experience, SPI identity |
| Davey Jones Ice Cream Locker | Candy + fudge + taffy + shaved ice — multi-category | Beat with: focused identity, specific product callouts |
| Turtle Island | "Ultimate souvenir store" — souvenir-heavy | Beat with: candy-first positioning, sweeter experience angle |
| Charmed | Gift/boutique angle | Beat with: fun/playful tone vs. their boutique feel |
| Ship Shape | Swimsuits + souvenirs, north end | Geographic separation — less direct overlap |

**Intelligence gaps to watch:** Are any running seasonal promos? What's their Facebook posting frequency? Any negative reviews to position against?

---

## What to Avoid
> Update when posts underperform or get rejected

- No text overlays in images — all text in post copy only
- No unverified testimonials — use aspirational language flagged as "Variant B" if needed
- _(add as you learn — e.g., "Generic 'stop by and visit us' CTAs get low clicks")_

---

## Best Posting Times
> Update based on actual engagement data

- Best days: _(fill in based on results)_
- Best times: _(fill in — e.g., "6–8pm Thursday/Friday before weekend")_
- Avoid: _(e.g., "Monday mornings — lowest reach")_

---

## Image Style Notes

- Format: `landscape_16_9` only
- Style: bright, colorful candy photography — no dark tones
- End all image prompts with: `professional photography, 4k`
- No text, logos, or people's faces in generated images

---

## Quick Commands

```powershell
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# Full pipeline (generate → preview → approve → post)
python fb_campaign_runner.py --business sugar_shack --mode full

# Post only (images already ready)
python fb_campaign_runner.py --business sugar_shack --mode post
```

---

## Target Keywords
> Content calendar — one keyword per blog session. Run: `python blog_writer.py --client sugar_shack --keyword "..." --publish`
> Channels: GBP + Facebook (no website repo)

| Priority | Keyword | Intent | Status |
|----------|---------|--------|--------|
| 1 | candy store south padre island tx | Local discovery | ✅ Published 2026-03-18 (FB + GBP) |
| 2 | best candy store south padre island | Best-of tourism | ✅ Published 2026-03-19 (FB + GBP) |
| 3 | things to do south padre island with kids | Tourism SEO | ⬜ Not started |
| 4 | south padre island spring break snacks | Seasonal | ⬜ Not started |
| 5 | bulk candy south padre island | Product SEO | ⬜ Not started |
| 6 | souvenir candy shop spi tx | Tourist intent | ⬜ Not started |
| 7 | sweet treats south padre island | Broader tourism | ⬜ Not started |

---

## Session Notes
> Scratch space for current session — clear after each session

_(notes go here)_
