# Optimum Health and Wellness Foundation — Agent Steering Document
> Read this before starting any Foundation session. Update it after every session.
> For full campaign pipeline SOP, use skill: `optimum-foundation-facebook`
> ⚠️ NEVER mix with optimum_clinic — different entity, different CTA, different tone.

---

## Organization Identity

- **Organization:** Optimum Health and Wellness Foundation
- **Type:** 501(c)(3) Nonprofit — Community Health
- **Mission:** Improve healthcare access and health literacy for underserved RGV communities
- **Location:** Pharr, TX / Rio Grande Valley _(confirm exact address with owner)_
- **Phone:** _(confirm with owner)_
- **EIN:** _(confirm from foundation documents — required for donation ads)_
- **Service Area:** Hidalgo County, Cameron County, Rio Grande Valley
- **Language:** Fully bilingual (English / Spanish)
- **Facebook Page:** ⚠️ PENDING — confirm page URL before any posting
- **Auth Account:** ⚠️ PENDING — confirm before posting
- **Page Key:** _(add to fb_pages_config.json once confirmed)_
- **GBP:** ❌ None_
- **Related Entity:** Optimum Health & Wellness Clinic — SEPARATE business, do NOT confuse

---

## The Critical Difference from the Clinic

| | Optimum Clinic | Optimum Foundation |
|-|-|-|
| Type | For-profit cash-pay clinic | Nonprofit 501(c)(3) |
| Primary CTA | "Walk in tonight" | "Donate / Volunteer / Share" |
| Tone | Urgent, cost-saving, direct | Community impact, mission-driven |
| Content | Medical services, pricing, hours | Outreach, events, health education |
| Offers | Medical services / pricing | Donation drives, volunteer calls, events |

---

## Foundation Programs

- **Health Access:** Supporting uninsured and underinsured residents
- **Health Education:** Community education on diabetes, hypertension prevention
- **Bilingual Outreach:** Health literacy in English and Spanish
- **Free / Subsidized Screenings:** Community health screening events
- **Partnership Programs:** Connecting businesses, schools, employers with health resources

---

## Critical Copy Rules (Nonprofit Compliance)

- **No medical service offers** in foundation posts — wrong entity if you see that
- **Include EIN** in any post explicitly asking for donations _(confirm number first)_
- **No clinical/medical language** — community-facing, not patient-facing
- **Testimonials:** Variant B only — "Families across the RGV benefit from..." _(until verified)_
- Every post must have a CTA: Donate / Volunteer / Share / Register / Learn more
- Lead with community impact, not organization features
- Use "your community" and "your neighbors" language
- Max 300 words | Max 3 hashtags | No text overlays in images

---

## Current Priorities
> Update this section at the start of each session

- [ ] **Confirm Facebook page URL** before any posting session ⚠️
- [ ] **Confirm EIN number** for donation posts ⚠️
- [ ] **Current campaign goal:** _(fill in — awareness / fundraising / event / volunteer recruitment)_
- [ ] **Active angle:** _(fill in — see 10 angles below)_
- [ ] **English or Spanish post (or both)?:** _(fill in)_
- [ ] **Upcoming event:** _(fill in — free screening, community health day, etc.)_

**10 Available Angles:**
1. Healthy Community, Stronger RGV — general awareness
2. Your Donation = A Neighbor's Doctor Visit — fundraising
3. Join Our Volunteer Team — recruitment
4. Free Health Screening Event — event promo
5. 28,000 Uninsured Neighbors — awareness shock stat
6. Health Education in Your Language — program awareness (Spanish speakers)
7. Partner With Us — local businesses / employers
8. We're Building a Healthier Pharr — brand story
9. Together We Can Close the Gap — donation / impact
10. Kids Deserve Healthy Futures — youth health / parents

---

## Posting Log
> Add a row after every post.

| Date | Angle | Goal | Language | Engagement | Notes |
|------|-------|------|----------|------------|-------|
| _(add after each post)_ | | | | | |

---

## What's Working

- _(add observations as posts go live)_

---

## Competing Organizations

> These serve similar missions in RGV. Know them — differentiate on community trust and local roots.

| Organization | Notes | How to Differentiate |
| ------------ | ----- | -------------------- |
| Renaissance Cares Foundation | DHR Health nonprofit, underserved RGV residents | We're independent, community-first — not attached to a hospital system |
| Valley Baptist Legacy Foundation | Health grants, scholarships across RGV | Different scope — their focus is grants/scholarships, ours is direct access |
| Hidalgo County Health & Human Services | 8 free/low-cost county clinics | Government entity — we offer community warmth, bilingual personal touch |
| UT Health RGV | 30+ clinics valleywide, community-access | Academic/institutional — we're grassroots, neighbor-to-neighbor |
| Texas Mission of Mercy RGV | Free dental/medical events, Edinburg area | Event-based only — we offer ongoing programs and outreach |

**Differentiation angle:** We are Pharr-based, community-led, bilingual from the ground up — not a branch of a hospital or government program.

---

## What to Avoid

- No mixing clinic services / pricing into foundation posts
- No claiming specific patient outcomes
- No donation request without EIN present
- _(add as you learn)_

---

## Facebook Setup Needed Before First Post

- [ ] Get Facebook page URL from owner / confirm the page exists
- [ ] Add to `fb_pages_config.json` with key `optimum_foundation`
- [ ] Confirm which auth account manages this page (Mario or Yehuda)
- [ ] Confirm EIN number for donation-focused ads
- [ ] Run text-only test post first before image posts

---

## Image Style Notes

- Format: `landscape_16_9` only
- Style: community warmth — diverse RGV families, warm lighting, community gatherings, hopeful tone
- Output folder: `C:\Users\mario\optimum_foundation_ad_images\`
- End all image prompts with: `professional photography, 4k`
- No text, logos, or people's faces in generated images

---

## Quick Commands

```powershell
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# Generate + optimize copy (confirm page URL first before posting)
python ad_copy_optimizer.py optimum_foundation --angle "your donation equals a neighbors doctor visit"
python ad_copy_optimizer.py optimum_foundation --angle "free health screening event" --language es
```

---

## Session Notes

_(notes go here — clear after each session)_
