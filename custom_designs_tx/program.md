# Custom Designs TX — Agent Steering Document
> Read this before starting any Custom Designs TX session. Update it after every session.
> For full campaign pipeline SOP, use skill: `/custom-designs-facebook`

---

## Business Identity

- **Business:** Custom Designs TX (home tech, security, smart home, A/V)
- **Founder:** Curtis
- **Location:** McAllen, TX (RGV) + Houston service area
- **Phone:** (956) 624-2463
- **Email:** info@customdesignstx.com
- **Website:** customdesignstx.com
- **Support:** 24/7 emergency support for security/lighting
- **Facebook Page:** ✅ CONFIRMED | https://www.facebook.com/profile.php?id=61553759342111 | Page ID: `61553759342111`
- **Auth Account:** Mario (`marioelizondo81@gmail.com`) — Facebook posts via GraphQL API (no Playwright profile dependency)
- **Page Key:** `custom_designs_tx` | Added to `fb_pages_config.json` 2026-03-22
- **GBP:** ✅ ACTIVE | Profile: `gbp_mario_profile/` | Business ID: `13185634142027650449`
- **GBP Script:** `_gbp_custom_designs_with_image.py` (with image) | `gbp_post_custom_designs.py` (text only)
- **GBP Re-auth:** `reauth_mario_gbp.py` (passkey, no password needed)
- **Website:** customdesignstx.com | Platform: Lovable.dev (React+Vite+TypeScript) | Repo: `mar2181/custom-designs`
- **Blog system:** Static TSX components in `src/pages/blog/static/` | Router: `StaticBlogRouter.tsx` | Registry: `src/data/staticBlogs.ts`
- **vercel.json SPA fix:** Pushed 2026-03-18 — all routes now work (no more 404 on direct URL)

---

## Services

**Residential:**
- Home Theater & Media Rooms (4K projection, luxury cinema seating, hidden wiring)
- Smart Home Automation (lighting, HVAC, audio integration)
- High-End Security (cameras, smart locks, alarms, 24/7 monitoring)
- Multi-Room Audio
- Outdoor Entertainment (weatherproof A/V, landscape lighting)
- Cabling & Networking (Cat6/Cat7)

**Commercial:**
- Retail Technology (interactive displays)
- Commercial Lighting (exterior + security)
- Enterprise Networking

---

## Brand Identity

