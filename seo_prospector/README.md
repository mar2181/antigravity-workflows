# SEO Prospector — RGV Rank-5-to-10 Lead Finder

Finds businesses that rank **mid-page (positions 5-10)** in Google's local
results for an industry + city across the Rio Grande Valley. These are SEO
sales prospects: they already show up on Google but aren't in the top 3, so the
pitch is **"we'll move you from #7 to #1."**

This is the counterpart to `../lead_gen/` — that tool finds **no-website**
businesses in the **top 3**; this one finds **rank-5-10** businesses regardless
of website status (website yes/no is recorded as a column).

**Pattern:** Places text search → slice rank 5-10 → enrich (phone, website, email, Facebook) → score → CSV (per city) → Twenty CRM (optional)

---

## Files

| File | Purpose |
|---|---|
| `rank_prospector.py` | Scraper. Places API text search per category × city, slices rank 5-10, enriches with phone / website / email / Facebook, scores, writes CSV (combined or one per city). |
| `upload_to_twenty.py` | Uploads the latest CSV into Twenty CRM as `SEO \| R<rank> \| <category> \| <name>` companies. |
| `output/` | CSV output (auto-created). |

Categories (41) and cities (16) are imported from `../lead_gen/config.py` — edit
that file to change coverage.

---

## Engine

Google Places API **text search** (`maps.googleapis.com/maps/api/place/textsearch`).
One call per `"{category} in {city} TX"` query returns up to 20 places in
Google's ranked order; positions 5-10 are sliced out and each is enriched with a
`details` call for phone + website. No scraping, no CAPTCHAs.

> Note: text-search order is Google's ranked Places data localized by the city
> in the query. It is a close proxy for the local pack a user sees, but not
> pixel-identical to a logged-in user's personalized results. Good enough for
> prospecting.

There is no Printing Press CLI for ranked Places search, so this uses the
Places API over raw HTTP (same approach as `lead_prospector.py`).

---

## Contact enrichment

For each rank-band business, the tool visits the firm's own website
(homepage + `/contact`, `/contact-us`, `/about`, `/about-us`) and extracts:

- **email** — every address found in `mailto:` links and page text, junk
  filtered (asset files, placeholders, vendor addresses).
- **facebook** — the firm's Facebook page URL. If the website doesn't link
  one, a Bright Data Google search (`"{name}" {city} TX facebook`) is the
  fallback.

Both land in their own CSV columns. **Email coverage is partial** — many
businesses publish only a contact form, with no address to scrape. A blank
cell means none was found; nothing is ever fabricated. Skip this step with
`--no-enrich`.

---

## Prerequisites

- **`GOOGLE_PLACES_API_KEY`** in `../.env.local` — the Google Maps Platform key
  with legacy Places API enabled (already set).
- **`BRIGHT_DATA_KEY`** in `../.env.local` — used only for the Facebook-search
  fallback during enrichment (already set).
- **`TWENTY_API_KEY`** in `../.env.local` + **Twenty CRM** at `localhost:3000` —
  only for the optional upload step.

---

## Run

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution/seo_prospector"

# Dry run — search plan + cost estimate, no API calls
python rank_prospector.py --dry-run

# Single-city test (recommended first)
python rank_prospector.py --category "attorney" --city "McAllen"

# Attorneys across 3 cities, one CSV per city
python rank_prospector.py --category "attorney" --cities "Harlingen,McAllen,Mission" --separate-by-city

# All categories, one city
python rank_prospector.py --city "McAllen"

# Full RGV sweep (41 categories × 16 cities)
python rank_prospector.py

# Optional: upload the latest CSV to Twenty CRM
python upload_to_twenty.py            # add --dry-run to preview names first
```

### Flags

| Flag | Effect |
|---|---|
| `--category NAME` | Single category — free text (e.g. `"attorney"`). |
| `--city NAME` | Single city. |
| `--cities "A,B,C"` | Comma-separated list of cities. |
| `--separate-by-city` | Write one CSV per city instead of one combined file. |
| `--no-enrich` | Skip the email/Facebook enrichment step (faster). |
| `--rank-min N` / `--rank-max N` | Rank band to keep (default 5-10). |
| `--limit N` | Cap categories (testing). |
| `--output NAME` | Custom CSV name (combined mode only). |

Output files: `output/{category}_{City}_{date}.csv` per city, or
`output/rgv_rank5to10_{date}.csv` combined.

---

## Scoring (SEO-prospect rubric)

A mid-page business worth pitching is established and close to breaking the top 3.

| Signal | Points |
|---|---|
| Rank #4-6 | +25 |
| Rank #7-8 | +15 |
| Rank #9-10 | +10 |
| 100+ reviews | +30 |
| 50-99 reviews | +20 |
| 20-49 reviews | +10 |
| Rating ≥ 4.5 | +10 |
| Rating ≥ 4.0 | +5 |
| Has a real website | +10 |

**Tiers:** HOT ≥ 55 · WARM 35-54 · COLD < 35.

---

## Twenty CRM

- Company name: `SEO | R{rank} | {category} | {business name}`
  (e.g. `SEO | R7 | plumber | Trevino Plumbing`).
- The `SEO |` prefix keeps these separate from the `HS |` no-website leads.
- The uploader paginates existing companies and skips any `SEO |` name already
  present, so re-running it is safe (no duplicates).

---

## Cost

Places `textsearch` (~$0.032/call) + `details` (~$0.017/call).

| Run | Approx cost |
|---|---|
| Single category × city | ~$0.13 |
| One city (41 categories) | ~$5 |
| Full 16-city RGV sweep | ~$88 |

Run a single-city test before the full sweep.

---

## Known limits

- Text-search ranking ≈ local-pack order but not identical (see Engine note).
- No Supabase / Mission Control `/leads` integration yet — Twenty CRM + CSV only.
- No `--deep` neighborhood-level queries; one query per category × city.
