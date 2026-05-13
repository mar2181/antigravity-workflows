# Talgaos LLC — Edinburg Subdivision Feasibility Study
**000 Rogers Rd., Edinburg TX (4.16 ac combined) — 27-Lot Townhouse Plat**

| | |
|---|---|
| **Prepared for** | Talgaos LLC — Alicia Garza, Manager (1812 Sabinal St., Mission TX 78572) |
| **Prepared by** | Juan Jose Elizondo, RE/MAX Elite — Texas Real Estate Lic. **0620235** |
| **Brokerage** | RE/MAX Elite, 2575 E. Griffin Pkwy Ste 14, Mission TX 78572 |
| **Date** | 2026-04-26 |
| **Document type** | Buyer-side institutional feasibility & pro forma |
| **Visual companion** | `dashboard.html` / `dashboard.png` (in this folder) |
| **Confidentiality** | Privileged advisory work product. Prepared exclusively for Talgaos LLC. Not for public distribution, lender circulation, or third-party reliance without written consent. |

---

## Executive Summary — DUAL VERDICT

This deal does **not** have one answer. It has two — depending on which exit Talgaos commits to.

**(A) PROCEED — but only if Talgaos commits up front to *Scenario B (vertical build to townhomes)* OR can re-trade Subject below ~$325K.** The vertical-build model produces **$104K of gross profit** (1.8% margin) over ~30 months at a $215K average retail price (final_proforma.json). Scenario A — the platted-lot wholesale exit that is the natural reading of a 27-lot plat sale — **loses $546K (-52.5%)** at the comp-supported $55K/lot retail (lot_pricing.json Tier-A median) because dev cost ($41,200/lot mid case) plus land basis ($15,740/lot) plus carry plus commission lifts break-even retail to **~$58K/lot**, which is at or above the Tier-A P75 ($65K). The land basis is too rich for a "buy-finish-flip-lots" play.

**(B) DO NOT PROCEED on the originally-implied wholesale-the-platted-lots thesis.** Subject is priced **148% over CAD** ($385K ask vs. $155,022 assessed land — hcad_subject.json) and the seller is an **18-month flipper** (Turquesa acquired 2024-10-11 from Orocio Jorge & Karina via WDV instrument 3589780). At this basis, the wholesale exit is structurally negative. Either re-trade Subject to ≤$325K (saves ~$2,222/lot, pushes Scenario A to break-even at $55K), pivot to vertical, or walk.

A **clean third option** — **Scenario C, contract assignment** — yields **+$29K in ~6 weeks** (final_proforma.json) if a builder-buyer materializes during feasibility. This is the lowest-risk, highest-velocity exit and should be marketed in parallel with feasibility diligence.

**All-in mid-case cost (27 lots, vertical-build basis):** $1,543,575 land + horizontal ($57,169/lot all-in horizontal). Adding vertical $140K COGS/unit pushes total to $5.70M against $5.81M revenue at $215K/unit avg.

**Recommended go/no-go:** **Conditional GO — proceed into feasibility with three hard gates** (see §11 Action Checklist). If any of the three gates fail (Stonecrest LOI in 2 weeks, plat status confirmed recorded or path clear, civil engineer cost-validation within ±15% of $41,200/lot), terminate inside the feasibility window and recover earnest money.

---

## 1. Subject + Adjacent Parcel

### 1.1 Subject — 000 Rogers Rd., Edinburg TX (Hidalgo Co.)

| Field | Value | Source |
|---|---|---|
| Legal description | TEX-MEX SURVEY LOT 8 — W 177' — S 660' BLK 244 | TXR-1802 contract |
| Acres (per legal) | 2.69 ac | subject.json |
| Acres (per plat geometry) | 2.682 ac (116,820 SF) | subject.json plat_geometry |
| HCAD parcel ID / Geo ID | 295816 / T2100-00-244-0008-08 | hcad_subject.json |
| HCAD account | 7242248 | hcad_subject.json |
| 2026 CAD assessed (land) | **$155,022** | hcad_subject.json |
| Asking price | **$385,000 cash** | TXR-1802 |
| Implied $/ac | $143,123 | computed |
| Implied $/SF gross | $3.30 | computed |
| **Premium over CAD** | **+148%** | $385K vs $155K |
| Seller (entity) | Turquesa Construction LLC | TXR-1802 |
| Seller signatory | Belkis Noemi Garcia | TXR-1802 |
| **Seller acquired** | **2024-10-11 from Orocio Jorge & Karina** (WDV, instrument **3589780**) | hcad_subject.json deed_history |
| **Days held to listing** | **~18 months** | computed |
| Earnest money | $5,000 (1.3% of price — light) | TXR-1802 |
| Independent consideration | $500 | TXR-1802 |
| Feasibility | 30 days + 14-day extension ($1,000 EM add) | TXR-1802 |
| Closing | 14 days post-feasibility | TXR-1802 |
| Title company | Dante Title — Eugene Ragsdale closer | TXR-1802 |
| Deed type | Special warranty | TXR-1802 |
| Buyer assignable | **Yes** | TXR-1802 |
| Financing contingent | No | TXR-1802 |
| Co-listed by | Tania J. Salinas (RE/MAX Elite, Seller) — intermediary status disclosed | TXR-1409 |

**18-Month Flip Read.** Turquesa is a Hidalgo townhouse builder (also the developer of Russell Village, see §4 comp set). The 18-month hold without any visible site work (CAD `improvementValue = 0`, `arbHearing = No`, no permit pulls disclosed) on a parcel they bought for an undisclosed price is consistent with one of three patterns: (i) speculative land position they are now flipping at a markup; (ii) parcel acquired below market that they are now harvesting; (iii) they intended to develop and changed strategy (RGV townhouse demand cooled, capital reallocated). All three patterns indicate **a motivated seller with re-trade exposure**. Talgaos should ask Tania Salinas directly: *"What did Turquesa pay in 2024-10-11, and what changed?"* The answer either supports re-trade leverage or hardens Turquesa's floor.

### 1.2 Stonecrest Adjacent — 1.47 ac, immediately west