- **Aesthetic:** Dark Luxury — sleek, premium, high-tech
- **Colors:** Gold (#D4AF37) on Obsidian Black (#0A0A0C)
- **Feel:** Like a luxury concierge service, not a handyman

---

## Brand Voice

- Premium, confident, technical-but-accessible
- "We transform spaces" — never "we install stuff"
- Speaks to homeowners who want the best and will pay for it
- Tone: sophisticated, aspirational, expert — but warm enough to not feel cold
- English primary (RGV market — bilingual option available if needed)
- Hashtag limit: 3 max per post

---

## Target Audience

- Homeowners in RGV earning $150k+ who are building, renovating, or upgrading
- Business owners wanting commercial security or display tech
- High-end builders / contractors who refer clients
- Houston market: executive homeowners, luxury builds

---

## Current Priorities
> Update this section at the start of each session

- [x] **Facebook page confirmed** — `profile.php?id=61553759342111` | Mario's account | Graph API
- [x] **Facebook config** — `fb_pages_config.json` → `pages.custom_designs_tx` → `posting_method: graph_api`, page_id `177280908799458`, auth: `facebook_mario_profile` ✅
- [x] **Blog posts all live (200)** — verified 2026-05-05: alarm-system, cctv, home-theater-surround-sound, home-theater-installation, security-camera all return 200 via SPA catch-all
- [x] **Supabase rankings** — 751 keyword rows, last updated 2026-05-04. Map pack: 102 ranked. Organic: 54 ranked.
- [x] **Star rankings** — `smart home installation mcallen` #3 Map Pack | `commercial security cameras McAllen` #1 Organic
- [ ] **BLOCKER #1:** SPA/React site — Googlebot reads empty shell (`<div id="root"></div>`). All blog/service pages have zero crawlable body text. Fix: SSR/SSG via Vercel or Prerender.io (~$15/mo).
- [ ] **BLOCKER #2:** GSC token expired 2026-04-18 — no search console data. Re-auth: `python reauth_gsc.py` (ports 8090–8094 with trailing slash must be in OAuth client + Testing mode).
- [ ] **BLOCKER #3:** Facebook health check failing for ALL pages (Graph API token expired/invalid). Fix: re-auth Graph API token before any FB posting.
- [ ] **BLOCKER #4:** Review gap — 7 reviews vs. D-Tronics (225+), Vivint (300+). Need 20+ reviews in 60 days to compete in map pack.
- [ ] **ACTION:** Resume GBP posting — last post was 2026-03-18 (48+ days ago). 3 SEO optimizer posts READY.
- [ ] **ACTION:** Run Facebook campaigns — 0 Facebook posts ever. Fix Graph API token first, then: `/custom-designs-facebook`
- [ ] **Current campaign goal:** _(fill in — e.g., "home theater consultations", "smart home leads")_
- [ ] **Active offer:** _(fill in — e.g., "Free smart home assessment this month")_
- [ ] **Target service this week:** _(fill in — e.g., "security systems", "home theater", "smart home")_
- [ ] **Target audience this week:** _(fill in — e.g., "new build homeowners in McAllen")_

---

## Posting Log
> Add a row after every post.

| Date | Service | Ad Angle | Channel | Offer | Notes |
|------|---------|----------|---------|-------|-------|
| 2026-03-14 | Security / Home Theater | After Hours Blind Spot (ad_1) | GBP | Free consultation | GBP post; business security angle |
| 2026-03-14 | Home Theater | Home Theater Reveal (ad_2) | GBP | Free consultation | GBP post; home theater reveal angle |
| 2026-03-15 | Security | Family Safety (ad_5) | GBP | Free on-site consultation | GBP post; family home security angle |
| 2026-03-18 | Security cameras | Professional Security Camera Installation in McAllen TX | GBP + Blog + Website | Free on-site consultation | ✅ GBP posted with fal.ai hero image (`_gbp_custom_designs_with_image.py`). Blog live at customdesignstx.com/blog/security-camera-installation-mcallen-tx. fal.ai images: hero.png + section_1-3.png in `blog_posts/custom_designs_tx/images/2026-03-18_security-camera.../` |
| 2026-05-03 | Smart Home Security | smart_home_security | Facebook | | Write-back test confirmed ✅ — Playwright flow working |

---

## What's Working

- _(add observations as you post and see results)_

---

## Competitors

> Watch these. Track their project photos, offers, and how they position on social.

| Competitor | Notes | Angle to Beat Them |
| ---------- | ----- | ------------------ |
| Mach 1 Media | Control4 smart home, home theater, AV, security — RGV | Beat with: darker luxury aesthetic, faster response, local roots |
| D-Tronics Home & Business | McAllen, 30+ years in AV and automation | Beat with: modern brand, cutting-edge smart home vs. their legacy feel |
| Safehouse Security Systems | McAllen local — alarms, cameras, smart home | Beat with: full luxury integration (not just security) |
| Frontline Smart Security | McAllen, home theater install | Beat with: Custom Designs' premium aesthetic, full-room transformations |
| Vivint | National chain, strong McAllen presence | Beat with: local expertise, no call centers, white-glove personal service |

**Intelligence gaps to watch:** What projects are they posting? Product shots or actual installs? Google review volume vs. ours? Any pricing advertised?

---

## What to Avoid

- No text overlays in images — all text in post copy only
- No price guarantees or ROI claims without sourcing
- Don't sound like a generic electrician or handyman — always luxury tier language
- _(add as you learn)_

---

## Facebook Setup Needed
> Before the first posting session, complete this:

- [x] Facebook page URL confirmed: `https://www.facebook.com/profile.php?id=61553759342111`
- [x] Added to `fb_pages_config.json` with key `custom_designs_tx` (2026-03-22)
- [x] Auth account: Mario (`facebook_mario_profile`) — Playwright
- [x] Test posting flow — confirmed 2026-05-03 (smart_home_security write-back)

---

## Image Style Notes

- Format: `landscape_16_9` only
- Style: dark luxury aesthetic — gold accents, dramatic lighting, premium home interiors, high-tech equipment
- End all image prompts with: `professional photography, 4k`
- No text, logos, or people's faces in generated images

---

## Quick Commands

```powershell
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# Optimize copy
python ad_copy_optimizer.py custom_designs_tx --angle "home theater consultation"
python ad_copy_optimizer.py custom_designs_tx --angle "smart home security upgrade"
```

---

## Target Keywords
> Content calendar — one keyword per blog session. Run: `python blog_writer.py --client custom_designs_tx --keyword "..." --publish`
> Channels: GBP + Website (Facebook pending page confirmation)

| Priority | Keyword | Intent | Status |
|----------|---------|--------|--------|
| 1 | security camera installation mcallen tx | Service SEO | ✅ Published 2026-03-18 |
| 2 | home theater installation mcallen tx | Service SEO | ⬜ Not started |
| 3 | smart home automation mcallen tx | Service SEO | ⬜ Not started |
| 4 | whole home audio system installer rgv | Service SEO | ⬜ Not started |
| 5 | smart lock installation mcallen tx | Service SEO | ⬜ Not started |
| 6 | home security system mcallen tx | Broad local | ⬜ Not started |
| 7 | outdoor entertainment system installer texas | Service SEO | ⬜ Not started |
| 8 | cat6 wiring installer mcallen tx | Technical SEO | ⬜ Not started |
| 9 | home theater cost mcallen tx | Cost/research | ⬜ Not started |
| 10 | smart home installation cost texas | Cost/research | ⬜ Not started |
| **Location Pages** | | | |
| L1 | security camera installation edinburg tx | Location SEO | ⚠️ Generated 2026-03-27 — EMPTY STUB (0 words, score 0) — needs full content |
| L2 | security camera installation mission tx | Location SEO | ⚠️ Generated 2026-03-27 — EMPTY STUB (0 words, score 0) — needs full content |
| L3 | security camera installation pharr tx | Location SEO | ⚠️ Generated 2026-03-27 — BROKEN CANONICAL (`customdesignstx.comundefined`) — fix required |
| L4 | security camera installation harlingen tx | Location SEO | ⚠️ Generated 2026-03-27 — EMPTY STUB (0 words, score 0) — needs full content |

---

## Session Notes

_(notes go here — clear after each session)_
