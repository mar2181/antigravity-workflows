# Island Candy — Agent Steering Document
> Read this before starting any Island Candy session. Update it after every session.
> For full campaign pipeline SOP, use skill: `island-candy-facebook`

---

## Business Identity

- **Business:** Island Candy (ice cream, inside Island Arcade)
- **Location:** South Padre Island, TX (inside Island Arcade)
- **Season:** Peak = spring break, summer heat, beach days
- **Facebook Page:** https://www.facebook.com/profile.php?id=100090560413893
- **Auth Account:** Mario (`marioelizondo81@gmail.com`) → profile: `facebook_mario_profile/`
- **Page Key:** `island_candy`
- **GBP:** ✅ Active | Profile: `gbp_sniffer_profile/`
- **Note:** Physically inside Island Arcade — coordinate offers and posting schedule with island_arcade

---

## Brand Voice

- Sweet, fun, summer-beach energy
- Speaks to the heat relief angle — "you've been on the beach all day"
- Works well with family + couple audiences
- Tone: refreshing, indulgent, carefree
- Hashtag limit: 3 max per post

---

## Current Priorities
> Update this section at the start of each session

- [ ] **Current campaign goal:** _(fill in — e.g., "afternoon foot traffic from beach crowd")_
- [ ] **Active offer:** _(fill in — e.g., "Buy any 2 scoops, get a topping free")_
- [ ] **Target audience this week:** _(fill in — e.g., "spring break families and couples")_
- [ ] **Deadline / event:** _(fill in)_

---

## Posting Log
> Add a row after every post.

| Date | Ad Angle | Offer Mentioned | Format | Engagement | Notes |
|------|----------|----------------|--------|------------|-------|
| 2026-03-14 | Cool Down / heat relief | "Walk off the beach into the sweetest spot" | Image (v3 — banana split, user approved) | Pending | Banana split replaced cone — standout visual |
| 2026-03-14 | Spring Break Treat (march14) | "Make every afternoon count" | Image (march14_spring_break) | Pending | Spring break beach crowd angle |
| 2026-03-15 | Sweet Reward (ad_2) | "Homemade ice cream starting at $3.99" | Image (ad_2_sweet_reward.png) | Pending | Games + ice cream combo; post-arcade reward angle |
| 2026-03-15 | Beach to Candy (gbp_ad3) — **GBP** | "Beach day done. Now comes the best part." | Image (ad_3_homemade_icecream.png) | Pending | GBP post; post-beach angle; $3.99 starting |
| 2026-03-16 | Spring Break Treat | "Starting at $3.99. Walk-ins welcome." | Image (new_island_candy.png — milkshakes) | Posted ✅ | Milkshake image; no cone/banana split; two-shake shot |

---

## What's Working

- _(add observations — e.g., "Heat/sun angle performs better than generic ice cream posts")_
- _(e.g., "Specific flavor callouts get more comments than generic 'ice cream' posts")_

---

## Competitors

> Watch these. Track flavors, pricing, and what angles they're hitting on social.

| Competitor | Notes | Angle to Beat Them |
| ---------- | ----- | ------------------ |
| KIC's Ice Cream | 2500 Padre Blvd, 16 Blue Bell flavors, indoor/outdoor seating | Beat with: inside Island Arcade = entertainment + ice cream combo |
| The Baked Bear | Ice cream sandwiches — novelty/Instagrammable format | Beat with: classic scoops done right, faster service |
| Dolce Roma | Italian gelato, 4200 Padre Blvd | Beat with: beach casual vs. their gelato-shop positioning |
| Cafe Karma | Coffee + 16 flavors + pastries | Beat with: pure ice cream focus, no distractions |
| Davey Jones Ice Cream Locker | Candy store + ice cream hybrid | Beat with: dedicated ice cream identity + arcade fun |

**Intelligence gaps to watch:** What flavors are they promoting? Any "flavor of the month" gaps? Instagram-worthy presentations we should match or beat?

---

## What to Avoid

- No text overlays in images
- No unverified testimonials
- Don't post at same time as Island Arcade — stagger by 1–2 hours minimum
- _(add as you learn)_

---

## Coordination with Island Arcade
> Both businesses share a physical location

- Stagger posts: don't post both pages within 1 hour of each other
- Joint offers possible: _(fill in — e.g., "Play games + ice cream combo")_
- When coordinating, Island Arcade posts first, Island Candy follows 90 min later

---

## Best Posting Times

- Best days: _(fill in)_
- Best times: _(fill in — e.g., "2–4pm when beach crowd starts heading in from the heat")_
- Avoid: _(fill in)_

---

## Image Style Notes

- Format: `landscape_16_9` only
- Style: bright, colorful ice cream photography — melting scoops, beach backdrop, pastel tones
- End all image prompts with: `professional photography, 4k`
- No text, logos, or people's faces in generated images

---

## Quick Commands

```powershell
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# Full pipeline
python fb_campaign_runner.py --business island_candy --mode full

# Post only
python fb_campaign_runner.py --business island_candy --mode post
```

---

## Target Keywords
> Content calendar — one keyword per blog session. Run: `python blog_writer.py --client island_candy --keyword "..." --publish`
> Channels: GBP + Facebook (no website repo)

| Priority | Keyword | Intent | Status |
|----------|---------|--------|--------|
| 1 | ice cream south padre island tx | Local discovery | ✅ Published 2026-03-19 (FB + GBP) |
| 2 | best ice cream south padre island | Best-of tourism | ⬜ Not started |
| 3 | homemade ice cream south padre island | Product SEO | ⬜ Not started |
| 4 | dessert south padre island spring break | Seasonal | ⬜ Not started |
| 5 | milkshakes south padre island | Product-specific | ⬜ Not started |
| 6 | ice cream shop inside arcade spi | Experience combo | ⬜ Not started |
| 7 | cool treats south padre island summer heat | Seasonal/weather | ⬜ Not started |

---

## Session Notes

_(notes go here — clear after each session)_
