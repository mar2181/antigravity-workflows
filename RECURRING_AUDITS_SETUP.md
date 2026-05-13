# Recurring Google Audits — Setup Guide

**Last updated:** 2026-05-05
**Why this exists:** The /routines page is cluttered with completed one-shots and paused failed attempts. The audit pattern that already wrote real data to Supabase (full GSC audits with 80+ populated columns) is proven — we just never converted it to a recurring schedule. This file is the recipe to do that.

---

## Step 1 — Cleanup (Mario, ~3 min, in claude.ai web UI)

Open https://claude.ai/code/routines (or whichever surface holds your "Scheduled tasks" page) and **delete these 17 routines**. They are all completed one-shots or paused failed attempts. Safe to remove.

### Completed one-shot keyword reruns (4 routines)
- Keyword rankings now batch 1
- Keyword rankings now batch 2
- Keyword rankings now batch 3
- Keyword rankings now batch 4

### Completed one-shot GSC audits (8 routines)
- Gsc now juan elizondo
- Gsc now custom designs
- Gsc now island arcade
- Gsc now island candy
- Gsc now optimum clinic
- Gsc now sugar shack
- Gsc rerun island arcade may4
- Gsc rerun sugar shack may4

### Paused failed-attempt weekly GSC audits (5 routines — replaced by ONE master below)
- Gsc audit island rk
- Gsc audit island candy
- Gsc audit sugar shack
- Gsc audit juan elizondo
- Gsc audit custom designs

**Keep these (they work):**
- ✅ Keyword rankings batch 1, 2, 3 (daily — alive, doing work)
- 🟡 YouTube intelligence monitor / Skool automations / Email reminders 2h (paused — your call)

---

## Step 2 — Create 3 NEW recurring routines (Mario, ~5 min total)

For each of the 3 prompts below, in claude.ai chat:
1. Open a new chat
2. Type `/schedule`
3. Paste the prompt
4. Set the cadence as noted
5. Save

**Cadence summary** (UTC times shown — your local Texas CDT = UTC - 5h, so 14:00 UTC = 9:00 AM CDT):

| Audit | Day | Time (UTC) | Local CDT |
|---|---|---|---|
| GSC weekly | Monday | 14:00 | 9:00 AM |
| GBP weekly | Wednesday | 14:00 | 9:00 AM |
| GA4 weekly | Friday | 14:00 | 9:00 AM |
| GA4 install tracker | Saturday | 15:00 | 10:00 AM |

(Spread across the week so you have something fresh in Mission Control every couple of days, and the runs don't collide. Saturday tracker fires AFTER Friday's audit so it sees the latest install state.)

---

## ── PROMPT 1: GSC Weekly Audit ──

**Schedule:** Every Monday 9:00 AM CDT (14:00 UTC)
**Coverage:** 6 clients with GSC installed: sugar_shack, island_arcade, island_candy, juan, optimum_clinic, rgv_reef. (Custom Designs TX is `external-only` and is audited via the daily cron already; skipping the weekly to avoid double-writes.)

