# Crexi DB Cross-Check — Talgaos Feasibility

**DB:** `/home/mario/crexiscrapperloopnet/warehouse/comps.db` (78 RGV land comps, mostly Hidalgo / Pharr / McAllen)
**Run date:** 2026-04-26
**Purpose:** Independent sanity check on IDX-derived per-acre and per-SF pricing for the subject parcel and its small-lot subdivisions.

---

## Aggregate validation

42 properties under 5 acres in DB with valid acreage + price. Distribution:

| Lot size band | n | Median $/acre | $/acre range | Use case |
|:---|---:|---:|---:|:---|
| **0.08–0.20 ac** (3,500–8,712 SF) | 3 | $3,492,462 | $2.9M–$4.9M | McAllen downtown commercial — NOT residential comp |
| **0.32–0.75 ac** (14K–32K SF) | 9 | $785K | $522K–$1.0M | Mid-size commercial / pad sites |
| **1.0–2.0 ac** (43K–87K SF) | 10 | $929K | $213K–$1.3M | Commercial corner / pad sites |
| **2.0–4.0 ac** | 13 | $580K | $213K–$884K | Multi-tenant commercial |
| **4.0–5.0 ac** (matches subject scale) | 7 | $475K | $130K–$1.05M | Mixed commercial / multi-family / large infill |

## Subject-comparable pricing band

Subject is 4.16 ac at **$102,163/acre** combined basis ($425K total).

The closest Crexi comp by both size and use intent:
- **Mission 8.96 ac at $100,982/ac** (per Mario's prior validation note) — **0.2% off the subject blended basis** ✓
- McAllen 4.421 ac at $1,990K = $884K/ac — but this is W. Expressway 83 commercial (not comparable)
- N Jackson Rd Pharr 0.75 ac at $1.0M/ac — commercial pad
- 4.7 acres at $130,971/ac (city: blank — likely McAllen mixed-use) — **closest direct dollar/acre match to subject** at 28% above

**Conclusion:** Subject's $102K/acre acquisition basis is consistent with rural-to-edge-of-town residential infill in Hidalgo County. Commercial-zoned tracts trade at 5×–10× this rate. The Mission 8.96 ac comp is the strongest Crexi cross-check — confirms the seller is not asking commercial pricing.

---

## Small-lot validation (sub-0.10 ac)

Crexi small-lot sample (all McAllen 17th Street downtown):

| Address | Acres | Lot SF | Price | $/SF | Status |
|---|---:|---:|---:|---:|:---|
| 325 S 17th St McAllen | 0.080 | 3,484 | $235,000 | $67.45 | active |
| 215 S 17th St McAllen | 0.097 | 4,203 | $475,000 | $113.01 | active |

These are **commercial downtown McAllen lots**, not residential townhouse comps. They appear in IDX too (same listings) and are correctly excluded from Tier A in our final comp set.

## Why Crexi is limited for this study

- **78 total RGV records, not 78 small lots** — Crexi indexes commercial / development land more thoroughly than small residential lots
- **Most records lack zip** (`zip` field blank for 75 of 78) and many addresses are munged (e.g., `"th Street McAllen"` from URL slug parsing)
- **No Edinburg residential lots** under 0.5 ac in Crexi data
- **Use case:** sanity check on per-acre pricing for the **whole 4.16 ac subject**, not for individual townhouse pads

The IDX MLS data + HCAD tax-office Russell Village deep-dive remain the primary sources. Crexi confirms we're not in a different ballpark on the gross subject price.

---

## Validation outcome

| Check | Crexi finding | Our model | Pass/Fail |
|:---|---|---|:---|
| Subject $/acre vs Hidalgo Co rural-residential infill | $100,982/ac (Mission 8.96 ac) | $102,163/ac (4.16 ac combined) | ✓ |
| Sub-0.10 ac McAllen commercial pricing | $67–$113/SF | excluded from Tier A | ✓ |
| Small residential lot direct comp | None in DB | 0 comparable | Confirmed gap |

No adjustments to lot_pricing.json based on Crexi cross-check — the IDX-derived $45K/$55K/$65K recommendation stands.
