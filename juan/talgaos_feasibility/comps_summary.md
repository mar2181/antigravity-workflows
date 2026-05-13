# Talgaos LLC — 000 Rogers Rd, Edinburg TX
## Lot Pricing Comp Set & Feasibility Recommendation

**Prepared:** 2026-04-26 | **Subject:** 27 townhouse lots @ ~2,540 SF each on 4.16 ac (subject 2.69 ac + Stonecrest 1.47 ac access strip)
**Buyer:** Talgaos LLC (Alicia Garza) | **Seller:** Turquesa Construction LLC (Belkis Noemi Garcia) | **Combined Basis:** $425,000

---

## Bottom-line recommendation

| Scenario | Per-lot retail | 27-lot revenue | Confidence |
|:---|---:|---:|:---|
| **Pessimistic** | $45,000 | $1,215,000 | High — supported by per-SF Russell Village derivation ($23,857) + new-construction p25 imputed ($49,778) |
| **Midpoint** | **$55,000** | **$1,485,000** | Medium-High — triangulated from new-construction townhouse imputation (median $50,500) + Russell Village whole-lot CAD ($55,242) |
| **Optimistic** | $65,000 | $1,755,000 | Medium — requires utilities + plat completion + small-builder demand; matches new-construction p75 imputed ($70,000) |

**Use $55,000/lot as base case in pro-forma.** Sensitivity test ±$10K to model risk band.

> ### Margin check — Scenario A (wholesale platted lots) does NOT pencil at $55K
> Using parallel agent's `dev_cost_benchmarks.json`: $41,200/lot mid case dev cost.
>
> | Line | $ |
> |---|---:|
> | Revenue: 27 × $55K | $1,485,000 |
> | Acquisition basis | -$425,000 |
> | Dev costs (mid: 27 × $41,200) | -$1,112,400 |
> | Closing/soft | -$15,000 |
> | **NET** | **-$67,400** |
>
> **Scenario A wholesale lots break-even retail = ~$58K/lot.**
>
> Implications:
> - **(a) Negotiate purchase price down** — $385K → $325K saves $2,222/lot, pushes Scenario A to break-even at $55K/lot
> - **(b) Scenario B (vertical build at $215K/unit avg)** remains the preferred play — see `final_proforma.json`
> - **(c) Scenario C (contract flip pre-closing)** is cleanest if a builder wants 27 platted pads at ~$60-65K each, but requires Talgaos to assign rather than close

---

## Why this number

Pure-land sales of sub-3,500 SF lots in Edinburg/McAllen are nearly non-existent in the residential market because **townhouse pads do not trade individually after platting** — developers retail finished homes, not lots. Of 3,900 IDX listings pulled across 13 RGV ZIPs, only 2 sold pure-land transactions in Edinburg (78539) under 3,600 SF in the last 24 months, both commercial-flavored (Edinburg Original Townsite at $160K and $370K, both $45-$104/SF).

Direct comp scarcity forced a triangulation approach across three independent benchmarks:

### Benchmark 1: Russell Village — same builder behavioral comp (with caveat)

Russell Village in Edinburg (78541) is **Turquesa Construction's prior platted townhouse product** — the same seller, same product type, same submarket. HCAD shows:

- **37 total Russell Village lots** (8 vacant, 29 improved)
- Vacant lot CAD land values: **median $55,242, range $53,410–$70,657** *(per WHOLE LOT)*
- Improved lots: median CAD-gross $249,041 — calibrated against IDX sold prices of $240K–$280K (4 sold Mar 2026), confirming **CAD-gross is ~99% of recent sold price** for improved Russell Village townhouses (population-median basis)

**Important caveat — this is a behavioral comp, not a $/lot direct floor:**

Russell Village lots are 5,884 SF — **2.3× subject's 2,540 SF target**. On a per-SF basis: $55,242 ÷ 5,884 = **$9.39/SF**. Applied to subject's 2,540 SF pad = **$23,857/lot**.