```
You are running the weekly Google Search Console audit for Antigravity Digital's clients. Run for ALL clients listed below in sequence, one at a time. Do not parallelize.

CLIENTS TO AUDIT THIS WEEK (in order):
1. sugar_shack — the-sugar-shack.com
2. island_arcade — island-arcade.com
3. island_candy — island-candy.com
4. juan — juanjoseelizondo.com
5. optimum_clinic — optimumhealthandwellnessclinic.com
6. rgv_reef — rgvreef.org

FOR EACH CLIENT:

1. Open Google Search Console for that client's property in the browser. Use the canonical property (sc-domain:{domain} preferred; otherwise the verified prefix property).

2. Execute the full audit per the template at:
   C:/Users/mario/.gemini/antigravity/tools/execution/audit_prompts/gsc_audit_template.md
   Phases 1–9. Capture screenshots. Stop after each phase to summarize.

3. After Phase 9 is complete, INSERT one row into the Supabase `gsc_audits` table via the Supabase MCP. Match the existing schema (see the most recent row for custom_designs_tx as a template — there are 80+ columns including total_clicks, total_impressions, top_queries (JSON), top_pages (JSON), indexing_grade, sitemap_status, cwv_*, links_grade, schema_*, full_report_markdown, audit_notes). Use today's date for `audit_date`.

4. Send a 3-line Telegram summary to Mario via notify_mario() — exec from C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env. Include: client_key, overall_grade, biggest issue.

5. Move to the next client.

WHEN ALL 6 CLIENTS DONE:
- Send one final Telegram summary listing all 6 grades in a table.
- Update the per-client program.md files at tools/execution/{client_key}/program.md with a "GSC Audit Log — {date}" section.

HARD RULES:
- READ-ONLY in GSC. Do NOT click "Request indexing", "Start new validation", or modify anything.
- Do NOT fake numbers. Only report what is visible in GSC.
- If a section is missing, screenshot "No data" and document it.
- One client at a time, sequential, no parallel.
- If GSC asks you to log in, the gsc_token.json at tools/execution/gsc_token.json should be valid; if not, abort and Telegram Mario for re-auth.
```

---

## ── PROMPT 2: GBP Weekly Audit ──

**Schedule:** Every Wednesday 9:00 AM CDT (14:00 UTC)
**Coverage:** 5 active GBP clients across 2 Google accounts (Mario's profile + Yehuda's profile).

```
You are running the weekly Google Business Profile audit for Antigravity Digital's clients. Run for each client in sequence, one at a time. Some are on Mario's GBP account, some on Yehuda's.

CLIENTS TO AUDIT THIS WEEK (in order):

ON MARIO'S GBP ACCOUNT (gbp_mario_profile/):
1. custom_designs_tx — Custom Designs TX (security/AV, McAllen) — GBP ID 02979998023027904297
2. optimum_clinic — Optimum Health & Wellness Clinic — GBP ID 16753182239006365635
3. sugar_shack — The Sugar Shack (candy, South Padre Island)
4. spi_fun_rentals — SPI Fun Rentals — GBP ID 03916507027076722961

ON YEHUDA'S GBP ACCOUNT (gbp_sniffer_profile/):
5. island_candy — Island Candy (ice cream, South Padre Island)
6. island_arcade — Island Arcade (arcade, South Padre Island)

SKIP: juan (suspended, awaiting reinstatement), optimum_foundation (page URL pending).

FOR EACH CLIENT:

1. Open Google Business Profile manager for that client. Make sure you're on the correct Google account first (Mario vs Yehuda) — if you're on the wrong account, switch before opening the profile.

2. Execute the full audit per the template at:
   C:/Users/mario/.gemini/antigravity/tools/execution/audit_prompts/gbp_audit_template.md
   Phases 1–13. Capture screenshots. Stop after each phase to summarize.

3. After Phase 13 is complete, INSERT one row into the Supabase `gbp_audits` table via Supabase MCP. Populate at minimum: client_key, audit_date (today), business_name, plus the grade columns (completeness_grade, nap_grade, category_grade, services_grade, performance_grade, reviews_grade, contact_grade, public_profile_grade, overall_grade), review_count, average_rating, primary_category, secondary_categories (JSON), photo_count, last_post_date, profile_strength, full_report_markdown, audit_notes.

4. Telegram Mario a 3-line summary: client_key, overall_grade, biggest issue.

5. Move to the next client.

WHEN ALL 6 CLIENTS DONE:
- Send one final Telegram summary listing all 6 grades.
- Update each client's tools/execution/{client_key}/program.md with a "GBP Audit Log — {date}" section.

HARD RULES:
- READ-ONLY in GBP. Do NOT click Save, Publish, Post, Reply, Send, Upload, Delete, Edit, Verify, or Connect.
- Open Edit panels only to inspect, then Cancel without saving.
- Do NOT modify hours, categories, services, photos, posts, or any field.
- One client at a time, sequential.
- If you land on the wrong account, switch BEFORE opening the profile (do not open the profile while logged in to the wrong account — confuses GBP).
```

