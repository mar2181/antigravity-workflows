# Prompt: GSC + Sitemap + GBP Audit & Fix — One Client at a Time

> **Usage:** Copy this entire file as the agent's task prompt. Replace `{CLIENT_KEY}` with one of:
> `sugar_shack | island_arcade | island_candy | juan | spi_fun_rentals | custom_designs_tx | optimum_clinic | optimum_foundation`
>
> Run agents sequentially, not in parallel — each writes to the same Supabase tables and the same Mission Control endpoints, and Mario needs to approve fixes between clients.

---

## Your role

You are auditing and (with approval) fixing the Google Search Console + sitemap + Google Business Profile health for ONE Antigravity Digital client: **`{CLIENT_KEY}`**.

You are NOT auditing all 8 clients. Just this one. End-to-end. Full quality bar.

You report a **fix plan** to Mario. Mario approves. You execute. You verify. You write back.

---

## What "good standing" means for this client (the success bar)

A client passes audit when **all** of the following are true:

### A. GSC connection layer
1. Row exists in `gsc_properties` with `client_key='{CLIENT_KEY}'`, `verified_at IS NOT NULL`
2. Row exists in `google_oauth_tokens` with `revoked_at IS NULL` and scopes include `https://www.googleapis.com/auth/webmasters` (write scope, not just `.readonly`)
3. `client_seo_status.gsc_status = 'installed'` (not `needs-verification`, `external-only`, `missing`, or `unknown`)
4. Property URL format matches the live site (e.g. `sc-domain:customdesignstx.com` OR `https://www.customdesignstx.com/` — pick whichever is verified)
5. Calling `GET /api/search-console/{CLIENT_KEY}/test-token` returns `ok: true`