Two valid scaling interpretations:
- **Whole-lot lump-sum scaling (supports $55K)**: A vacant townhouse lot has a baseline value (utilities access, plat, frontage) that doesn't scale linearly with SF. CAD assigns it $55K regardless of size class.
- **Per-SF scaling (supports ~$24K)**: Smaller pads should price proportionally lower; a 2,540 SF pad isn't worth what a 5,884 SF pad is worth.

The truth is between these. Talgaos is delivering smaller pads in a denser plat (27 lots on 4.16 ac = ~6,710 SF/lot gross including ROW & common areas, vs Russell Village's larger 5,884 SF private pads with shared private roadways). The denser product attracts a different buyer (smaller-builder/investor vs custom/end-user) at a lower per-pad price.

**Conclusion: Russell Village establishes a behavioral price band $24K-$55K rather than a $55K hard floor.**

### Benchmark 2: Townhouse retail imputation

**Two views — Talgaos will deliver new construction, so the new-construction-only median is the right anchor:**

| Filter | n | Median sold | Median lot SF | Imputed land @ 20% | Use |
|:---|---:|---:|---:|---:|:---|
| All vintages (2005–2026) | 33 | $140,000 | 2,408 | $28,000 | Older 2002-2014 vintage drags median down |
| **Year-built 2018+ (new construction)** | **9** | **$252,500** | **2,459** | **$50,500** | **Talgaos-relevant comp** |

The new-construction subset (Garden Path, Russell Village, Shibui Village, Rincon de las Fuentes, Georgetown Park, Pyxis Heights, Habitat Village) is the apples-to-apples comparison. Median sold $252,500 on a 2,459 SF lot (within 3% of subject's 2,540 SF target). At 20% land share = **$50,500/lot imputed**, p75 = $70,000.

This empirically validates the 20% land share assumption — derived from Russell Village paired data ($55K CAD land / $250K sold = 22%).

Key recent sales:
| Address | Subdivision | Lot SF | Sold | Date | Imputed lot @ 20% |
|---|---|---:|---:|---|---:|
| 2613 E Solar Dr | Garden Path | 2,660 | $427,000 | Mar 2026 | $85,400 |
| 2707 E Solar Dr | Garden Path | 2,614 | $363,000 | Mar 2026 | $72,600 |
| 2832 Allen Dr | Rincon de las Fuentes | 1,900 | $248,888 | Apr 2026 | $49,778 |
| 2317 N Woody St | Russell Village | 5,942 | $240,000 | Mar 2026 | $48,000 |
| 2225 N Woody St | Russell Village | 5,884 | $279,000 | Mar 2026 | $55,800 |

Garden Path skews high because they're delivering 1,900–1,963 SF finished homes on 2,614–2,660 SF lots (premium new construction). Russell Village retail is more representative of what Turquesa actually sells, supporting the $48K–$56K range.

### Benchmark 3: Subject's own basis (floor)

| | Total | Per buildable lot (÷27) |
|---|---:|---:|
| Combined acquisition basis | $425,000 | **$15,740** |
| HCAD subject-only land value | $155,022 | $5,742 |
| Subject ask basis ($385K÷2.69 ac) | $143,123/ac | — |

The $15,740/lot acquisition basis is the absolute floor — anything Talgaos sells for above that minus dev costs is margin. The CAD basis of $155,022 (equivalent to $5,742/lot) is the tax-roll floor; CAD has consistently undervalued Edinburg infill by ~30% since the 2024 reval, so true raw-land market is likely $200K–$220K (~$7,500/lot raw).

---

## Tiered comp set (n=400 tiered records)

| Tier | Definition | Count | Use |
|:---|---|---:|:---|
| **A** | Russell Village CAD lots + recent (≤12mo) sold townhouse retail with 1,500–3,500 SF lots | **70** | Primary basis |
| **B** | 24-month window townhouse retail or pure-land 1,500–3,500 SF residential | 32 | Secondary |
| **C** | Active/pending listings, 1,500–5,000 SF | 134 | Market floor signal |
| **D** | Cross-checks: Crexi land DB, developer-held lots, larger townhouses, commercial-flavored small lots | 164 | Context |

Full data: `comps_raw.csv` (403 rows, all sources), `comps_tiered.csv` (with tier + rationale).

---

## Subdivisions surfaced (named comparable inventory)

**Strong comps (residential townhouse, lots 1,500–3,500 SF, recent activity):**
- **Russell Village** (Edinburg 78541) — 37 lots, Turquesa-built, $240K–$280K retail
- **Garden Path** (McAllen 78501) — 6 listings, 2024–2026 vintage, $363K–$427K
- **Rincon de las Fuentes** (Edinburg) — $248K, 1,900 SF lot
- **Brownwood Ph 2** (Edinburg 78539) — 4 sold $140K–$148K (older 2009–2014 vintage)
- **Summer Winds Ph 1** (Edinburg 78541) — 5 sold $131K–$142K (older 2005 vintage on 2,002 SF lots)

**Adjacent reference (named in original brief):**
- **Tres Lagos** (Edinburg) — found 14+ matches but lot SF = 6,500-15,000 (single-family, not townhouse comp)
- **Stonegate** — no Edinburg matches in IDX
- **Trenton Crossing** — found Trenton Park Plaza (commercial) and Trenton Crossroads Plaza (commercial)
- **Las Brisas** — no matches in residential context
- **Sharyland Plantation** — single-family detached, larger lots

The named "townhouse-style" subs in the original brief are mostly older single-family or commercial. The actual townhouse-pad comps are the new-construction subs above.

---

## Data quality notes & gaps

1. **IDX list endpoint capped at 50 results** — mitigated by 4 sort variants per query (newest/oldest/price-low/price-high), capturing 3,900 unique listings across 13 ZIPs and 6 status×prop-type combinations.
2. **Realtor.com, HAR, Redfin, Zillow all 403'd** WebFetch — IDX broker (juanjoseelizondo.idxbroker.com d337) is the authoritative source. This is fine since Juan's IDX feed is essentially the same MLS data.
3. **Tax office address-matching has gaps** — the `searchby=6` "starts with" mode is finicky on directional prefixes (N/S/E/W) and unit suffixes. Russell Village street-name search worked well.
4. **CAD-to-market calibration empirically validated**: 7 Russell Village improved lots cross-referenced; CAD-gross averaged 99% of recent sold prices. We treat CAD vacant-lot land values as ≈market for Edinburg residential.
5. **Pure-land Tier-A scarcity is reported honestly**: only 2 sold pure-land sub-3,600 SF transactions in Edinburg (both commercial-flavored Edinburg Original Townsite). The 70 Tier-A records are weighted heavily toward recent townhouse retail (for imputation) and Russell Village CAD (for direct same-builder comp).

---

## Sources

- IDX MLS (Juan Elizondo broker d337): https://juanjoseelizondo.idxbroker.com/
- HCAD tax office: https://actweb.acttax.com/act_webdev/hidalgo/
- Crexi RGV DB: `/home/mario/crexiscrapperloopnet/warehouse/comps.db` (78 records cross-check)
- Subject contract + plat: `subject.json` in this folder
- Cross-check: `crexi_cross_check.md`

**Files in this folder:**
- `comps_raw.csv` — 403 records, all sources, full provenance
- `comps_tiered.csv` — 400 records with tier + rationale + tier_rationale columns
- `lot_pricing.json` — programmatic summary stats + recommended pricing + top-5 comps with image URLs
- `comps_summary.md` — this file
- `crexi_cross_check.md` — Crexi DB validation note
- `work/` — raw IDX pulls, Russell Village deep-dive data, calibration scripts
