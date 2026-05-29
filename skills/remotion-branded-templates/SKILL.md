---
name: remotion-branded-templates
version: 1.0.0
author: mario
category: content-creation
risk: low
tags: [remotion, video, motion-graphics, react, listing-card, before-after, kinetic-listicle, price-card, cta-endcard, mission-control, draft]
description: >
  Data-driven branded motion-graphic video templates rendered with Remotion
  (React -> MP4). Produces the content SHAPES the ffmpeg/ASS pipeline cannot:
  real-estate listing cards, before/after drag-line wipes, "N reasons" kinetic
  listicles, animated price/stat cards, lower-thirds, and animated CTA
  end-cards. Re-render any template per client / listing / SKU by swapping a
  JSON props file. CONSUMES existing Kling/Higgsfield clip URLs + per-client
  brand presets as inputs; it does NOT regenerate footage, VO, music, or
  captions. Outputs an MP4 to the Mission Control Ad Library as status=draft.
  Trigger phrases: "make a listing card reel", "before and after video",
  "5 reasons countdown", "animated price card", "kinetic listicle",
  "stat card reel", "remotion template", "branded motion graphics",
  "listing card for juan".
---

# remotion-branded-templates

The one genuinely **new engine** out of the 2026 AI-content video review: a
deterministic, prop-driven motion-graphics layer. Everything else in Mario's
stack (Content Loop, Cinematic Blog, Higgsfield) animates *real footage* and
burns a single flat text line. This produces a different KIND of content —
listing cards, before/after wipes, kinetic listicles, price/stat cards — the
formats local-biz audiences recognize as "real content," not "another AI ad."

> **Why it exists:** the content review diagnosed the clients' real complaint as
> **format monotony**, not low quality. This skill is the direct fix: infinite
> cheap on-brand variation of genuinely new shapes.

## Where it lives

```
C:/Users/mario/remotion-branded-templates/
├── package.json                 # Remotion 4.0.x, react 18, @remotion/google-fonts
├── remotion.config.ts           # h264 + yuv420p (FB/IG/TikTok-safe), jpeg frames
├── tsconfig.json
├── public/                      # input assets (real photos / downloaded clips)
├── out/                         # rendered MP4s
└── src/
    ├── index.ts                 # registerRoot
    ├── Root.tsx                 # <Composition> registry + defaultProps
    ├── brand.ts                 # per-client palette/font (mirror of Content Loop §9/§17)
    ├── fonts.ts                 # Google fonts (Bebas/Anton/Bungee/Inter), weight-limited
    ├── components/
    │   ├── primitives.tsx       # SafeZone, AnimatedCounter, StatChip, KineticHeadline
    │   └── cards.tsx            # PhoneMockup, PhotoCarousel, BeforeAfterWipe, ProofCard, CTAEndCard
    └── compositions/
        ├── JuanListingCard.tsx          # 9:16 18s — listing card (v1 shipped)
        └── CustomDesignsBeforeAfter.tsx # 9:16 12s — before/after wipe + proof (v1 shipped)
```

**Studio port: 4001** (registered; do NOT use 3001 — that is Mission Control).

## Validated benchmark (2026-05-29, Mario's Windows box, Node 22, ffmpeg 8)

| Composition | Frames | Render wall time | Size |
|---|---|---|---|
| JuanListingCard (18s 1080x1920) | 540 | **27s** | 6.7 MB |
| CustomDesignsBeforeAfter (12s 1080x1920) | 360 | **17s** | 1.9 MB |

≈ **1.5s render per 1s of video** — production-viable. First-ever render also
downloads Chrome Headless Shell (~113 MB, one-time) and caches the bundle.

## One-time setup (already done; re-run only on a fresh machine)

```bash
cd /c/Users/mario/remotion-branded-templates
npm install --no-audit --no-fund
# Confirm: all @remotion/* AND remotion are the SAME version (4.0.x).
node -p "require('remotion/package.json').version"
```

## Render a template (the everyday command)

```bash
cd /c/Users/mario/remotion-branded-templates

# Defaults (the demo data baked into Root.tsx):
npx remotion render src/index.ts JuanListingCard out/juan_listing.mp4
npx remotion render src/index.ts CustomDesignsBeforeAfter out/custom_designs_beforeafter.mp4

# Real data — swap the JSON, same template, new video in minutes:
npx remotion render src/index.ts JuanListingCard out/123main.mp4 --props=props/123main.json
```

### Example props file (`props/123main.json`) — Juan listing card

