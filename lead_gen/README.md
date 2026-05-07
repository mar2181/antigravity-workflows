---
name: RGV Lead Generation — No-Website Business Finder
description: Full pipeline to find, score, and organize RGV businesses without websites. Scrapes Google SERPs via Bright Data, scores leads, outputs CSV, uploads to Supabase + Twenty CRM, and serves them in Mission Control /leads. Validated 2026-05-06 with 547 leads across 38 categories × 16 cities.
tags: ["lead-gen", "bright-data", "supabase", "twenty-crm", "mission-control", "rgv", "sales", "hs-solutions"]
icon: 🎯
status: LIVE
version: 1.0
validated: "2026-05-06 — 547 leads scraped, Supabase table created, Twenty CRM uploaded, Mission Control /leads page live"
---

# RGV Lead Generation — No-Website Business Finder

**Skill ID:** `rgv-lead-generation`
**Pattern:** scrape → score → deduplicate → CSV → Supabase → Twenty CRM → Mission Control

This pipeline finds RGV businesses that DON'T have a website and scores them by lead quality.
It searches Google Local Pack (3-pack) results across 38 business categories × 16 RGV cities ×
3 query variations = ~1,824 searches, producing a prioritized lead list.

---

## Architecture Overview

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ 1. scraper.py    │→  │ 2. batch_runner  │→  │ 3. upload_to_    │
│    Single cat ×   │   │    .py            │   │    supabase.py   │
│    city search    │   │    Parallel sweep  │   │    547 rows →    │
│    + scoring      │   │    across all 38   │   │    hs_solutions_ │
│                   │   │    categories      │   │    leads table   │
└──────────────────┘   └──────────────────┘   └──────────────────┘
                                                       │
                                                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ 5. Mission       │←  │ 4. upload_to_    │   │ Supabase          │
│    Control        │   │    twenty.py     │   │ (source of truth) │
│    /leads page    │   │    ~514 leads →  │   │                   │
│    Filter, sort,  │   │    Twenty CRM    │   └──────────────────┘
│    status update  │   │    REST API      │
└──────────────────┘   └──────────────────┘
```

---

## Files

All scripts live in `C:/Users/mario/.gemini/antigravity/tools/execution/lead_gen/`:

| File | Purpose |
|---|---|
| `config.py` | Categories (38), cities (16), scoring weights, query templates |
| `scraper.py` | Single-process scraper. Bright Data → Google SERP → parse local pack → score |
| `batch_runner.py` | Multi-process orchestrator. Splits categories across N workers |
| `upload_to_supabase.py` | CSV → `hs_solutions_leads` table in Supabase (batches of 50) |
| `upload_to_twenty.py` | CSV → Twenty CRM REST API (`localhost:3000/rest/companies`) |
| `output/` | CSV output directory (auto-created) |

Mission Control files (in `C:/Users/mario/Projects/missioncontrol/dashboard/`):

| File | Purpose |
|---|---|
| `src/app/api/v1/leads/route.ts` | GET (list + filter + sort + paginate) + PATCH (update status) |
| `src/app/leads/page.tsx` | Full leads browser with glass-card dark theme |
| `src/components/Sidebar.tsx` | Added "Leads" nav item (Target icon) |

---

## Prerequisites

### Bright Data API Key
- Stored in `.env.local` alongside the scraper as `BRIGHT_DATA_KEY`
- The scraper auto-loads it — no env var export needed
- **Cost:** ~$0.001 per SERP fetch. Full sweep (~1,824 queries) = ~$1.82

### Supabase
- Project: `svgsbaahxiaeljmfykzp` (Mission Control's Supabase)
- Service role key in `upload_to_supabase.py` (hardcoded — move to env var)
- Table: `hs_solutions_leads` (created via migration `create_hs_solutions_leads`)

### Twenty CRM
- Self-hosted at `localhost:3000`
- API key (JWT) in `upload_to_twenty.py` (hardcoded — move to env var)
- Rate limits: 100 tokens per 1s AND 100 tokens per 60s
- Script uses 0.6s delay + 2s cooldown every 30 requests

---

## Step-by-Step Execution

### Step 1: Dry-Run (verify config)

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution/lead_gen"
python scraper.py --dry-run
```

Shows: category count, city count, total API calls, estimated time, sample queries.

### Step 2: Run the Sweep

**Option A — Single category (fast test):**
```bash
python scraper.py --category "dentist"
```

**Option B — Full parallel sweep (recommended):**
```bash
python batch_runner.py --workers 4
```

- 4 workers = ~15-20 minutes for all 38 categories
- Progress logged per batch with running lead count
- Output: `output/rgv_full_sweep_YYYY-MM-DD_HHMM.csv`

**Option C — Single category + single city:**
```bash
python scraper.py --category "plumber" --city "McAllen"
```

**Other flags:**
- `--limit 5` — only first N categories (test mode)
- `--no-website-only` — filter to ONLY businesses without websites
- `--min-score 20` — raise/lower the score cutoff
- `--output custom.csv` — custom output filename
- `--debug` — save raw HTML responses

### Step 3: Upload to Supabase