### B. Sitemap layer
1. `client_seo_status.sitemap_url` is set and points at the canonical sitemap (typically `https://{domain}/sitemap.xml`)
2. The sitemap URL is publicly reachable over HTTPS — `curl -I {sitemap_url}` returns 200 (or a 301/302 to a 200)
3. The sitemap is valid XML and contains at least one `<url>` entry. Spot-check 3 URLs from inside it — they must return 200, not 404.
4. The sitemap is referenced in `robots.txt` (line: `Sitemap: https://{domain}/sitemap.xml`)
5. `gsc_sitemaps` has at least one row for this client's property where:
   - `last_submitted` is within the last 90 days
   - `errors = 0`
   - `is_pending = false`
   - `contents.indexed > 0` (or `submitted > 0` if the site is brand new and Google hasn't crawled yet)
6. If the homepage is `https://www.{domain}/` but the sitemap lists `https://{domain}/` (no www), or vice-versa — that's a redirect mismatch. Flag it.

### C. URL indexation layer
1. Pick **6 priority URLs** for this client (homepage + 5 most important pages — use `client_seo_status.priority_urls` if populated, otherwise pick the homepage + top 5 by impressions from the last `gsc_events.audit_run` entry's `top_pages`)
2. Run URL Inspection on each (use `inspectUrl()` from `dashboard/src/lib/google/gsc-api.ts` — there's already a working implementation, or call it via the Google Search Console v1 API directly with the OAuth token from Supabase)
3. Each URL must report `verdict='PASS'` (indexed). Anything else (`NEUTRAL`, `FAIL`, `PARTIAL`) gets logged with the specific failure: `coverageState`, `pageFetchState`, `robotsTxtState`, `indexingState`.
4. `lastCrawlTime` should be within the last 30 days for active pages.

### D. Search Analytics health
1. Property has clicks + impressions in the last 28 days. Pull via `pullSearchAnalytics()` (already in `gsc-api.ts`).
2. If a brand-new site (<30 days), zero clicks is acceptable — note it but don't flag.
3. Capture top 10 queries by clicks and top 10 pages by impressions for the report.
4. Compare to the previous 28-day window if data exists — note direction (improving / flat / declining).

### E. Google Business Profile (GBP) layer
The audit isn't complete without GBP. This client may have GBP via either:
- Mario's account (`gbp_mario_profile/`)
- Yehuda's account (`gbp_sniffer_profile/`)
- Both (duplicate — needs cleanup)
- Neither (some clients don't have GBP — note it and skip)

GBP mapping table (from `MASTER_WORKFLOW.md`):

| client_key | GBP account | GBP ID / status |
|---|---|---|
| sugar_shack | Yehuda | active |
| island_arcade | Yehuda | duplicate (needs cleanup) |
| island_candy | Yehuda | active |
| juan | Mario | suspended (needs reinstatement request — escalate to Mario) |
| spi_fun_rentals | Mario | duplicate (`12018623800655095562`) |
| custom_designs_tx | Mario | active (`02979998023027904297`) |
| optimum_clinic | Mario | active (`16753182239006365635` verified) |
| optimum_foundation | unknown | TBD — escalate to Mario |

Check (read-only — DO NOT modify GBP without Mario's explicit OK):
1. Profile loads (use `competitor_monitor.py --business {CLIENT_KEY}` output if recent, or pull fresh via Places API if available)
2. Categories are correct for the business
3. Hours are populated and don't show "permanently closed"
4. At least 3 photos uploaded
5. Latest post within last 30 days (this is the integration with the SEO optimizer — if the optimizer is healthy, posts should be daily)
6. Star rating + review count vs. 7-day-old baseline (look at `competitor_reports/state.json` for the diff)
7. No "duplicate" warning, no "suspended" status

### F. Daily suggestions automation
1. Confirm the daily GSC audit cron has fired in the last 26 hours: query `gsc_events` for `event_type='audit_run' AND client_key='{CLIENT_KEY}'` ordered by `created_at DESC LIMIT 5`. Latest must be <26h old.
2. Confirm the SEO Ranking Optimizer is processing this client: check `seo_optimizer/seo_optimizer_state.json` for actions logged in the last 7 days for this `client_key`.
3. If either pipeline is silent, flag it as a separate fix and escalate.

---

## Reference data the agent needs

**Mission Control dev server (for testing API endpoints):**
```bash
cd "C:/Users/mario/Projects/missioncontrol/dashboard"
npm run dev -- --port 3001
# URL: http://localhost:3001
```

**Mission Control production:** runs on the VPS, not Vercel. Endpoints there hit the live Supabase. Use VPS for "real" sitemap submissions.

**Supabase project:** `svgsbaahxiaeljmfykzp`. Use the Supabase MCP for read queries — write queries should go through Mission Control's API (because those endpoints handle the OAuth refresh, error logging into `gsc_events`, etc.).

**Local Python tools:**
- `C:/Users/mario/.gemini/antigravity/tools/execution/gsc_audit_run.py` — currently hardcoded for `customdesignstx.com`. **DO NOT modify it for this client.** Instead, generalize it (see Phase 4 below) — but only if Mario approves the generalization.
- `C:/Users/mario/.gemini/antigravity/tools/execution/gsc_token.json` — local OAuth token, kept fresh by the script's auto-refresh.
- `C:/Users/mario/.gemini/antigravity/tools/execution/reauth_gsc.py` — re-authorize if `gsc_token.json` is dead.

**Mission Control API endpoints (already built — use these, don't rebuild):**
- `GET /api/search-console/overview` — all clients
- `GET /api/search-console/{CLIENT_KEY}` — this client's data
- `GET /api/search-console/{CLIENT_KEY}/audit` — latest audit row from `gsc_audits`
- `GET /api/search-console/{CLIENT_KEY}/test-token` — verify OAuth still works
- `POST /api/search-console/{CLIENT_KEY}/sitemap-submit` — actually submits a sitemap to Google. Body: `{ "sitemap_url": "https://example.com/sitemap.xml" }`. Requires the OAuth token to have full `webmasters` scope; will return `needs_write_scope` error otherwise (with a `reconnectUrl` to fix).
- `POST /api/search-console/trigger-audit` — fires the daily audit on demand

**OAuth re-consent (for full write scope):**
`http://localhost:3001/api/oauth/google/start?client={CLIENT_KEY}&scopes=full`

---

## Phases — execute in order

### Phase 1 — Discover (no writes)

Goal: build a complete picture of where this client stands. Output a `discovery.json`.

1. Pull from Supabase (read-only): `client_seo_status`, `gsc_properties`, `gsc_sitemaps`, `gsc_events` (last 30 days), `google_oauth_tokens`, `gsc_url_inspections` (last 14 days), `gsc_audits` (latest row).
2. `curl -I` the homepage and `/sitemap.xml` and `/robots.txt`. Capture status codes + redirect chain.
3. `curl` the sitemap body, parse the XML, count URLs, sample 3 random URLs.
4. Read `client_seo_status.priority_urls` and run URL Inspection on each via the Mission Control API or directly. (Stay under 6 inspections to respect the per-day GSC quota — pick wisely.)
5. Pull last 28 days of search analytics. Save top 10 queries + top 10 pages.
6. Run `competitor_monitor.py --business {CLIENT_KEY}` to refresh GBP standing — capture rating, review count, hours, post recency.
7. Check `gsc_events` for the latest `audit_run` event timestamp.
8. Check `seo_optimizer/seo_optimizer_state.json` for recent actions on this client.

Output: `gsc_audit_reports/{YYYY-MM-DD}_{CLIENT_KEY}_discovery.json` + a human-readable `.md` summary.

### Phase 2 — Diagnose (no writes)

Goal: enumerate every failed check from sections A–F above. Each failure becomes a numbered item with:

- **What's wrong** (one sentence)
- **Evidence** (the specific field / response that proves it)
- **Severity** (`blocker` | `warning` | `info`)
- **Proposed fix** (concrete action — API call, manual GSC step, code change, etc.)
- **Risk of fix** (none / low / requires-mario / requires-google-side / requires-client-side)
- **Reversible?** (yes / no — e.g. submitting a sitemap is effectively reversible by deleting it; OAuth re-consent is reversible by re-revoking; manual GSC verification is harder to reverse)

Output: `gsc_audit_reports/{YYYY-MM-DD}_{CLIENT_KEY}_fix_plan.md`

**STOP HERE.** Send the fix plan to Mario via Telegram (`notify_mario()`) with a link to the markdown file. Wait for explicit approval before Phase 3.

### Phase 3 — Fix (with explicit approval per item)

For each item Mario approves:

1. Execute the fix using the **least-invasive** path:
   - Sitemap submission → `POST /api/search-console/{CLIENT_KEY}/sitemap-submit`
   - OAuth re-consent → open `http://localhost:3001/api/oauth/google/start?client={CLIENT_KEY}&scopes=full` and walk Mario through the consent screen
   - Trigger fresh audit → `POST /api/search-console/trigger-audit`
   - `client_seo_status.sitemap_url` update → use Supabase MCP
   - Robots.txt fix → identify the website repo (from `MASTER_WORKFLOW.md` — e.g. `mar2181/custom-designs` for Custom Designs TX), edit the file in a feature branch, push, await Mario's deploy approval (DO NOT auto-deploy)
   - GBP issues → flag for manual fix (no API access for most GBP modifications); generate a clear instruction list for Mario to execute in `business.google.com/locations`
2. After each fix, **verify** by re-running the relevant Phase 1 check.
3. Log every fix attempt + result into `gsc_events` via Supabase: `event_type='manual_fix'`, `detail={ fix_id, before, after, executed_by:'claude_agent', verified:true|false }`.

### Phase 4 — Wire up the daily suggestions output (if Mario approves)

The daily cron currently writes events but doesn't surface "today's suggestions" to anyone. Build it once during the **first** client's audit, then it covers all 8.

1. Add a script `tools/execution/gsc_daily_suggestions.py` that:
   - Reads `gsc_events` for the last 24h (`event_type='audit_run'`)
   - For each client, computes a "today's actions" list (same logic as Phase 2 diagnose, but only flagging items that changed in the last 24h)
   - Sends a Telegram digest grouped by client
   - Cap: max 5 actions per client per day
2. Wire into the morning brief (`morning_brief.py`) — add a "GSC Suggestions" section.
3. Add to Windows Task Scheduler at 7:30 AM (after the nightly cron's 12 AM and 6:30 AM phases).

This is **only if Mario approves** during Phase 2 review of the first client. If he says "just do the audit/fix for now, leave the daily suggestions for later," skip Phase 4 entirely.

### Phase 5 — Final report

For this client:

1. Update `client_seo_status` with any field changes (sitemap_url, gsc_status, etc.)
2. Update the per-client `program.md` (`tools/execution/{CLIENT_KEY}/program.md`) → add a "GSC Audit Log" section with date + items fixed + items deferred
3. Generate `gsc_audit_reports/{YYYY-MM-DD}_{CLIENT_KEY}_final.md` with: before-state, fixes applied, after-state, items still open (and why — escalation path)
4. Send a Telegram summary to Mario (3-5 bullets max)
5. **Apply the global push-confirmation rule:** if any code or website-repo changes were made in Phase 3, list them and ask whether to push to GitHub / VPS / Vercel.

---

## Hard rules

- **One client per run.** Do not "while you're at it" the next client.
- **No writes in Phase 1 or Phase 2.** Read-only discovery + diagnosis.
- **No GSC writes without Mario's explicit per-item approval.** A sitemap submission is a real Google API call that creates a record on the property — get the OK first.
- **No website repo changes without Mario's approval.** Robots.txt edits, sitemap.xml regeneration, etc. all go through the global push-confirmation rule.
- **No GBP modifications.** Read-only. Surface issues + give Mario a manual playbook.
- **Respect quotas.** GSC URL Inspection allows ~2,000 QPD per property — don't burn it on 50 inspections per client. Cap at 6.
- **OAuth scope check first.** Before calling `sitemap-submit` or any write endpoint, hit `test-token`. If it returns `needs_write_scope`, route Mario to the OAuth re-consent URL — don't error halfway through Phase 3.
- **Telegram for every gate.** Phase 2 → fix plan. Phase 5 → summary. Use `notify_mario()` from `MASTER_WORKFLOW.md`.

---

## Output locations (use these paths consistently)

```
C:/Users/mario/.gemini/antigravity/tools/execution/gsc_audit_reports/
├── {YYYY-MM-DD}_{CLIENT_KEY}_discovery.json
├── {YYYY-MM-DD}_{CLIENT_KEY}_discovery.md
├── {YYYY-MM-DD}_{CLIENT_KEY}_fix_plan.md
└── {YYYY-MM-DD}_{CLIENT_KEY}_final.md
```

Per-client steering doc to update:
```
C:/Users/mario/.gemini/antigravity/tools/execution/{CLIENT_KEY}/program.md
  → append section: "## GSC Audit Log — {YYYY-MM-DD}"
```

---

## Done definition

You're done with this client when:
- [ ] All 6 success-bar layers (A-F) pass OR have a documented escalation
- [ ] Final report markdown exists in `gsc_audit_reports/`
- [ ] `program.md` is updated
- [ ] Mario has approved (or skipped) every Phase 2 item
- [ ] Telegram summary sent
- [ ] Push-confirmation question asked if any code/repo changes were made

Then ask Mario: "Ready to run `{NEXT_CLIENT_KEY}`?"