```json
{
  "client": "juan",
  "city": "Edinburg",
  "price": 419000,
  "beds": 4,
  "baths": 3,
  "sqft": 2640,
  "feature": "CASITA",
  "photos": ["123main_1.jpg", "123main_2.jpg", "123main_3.jpg", "123main_4.jpg"],
  "agentInitials": "JE",
  "agentName": "JUAN ELIZONDO",
  "ctaPrimary": "DM Juan · RE/MAX Elite",
  "ctaSecondary": "Escríbele a Juan hoy"
}
```

Put the listing's real photos in `public/` (filenames must match `photos`).
For backgrounds you can also pass an `http(s)` Kling/Higgsfield clip URL.

### Before/after props (`CustomDesignsBeforeAfter`)

```json
{
  "client": "custom_designs_tx",
  "hookWords": ["THEY", "COULDN'T", "SEE", "THEIR", "DRIVEWAY.", "WATCH."],
  "beforeSrc": "job17_before.jpg",
  "afterSrc": "job17_after.jpg",
  "stats": [{"value": "6", "label": "Cameras"}, {"value": "4K", "label": "Resolution"}, {"value": "1 DAY", "label": "Install"}],
  "proofQuote": "",
  "proofFirstName": "",
  "ctaPrimary": "Free quote · Hidalgo & Cameron",
  "ctaSecondary": "Presupuesto gratis",
  "brandInitials": "CD"
}
```

> **`proofQuote` MUST stay empty unless you paste a REAL, verified Google
> review** (and use the reviewer's FIRST NAME only). The default is empty so no
> fabricated testimonial can ever ship. This is the real-testimonials-only rule
> enforced in code — do not "fill it in" with invented praise.

## Authoring a NEW template (the growth path)

1. Add a `.tsx` to `src/compositions/`. Compose the building blocks in
   `components/` (don't reinvent — `KineticHeadline`, `StatChip`,
   `AnimatedCounter`, `BeforeAfterWipe`, `PhoneMockup`, `PhotoCarousel`,
   `ProofCard`, `CTAEndCard`).
2. Wrap content in `<SafeZone>` so TikTok/IG/Reels chrome never clips text.
3. Pull color/font from `getBrand(client)` — never hardcode brand colors.
4. Register it in `Root.tsx` with `durationInFrames`, 1080x1920, fps 30, and
   `defaultProps`.
5. Preview live: `npm run studio` (opens Remotion Studio on :4001).
6. Roadmap formats to add next: `kinetic_listicle` (N-reasons countdown),
   generic `price_card`, `lower_third`, `island_arcade_top_games`,
   cross-promo `price_card` (Island Candy x Island Arcade).

## Hard rules (enforced)

- **Text in the Remotion burn layer is allowed** — that is NOT an image-gen
  prompt. The "no text in image prompts" rule applies only to fal/Higgsfield
  image generation upstream. Never bake text into a generated background image.
- **Real photos/testimonials only.** Before/after must use real finished-work
  photos; `proofQuote` only ever holds a real review, first-name only.
- **Left-hand-drive** steering wheel in any spi_fun_rentals / juan vehicle clip
  used as a background.
- **Route to MC Ad Library as DRAFT, never auto-post.** (See next section.)
- **<= 3 hashtags, <= 300 words** in the post copy that accompanies the video.

## Publish to Mission Control (draft only)

After render, POST the MP4 to the MC Ad Library exactly as Content Loop does —
`POST http://localhost:3001/api/ad-creatives` with `status: "draft"` and the
client's UUID (see Content Loop §4 / `ad_variant_fanout.py CLIENT_DB_ID`). Then
Telegram-notify Mario with the preview. **Never** post to Facebook from here.

## QC checklist before declaring a render shippable

1. Render the MP4 and confirm it lands in MC as `status=draft`.
2. Extract frames (`ffmpeg -ss <t> -i out.mp4 -frames:v 1 f.png`) and eyeball:
   text inside safe zones, brand colors correct, before/after wipe reveals
   cleanly, CTA legible.
3. Confirm zero text was baked into any upstream image-gen prompt.
4. Confirm before/after uses REAL photos and any review is real + first-name.
5. Re-render the same composition with a SECOND props file to prove prop-driven
   variation works in minutes.
6. (Optional) Score the clip with Higgsfield `virality_predictor` as a gate.
7. Get Mario's approval on the reference render before client production volume.

## Gotchas

- All `@remotion/*` packages + `remotion` must share the EXACT same version, or
  render throws a version-mismatch error. `npm run` won't auto-fix it.
- Run renders from the project root so `staticFile()` resolves `public/`.
- `@remotion/google-fonts` Inter is weight-limited in `fonts.ts` (4 weights,
  latin) — adding more weights re-introduces the 100+ font-fetch warning and
  slows headless render.
- Studio is the only thing that needs a port (4001). `remotion render` is
  headless and uses no port.