---

## ── PROMPT 3: GA4 Weekly Audit ──

**Schedule:** Every Friday 9:00 AM CDT (14:00 UTC)
**Coverage:** 3 clients with GA4 installed (the rest don't have GA4 yet — that's a separate "install GA4" project).

```
You are running the weekly Google Analytics 4 audit for Antigravity Digital's clients. Run for each client in sequence, one at a time.

CLIENTS TO AUDIT THIS WEEK (in order):
1. sugar_shack — the-sugar-shack.com — GA4 measurement ID G-2NTNTJ85EG
2. juan — juanjoseelizondo.com — GA4 measurement ID G-RC60FN4ZDD
3. custom_designs_tx — customdesignstx.com — GA4 measurement ID G-TDZPYLQHYY

SKIP: island_arcade, island_candy, optimum_clinic, optimum_foundation, spi_fun_rentals, rgv_reef — GA4 not installed (separate project).

FOR EACH CLIENT:

1. Open Google Analytics 4 in the browser. Switch to the correct property using the property selector (match the GA4 measurement ID listed above).

2. Execute the full audit per the template at:
   C:/Users/mario/.gemini/antigravity/tools/execution/audit_prompts/ga_audit_template.md
   Phases 1–15. Capture screenshots. Stop after each phase to summarize.

3. Use the LAST 90 DAYS as the default date range (if it can be set without saving). Document the actual range used.

4. After Phase 15 is complete, INSERT one row into the Supabase `ga4_audits` table via Supabase MCP. Populate: client_key, audit_date (today), property_name, property_id, measurement_id, total_users, new_users, sessions, engaged_sessions, engagement_rate, avg_engagement_time, event_count, key_events_count, top_channels (JSON), top_source_medium (JSON), top_pages (JSON), top_landing_pages (JSON), top_events (JSON), top_countries (JSON), top_cities (JSON), realtime_users_30min, traffic_grade, engagement_grade, acquisition_grade, events_grade, setup_grade, realtime_grade, data_quality_grade, overall_grade, search_console_linked (bool), google_ads_linked (bool), enhanced_measurement_enabled (bool), full_report_markdown, audit_notes.

5. Telegram Mario a 3-line summary: client_key, overall_grade, biggest tracking gap.

6. Move to the next client.

WHEN ALL 3 CLIENTS DONE:
- Send one final Telegram summary listing all 3 grades + which clients are missing GA4 entirely.
- Update each client's tools/execution/{client_key}/program.md with a "GA4 Audit Log — {date}" section.

HARD RULES:
- READ-ONLY in GA4. Do NOT click Save, Create, Submit, Publish, Link, Unlink, Delete, or Confirm.
- Do NOT create reports, explorations, events, or audiences.
- Do NOT change attribution settings, data retention, filters, or any property setting.
- One client at a time, sequential.
- If GA4 demands login, abort and Telegram Mario.
```

---

## ── PROMPT 4: GA4 Install Tracker (the "what's still missing" weekly nag) ──

**Schedule:** Every Saturday 10:00 AM CDT (15:00 UTC)
**Purpose:** Surface which clients still don't have GA4 installed, with a concrete next step for each. No comprehensive audit — just a checklist + weekly nag so missing installs don't slip into the void.

**Why we need this:** GA4 is currently only on 3 of 8 clients. The other 5 need GA4 set up before they can ever appear in the Friday GA4 weekly audit. Without a tracker, we forget.