| Field | Value | Source |
|---|---|---|
| Legal description | STONECREST (R/S LTS 11 & 12) AN UNNUMBERED LOT EAST LOTS 8-17 | hcad_stonecrest.json |
| HCAD parcel ID / Geo ID | 645048 / S6447-00-000-0000-00 | hcad_stonecrest.json |
| Acres (per buyer file) | 1.47 ac (64,033 SF) | subject.json |
| 2026 CAD assessed (land) | **$10,915** | hcad_stonecrest.json |
| Owner of record | **FIRST NATIONAL BANK** (PO Box 810, Edinburg TX 78540-0810) — *closed by OCC 2013-09-13* | hcad_stonecrest.json + FDIC/OCC records |
| **Practical successor** | **PlainsCapital Bank, Special Assets / OREO** (acquired FNB-Edinburg via 2013 P&A) | stonecrest_owner_brief.md |
| Cap (per Talgaos contract Exhibit A) | **$40,000** | TXR-1937 |
| Implied $/ac at cap | $27,211 | computed |
| Contingency window | 60 days from effective date | TXR-1937 |
| **Best contact** | **PlainsCapital Cano Branch (956) 380-8530** (former FNB-Edinburg HQ); escalate to **Jeff Flenar, EVP Special Assets** (Dallas) or **Michael Flotté, SVP Special Assets & Acquisitions** | stonecrest_owner_brief.md |

**Bank-Owned Status — Why This Matters.** First National Bank of Edinburg failed 2013-09-13 (OCC News Release 2013-135) and was the largest US bank failure that year. The FDIC sold ~$2.7B of FNB assets to PlainsCapital Bank (subsidiary of Hilltop Holdings, NYSE: HTH) on the same day under a Purchase & Assumption agreement with a $1.8B loss-share pool. The Stonecrest parcel was almost certainly an OREO asset on FNB's books at the time of failure. **Tax-payment evidence makes the orphan-asset hypothesis nearly certain:** taxes were paid normally through 2013, then **eight years went unpaid (2014–2021)**, then in April 2022 someone (almost certainly PlainsCapital Special Assets after a delinquency sweep) cleared all eight years in a single $1,397.95 lump-sum payment and has paid annually on time since. Tax-roll address has never been updated from FNB to PlainsCapital — the textbook fingerprint of an orphaned OREO asset that the special-assets desk wants to dispose of without legal cost (stonecrest_owner_brief.md Layer 1).

**Negotiating implications:**
- $0 income on the books for 13+ years.
- Cumulative tax leakage ~$2,200+ since 2014 — paid out, not earned.
- Banks routinely take any reasonable offer above book value to clear OREO. Special-assets officers are measured on $-cleared per quarter, not max $-realized per parcel.
- **Open at $20,000.** Negotiating room to **$35,000.** **Walk at $40,000** (contract cap).
- Bank will require **special warranty** + standard "as-is, where-is" — matches Talgaos contract.
- **Approval risk:** OREO sales >$25K commonly require Credit Committee approval; that committee meets weekly. **Build 3–4 weeks of internal-approval time into the contingency window.** With a 60-day window, Juan must have an LOI in PlainsCapital's hands inside 14 days of effective date. This is the single tightest timing gate in the entire deal.

### 1.3 Combined Project

| Element | Value |
|---|---:|
| Total combined acres | **4.16 ac** |
| Total combined SF | 181,220 SF |
| **Combined land basis** | **$425,000** |
| Combined $/ac | $102,163 |
| Combined $/SF | $2.34 |

Cross-check: Mission TX 8.96-ac comp at $100,982/ac in the Crexi RGV land database is **0.2% off** the subject blended basis (crexi_cross_check.md). The combined acquisition basis is consistent with rural-to-edge-of-town residential infill in Hidalgo County and is **not** at commercial-pad pricing (commercial-zoned tracts trade at 5×–10× this rate per Crexi).

---

## 2. Plat Analysis

The plat (subject.json `plat_geometry`) shows **27 buildable lots** in three groupings, plus interior 50' ROW (N. Turquesa St + E. Aqua St) and an 8,850 SF detention pond at the NE corner.

### 2.1 Lot inventory

| Group | Lot #s | Count | Typical SF | Frontage × Depth |
|---|---|---:|---:|---|
| North row along N. Turquesa St | 1–11 | 11 | 2,540 SF (corners 2,657–2,681) | 40' × 63.5' |
| East side along E. Aqua St | 12–16 | 5 | 2,513 SF | 35.4' × 71.0' |
| South row along N. Turquesa St | 18–27 (skip 17) | 10 | 2,540 SF (corners 2,657–2,682) | 40' × 63.5' |
| **Total buildable** | | **27** | min 2,513 / median 2,540 / max 2,682 SF | |

**Lot 17 numbering ambiguity.** The plat skips lot 17. We treat 27 as the working count, with a 24-floor / 28-ceiling sensitivity in §8. Surveyor confirmation is needed during feasibility (subject.json `ambiguities_flagged`).

### 2.2 Land budget

