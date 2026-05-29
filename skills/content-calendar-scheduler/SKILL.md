---
name: content-calendar-scheduler
version: 1.0.0
author: mario
category: content-creation
risk: medium
tags: [content-calendar, scheduling, mission-control, supabase, graph-api, lifecycle, format-rotation, draft]
description: >
  Calendar-as-primary-output for Mission Control. One trigger fans a client's
  content pillars into ~30 DATED, platform-tagged, FORMAT-assigned draft rows
  (so no two consecutive posts look alike) with a draft -> approved ->
  scheduled@time -> posted -> tracked lifecycle that the EXISTING Meta Graph
  API scheduler consumes. Guarantees cadence and designs-in variety. Adds a
  data model (scheduled_at, lifecycle_status, platform, content_format,
  calendar_slot) to the ad_creatives table — it is NOT a new generator; it
  orchestrates the existing ones. Never auto-posts. Trigger phrases: "build a
  content calendar", "month of posts for sugar shack", "what's queued for
  sugar shack next week", "schedule the month", "30 day calendar", "plan the
  content calendar", "fan pillars into a month".
---

# content-calendar-scheduler

Clients perceive **cadence as caring**. Today content is generated piece-by-
piece and dumped into the MC Ad Library as undated drafts with no scheduled
date and no lifecycle beyond `draft`. This skill adds a calendar + status data
model so one trigger produces a visible, varied month — and forces format
variety by assigning a DIFFERENT format to each slot.

> The "calendar-as-output" idea is borrowed from the Blotato video — but built
> on Mario's OWN compliant Graph-API + draft-then-approve path. We REJECT
> Blotato / upload-post auto-posters (they violate Facebook=Graph-API-only +
> no-auto-post). This skill steals the idea, never the tool.

## Status this session (Smart First Wave)

- **SKILL.md + migration SQL authored and staged.** The migration is NOT
  applied to live Mission Control yet (that was deferred by scope choice).
- Migration: `.claude/skills/content-calendar-scheduler/migration.sql`
  (idempotent; adds `scheduled_at`, `lifecycle_status`, `platform`,
  `content_format`, `calendar_slot`, `posted_at`, `post_permalink` + a
  scheduler index + a `content_calendar` view). Shares the `ad_creatives`
  table with `ad-variant-fanout`'s ledger.

## Apply (only on Mario's go)

Mission Control = **GitHub + VPS, NO Vercel**. Review `migration.sql`, then run
it against the MC Supabase (Projects/missioncontrol/dashboard). It is additive
and non-breaking (existing `status` column untouched; the lifecycle CHECK is
`NOT VALID` so legacy rows aren't rejected). **Ask before pushing** the schema
+ any UI to GitHub/VPS.

## The pipeline (what the skill does once the schema exists)

1. Read the client's content pillars (and optionally seed each slot's topic
   from existing GSC quick-wins / `rankings_refresh` data, so posts target
   rankings rather than random ideas).
2. Emit ~30 dated DRAFT rows, each PRE-ASSIGNED a `content_format` on a
   rotation so no two consecutive slots match, e.g.:
   - Mon — `remotion_listicle` (remotion-branded-templates "top 3 / 5 reasons")
   - Wed — `ugc_variant` (ad-variant-fanout top pick)
   - Fri — `before_after` (remotion before/after wipe)
   - Sun — `price_card` / cross-promo (e.g. Island Candy x Island Arcade)
   - plus periodic `cinematic_clip` (Content Loop)
3. Each row lands as `lifecycle_status='draft'` with a `calendar_slot` date and
   `platform`. Mario approves a week at a time → `approved` → set
   `scheduled_at` → `scheduled`.
4. The EXISTING Meta Graph API scheduler consumes ONLY `scheduled` rows whose
   `scheduled_at` is due (Facebook for the 8 clients; GBP via `blog_writer.py`
   for the GBP-active clients: custom_designs_tx, sugar_shack, island_candy).
   On publish, advance to `posted` and store `post_permalink` (FB verification
   rule: confirm post ID + permalink).
5. Claude answers "what's queued for sugar_shack next week?" straight from the
   `content_calendar` view.

## Hard rules (enforced)

- **Never auto-generate-and-post.** Generation produces drafts; posting
  requires a prior `approved` status set by Mario.
- **<= 3 hashtags, <= 300 words** on every generated post.
- **No text baked into image-gen prompts**; real testimonials only.
- **optimum_clinic excluded** (CLOSED 2026-05-22).
- **Bilingual EN/ES** slots for the RGV/SPI market.

## QC checklist (when applied)

1. Generate a 30-day calendar for one client (e.g. island_arcade): confirm 30
   dated rows land as DRAFT, each tagged platform + a rotating format, no two
   consecutive slots sharing a format.
2. Where topic-seeded, confirm seeds trace to real GSC quick-wins.
3. Approve a week → confirm status flips to `approved`/`scheduled` and the
   Graph API scheduler picks up ONLY scheduled+due rows.
4. Publish one test scheduled post → confirm it flips to `posted` with a real
   post ID + permalink.
5. Zero-unapproved-post audit: nothing posts without a prior `approved` status.
6. Mario approves the format-rotation logic before ship.