```
You are the weekly GA4 install tracker for Antigravity Digital. Your job is to surface which clients still don't have GA4 installed so Mario can knock them out one by one. NOT a comprehensive audit — a checklist + actionable next steps.

WORKFLOW:

1. Query Supabase via the Supabase MCP:
   SELECT client_key, ga4_status, ga4_id, sitemap_url
   FROM client_seo_status
   WHERE archived = false
   ORDER BY client_key;

2. Categorize each client into one of three buckets:
   - INSTALLED — ga4_status = 'installed' AND ga4_id IS NOT NULL
   - MISSING — ga4_status IN ('missing','unknown') OR ga4_id IS NULL
   - SKIPPED — manually flagged (e.g., archived nonprofits)

3. For each MISSING client, generate a one-line install recommendation:
   - If they have a website (sitemap_url present): "Install GA4 via gtag.js or GTM in <head> of {domain}. Get a measurement ID from analytics.google.com → Admin → Create Property."
   - If sitemap_url is null: "First confirm the client has a live website. Then install GA4."
   - Note any client that's been on the MISSING list for 4+ weeks (compare to history — see step 5) — flag as "STALE: been 4+ weeks, escalate."

4. Build a Telegram digest. Format:

   📊 GA4 INSTALL TRACKER — {YYYY-MM-DD}

   ✅ INSTALLED ({count}):
   - {client_key} — {ga4_id}
   - ...

   ❌ MISSING ({count}):
   - {client_key} — {one-line recommendation}
   - ...

   🚨 STALE (4+ weeks missing):
   - {client_key} — escalate this week

   This week's recommendation: {pick the easiest one to install based on website readiness}

5. Append a row to a `ga4_install_tracking` table (create the table if it doesn't exist with columns: id uuid pk, run_date date, client_key text, status text, ga4_id text, weeks_missing int, recommendation text, created_at timestamptz default now()). One row per client per run. This builds the history we use for the "STALE" detection in step 3.

6. Send the Telegram digest to Mario via notify_mario(). Use the helper at C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env for the bot token.

7. Write a markdown summary to:
   C:/Users/mario/.gemini/antigravity/tools/execution/ga4_install_tracker/{YYYY-MM-DD}.md
   Same structure as the Telegram digest but with deeper notes (which client should be tackled first this week + why).

HARD RULES:
- READ-ONLY for client_seo_status (no UPDATEs unless Mario approves)
- INSERT-only for ga4_install_tracking
- ONE digest per Saturday — don't fire multiple times if you re-run by mistake
- If ga4_install_tracking table doesn't exist, create it with the schema in step 5
- Don't lecture — just show the list and the recommendation. Mario knows what GA4 is.
- If ALL clients are INSTALLED, send a one-liner: "🎉 All {count} clients have GA4 installed. Tracker idle this week." — and skip the markdown file.
```

---

## Why this design

- **Same pattern that produced 80+ columns of real GSC data on 2026-05-04** for custom_designs_tx — proven working approach. We're not reinventing anything; we're putting the proven thing on a recurring schedule.
- **One prompt per service** instead of one per client = 4 routines instead of 24. Less clutter, easier to maintain.
- **Tuesdays / Thursdays free** for the existing keyword rankings batches (8:00 / 8:45 / 9:30 AM) and ad-hoc work.
- **Mon GSC → Wed GBP → Fri GA4 → Sat tracker** spreads the load so you always have fresh data in Mission Control every 1-2 days, and Saturday's tracker reads Friday's GA4 results.
- **GA4 install tracker is separate from the GA4 audit on purpose:** the audit deeply analyzes properties we DO have. The tracker only reminds you about the ones we DON'T have. Different jobs, different cadences.

## What if a routine fails?

Each prompt sends Telegram on failure (login wall, missing template, etc.). When you see a failure:
1. Check what failed (login expired? template moved?)
2. Run the same prompt manually one time to confirm the fix
3. The recurring schedule fires again next week — no need to re-create the routine

## After they run for 2 weeks

Compare the data freshness across `gsc_audits`, `gbp_audits`, `ga4_audits`. If everything is healthy and Mission Control is showing fresh weekly data, we can talk about migrating to the Path A API-driven approach (PR #46 in `mar2181/missioncontrol`) for cheaper / faster runs. Until then, the prompt-driven recurring routines are the source of truth.