```bash
python upload_to_supabase.py
```

- Reads the latest CSV from `output/`
- Batches of 50 rows via `supabase.table("hs_solutions_leads").insert()`
- Verifies total row count after upload
- **This is required** for Mission Control `/leads` to work

### Step 4: Upload to Twenty CRM

```bash
# Make sure Twenty is running first (localhost:3000)
python upload_to_twenty.py
```

- Checks for existing "HS |" companies before uploading
- Format: `HS | {TIER} | {category} | {Business Name}`
- Includes phone, address (city=TX, state=TX, country=US), domain (if they have one)
- Rate-limited: 0.6s between requests, 2s cooldown every 30
- **Note:** If the listing check hits rate limits, duplicates may occur. Run once, then manually deduplicate if needed.

### Step 5: Open in Mission Control

```
http://localhost:3001/leads
```

Features:
- Filter by tier (HOT/WARM/COLD), category (38 options), city (16 options), status
- Search by business name
- Sort by score, name, category, city, reviews
- Click any row → detail modal with full info + status update buttons
- Pagination (50 per page)

### Step 6: Open in Twenty CRM

```
http://localhost:3000/objects/companies
```

Search "HS |" to see all leads. Each company has phone, address, and domain fields populated.

---

## Scoring System

| Signal | Points |
|---|---|
| Rank #1 in search | +30 |
| Rank #2 in search | +25 |
| Rank #3 in search | +20 |
| NO website at all | +40 |
| Social media as "website" | +15 |
| 5+ reviews | +5 |
| 20+ reviews | +10 |
| 50+ reviews | +15 |
| 100+ reviews | +20 |
| 200+ reviews | +25 |
| Rating ≥ 4.5 | +10 |
| Rating ≥ 4.0 | +5 |

**Tiers:**
- **HOT:** 75+ points — high reviews + no website + top rank
- **WARM:** 55-74 points — solid business, good prospect
- **COLD:** 35-54 points — worth tracking, lower priority
- **LOW:** < 35 — excluded by default (min_score = 10)

---

## The 38 Categories

```
dentist, orthodontist, cosmetic dentist, chiropractor, physical therapist,
optometrist, veterinarian, urgent care, dermatologist,
personal injury lawyer, divorce attorney, immigration lawyer, criminal defense attorney,
plumber, electrician, hvac contractor, roofing contractor, landscaping,
general contractor, home remodeler,
auto repair shop, auto body shop,
hair salon, nail salon, day spa, massage therapist,
accountant, insurance agent, real estate agent,
restaurant, catering,
gym, personal trainer, martial arts,
cleaning service, moving company, photographer, event planner,
towing service, pest control, pool contractor
```

To add/remove categories: edit `CATEGORIES` in `config.py`.

---

## The 16 RGV Cities

```
McAllen, Edinburg, Mission, Harlingen, Brownsville, Pharr, Weslaco,
San Benito, Donna, Alamo, Mercedes, Los Fresnos, Hidalgo,
Rio Grande City, Port Isabel, South Padre Island
```

To add/remove cities: edit `CITIES` in `config.py`.

---

## Maintenance Notes

### Adding a new city or category
1. Edit `config.py` — add to `CATEGORIES` or `CITIES` list
2. Re-run `batch_runner.py`
3. Re-run `upload_to_supabase.py` (UPSERT not implemented — manually deduplicate or clear table first)
4. Re-run `upload_to_twenty.py`

### Refreshing leads (monthly/quarterly)
1. Run `batch_runner.py` to get fresh rankings
2. Decide: replace all rows in Supabase, or merge by dedup key
3. Currently there's no UPSERT — simplest approach is to write to a new CSV and manually compare

### Twenty CRM API key rotation
- API keys are in Twenty Admin → Developers → API Keys
- Update the `API_KEY` variable in `upload_to_twenty.py`
- Keys are workspace-scoped JWTs with long expiration

### Bright Data key rotation
- Update `BRIGHT_DATA_KEY` in `.env.local` (parent directory of `lead_gen/`)
- The scraper auto-loads it — no code changes needed

---

## Known Limitations

1. **No UPSERT on Supabase** — re-running `upload_to_supabase.py` will create duplicates. Manually truncate `hs_solutions_leads` before re-uploading.
2. **Twenty rate limits** — the "check existing" listing also burns rate limit tokens. On large databases, this can fail before completing.
3. **No enrichment yet** — leads have name/phone/address/category but no photos, Facebook pages, or Google Place IDs. Enrichment pipeline is the next phase.
4. **Google SERP parsing is fragile** — relies on specific CSS class names (`VkpGBb`, `yYlJEf`, `OSrXXb`). Google changes these periodically. If results drop to 0, the parser needs updating.
5. **Bright Data costs** — full sweep costs ~$1.82. Running daily would be ~$55/month. Recommended cadence: monthly.

---

## Session History

| Date | What | Result |
|---|---|---|
| 2026-05-06 | Initial build + first sweep | 547 leads across 38 categories. Supabase table created. Twenty CRM uploaded. Mission Control /leads page live. Pushed to GitHub branch `claude/recurring-google-audits-7p2L`. |