| Element | SF | % of subject |
|---|---:|---:|
| Total subject parcel | 116,820 | 100.0% |
| Total buildable (27 × ~2,540 median) | 68,580 | 58.7% |
| Interior ROW (50' streets, 474 LF + 177 LF) | ~32,550 | 27.9% |
| Detention pond (NE corner) | 8,850 | 7.6% |
| Easement burden (drain ditch + irrigation + abandoned canal, *outside* buildable) | ~6,840 | 5.9% |

### 2.3 Easement burden — north strip

Three concurrent easements run along the north strip (subject.json `easements_inside_or_adjacent_subject`):

| Easement | Width | Reference | Status |
|---|---:|---|---|
| Drain ditch easement | 57.95 ft | Vol. 34 Pg. 164A H.C.M.R. | Active (verify on/adjacent — see §9 risk) |
| HCID No. 1 irrigation easement | 24 ft | (per plat) | Active — district authority persists even if unused |
| Abandoned canal ROW | 45 ft | Vol. 34 Pg. 164A H.C.M.R. | Marked abandoned but **legal release from HCID No. 1 still required** |
| Interior utility easements | 10' rear-rear, 15' perimeter | Standard plat | No buildable impact |

**Open verification item (subject.json):** *Does the 57.95' drain ditch easement sit ON the subject parcel or just adjacent?* The plat shows it on the north strip (consistent with "adjacent"), but legal verification is required during feasibility. **If on-subject and unbuildable**, the project loses ~57.95' × 660' / 43,560 = **0.88 ac of buildable area** — which would push lot yield well below the 24-lot floor in §8 sensitivity. *Cost basis is conditional on the easement being adjacent, not within.*

---

## 3. Comparable Lot Sales — Tier A

**Methodology.** Pure-land trades of sub-3,500 SF lots in Edinburg are nearly non-existent because **townhouse pads do not trade individually after platting** — developers retail finished homes, not lots. Of 3,900 IDX listings pulled across 13 RGV ZIPs, only 2 sold pure-land transactions in Edinburg (78539) under 3,600 SF in the last 24 months, both commercial-flavored. Direct comp scarcity forced a **three-source triangulation** (lot_pricing.json `methodology`):

1. **IDX-MLS** via `juanjoseelizondo.idxbroker.com` (broker code d337) for sold + active townhouse and pure-land listings — 13 ZIPs, 6 status × prop-type combinations, 3,900 listings, 704 detail-page fetches.
2. **HCAD** (acttax.com) for CAD-assessed land values, calibrated against IDX — CAD ≈ 99% of recent sold price for Edinburg residential (validated on 7 Russell Village improved lots).
3. **Crexi RGV land DB** (78 RGV land comps) cross-check — confirms blended basis of $102K/ac matches Mission 8.96 ac at $100,982/ac (0.2% off).

The 70 Tier-A records weight heavily toward (a) Russell Village CAD vacant lots (n=8, same-builder behavioral comp) and (b) recent townhouse retail with small lots imputed to 20% land share (empirically derived from Russell Village paired data: $55K CAD land / $250K sold = 22%).

### 3.1 Top-5 Tier-A comps

#### Comp #1 — 2707 E Solar Drive, Mission TX (Garden Path) — *bullseye size match*

| | |
|---|---|
| Subdivision | Garden Path |
| Lot SF | **2,614** (within 3% of subject's 2,540 SF) |
| Finished SF | 1,963 |
| Year built | 2025 |
| Sold price | **$363,000** |
| Sold date | 2026-03-19 |
| $/finished SF | $184.92 |
| Imputed lot value @ 20% | **$72,600** |
| MLS # | 491020 |
| IDX listing | https://juanjoseelizondo.idxbroker.com/idx/details/listing/d337/491020/2707-E-Solar-Drive-Mission-TX?widgetReferer=true |
| Image | https://dvvjkgh94f2v6.cloudfront.net/5570223/19172414/83dcefb7.jpeg |

**Why:** New construction 2025, sold March 2026, lot SF within 3% of subject pad target. Single best-fit comp in the entire data pull.

#### Comp #2 — 2613 E Solar Drive, Mission TX (Garden Path) — *upper-bound new-construction*

| | |
|---|---|
| Subdivision | Garden Path |
| Lot SF | 2,660 |
| Finished SF | 1,918 |
| Year built | 2025 |
| Sold price | **$427,000** |
| Sold date | 2026-03-09 |
| $/finished SF | $222.63 |
| Imputed lot value @ 20% | **$85,400** |
| MLS # | 483734 |
| IDX listing | https://juanjoseelizondo.idxbroker.com/idx/details/listing/d337/483734/2613-E-Solar-Drive-Mission-TX?widgetReferer=true |
| Image | https://dvvjkgh94f2v6.cloudfront.net/5570223/19007330/83dcefb7.jpeg |

**Why:** Premium-priced peer comp at $222/finished SF — represents the upper bound of the new-construction townhouse retail band. Garden Path is delivering 1,900–1,963 SF homes on 2,614–2,660 SF pads; that's the product profile a builder-developer would target on Subject.

#### Comp #3 — 2225 N Woody Street, Edinburg TX (Russell Village) — *SAME BUILDER as Subject seller*

| | |
|---|---|
| Subdivision | Russell Village (Turquesa Construction product) |
| Lot SF | 5,884 (2.3× Subject pad — see scaling note below) |
| Finished SF | 1,459 |
| Year built | 2024 |
| Sold price | **$279,000** |
| Sold date | 2026-03-04 |
| $/finished SF | $191.23 |
| Imputed lot value @ 20% | **$55,800** |
| MLS # | 491922 |
| IDX listing | https://juanjoseelizondo.idxbroker.com/idx/details/listing/d337/491922/2225-N-Woody-Street-Edinburg-TX?widgetReferer=true |
| Image | https://dvvjkgh94f2v6.cloudfront.net/5570223/19192983/83dcefb7.jpeg |

**Why:** **Most recent retail evidence of what Turquesa Construction (the Subject seller) actually sells in Edinburg.** Behaviorally critical — if Turquesa-built product on a 5,884 SF pad sells for $279K, then a 2,540 SF pad in the same submarket should sell for less, but the question is *how much* less — see "Per-SF vs whole-lot debate" below.

#### Comp #4 — 2832 Allen Drive, Edinburg TX (Rincon de las Fuentes) — *most recent Edinburg townhouse sold*

| | |
|---|---|
| Subdivision | Rincon de las Fuentes |
| Lot SF | 1,900 (smaller than Subject — true per-SF comp) |
| Finished SF | 1,430 |
| Year built | 2020 |
| Sold price | **$248,888** |
| Sold date | 2026-04-17 |
| $/finished SF | $174.05 |
| Imputed lot value @ 20% | **$49,778** |
| MLS # | 492054 |
| IDX listing | https://juanjoseelizondo.idxbroker.com/idx/details/listing/d337/492054/2832-Allen-Drive-Edinburg-TX?widgetReferer=true |
| Image | https://dvvjkgh94f2v6.cloudfront.net/5570223/19195827/83dcefb7.jpeg |

**Why:** Smaller lot SF (1,900) than Subject — gives a legitimate per-SF price benchmark unsmeared by larger-lot premium. Most recent Edinburg townhouse sold (April 2026).

#### Comp #5 — Russell Village vacant lots (HCAD inventory, n=8) — *same-builder behavioral floor*

| | |
|---|---|
| Subdivision | Russell Village |
| Vacant lot count | 8 |
| Lot SF each | 5,884 (whole-lot — see scaling note) |
| CAD median (whole-lot) | **$55,242** |
| CAD P25 / P75 | $55,242 / $69,103 |
| Per-SF land basis | **$9.39/SF** |
| Implied 2,540 SF pad value (per-SF scaling) | **$23,857** |
| Source | https://actweb.acttax.com/act_webdev/hidalgo/showlist.jsp (street search: N WOODY) |
| Image | https://dvvjkgh94f2v6.cloudfront.net/5570223/19135809/83dcefb7.jpeg |

**Why:** This is the most direct same-builder behavioral comp and the source of the $55K headline midpoint. **But it has a critical scaling caveat — see below.**

### 3.2 Per-SF vs whole-lot debate (transparently disclosed)

Russell Village lots are **2.3× the size** of Subject's target pads (5,884 SF vs. 2,540 SF). There are two valid interpretations of how that translates into Subject's $/lot:

- **Whole-lot lump-sum scaling → $55,242/lot.** A vacant townhouse lot has a baseline value (utilities access, plat, frontage) that does *not* scale linearly with SF. CAD assigns ~$55K regardless of size class, and this is consistent with what end-buyers actually pay for a buildable pad.
- **Per-SF scaling → $23,857/lot.** Smaller pads should price proportionally lower — a 2,540 SF pad simply isn't worth what a 5,884 SF pad is worth.

The truth is between these. Talgaos is delivering smaller pads in a denser plat (27 lots on 4.16 ac = ~6,710 SF/lot gross including ROW & common areas, vs. Russell Village's larger 5,884 SF private pads with shared private roadways). The denser product attracts a different buyer (smaller-builder/investor vs. custom/end-user) at a lower per-pad price.

**Conclusion: Russell Village establishes a behavioral price band of $24K–$55K, not a $55K hard floor.** The recommendation table below splits the difference: $45K low / $55K mid / $65K high.

### 3.3 Recommended retail-lot pricing

| Confidence | $/lot | 27-lot revenue | Anchor |
|:---|---:|---:|:---|
| Pessimistic | $45,000 | $1,215,000 | Per-SF Russell Village derivation ($23,857) blended with new-construction P25 imputed ($49,778) |
| **Midpoint (use in pro forma)** | **$55,000** | **$1,485,000** | New-construction townhouse imputation median ($50,500) + Russell Village whole-lot CAD ($55,242) |
| Optimistic | $65,000 | $1,755,000 | New-construction P75 imputed ($70,000); requires utilities + plat completion + small-builder demand |

**Use $55,000/lot as base case in pro forma. Sensitivity-test ±$10K to model the risk band.** (lot_pricing.json `recommended_per_lot_for_proforma`)

### 3.4 Tier-A statistics (full set)

- Tier-A records: **n = 70** (Russell Village CAD + recent ≤12-month sold townhouse retail with 1,500–3,500 SF lots)
- Tier-A new-construction-only median imputed lot @ 20%: **$50,500** (n=9, year-built 2018+)
- Tier-A new-construction P25/P75: $49,778 / $70,000

### 3.5 Subdivisions surfaced (named comparable inventory)

- **Russell Village** (Edinburg 78541) — 37 lots, Turquesa-built, $240K–$280K retail
- **Garden Path** (McAllen/Mission 78501) — 6 listings, 2024–2026 vintage, $363K–$427K
- **Rincon de las Fuentes** (Edinburg) — $248K, 1,900 SF lot
- **Brownwood Ph 2** (Edinburg 78539) — 4 sold $140K–$148K (older 2009–2014 vintage — Tier B)
- **Summer Winds Ph 1** (Edinburg 78541) — 5 sold $131K–$142K (older 2005 vintage on 2,002 SF lots — Tier B)

Original-brief named subs (Tres Lagos, Stonegate, Trenton Crossing, Las Brisas, Sharyland Plantation) were investigated and confirmed to be either (a) single-family larger-lot, (b) commercial, or (c) without IDX matches — not townhouse-pad comps.

---

## 4. Development Cost Model

**Per Mario's direction, no local civil engineer was interviewed for this draft.** Cost numbers are derived from published web benchmarks anchored on **TxDOT Pharr District 12-month average bid prices (Aug 2024)** with TxDOT Highway Cost Index escalation to 2026 (HCI Oct 2025 = 320.82, +4%/yr 2024→2026). 55+ inline citations are documented in `dev_cost_benchmarks.md` §10. **Validate with a RGV civil engineer (Halff Associates, Melden & Hunt, R. Gutierrez Engineering) before financial commitment.** Contingency held at **15%** (vs. typical 10%) to cover this validation gap.

### 4.1 Hard cost build-up (mid case, 27 lots, 40' pavement under Edinburg UDC multi-family classification)

| Line item | Total | Source / unit cost |
|---|---:|---|
| Clearing & grading (4.16 ac × $2,500/ac) | $10,400 | Daniel Dean Land Clearing 2025 + TxDOT Pharr Item 100 6001 cross-check |
| Asphalt paving (40' × 600 LF = 2,667 SY × $35/SY) | $93,300 | TxDOT Pharr Item 247 + Item 340 6104 build-up + private-subdivision markup |
| Curb & gutter (1,200 LF × $20/LF) | $24,000 | TxDOT Pharr Item 529 6007 ($15/LF) + private markup |
| Storm sewer + 8,850 SF detention | $109,000 | TxDOT Pharr Item 464 RCP series + earthwork |
| Water mains, hydrants, services | $115,000 | RGV utility benchmarks; 27 services + ~600 LF main |
| Sanitary sewer | $107,000 | TxDOT Pharr Item 400 series + manhole/lift assumptions (no lift station in mid case) |
| Dry utilities (electric, gas, telecom) | $87,750 | AEP Texas tariff PUC Docket 55957 ($250/lot subdivision allowance) + private trenching |
| Sidewalks + ADA ramps | $60,000 | TxDOT Pharr Item 531 + Item 110 build-up |
| Street lights (5 fixtures) | $25,000 | Hidalgo County 2018 amendment (lights every 250 LF + intersections + cul-de-sacs) |
| Signage + striping | $5,000 | TxDOT Pharr Item 666/671 |
| **Hard subtotal** | **$636,450** | |

### 4.2 Soft costs

| Line item | Total | Basis |
|---|---:|---|
| Civil engineering + surveying (~11% of hard) | $70,000 | RGV market rate |
| Plat fees + city permits + park fees | $105,000 | City of Edinburg fee schedule |
| GC fee / construction management (~8%) | $50,900 | Standard subdivision GC markup |
| Geotech + Phase I ESA | $11,000 | Two reports, RGV market rate |
| Drainage study + HCID coordination | $25,000 | Hidalgo Co. 50-year event drainage requirement |
| Legal — covenants + HOA setup | $15,000 | Standard townhouse HOA formation |
| **Soft subtotal** | **$276,900** | |

### 4.3 Carry costs (12-month construction window)

| Line item | Total | Basis |
|---|---:|---|
| Property tax during build (combined rate ~2.38%) | $10,115 | $425K basis × 2.38% |
| Builder's risk insurance | $2,545 | Industry rate ~0.4% of hard cost |
| Construction loan interest (9% APR, 50% avg drawn, 12 mo) | $41,100 | Conservative — Talgaos may close cash and skip this line |
| **Carry subtotal** | **$53,760** | |

### 4.4 Totals

| | $ |
|---|---:|
| Hard subtotal | $636,450 |
| Soft subtotal | $276,900 |
| Carry subtotal | $53,760 |
| **Pre-contingency total** | **$967,110** |
| Contingency (15%) | $145,067 |
| **Total horizontal dev cost** | **$1,112,177** |
| **Per-lot mid (÷27)** | **$41,200** |

### 4.5 Range (low / mid / high)

| Case | Per-lot | 27-lot total | Assumptions |
|---|---:|---:|---|
| Low | $32,000 | $865,000 | 32' pavement (single-family classification), no lift station, smooth HCID abandonment, mild contingency burn |
| **Mid** | **$41,200** | **$1,112,200** | 40' pavement (multi-family rule, mid-case), no lift station, full contingency, validated soft costs |
| High | $58,000 | $1,567,000 | 43' pavement (residential collector), lift station +$200K, complex HCID release, drainage study upsizes detention, 25% contingency burn |

### 4.6 Cost-basis disclosure

> Per Mario's direction, no local civil engineer was interviewed for this study. Cost numbers are anchored on TxDOT Pharr 12-month avg bid tabs (Aug 2024) escalated 4%/yr to 2026, NAHB 2024 Cost of Constructing a Home, City of Edinburg UDC Article 5 Table 5.203-1 (pavement classification), Hidalgo County Subdivision Rules (50-yr drainage event), AEP Texas PUC Docket 55957 (subdivision dry-utility allowance), and 50+ additional citations in `dev_cost_benchmarks.md`. **Talgaos should retain a RGV civil engineer for cost validation during the feasibility window.** Contingency is held at 15% (vs. typical 10%) to absorb up to ~±15% variance from the engineer's number. If the engineer's mid case lands beyond ±15% of $41,200/lot, this entire study should be re-run before the feasibility deadline.

---

## 5. All-In Pro Forma (mid case, 27 lots, $55K/lot retail)

### 5.1 Acquisition + horizontal stack

| Line | $ |
|---|---:|
| Subject acquisition | $385,000 |
| Stonecrest acquisition (cap) | $40,000 |
| **Combined land basis** | **$425,000** |
| Closing costs (~1.5% combined) | $6,375 |
| Total horizontal dev cost | $1,112,200 |
| **TOTAL ALL-IN** | **$1,543,575** |
| **Per-lot all-in (÷27)** | **$57,169** |

### 5.2 Base-case revenue & profit @ $55K/lot retail

| Line | $ |
|---|---:|
| Gross revenue (27 × $55,000) | $1,485,000 |
| Less commission (6%) | ($89,100) |
| Less marketing (1%) | ($14,850) |
| **Net revenue** | **$1,381,050** |
| Less all-in cost | ($1,543,575) |
| **Gross profit** | **($162,525)** |
| **Gross margin** | **-11.8%** |
| **Profit per lot** | **($6,019)** |
| Months total | 27 |

> **Per-lot all-in $57,169 versus base-case retail $55,000 → the wholesale-platted-lot exit does not pencil at current land basis. Break-even retail is ~$58,000/lot, which sits at the Tier-A P75 ($65K) — too thin a margin of safety to recommend as a primary exit.** This is the load-bearing finding of this study.

---

## 6. Three Exit Scenarios (final_proforma.json)

### 6.1 Scenario A — Wholesale finished lots to a builder (DO NOT RECOMMEND at current basis)

| Line | $ |
|---|---:|
| Strategy | Sell all 27 lots in bulk to a single builder at ~70% of $55K = $38,500/lot |
| Revenue (27 × $38,500) | $1,039,500 |
| All-in cost | ($1,585,155) |
| **Gross profit** | **($545,655)** |
| **Margin** | **-52.5%** |
| Months | 14 |

**Break-even retail to make Scenario A pencil ≈ $58K/lot.** That price is achievable only at the Tier-A P75 — a thin margin.

### 6.2 Scenario B — Vertical build & sell townhomes (RECOMMENDED IF TALGAOS COMMITS)

| Line | $ |
|---|---:|
| Strategy | Build 27 townhomes at $140K vertical COGS each, sell at $215K avg retail |
| Revenue (27 × $215,000) | $5,805,000 |
| All-in cost (horizontal $1.54M + vertical 27 × $140K + sales/marketing/carry) | ($5,700,900) |
| **Gross profit** | **$104,100** |
| **Margin** | **+1.8%** |
| Months | 30 |

**Why this works.** Vertical-build at $215K avg matches the Russell Village retail comp ($240K–$280K) discounted for smaller pad SF. Talgaos is selling *finished homes*, not lots, into a market where the comp evidence is dense (33 recent townhouse sales) — a fundamentally easier sell than 27 wholesale pads to a single builder.

**Why it's tight.** The 1.8% margin offers minimal cushion for cost overruns or retail softening. **A 5% drop in average retail (to ~$204K) wipes out the profit; a 10% drop (~$193K) loses ~$465K** (see §7 sensitivity).

**Capital requirement.** $5.70M all-in over 30 months — Talgaos will need either substantial cash or a vertical construction loan facility. This is not a $1.5M project; it is a $5.7M project with $1.5M in early sunk basis.

### 6.3 Scenario C — Contract flip pre-closing (CLEANEST IF AN ASSIGNEE EMERGES)

| Line | $ |
|---|---:|
| Strategy | Assign the contract to a builder-buyer for $35K assignment fee before close |
| Revenue | $35,000 |
| All-in cost (EM + indep. consideration + due-diligence) | ($6,000) |
| **Gross profit** | **$29,000** |
| **Margin** | **+82.9%** |
| Months | 1.5 |

**Why this is the cleanest exit.** Lowest capital risk (only $5K EM at risk before feasibility expires). Highest velocity (~6 weeks). Captures the full value of Talgaos's contract position without taking development risk. **Talgaos's contract is buyer-assignable per TXR-1802.**

**Why it is hard.** The Stonecrest 60-day contingency makes the contract harder to assign — any assignee inherits the same contingency and the same compressed timeline against PlainsCapital's Special Assets approval cycle. Assignee market is small. **Marketing the assignment in parallel with feasibility diligence is the right hedge** — if a builder emerges, take Scenario C and exit. If no assignee by week 4, default to Scenario B planning.

### 6.4 Scenarios side-by-side

| Metric | Scenario A — Wholesale | **Scenario B — Vertical Build** | Scenario C — Assignment |
|---|---:|---:|---:|
| Revenue | $1,039,500 | $5,805,000 | $35,000 |
| All-in cost | $1,585,155 | $5,700,900 | $6,000 |
| **Gross profit** | **($545,655)** | **+$104,100** | **+$29,000** |
| Margin | -52.5% | +1.8% | +82.9% |
| Months | 14 | 30 | 1.5 |
| Capital at risk | $1.5M | $5.7M | $6,000 |
| Break-even retail / unit | $58K/lot | ~$211K/unit | n/a |
| **Recommendation** | **REJECT** | **PRIMARY** | **PARALLEL HEDGE** |

---

## 7. Sensitivity Analysis

### 7.1 Hard cost ±20% × lot count {24/27/28/32} — Scenario A wholesale @ $55K/lot

(Source: final_proforma.json `sensitivity_grid`. All-in includes land $425K + closing $6.4K + dev cost. Revenue at $55K/lot baseline.)

| Lot count | Cost case | Per-lot dev | Total dev | All-in | Gross profit | Margin | Per-lot all-in |
|---:|:---|---:|---:|---:|---:|---:|---:|
| 24 | low (-20%) | $35,520 | $852,480 | $1,283,855 | ($56,255) | -4.6% | $53,494 |
| 24 | mid | $44,400 | $1,065,600 | $1,496,975 | ($269,375) | -21.9% | $62,374 |
| 24 | high (+20%) | $53,280 | $1,278,720 | $1,710,095 | ($482,495) | -39.3% | $71,254 |
| **27** | **low (-20%)** | **$32,960** | **$889,920** | **$1,321,295** | **+$59,755** | **+4.3%** | **$48,937** |
| **27** | **mid** | **$41,200** | **$1,112,400** | **$1,543,775** | **($162,725)** | **-11.8%** | **$57,177** |
| **27** | **high (+20%)** | **$49,440** | **$1,334,880** | **$1,766,255** | **($385,205)** | **-27.9%** | **$65,417** |
| 28 | low (-20%) | $32,240 | $902,720 | $1,334,095 | +$98,105 | +6.8% | $47,646 |
| 28 | mid | $40,300 | $1,128,400 | $1,559,775 | ($127,575) | -8.9% | $55,706 |
| 28 | high (+20%) | $48,360 | $1,354,080 | $1,785,455 | ($353,255) | -24.7% | $63,766 |
| 32 | low (-20%) | $29,760 | $952,320 | $1,383,695 | +$253,105 | +15.5% | $43,240 |
| 32 | mid | $37,200 | $1,190,400 | $1,621,775 | +$15,025 | +0.9% | $50,680 |
| 32 | high (+20%) | $44,640 | $1,428,480 | $1,859,855 | ($223,055) | -13.6% | $58,120 |

**Reading.** Scenario A becomes profitable at 27 lots only if hard costs come in 20% below mid (low case) — a stretch on a desktop benchmark. At 32 lots and mid hard costs the margin is razor-thin (+0.9%); only the 32-lot/low-cost combination produces a meaningful margin. **The wholesale exit needs both the lot ceiling AND the cost floor — a low-probability joint outcome.** Vertical build (Scenario B) is the more robust play.

### 7.2 Lot retail sensitivity (Scenario A, 27 lots, mid hard cost)

| Lot retail | 27-lot revenue | Net rev (post 7% commission/marketing) | Profit vs. all-in $1,543,775 |
|---:|---:|---:|---:|
| $45,000 | $1,215,000 | $1,129,950 | ($413,825) |
| $55,000 | $1,485,000 | $1,381,050 | ($162,725) |
| **$58,000** | **$1,566,000** | **$1,456,380** | **($87,395)** |
| $65,000 | $1,755,000 | $1,632,150 | +$88,375 |

**Scenario A break-even ≈ $58K/lot.** That price exists only at Tier-A P75.

### 7.3 Townhouse retail sensitivity (Scenario B, 27 units, $140K vertical COGS, $5.7M all-in)

| Avg unit retail | 27-unit revenue | Approx gross profit |
|---:|---:|---:|
| $200,000 | $5,400,000 | (~$300,000) |
| **$215,000** | **$5,805,000** | **+$104,000** |
| $230,000 | $6,210,000 | +$510,000 |
| $250,000 | $6,750,000 | +$1,050,000 |

**Reading.** Scenario B is highly retail-sensitive. The $215K base case is plausible against Russell Village comps but depends on Talgaos delivering a competitive product profile (square footage, finish level, price-per-finished-SF in line with Garden Path / Russell Village benchmarks). A 7% lift to $230K avg adds $400K of profit; a 7% miss to $200K wipes the project out by $300K. **Pricing discipline at vertical-build phase is the single biggest profit lever.**

### 7.4 Cost-basis disclosure (sensitivity context)

> The mid-case cost basis is web-benchmark-only. Civil engineer validation pending. If the validated mid case lands ≥15% above $41,200/lot, this study must be re-run. The 15% contingency held in §4 is intended to absorb ordinary engineer-version variance, not a fundamental shift in cost classification (e.g., lift station required).

---

## 8. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|:---:|:---:|---|
| 1 | **Stonecrest 60-day contingency vs. PlainsCapital 3–4 wk Credit Committee approval cycle** | Medium-High | Deal-killer if missed | LOI to PlainsCapital Special Assets within 14 days of effective date (see §11). Negotiate written contingency extension if approval slips. |
| 2 | **Plat recordation status unconfirmed** | Medium | +6 mo timeline if preliminary | Pull plat status from City of Edinburg Planning **(956) 388-8204** within 5 business days of effective date. |
| 3 | **Pavement classification: 40' (multi-family) vs. 32' (single-family)** | Medium | ±$700/lot ($19K total) | Confirm with City of Edinburg Planning. Mid case assumes the strict-reading 40' rule under Edinburg UDC Table 5.203-1. |
| 4 | **HCID No. 1 abandoned-canal release** | Medium | +$15K–$35K, +60–120 days, OR refusal | Phone HCID No. 1 (hcid1.com — main 956-787-6471) Day 1. Coordinate written abandonment-release request through title. |
| 5 | **Lift station required (sanitary)** | Low-Medium | +$200,000 (+$7,400/lot) | Walk site to identify nearest existing manholes; confirm gravity tie distance with City Planning. |
| 6 | **Drain ditch easement on-subject vs. adjacent** | Low | -3 lots if on-subject | ALTA survey (Cat 1A insufficient) ordered Day 1 of feasibility. |
| 7 | **Turquesa flipper motivation unclear** | n/a (informational) | n/a | Ask Tania Salinas directly: "What did Turquesa pay 2024-10-11, and why are they selling now?" Use answer to size re-trade leverage. |
| 8 | **Dev cost web-benchmark-only (no engineer)** | Medium | ±$300K total | Retain RGV civil engineer (Halff, Melden & Hunt, R. Gutierrez) within 5 days of effective date. Contingency held at 15% to absorb. |
| 9 | **Townhouse retail demand softens (Scenario B)** | Medium | -$300K to -$500K | Maintain Scenario C (assignment) as parallel hedge. Pre-marketing to builder-buyers during feasibility. |
| 10 | **CAD basis 148% under ask suggests negotiability** | Medium (opportunity) | Re-trade $60K → +$2,222/lot | Use CAD-vs-ask gap and 18-month flip evidence to push for ≤$325K Subject. |
| 11 | **Earnest money light at 1.3%** | Low (in Buyer's favor) | n/a | No mitigation — favorable to Talgaos. |
| 12 | **Encumbrance ambiguities (HCID assessment, FEMA flood zone, PID)** | Low-Medium | $5K–$25K | Title commitment review + FEMA Map Service Center pull within 10 days. |

---

## 9. Stonecrest Contingency Tree

```
DAY 0 (effective): Talgaos signs Subject contract + Stonecrest Exhibit A
                   |
                   ├─ Day 1: Juan calls PlainsCapital Cano (956) 380-8530
                   |          → routes to Special Assets / OREO
                   |          → name reference: Jeff Flenar EVP / Michael Flotté SVP
                   |
                   ├─ Day 1–3: Send written LOI by overnight mail
                   |          → Dallas HQ: 325 N. St. Paul St. Ste 800, Dallas TX 75201
                   |          → Cc: PO Box 810, Edinburg TX 78540 (tax-roll backup)
                   |          → Open offer: $20,000 cash, 30-day close, as-is, special warranty
                   |
                   ├─ Day 4–14: PlainsCapital Special Assets responds
                   |          ├── ACCEPTED at $20K  ─→ proceed to title work + closing
                   |          ├── COUNTERED $25–35K ─→ Juan accepts up to $35K (room to $5K under cap)
                   |          ├── COUNTERED $36–40K ─→ Juan tries $35K final / accept at $40K cap
                   |          └── REFUSED          ─→ deal dies; terminate Subject in feasibility, recover EM
                   |
                   ├─ Day 14–35: PlainsCapital Credit Committee approves (typically 3–4 weeks)
                   |          ├── Approved        ─→ open title at Dante Title (Eugene Ragsdale)
                   |          └── Stalled >Day 45 ─→ negotiate written contingency extension
                   |
                   ├─ Day 35–55: Title curative for FDIC→PlainsCapital chain-of-title
                   |          → routine: Bulk Bargain & Sale Deed or Receiver's Deed from 2013-09 P&A
                   |          → if not individually recorded, curative affidavit needed (+2–4 wks)
                   |
                   └─ Day 55–60 (window closes 2026-06-29 if eff. 2026-04-30):
                              ├── Stonecrest signed   ─→ proceed to Subject closing
                              └── Window expires      ─→ terminate Subject, recover EM ($5K + $1K extension)
```

**Decision rule:** If no LOI in PlainsCapital's hands by Day 14, escalate to FDIC DRR Asset Disposition (Dallas regional). If no Stonecrest LOI accepted by Day 30, prepare Subject-termination documents in parallel.

---

## 10. Timeline (assumes effective date 2026-04-30, Scenario B path)

| Phase | Months | Activity | Critical-path gate |
|---|---|---|---|
| Feasibility (initial) | 0–1 | Stonecrest LOI, plat status, civil engineer cost validation, ALTA survey, HCID coordination, FEMA pull | LOI executed by Day 14 |
| Feasibility (extended) | 1–1.5 | Title curative, financing-out review, Credit-Committee tracking | Stonecrest contract by Day 45 |
| Closings | 1.5–2 | Subject + Stonecrest close | Both close on or before 2026-06-27 |
| Entitlement (plat → permit) | 2–8 | Drainage study, plat recordation if needed, construction plans, permits | Plat recorded by month 8 |
| Horizontal construction | 8–18 | Grading, paving, utilities, sidewalks, detention | Substantial completion by month 18 |
| Vertical construction (Scenario B) | 18–30 | Townhome construction, model unit, presales | First closings by month 24 |
| Sellout | 24–30 | Retail closings | Last unit by month 30 |

---

## 11. Action Checklist — Next 14 Days

| Day | # | Action | Owner | Phone |
|---|---|---|---|---|
| 1 | 1 | Call PlainsCapital Cano Branch — request Special Assets / OREO routing | Juan | **(956) 380-8530** |
| 1 | 2 | Call Edinburg Planning — confirm plat recordation status + pavement classification (40' vs. 32') | Juan | **(956) 388-8204** |
| 1 | 3 | Call HCID No. 1 — initiate canal-ROW abandonment release inquiry | Juan | hcid1.com (main 956-787-6471) |
| 1 | 4 | POF letter from Talgaos to Seller (3-day deadline per TXR practice) | Talgaos / Juan | — |
| 2 | 5 | Email Tania Salinas — ask: "What did Turquesa pay 10/11/2024, and why selling now?" | Juan | listing agent |
| 2 | 6 | Engage RGV civil engineer for cost validation (Halff / Melden & Hunt / R. Gutierrez) — quote within 5 days, cost validation within 14 days | Juan | — |
| 2 | 7 | Order ALTA Cat 1A+ survey on Subject (north strip easement priority) | Juan / Dante Title | — |
| 3 | 8 | Send PlainsCapital LOI overnight to Dallas HQ + Cc PO Box 810 Edinburg | Juan | overnight courier |
| 3 | 9 | Pull FEMA flood-zone letter from FEMA Map Service Center | Juan | msc.fema.gov |
| 5 | 10 | Pull plat from City of Edinburg planning office (recorded or preliminary?) | Juan | (956) 388-8204 |
| 5 | 11 | Begin pre-marketing Scenario C assignment to builder network (Garden Path, Russell Village peers) | Juan / Talgaos | — |
| 7 | 12 | Title commitment ordered through Dante Title (Eugene Ragsdale) | Dante Title | — |
| 10 | 13 | Re-trade conversation with Tania Salinas if 18-month-flip facts support — target Subject ≤$325K | Juan | — |
| 14 | 14 | **Gate review:** Stonecrest LOI acknowledged? Plat status known? Engineer cost within ±15% of $41,200? If any "no" → prepare termination memo. | Talgaos + Juan | — |

---

## 12. Decision

| Option | Recommendation | Reason |
|---|:---:|---|
| Proceed unconditional on wholesale-platted-lot exit (Scenario A) | **NO** | Loses $546K at $55K retail; break-even at $58K is at Tier-A P75 |
| Proceed conditional on Scenario B commitment (vertical) **OR** re-trade Subject ≤$325K | **YES** | $104K profit at 30 months on $5.7M deployment — viable but tight; re-trade restores Scenario A margin |
| Proceed for Scenario C assignment as primary, with Scenario B as fallback | **YES — parallel** | $29K in 6 weeks if assignee emerges; $5K capital at risk |
| Walk | **YES, if** any §11 Day-14 gate fails | Recover EM, redeploy capital |

**Single biggest open question:** *Will PlainsCapital Special Assets get an LOI inside the 60-day window?* If Day-14 doesn't produce at least an acknowledgement and an internal committee date, the deal is mathematically harder to close and Scenario C becomes the dominant exit.

---

## Appendix A — Data Sources & Provenance

| Source | Use | Coverage |
|---|---|---|
| Juan Elizondo IDX broker (d337) — `juanjoseelizondo.idxbroker.com` | Primary comp set | 3,900 listings, 13 RGV ZIPs, 6 status×prop-type, 704 detail fetches |
| HCAD / Hidalgo Tax Office — `actweb.acttax.com/act_webdev/hidalgo/` | CAD assessed land + tax history + owner search | Subject + Stonecrest + Russell Village (n=37) + 7 portfolio sweeps |
| Hidalgo CAD Prodigy API — `hidalgo.prodigycad.com` | Parcel geometry, deed history, owner records | Subject (PID 295816) + Stonecrest (PID 645048) |
| Crexi RGV land DB | Cross-check on per-acre basis | 78 RGV land comps, 42 under 5 ac |
| TxDOT District 21 Pharr — 12-mo avg low bid prices (Aug 2024) | Hard cost build-up | Items 100, 110, 132, 150, 247, 340, 341, 360, 400, 464, 529, 530, 666, 671 |
| TxDOT Highway Cost Index (Oct 2025 = 320.82) | 2024→2026 escalation | +4%/yr |
| NAHB 2024 Cost of Constructing a Home survey | Site-work cross-check | National 41-builder survey |
| AEP Texas tariff PUC Docket 55957 | Dry-utility subdivision allowance | $250/lot |
| City of Edinburg UDC Article 5 Table 5.203-1 | Pavement classification + ROW | 40' multi-family rule (mid case) |
| Hidalgo County Subdivision Rules (2018 amended) | Drainage + streetlight requirements | 50-yr event, 250 LF spacing |
| FDIC — First National Bank failed-bank list | Stonecrest successor tracing | OCC NR 2013-135, FDIC P&A archive #4731 |
| Texas Dept. of Banking — entity registry | PlainsCapital good-standing | bid=3515 |
| FEMA Map Service Center | Flood zone (pending pull) | msc.fema.gov |
| `subject.json` | Contract terms + plat geometry | TXR-1802, plat 2026-04-26, TXR-1937, TXR-1409 |
| `dev_cost_benchmarks.md` (599 lines, 55 citations) + `dev_cost_benchmarks.json` | Cost build-up | All citations inline §10 |
| `lot_pricing.json` + `comps_summary.md` | Lot retail | Tier A/B/C/D = 70/32/134/164 records |
| `final_proforma.json` | All-in pro forma + sensitivity grid | 12-row sensitivity, 3-scenario table |
| `crexi_cross_check.md` | $/ac validation | Mission 8.96 ac match within 0.2% |
| `stonecrest_owner_brief.md` | Bank-owned successor analysis | 5-layer due-diligence brief |

**Visual companion:** `dashboard.html` and `dashboard.png` in this folder.

---

## Appendix B — Field-Verification Items (for civil engineer / title)

1. Plat recordation status with City of Edinburg (recorded vs. preliminary developer sketch).
2. ETJ classification + zoning-for-townhouse confirmation.
3. FEMA flood-zone letter (assumed Zone X, verify).
4. HCID No. 1 active assessment status (canal abandoned per Vol. 34 Pg. 164A H.C.M.R., but district authority may persist).
5. Public Improvement District (PID) assessment — none disclosed but no addendum checked.
6. Whether 57.95' drain ditch easement sits ON Subject or strictly adjacent (north).
7. Whether Stonecrest is the actual Rogers Rd access strip or merely an adjacent fill-in parcel.
8. Lot 17 numbering on the recorded plat (skip vs. typo).
9. FDIC→PlainsCapital chain-of-title for Stonecrest (whether individually recorded post-2013-09-13 P&A).
10. Loss-share residual rights (FDIC/PlainsCapital 2013 agreement — typically expired by 2026).

---

*Privileged buyer-side advisory work product. Prepared by Juan Jose Elizondo, Texas Real Estate License 0620235, RE/MAX Elite, exclusively for Talgaos LLC. Not legal, tax, or engineering advice. Talgaos should retain qualified counsel, civil engineer, and CPA before financial commitment. Cost figures are web-benchmark-derived pending engineer validation — see §4.6.*

*© 2026 RE/MAX Elite. Confidential. 2026-04-26.*
