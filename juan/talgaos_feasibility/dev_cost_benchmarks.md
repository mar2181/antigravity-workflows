# RGV Horizontal Subdivision Development Cost Benchmarks
**Compiled:** 2026-04-26
**Project basis:** Edinburg TX, 4.16 ac combined parcel (2.69 ac subject + 1.47 ac Stonecrest), 27 townhome lots (~2,540 SF each), ~600 LF interior 50'-ROW streets (N. Turquesa St + E. Aqua St), 8,850 SF detention pond, ~600 LF curb-and-gutter both sides
**Author note:** This is the SOLE cost source for the institutional-grade feasibility study. No engineer interviews per client decision. Every number is URL-cited. National-vs-RGV adjustments are flagged inline.

---

## 0. Critical project-design flags before reading the cost table

These are **dimensional / regulatory issues** that change cost numbers. They must be confirmed with City of Edinburg planning before the feasibility window closes (2026-05-30 / extended 2026-06-13).

| Flag | Issue | Cost impact |
|---|---|---|
| **Pavement width** | Project assumes 26' pavement in 50' ROW. City of McAllen requires 50' ROW + **32' pavement** for interior streets [\[1\]](#cite1). Edinburg UDC Table 5.203-1 minor street: **50–60' ROW + 32–36' pavement**, with **multi-family/townhome internal: "50' ROW with minimum 40' pavement"** [\[2\]](#cite2). **Reading note:** The Edinburg UDC language ("multi-family … internal streets may have a minimum ROW of 50 feet, a minimum pavement width of 40 feet") is **permissive of the 50'/40' standard as a relaxation from the otherwise-required residential collector (60' ROW / 43' pavement)** — it is *not* permission to go below 40'. Project is 27 townhomes on 2,540 SF lots, almost certainly classified as multi-family. Therefore: **mid case = 40' pavement** (the floor under the multi-family rule); low case = 32' (assumes single-family / detached classification negotiated); high case = 43' (full residential collector). | At 40' pavement: paving SF = 600 LF × 40 ft / 9 = 2,667 SY × $35/SY = $93,300. At 32': $74,650. At 43': $100,300. Mid case below uses **40' pavement** consistent with the strict-reading interpretation. |
| **Detention sizing** | 8,850 SF pond for 4.16 ac at ~70% impervious is **suspiciously small**. Typical RGV detention for 60% impervious requires ~0.3–0.5 ac-ft of storage. 8,850 SF × 4 ft avg depth = 0.81 ac-ft, which may be adequate, but verify with a drainage calc. Hidalgo County 2018 amended rules: drainage must handle a **50-year event** [\[3\]](#cite3). | If county/HCDD No. 1 requires more capacity, excavation CY rises proportionally. |
| **Heavy north-strip easements** | 57.95' drain ditch (Vol. 34 Pg. 164A H.C.M.R.) + 24' HCID irrigation + 45' abandoned canal ROW. HCID No. 1 holds residual authority even on abandoned ROW until formally released [\[4\]](#cite4). | Abandonment / quitclaim coordination is a real soft cost. Budget at least one dedicated HCID coordination line item below. |
| **Townhouse density** | 40' frontage townhomes mean shorter LF utility per lot (good) but higher density loading on storm/sanitary. Most public RGV cost data is SFR (60–80' lots). Adjust storm sizing upward but utility LF/lot downward. |
| **Streetlights every 250 ft** | Hidalgo County 2018 amendment: streetlights at intersections + cul-de-sacs + every 250 LF along internal streets [\[3\]](#cite3). 600 LF of street + intersection ⇒ 4–5 fixtures minimum. |
| **Plat status ambiguity** | If plat is preliminary (not recorded), engineering + plat fees are upstream; if recorded, only construction plans + permit fees remain. Treat as preliminary in mid case. |
| **Easement on/adjacent ambiguity** | `subject.json` flags an open question: does the 57.95' drain ditch easement sit ON the subject parcel or strictly adjacent (north of it)? Plat shows it on the **north strip**, but legal verification needed. **If on-subject and unbuildable:** the project loses ~57.95' × 660' / 43,560 = 0.88 ac of buildable area, which would push lot yield **well below the 24-lot floor** in §9 sensitivity. Per-lot dev cost would rise sharply because hard cost is mostly fixed. Treat 24-lot floor as **conditional on easement being adjacent (north of), not within, subject**. |

---

## 1. Summary table (per-lot all-in horizontal-only cost, 2026 dollars)

Per-lot estimates exclude land basis. 27-lot baseline, 4.16-acre site, urban Edinburg with full city utilities available at boundary.

| Source | Per-lot (low) | Per-lot (mid) | Per-lot (high) | Year basis | Project type | Notes |
|---|---|---|---|---|---|---|
| NAHB Cost of Constructing a Home 2024 (site work portion only) | $32,719 | $32,719 | $32,719 | 2024 | National SFR, 41-builder survey | Site work = 7.6% of $428,215 avg new home, includes permit + water/sewer inspection + arch/eng + impact fees. Not lot-development; per-home site work [\[5\]](#cite5)[\[6\]](#cite6). Adjust upward for full lot-development scope. |
| Hutson Land Planners (TX) lot-development range | $50,000 | $100,000 | $150,000 | 2024 | TX subdivision | "Subdivision development costs per acre typically range $50,000–$150,000." Per-acre, not per-lot. Project is 6.5 lots/ac so per-lot is $7,700–$23,100 (LOW; this excludes major utility extensions) [\[7\]](#cite7). |
| Hedgefield Homes North TX site dev | $30,000 | $47,000 | $65,000 | 2024 | North TX SFR per home | Per-home site dev range. Doesn't include subdivision-level infrastructure [\[8\]](#cite8). |
| TxDOT Pharr unit-cost build-up (THIS DOC §3) | $19,400 | $28,900 | $38,500 | 2024–2025 | TxDOT bid tabs, RGV | Bottom-up construction-only (no soft costs). See §3 below. |
| **Recommended consensus (this doc, §6)** | **$32,000** | **$41,200** | **$58,000** | **2026** | **Edinburg townhome subdivision** | Build-up + soft costs + 15% contingency. Mid uses 40' pavement (multi-family rule). See §6. |

**Per-acre conversion check:** $41,200/lot × 27 lots = $1,112,400 ÷ 4.16 ac = **$267,400/ac all-in horizontal** (mid). This is above Hutson Land Planners' $50K–$150K range because (a) townhouse density × utility intensity, (b) we include full soft costs that Hutson treats separately, (c) HCI inflation 2024→2026, and (d) Edinburg-specific easement/abandonment work. Reasonable for a small dense townhome plat.

---

## 2. Hard cost line-item benchmarks (with citations)

### 2.1 Clearing & grading (Item 1)

Site is ~4.16 ac of farmland (low vegetation, no major trees per project context). Should bid at the **low end** of clearing range.

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr District 12-mo avg low bid, Item 100 6001 (Preparing ROW) | $/AC | — | $1,253.64 | — | Lean prep; no trees [\[9\]](#cite9) |
| TxDOT Statewide avg low bid, Item 100 6001 (Preparing ROW) | $/AC | — | $6,958.13 | — | Statewide much higher than Pharr – validates that Pharr is a low-cost district [\[10\]](#cite10) |
| Daniel Dean Land Clearing 2025 (Texas) | $/AC | $1,500 | $2,500 | $7,000 | Light brush, $1,500–$3,000/ac; heavy clearing $4,000–$7,000+ [\[11\]](#cite11) |
| Angi 2026 Texas land clearing | $/AC | $500 | $2,500 | $5,600 | "Approximately $500 to $5,600 per acre" [\[12\]](#cite12) |
| TxDOT Pharr Embankment (final, dense compaction Type C) Item 132 6006 | $/CY | — | $5.50 | — | Final fill if grading import needed [\[9\]](#cite9) |
| TxDOT Pharr Roadway Excavation Item 110 6001 | $/CY | — | $4.50 | — | Cut for pad/road grading [\[9\]](#cite9) |
| TxDOT Pharr Blading Item 150 6001 | $/STA | — | $157.00 | — | Per 100 LF station [\[9\]](#cite9) |

**Project applicability (RGV, flat farmland, no trees):** Low end of range. 4.16 ac × $2,500/ac = **$10,400 mid**; range $5,000–$23,000.

---

### 2.2 Paving — interior streets (Item 2)

Project: ~600 LF of new 50' ROW interior streets. **Compliant minimum pavement width 32' per Edinburg UDC Table 5.203-1** [\[2\]](#cite2) (project assumes 26' — see §0 flag). Mid case uses **32' pavement = 600 LF × 32 ft / 9 = 2,133 SY per 600 LF**.

#### Asphalt option (2" surface + 8" flex base — typical residential)

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 247 6060 — Flex Base Type E Grade 4, Cmp In Place | $/CY | — | $21.88 | — | 8" base = 0.222 CY/SY → ~$4.86/SY base [\[9\]](#cite9) |
| TxDOT Pharr Item 247 6225 — Flex Base Type E Grade 4, Roadway Delivered | $/CY | — | $22.18 | — | Alternative measurement [\[9\]](#cite9) |
| TxDOT Pharr Item 340 6104 — Dense-graded HMA Type-D (PG64-22) | $/TON | — | $110.50 | — | Surface course; 2" = 0.122 TON/SY → ~$13.50/SY [\[13\]](#cite13) |
| TxDOT Pharr Item 341 6039 — Dense-graded HMA Type-D | $/TON | — | $68.47 | — | Lower cost variant; $8.36/SY for 2" [\[13\]](#cite13) |
| **Built-up subtotal (asphalt) per SY** | $/SY | $13 | $18 | $24 | 2" surface + 8" base [computed from TxDOT lines above] |
| TexPave Experts 2025 (Texas residential) | $/SY | $27 | $40 | $54 | $3–$6/SF residential paving [\[14\]](#cite14) — markup over TxDOT bid suggests private subdivision adds ~50–100% over TxDOT for staging/scale |
| **Recommended (private subdivision asphalt)** | $/SY | $25 | $35 | $50 | Includes contractor markup vs. TxDOT lean bid |

#### Concrete option (6" reinforced)

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 530 6001 — Concrete Intersections | $/SY | — | $115.00 | — | Heavy 8"+ concrete, intersection grade [\[15\]](#cite15) |
| TxDOT Pharr Item 530 6004 — Concrete Driveways | $/SY | — | $50.22 | — | Closer proxy for residential street-grade slab [\[15\]](#cite15) |
| TxDOT Pharr Item 360 6003 — CRCP 9" | $/SY | — | $54.00 | — | Highway grade [\[13\]](#cite13) |

**Project applicability (recommend asphalt over concrete given small subdivision economics; mid uses 40' pavement per multi-family rule reading in §0):**
- **Mid: 40' pav × 600 LF / 9 = 2,667 SY × $35/SY = $93,300**
- Low (32' pav, single-family classification): 2,133 SY × $25 = $53,300
- High (43' pav, full residential collector): 2,867 SY × $50 = $143,300
- *Reference only:* 26' pavement (project assumption, code-risk): 1,733 SY × $35 = $60,650

#### Curb & gutter

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 529 6007 — Concrete Curb & Gutter Type I | $/LF | — | $15.00 | — | Pharr 12-mo avg [\[15\]](#cite15) |
| TxDOT Pharr Item 529 6008 — Concrete Curb & Gutter Type II | $/LF | — | $14.21 | — | [\[15\]](#cite15) |
| TxDOT Pharr Item 529 6028 — Curb & Gutter Type B (mountable) | $/LF | — | $14.03 | — | [\[15\]](#cite15) |
| **Recommended (private subdivision)** | $/LF | $15 | $20 | $28 | TxDOT base + 33–87% private markup (curb-only sub-trades smaller crews) |

**Project applicability:** Both sides of 600 LF street = 1,200 LF × $20/LF = **$24,000 mid**; range $18,000–$33,600.

---

### 2.3 Storm sewer + detention (Item 3)

Project: 8,850 SF detention pond (~0.20 ac). For 0.81 ac-ft storage (8,850 SF × 4 ft avg) at $32/CY (Texas clay): ~1,300 CY excavation. Storm pipe estimated 600 LF (single trunk down street alignment + lateral inlets).

#### Storm pipe (RCP)

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 464 6003 — RCP Class III, 18" | $/LF | — | $57.43 | — | [\[16\]](#cite16) |
| TxDOT Pharr Item 464 6005 — RCP Class III, 24" | $/LF | — | $60.00 | — | [\[16\]](#cite16) |
| TxDOT Pharr Item 464 6007 — RCP Class III, 30" | $/LF | — | $83.50 | — | [\[16\]](#cite16) |
| TxDOT Pharr Item 464 6017 — RCP Class IV, 18" (lower-cost variant) | $/LF | — | $40.00 | — | [\[16\]](#cite16) |
| TxDOT Pharr Item 464 6038 — RCP Class III, 18" (Special) | $/LF | — | $46.33 | — | [\[16\]](#cite16) |

#### Inlets, manholes, junction boxes

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 465 6126 — Inlet Complete (PSL FG) 3'×3' | $/EA | — | $3,137.50 | — | [\[16\]](#cite16) |
| TxDOT Pharr Item 465 6005 — Junction Box (PJB) 3'×3' | $/EA | — | $9,957.75 | — | [\[16\]](#cite16) |
| TxDOT Pharr Item 465 6270 — Manhole Type M | $/EA | — | $4,160.00 | — | [\[16\]](#cite16) |
| TxDOT Pharr Item 466 6003 — Headwall (CH-FW-0) 18" dia | $/EA | — | $2,500.00 | — | Detention outfall [\[16\]](#cite16) |
| TxDOT Pharr Item 466 6005 — Headwall 24" dia | $/EA | — | $6,900.00 | — | [\[16\]](#cite16) |

#### Detention basin excavation

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 110 6002 — Excavation (Channel) | $/CY | — | $4.74 | — | Lean cost (highway scale) [\[9\]](#cite9) |
| Kitching Co. 2025 Texas | $/CY | $9.75 | $9.75 | — | Texas baseline excavation [\[17\]](#cite17) |
| Aqua Rain Water 2026 detention | $/CY | $25 | $32 | $55 | "Commercial detention projects … $25–$55/CY"; Houston clay ~$32/CY [\[18\]](#cite18) |
| **Recommended (RGV clay, small dense site)** | $/CY | $20 | $32 | $45 | Aligns with Aqua Rain mid; Pharr has clay soil similar to Houston |

**Project applicability:**
- Pipe: 600 LF × $60/LF (mix of 18"–24") = $36,000 mid; range $24,000–$50,000
- Inlets: 6 inlets × $3,138 = $18,825 mid
- Manholes: 2 storm MH × $4,160 = $8,320 mid
- Outfall headwall: 1 × $4,000 = $4,000 mid
- Detention excavation: 1,300 CY × $32 = $41,600 mid (range $26,000–$58,500)
- Detention grading/seeding/erosion control: 8,850 SF × $1.50/SY (~970 SY) = $1,500 mid
- **Storm + detention subtotal: $109,000 mid; range $80,000–$140,000**

---

### 2.4 Water mains (Item 4)

Project: 600 LF main + ~500 LF service stubs (1 stub per lot × 27 lots × ~18 ft avg). Assume **8" PVC C900 main** (typical residential per Edinburg standards & McAllen code [\[1\]](#cite1)).

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| City of Lubbock 2021 Unit Water Costs (8" C900 PVC) | $/LF | — | $46 | — | Per [\[19\]](#cite19) ext. summary |
| City of Lubbock 2022 Unit Water Costs (8" C900 PVC) | $/LF | — | $61 | — | Up 33% in 1 year [\[19\]](#cite19) |
| Eight Inch Water Main install cost guide 2024 | $/LF | $50 | $122 | $200 | $40 mat + $60 lab + $15 equip + $7 permits = $122 [\[20\]](#cite20) |
| HomeAdvisor 2025 water main installation | $/LF | $50 | $100 | $250 | "$50–$150 LF; up to $250 in urban deep" [\[21\]](#cite21) |
| **Recommended for RGV 8" C900 in subdivision (escalate Lubbock 2022 at 4%/yr × 4 yrs)** | $/LF | $60 | $75 | $95 | Lubbock $61 (2022) × 1.17 (HCI 2022→2026) = $71. Mid $75 |

#### Fire hydrants

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| Angi 2026 fire hydrant install | $/EA | $8,000 | $14,000 | $20,000 | "Average $8K–$20K including unit + install" [\[22\]](#cite22) |
| Angi private hydrant only | $/EA | $3,000 | $6,000 | $9,100 | "Private fire hydrant install $3,000–$9,100" [\[22\]](#cite22) |
| **Recommended (RGV subdivision, single hydrant per ~500 LF)** | $/EA | $6,000 | $8,500 | $12,000 | Mid-range public-grade |

#### Service laterals + meter boxes

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| Trenching cost 2026 | $/LF | $5 | $9 | $15 | $5–$12/LF baseline [\[23\]](#cite23) |
| Estimated service lateral cost (1" copper or PEX, 18 LF + meter box) | $/EA | $800 | $1,200 | $1,800 | Built up: 18 LF × $10 + $1,000 box/setter [computed] |

**Project applicability:**
- 8" C900 main: 600 LF × $75 = $45,000 mid
- Fire hydrants (2 minimum, plus dead-end blowoff): 3 × $8,500 = $25,500 mid
- Service laterals: 27 × $1,200 = $32,400 mid
- Gate valves (4 × $1,500 from Pharr Item 479 6005 adjusted up [\[16\]](#cite16)): $6,000 mid
- Tap-in/connection to existing main: $5,000–$15,000 (allowance)
- **Water subtotal: $115,000 mid; range $90,000–$155,000**

---

### 2.5 Sanitary sewer (Item 5)

Project: 600 LF main + 27 service laterals. Assume **8" PVC SDR-26 main** (typical RGV residential). Lift station NOT assumed — Edinburg has gravity sanitary at most parcel boundaries; if there isn't one within 600 LF, add $150K–$300K for a duplex lift station.

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| Angi Houston sewer line 2025 | $/LF | $25 | $90 | $200 | Labor $25–$200/LF Houston [\[24\]](#cite24) |
| HomeAdvisor 2025 sewer install | $/LF | $50 | $150 | $250 | "$50–$250+/LF traditional dig" [\[25\]](#cite25) |
| **Estimated 8" PVC SDR-26 (RGV, urban subdivision, 4-8 ft cover)** | $/LF | $55 | $80 | $115 | Mid escalated from 2024 baseline; 8" thicker than residential service so above $50 floor |

#### Sanitary manholes (4-ft diameter, depth-dependent)

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 465 6270 — Manhole Type M | $/EA | — | $4,160 | — | Storm grade — sanitary similar size [\[16\]](#cite16) |
| Sewer Manhole Cost Guide 2024 | $/EA | $3,500 | $5,500 | $8,000 | 4-ft dia, 4-6 ft depth typical [\[26\]](#cite26) |
| **Recommended sanitary MH (RGV, 4-ft dia, 4-8 ft depth)** | $/EA | $4,000 | $5,500 | $7,500 | Pharr base + 33% sanitary premium (more demanding waterproofing) |

#### Service laterals (4" or 6")

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| Estimated service lateral (4" PVC, 18 LF + cleanout + tap) | $/EA | $700 | $1,000 | $1,500 | Typical RGV; less than water lateral because no meter box [computed] |

**Project applicability:**
- 8" sanitary main: 600 LF × $80 = $48,000 mid
- Manholes (every 300 LF + each end + at street junction = 4 MH): 4 × $5,500 = $22,000 mid
- Service laterals: 27 × $1,000 = $27,000 mid
- Tie-in to existing trunk: $5,000–$15,000 allowance
- **Sanitary subtotal (assuming gravity, no lift station): $107,000 mid; range $80,000–$145,000**
- **CRITICAL CONTINGENCY:** If lift station required, add **$200,000 ± $50,000** [computed from regional duplex lift station benchmarks].

---

### 2.6 Dry utilities — electric, gas, telecom (Item 6)

Per AEP Texas tariff (PUC Docket 55957), for each qualified subdivision AEP adds **$250 per residential connection** as a Standard Allowance credit toward developer's electric infrastructure cost [\[27\]](#cite27). Developer pays remainder.

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| AEP Texas tariff developer allowance | $/lot | -$250 | -$250 | -$250 | Credit deducted from developer cost [\[27\]](#cite27) |
| Trenching cost 2026 — joint trench (electric, gas, telecom) | $/LF | $5 | $9 | $15 | [\[23\]](#cite23) |
| Gas line install 2026 | $/LF | $15 | $30 | $50+ | Includes pipe + trench [\[28\]](#cite28) |
| Telecom conduit 2026 | $/LF | $5.50 | $15 | $25 | "$5.50–$25/LF" [\[28\]](#cite28) |
| **Built-up dry utilities cost per lot (joint trench, ~50–80 LF/lot)** | $/lot | $1,500 | $3,500 | $6,000 | Industry composite [computed] |

**Project applicability:** 27 lots × $3,500 = $94,500 mid (gross); minus $6,750 AEP credit = **$87,750 mid; range $35,000–$155,000**

**Note:** RGV electric is split between **AEP Texas Central** (most of Edinburg/Hidalgo Co.) and **Magic Valley Electric Cooperative** in some pockets — confirm service territory before finalizing.

---

### 2.7 Sidewalks (Item 7)

Edinburg UDC Table 5.203-1 requires **5' sidewalks both sides** on minor streets [\[2\]](#cite2). Hidalgo County also requires sidewalks on internal subdivision streets.

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 531 6001 — Concrete Sidewalks 4" | $/SY | — | $40.92 | — | [\[15\]](#cite15) — equals $4.55/SF |
| Texas Concrete Costs 2025 (4" sidewalk) | $/SF | $6 | $9 | $12 | Residential install [\[29\]](#cite29) |
| **Recommended (private subdivision, 5' wide × 4" concrete)** | $/SF | $7 | $9 | $11 | Pharr base ($4.55/SF) + 50–100% private markup |

#### Curb ramps (ADA, at intersections + lot driveways)

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT Pharr Item 531 6004 — Curb Ramps Type 1 | $/EA | — | $1,320 | — | [\[15\]](#cite15) |
| TxDOT Pharr Item 531 6005 — Curb Ramps Type 2 | $/EA | — | $1,300 | — | [\[15\]](#cite15) |
| TxDOT Pharr Item 531 6015 — Curb Ramps Type 20 | $/EA | — | $1,600 | — | [\[15\]](#cite15) |

**Project applicability:**
- Sidewalk both sides 600 LF × 5 ft = 6,000 SF × $9/SF = **$54,000 mid**
- Curb ramps (4 corners at intersection): 4 × $1,500 = $6,000 mid
- **Sidewalk subtotal: $60,000 mid; range $45,000–$78,000**

---

### 2.8 Street lighting (Item 8)

Hidalgo County 2018 amendment: **streetlights at all intersections, cul-de-sacs, and every 250 LF** along internal streets [\[3\]](#cite3). Developer pays full cost [\[30\]](#cite30).

For 600 LF of streets + 1 intersection: minimum **4–5 fixtures** (intersection + ends + 250-ft spacing).

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| ADN Lite streetlight install 2024 | $/EA | $2,000 | $2,500 | $3,000 | Pole + lamp [\[31\]](#cite31) |
| ADN Lite + decorative pole | $/EA | $2,500 | $4,000 | $7,000 | Decorative pole option [\[31\]](#cite31) |
| Standard install with conduit | $/EA | $3,000 | $5,000 | $8,000 | Including conduit + trenching + connection [composite] |

**Project applicability:** 5 fixtures × $5,000 = **$25,000 mid; range $15,000–$40,000**

---

### 2.9 Signage + striping (Item 9)

| Source | Unit | Low | Mid | High | Note |
|---|---|---|---|---|---|
| TxDOT 12-mo (general signage allowance) | LS | $2,000 | $5,000 | $10,000 | Stop sign + street-name + no-parking + striping for small subdivision [composite] |

**Project applicability:** **$5,000 mid (all-in lump sum)**

---

## 3. Bottom-up TxDOT Pharr build-up (sanity check, hard cost only, no soft costs)

Using only TxDOT Pharr 12-month moving average bid prices from August 2024 [\[9\]](#cite9)[\[13\]](#cite13)[\[15\]](#cite15)[\[16\]](#cite16):

| Item | Quantity | Unit | TxDOT Pharr unit price | Subtotal |
|---|---|---|---|---|
| Preparing ROW | 4.16 | AC | $1,254 | $5,217 |
| Roadway excavation | 1,200 | CY | $4.50 | $5,400 |
| Embankment Type C | 600 | CY | $5.50 | $3,300 |
| Flex base 8" Type E Gr 4 (40' pav × 600 LF) | 593 | CY | $21.88 | $12,975 |
| Asphalt 2" Type-D HMA (40' pav × 600 LF) | 326 | TON | $97.33 | $31,729 |
| Curb & Gutter Type II | 1,200 | LF | $14.21 | $17,052 |
| Concrete sidewalk 4" | 670 | SY | $40.92 | $27,416 |
| Curb ramps Type 1 | 4 | EA | $1,320 | $5,280 |
| Concrete intersection (1 intersection ~150 SY) | 150 | SY | $115.00 | $17,250 |
| RCP 18" Class III | 400 | LF | $57.43 | $22,972 |
| RCP 24" Class III | 200 | LF | $60.00 | $12,000 |
| Storm inlet 3'×3' | 6 | EA | $3,137.50 | $18,825 |
| Storm manhole | 2 | EA | $4,160 | $8,320 |
| Headwall 18" outfall | 1 | EA | $2,500 | $2,500 |
| Channel excavation (detention) | 1,300 | CY | $4.74 | $6,162 |
| Soil retention blanket (detention) | 1,000 | SY | $1.78 | $1,780 |
| Mobilization | 1 | LS | $152,459 (Pharr Item 500 6001) ÷ 5 (small project share) | $30,492 |
| Barricades / traffic handling (3 mo) | 3 | MO | $2,840 | $8,520 |
| **Subtotal — TxDOT public-bid prices** | | | | **$237,189** |
| **Add 35% private subdivision markup (small-job premium, sub-tier coordination)** | | | | **$320,205** |

**Per lot (TxDOT bottom-up, no soft costs):** $320,205 ÷ 27 = **$11,860/lot construction-only**

This excludes: water main, sanitary main, dry utilities, fire hydrants, service laterals (all 27 × 2), street lights, signage. Adding those from §2.4–2.8 mid cases: $115,000 + $107,000 + $87,750 + $25,000 + $5,000 = $339,750. **Total construction = $659,955 ÷ 27 = $24,440/lot construction-only mid** (slightly higher than the §6.1 hard-cost subtotal $636,450 because §3 builds up paving from raw TxDOT bid items at 40' pavement, then applies a flat 35% private subdivision premium and adds mobilization separately, which double-counts mobilization vs. the §2 line items that already include contractor markup; treat §3 as a sensitivity-check upper bound).

---

## 4. Soft cost benchmarks (with citations)

### 4.1 Civil engineering & surveying

| Source | Basis | Low | Mid | High | Note |
|---|---|---|---|---|---|
| 24hPlans Land Development Cost Guide | % of construction | 5% | 10% | 15% | "Design and engineering fees typically 5–15%" [\[32\]](#cite32) |
| Hutson Land Planners (TX) | Flat | $10,000 | $50,000 | $100,000 | Range by complexity [\[7\]](#cite7) |
| **Recommended (small-but-complex 27-lot townhome plat with 3 easements + HCID coord.)** | % | 8% | 11% | 14% | Higher end given easement complexity |

**Project applicability (engineering + surveying combined to avoid double-count; the 11% engineering scope typically encompasses plat/topo):** 11% of mid hard cost = **$71,000–$78,000 mid** depending on hard-cost final; range $50,000–$95,000. **Includes** boundary survey, topographic, plat preparation, civil construction plans, drainage report, water/sanitary design.

### 4.2 Plat review and city permit fees

The City of Edinburg UDC specifies fees in Article 9 / Article 8 Administration but the public encodeplus.com viewer doesn't expose dollar amounts via web scraping (verified 2026-04-26). **Confirm directly with City of Edinburg Planning at (956) 388-8204** [\[33\]](#cite33).

| Source | Item | Low | Mid | High | Note |
|---|---|---|---|---|---|
| Hutson Land Planners (TX baseline) | County subdivision approval | $1,000 | $5,000 | $10,000 | [\[7\]](#cite7) |
| Hutson Land Planners | City zoning/site dev permit | $2,500 | $8,500 | $15,000 | [\[7\]](#cite7) |
| McAllen "fee in lieu of parkland dedication" | $/dwelling unit | $700 | $700 | $700 | RGV reference; Edinburg may have similar [\[1\]](#cite1) |
| NAHB 2024 average building permit fee per home | $/home | — | $7,640 | — | [\[6\]](#cite6) |
| NAHB 2024 average water/sewer inspection fee | $/home | — | $6,260 | — | [\[6\]](#cite6) |
| NAHB 2024 average impact fee | $/home | — | $6,367 | — | [\[6\]](#cite6) — **McAllen MPU charges no impact fees** [\[34\]](#cite34); Edinburg likely similar |

**Project applicability (Edinburg, where impact fees are likely zero/nominal):**
- Plat review (preliminary + final): $5,000 (allowance)
- Building permits 27 × $1,500 (RGV is generally less than NAHB national $7,640 — adjust down 80%): $40,500
- Water/sewer connection fees 27 × $1,500: $40,500
- Park-land dedication fee in lieu (using McAllen $700/unit as RGV proxy): 27 × $700 = $18,900
- **Plats + permits + city fees subtotal: $105,000 mid; range $75,000–$140,000**

### 4.3 Construction management / GC fee

| Source | Basis | Low | Mid | High | Note |
|---|---|---|---|---|---|
| Industry standard horizontal | % of construction | 5% | 8% | 12% | [composite — Hutson + general industry] |
| **Project applicability** | % of $636,450 hard | $31,800 | $50,900 | $76,400 | At 8% mid |

### 4.4 Geotechnical / environmental

| Source | Item | Low | Mid | High | Note |
|---|---|---|---|---|---|
| HRK Engineering 2024 (geotech) | Flat | $1,000 | $2,700 | $5,000 | Average $2,700 [\[35\]](#cite35) |
| HomeGuide / Soils-Inc 2024 (subdivision) | Flat | $3,000 | $7,500 | $15,000 | 4–6 borings × $1,500 each [\[36\]](#cite36) |
| Aegis Environmental 2025 | Phase I ESA flat | $1,800 | $3,500 | $6,000 | Typical commercial property [\[37\]](#cite37) |
| CRG Texas 2025 | Phase I ESA flat | $2,000 | $3,500 | $5,000 | TX-specific [\[38\]](#cite38) |

**Project applicability:** Geotech $7,500 + Phase I ESA $3,500 = **$11,000 mid; range $5,000–$20,000**

### 4.5 Drainage study / HCID coordination

| Source | Item | Low | Mid | High | Note |
|---|---|---|---|---|---|
| Hutson Land Planners | Floodplain & environmental study | $3,000 | $9,000 | $15,000 | [\[7\]](#cite7) |
| Estimated HCID No. 1 coordination + abandonment paperwork | LS | $5,000 | $15,000 | $35,000 | Required for 45' abandoned canal ROW + 24' irrigation easement; HCID has residual authority [\[4\]](#cite4) |
| Estimated drainage study (50-yr event per Hidalgo Co. amended rules) | LS | $5,000 | $10,000 | $18,000 | Per [\[3\]](#cite3) |

**Project applicability:** **$25,000 mid; range $13,000–$50,000** (this is a meaningful line specific to this project's easement complexity)

### 4.6 Legal / title / closing

| Source | Basis | Low | Mid | High | Note |
|---|---|---|---|---|---|
| Houzeo / Bankrate 2024 TX | % of sale price | 0.5% | 0.75% | 1.0% | Title insurance [\[39\]](#cite39) |
| Bankrate / Herring Bank | Buyer closing % | 2% | 3% | 5% | Total buyer closing [\[40\]](#cite40) |
| **Recommended for development project (legal entity setup, restrictive covenants, plat dedication, HOA docs)** | LS | $8,000 | $15,000 | $25,000 | Covers attorney work beyond title [composite] |

**Project applicability:** Closing on land basis is a separate land cost (not in horizontal-dev). For the 27-lot subdivision-development closing soft costs (covenants, HOA formation, plat recording attorney fees): **$15,000 mid**

### 4.7 Marketing & sales commission

Standard 6% commission on lot sales is a **disposition** cost, not a development cost. Excluded from horizontal-cost-per-lot but flagged here for proforma reconciliation.

- 27 lots × estimated $90,000 sale price × 6% = $145,800 sales commission **(separate proforma line)**

---

## 5. Carrying / financing benchmarks

### 5.1 Construction loan rate

| Source | Rate | Date | Note |
|---|---|---|---|
| Biz2Credit Texas commercial 2026 | 7.5%–9.5% | Q1 2026 | Traditional banks [\[41\]](#cite41) |
| Terrydale Capital averages | 5.50%–8.75% | Feb 2026 | Commercial RE [\[42\]](#cite42) |
| Terrydale Capital | ~7.75% | Q1 2026 | Average construction [\[42\]](#cite42) |
| **Recommended for South TX small developer (Lone Star Bank, Texas Regional, IBC reference)** | 8.5%–9.5% | Apr 2026 | Mid 9.0% for proforma |

### 5.2 Property tax (carrying cost during build/sale)

| Taxing entity | Rate per $100 | Source | Year |
|---|---|---|---|
| Hidalgo County | $0.5750 | Edinburg Advocate Sept 2024 [\[43\]](#cite43) | FY 2025 |
| City of Edinburg | $0.6300 | Texas Border Business / MyRGV Sept 2024 [\[44\]](#cite44)[\[45\]](#cite45) | FY 2024–2025 |
| Edinburg CISD (estimated school M&O+I&S) | ~$1.10 (typical RGV) | [composite — verify with HCAD] | FY 2024–2025 |
| Hidalgo County Drainage District No. 1 | ~$0.075 (typical) | [verify] | — |
| **Combined effective rate (Edinburg city limits, no MUD)** | **~2.38** | | — |

This aligns with Ownwell's "1.78% median effective rate" [\[46\]](#cite46) which is on appraised (lower) value. Adopted-rate sum-of-entities is higher.

**Project applicability:** Combined parcel basis $425,000 × 2.38% = **$10,115/yr in property taxes during hold/build**. For a 12–18 month development cycle: **$10K–$15K**.

### 5.3 Insurance during build

Builders risk insurance (subdivision horizontal, no vertical): **0.25–0.50% of hard cost** = $636,450 × 0.4% = **$2,545/yr** [composite industry rule].

---

## 6. Recommended consensus per-lot dev cost (2026 dollars, 27 lots, Edinburg TX)

### 6.0 Scope of "per-lot horizontal development cost"

This number is **horizontal-only** — i.e., everything required to deliver a buildable platted lot:
- ✅ Includes: site clearing/grading, paving, curb/gutter, storm + detention, water + sanitary mains, dry utility extensions, sidewalks, lighting, signage, plus all soft costs (engineering, plats, permits, geotech, drainage, legal/HOA setup, GC fee), plus carry/financing during build.
- ❌ **Excludes (separate proforma lines):**
  - Land basis: $425,000 combined ($385K subject + $40K Stonecrest)
  - Vertical construction (the townhomes themselves)
  - Disposition costs: 6% sales commission ≈ $5,400/lot at $90K avg sale price = $145,800 total
  - Marketing / model staging
  - Developer profit/return on equity

### 6.1 Mid-case build-up table (compiled from §2–§5; mid uses 40' pavement per §0)

| Cost category | Total project | Per lot (÷27) | Source |
|---|---|---|---|
| Clearing & grading | $10,400 | $385 | §2.1 |
| **Paving (asphalt, 40' pav per multi-family rule)** | **$93,300** | **$3,455** | §2.2 |
| Curb & gutter (both sides 1,200 LF) | $24,000 | $890 | §2.2 |
| Storm sewer + detention | $109,000 | $4,037 | §2.3 |
| Water mains + hydrants + services | $115,000 | $4,259 | §2.4 |
| Sanitary sewer (no lift station) | $107,000 | $3,963 | §2.5 |
| Dry utilities (electric/gas/telecom) | $87,750 | $3,250 | §2.6 |
| Sidewalks + ADA ramps | $60,000 | $2,222 | §2.7 |
| Street lights (5 fixtures) | $25,000 | $926 | §2.8 |
| Signage + striping | $5,000 | $185 | §2.9 |
| **HARD COST SUBTOTAL** | **$636,450** | **$23,572** | — |
| Civil engineering + surveying combined (11% of hard) | $70,000 | $2,593 | §4.1 |
| Plat review + city permits + park-fee-in-lieu | $105,000 | $3,889 | §4.2 |
| GC fee / construction mgmt (8% of hard) | $50,900 | $1,886 | §4.3 |
| Geotech + Phase I ESA | $11,000 | $407 | §4.4 |
| Drainage study + HCID coord. | $25,000 | $926 | §4.5 |
| Legal / covenants / HOA setup | $15,000 | $556 | §4.6 |
| **SOFT COST SUBTOTAL** | **$276,900** | **$10,256** | — |
| Property tax during build (12 mo @ 2.38% × $425K basis) | $10,115 | $375 | §5.2 |
| Builders risk insurance (12 mo @ 0.4% of hard) | $2,545 | $94 | §5.3 |
| Construction loan interest (12 mo @ 9% × ~50% avg drawn × $913K) | $41,100 | $1,522 | §5.1 |
| **CARRY / FINANCING SUBTOTAL** | **$53,760** | **$1,991** | — |
| **PRE-CONTINGENCY TOTAL** | **$967,110** | **$35,819** | — |
| **15% contingency** | **$145,067** | **$5,373** | Standard for institutional feasibility |
| **TOTAL HORIZONTAL DEVELOPMENT COST** | **$1,112,177** | **$41,192 → round to $41,200** | — |

### 6.2 Range summary

- **Low:** $32,000/lot ($865K total) — 32' pavement (single-family classification negotiated), no lift station, lean engineering, HCID abandonment goes smoothly, mild contingency burn
- **Mid:** **$41,200/lot** ($1.11M total) — 40' pavement (multi-family rule), full HCID coordination, 15% contingency held
- **High:** $58,000/lot ($1.57M total) — 43' pavement (full residential collector), lift station required (+$200K), complex HCID release, drainage study triggers detention upsize, 25% contingency burn
- **Recommended for proforma:** **$41,200/lot mid case** with 15% contingency already baked in. If lift station risk materializes, swing to **$48,500/lot**. If full residential-collector pavement triggered, swing to **$45,000/lot** independently.

### 6.3 Reconciliation to per-acre and density check

- Per-acre all-in: $1,112,177 ÷ 4.16 ac = **$267,350/ac** (mid)
- This sits **above** the Hutson Land Planners' $50K–$150K/ac TX subdivision range [\[7\]](#cite7) because:
  1. Townhouse density (6.5 lots/ac) loads infrastructure intensity per acre
  2. Hutson range excludes financing carry & contingency
  3. HCI inflation 2024→2026 (~8% combined per TxDOT October 2025 HCI of 320.82 [\[47\]](#cite47))
  4. 3 layered easements (drain ditch + HCID irrigation + abandoned canal) require non-trivial coordination
  5. Small project size (no economies of scale; 35% subdivision markup over TxDOT bid baseline)

---

## 7. RGV-specific multipliers / adjustments (vs. national)

| Adjustment | Direction | Magnitude | Rationale |
|---|---|---|---|
| Pharr District labor (vs. Texas statewide TxDOT) | **Lower** | -15 to -25% | Pharr Item 100 6001 ROW prep is $1,254/AC vs. statewide $6,958/AC [\[9\]](#cite9)[\[10\]](#cite10). Pharr is one of the cheapest TxDOT districts. |
| RGV materials (concrete, asphalt) | **Higher** | +10–15% | "Material costs in South Texas remain 10–15% higher than national averages due to supply chain logistics from Gulf Coast ports" [\[41\]](#cite41) |
| RGV specialty trades (electric, plumbing) | **Lower** | -10–20% | Smaller labor pool but lower wage base; offset by mobilization |
| Heat / weather (summer slowdown June–September) | **+** | +5% schedule risk, +3% cost | Build calendar matters; extending summer build adds general conditions |
| HCID No. 1 / drainage district coordination | **+** | +$15K–$35K hard cost item | Specific to this project — abandoned canal release [\[4\]](#cite4) |
| Edinburg impact fees | **Lower** | $0 vs. national $6,367/home [\[6\]](#cite6) | McAllen MPU charges no impact fees [\[34\]](#cite34); Edinburg likely similar — assume $0 to $1,500/home max |
| Edinburg permit fees | **Lower** | -50–80% vs. NAHB national $7,640/home [\[6\]](#cite6) | RGV is broadly a low-fee market |
| Construction loan rates (RGV) | Same | 8.5–9.5% in 2026 | Matches national [\[41\]](#cite41)[\[42\]](#cite42) |
| **Net-net RGV vs. national average** | **Approximately neutral; slight lower** | **-5 to -10%** | Lower labor/fees offsets higher materials and small-project premium |

---

## 8. Confidence notes (where data is thin)

1. **No direct RGV townhome subdivision cost disclosure found.** Closest comparable is Tres Lagos (McAllen master-planned) which is 2,571 ac with $232M private + $151M public = ~$148K/ac for public infrastructure only [\[48\]](#cite48). At master-planned scale this is misleading for a 4.16-ac plat — economies of scale don't apply. **Confidence: MEDIUM** on subdivision-level cost; **HIGH** on individual line-items via TxDOT Pharr.
2. **Edinburg fee schedule not retrievable via web.** The UDC fee tables are inside the encodeplus.com viewer behind navigation — Web scraping returns empty pages. **Action item: Phone-verify Edinburg Planning at (956) 388-8204 [\[33\]](#cite33) for plat review fee, building permit fee, water/sewer connection fee.**
3. **HCID No. 1 abandonment/coordination process is undocumented online.** Project hinges on the 45' abandoned canal ROW being formally releasable. **Action item: Direct contact with HCID No. 1 at hcid1.com [\[4\]](#cite4).**
4. **Lift station risk not resolvable from desktop research.** Whether the 600 LF gravity sanitary tie can reach an existing trunk depends on existing main locations not visible in subject.json. **If lift station required, add $200K (range $150K–$300K), which moves per-lot from $41.2K → $48.5K mid.**
5. **Lubbock 2022 unit cost data is the primary water/sewer anchor.** It was the highest-quality TX municipal cost manual we could reach without paywalls. **Confidence: MEDIUM** — Lubbock is West TX; RGV labor is similar but soils are different (Lubbock = sandy/caliche; RGV = clay). I escalated 4%/yr to 2026; this may understate clay-soil trenching difficulty. Add 5–10% to water/sewer if RGV clay verified.
6. **NAHB 2024 site work figure of $32,719 includes vertical construction site work** (excavation + foundation prep for the home pad) [\[6\]](#cite6). It is **not** a substitute for our subdivision-level horizontal cost; it understates because there's no road/utility extension cost in the NAHB number. We use it only as a sanity-check lower bound. **Confidence: HIGH on NAHB data; LOW on its applicability as a primary anchor.**
7. **TxDOT Pharr bid prices are highway-grade, not residential subdivision-grade.** TxDOT projects benefit from scale, mobilization on long stretches, and unionized prevailing wage. Private subdivisions pay a premium of **30–50%** over TxDOT bid prices for small jobs. We applied **+35%** in §3 build-up — this is an estimate, not a sourced figure. Reasonable per industry consensus but **MEDIUM confidence**.
8. **HCI 2024→2026 escalation.** Used 4%/yr (8% over 2 yrs) based on October 2025 TxDOT HCI of 320.82, +61% from May 2020 to May 2024 (= ~12.6%/yr in pandemic recovery) [\[47\]](#cite47). Recent trend is moderating. **Confidence: MEDIUM.**

---

## 9. Sensitivity to lot count (24, 27, 28, 32 lots)

Hard costs are largely fixed (one set of streets/utilities). Only lot-specific costs (services + connection fees + dry-utility lateral) scale.

| Lot count | Total dev cost (mid) | Per-lot (mid) |
|---|---|---|
| 24 (floor — assumes drain ditch easement is adjacent, not on-subject) | $1,066,000 | **$44,400/lot** |
| 27 (baseline) | $1,112,200 | **$41,200/lot** |
| 28 (Stonecrest +1) | $1,127,500 | **$40,300/lot** |
| 32 (max if Stonecrest yields more) | $1,189,000 | **$37,200/lot** |

Per-lot cost falls ~16% going from 24 to 32 lots — this is the lot-yield sensitivity that makes the Stonecrest acquisition strategically meaningful beyond just access. **Caveat:** If the 57.95' drain ditch easement is verified to sit ON the subject parcel (not adjacent), buildable area drops by ~0.88 ac and lot yield falls below 24, breaking this table's floor.

---

## 10. Citations (URLs, all accessed 2026-04-26)

<a id="cite1"></a>1. City of McAllen Code of Ordinances Chapter 134 (Subdivisions) — interior streets minimum 50' ROW + 32' pavement; sidewalks both sides. https://library.municode.com/tx/mcallen/codes/code_of_ordinances?nodeId=SPBLAUSREREAC_CH134SU
<a id="cite2"></a>2. City of Edinburg Unified Development Code (UDC), Article 5 — Subdivision Standards, Table 5.203-1 (street ROW & pavement widths). Multi-family/townhome internal: 50' ROW + 40' pavement. https://online.encodeplus.com/regs/edinburg-tx-udc-update/doc-viewer.aspx?secid=6466
<a id="cite3"></a>3. Texas Housers (Oct 2018) — Hidalgo County adopts higher drainage and streetlight infrastructure standards (50-yr drainage event; streetlights every 250 LF). https://texashousers.org/2018/10/17/county-adopts-higher-standards-for-drainage-and-streetlight-infrastructure/
<a id="cite4"></a>4. Hidalgo County Irrigation District No. 1 (HCID #1) — official site. http://hcid1.com/
<a id="cite5"></a>5. NAHB blog "Cost to Construct a Home Rose Significantly Over Last Two Years" (Jan 2025) — Construction = 64.4% of new home price; finished lot 13.7%; profit 11.0%. https://www.nahb.org/blog/2025/01/cost-of-construction-survey-2024
<a id="cite6"></a>6. EyeOnHousing — "Cost of Constructing a Home in 2024" (NAHB summary) — site work 7.6% ($32,719); permit $7,640; water/sewer inspection $6,260; arch/eng $6,480; impact fee $6,367. https://eyeonhousing.org/2025/01/cost-of-constructing-a-home-in-2024/
<a id="cite7"></a>7. Hutson Land Planners — "Understanding Land Development Costs in Texas." Subdivision $50K–$150K/ac; engineering $10K–$100K; permits $1K–$10K; impact fees $5K–$25K/ac. https://www.hutsonlandplanners.com/post/land-development-costs-texas
<a id="cite8"></a>8. Hedgefield Homes — "Site Development Cost in North Texas." $30K–$65K per home, with line-item breakdown. https://www.hedgefield.com/blog/how-much-does-site-development-cost-in-north-texas-hedgefield-homes
<a id="cite9"></a>9. TxDOT Pharr District 12-month moving average low bid prices — Items 100–199 (Preparing ROW $1,253.64/AC; excavation $4.50/CY; embankment $5.50/CY; flex base $21.88/CY). Updated Aug 8, 2024. https://www.dot.state.tx.us/insdtdot/geodist/phr/cserve/bidprice/s_0101.htm
<a id="cite10"></a>10. TxDOT Statewide 12-month moving average low bid prices — Items 100–199 (Preparing ROW $6,958.13/AC). https://www.dot.state.tx.us/insdtdot/orgchart/cmd/cserve/bidprice/s_0101.htm
<a id="cite11"></a>11. Daniel Dean Land Clearing & Dirt Work — "How Much Does It Cost to Clear Land in 2025?" Texas. https://www.danieldean.com/how-much-does-it-cost-to-clear-land-in-2025/
<a id="cite12"></a>12. Angi 2026 — "How Much Does It Cost to Clear Land?" $500–$5,600/AC. https://www.angi.com/articles/how-much-does-it-cost-clear-land.htm
<a id="cite13"></a>13. TxDOT Pharr District 12-month moving average — Items 300–360 (HMA Type-D $97.33–$110.50/TON; CRCP 9" $54/SY). Updated Aug 8, 2024. https://www.dot.state.tx.us/insdtdot/geodist/phr/cserve/bidprice/s_0301.htm
<a id="cite14"></a>14. TexPave Experts (TX) — "Asphalt Paving Cost Per Sq Ft 2025." Residential $3–$6/SF (= $27–$54/SY). https://texpaveexperts.com/blog/how-much-does-asphalt-paving-cost/
<a id="cite15"></a>15. TxDOT Pharr District 12-month moving average — Items 500–599 (Curb & Gutter $14.21/LF; Sidewalk 4" $40.92/SY; Curb Ramps $1,300–$1,600/EA). Updated Aug 8, 2024. https://www.dot.state.tx.us/insdtdot/geodist/phr/cserve/bidprice/s_0501.htm
<a id="cite16"></a>16. TxDOT Pharr District 12-month moving average — Items 400–499 (RCP 18" $40–$57/LF; Manhole $4,160/EA; Inlet 3'×3' $3,138/EA; Headwalls). Updated Aug 8, 2024. https://www.dot.state.tx.us/insdtdot/geodist/phr/cserve/bidprice/s_0401.htm
<a id="cite17"></a>17. Kitching Co. 2025 — "Average Excavation Cost Per Yard by Region." Texas $9.75/CY baseline. https://kitchingco.com/uncategorized/average-excavation-cost-per-yard-by-region-2025-report/
<a id="cite18"></a>18. Aqua Rain Water 2026 — "Stormwater Detention Cost Per Cubic Foot." Commercial detention $25–$55/CY; Houston clay $32/CY. https://aquarainwater.com/stormwater-detention-cost-per-cubic-foot/
<a id="cite19"></a>19. City of Lubbock Unit Water Costs (2021 + Dec 2022 schedules; 8" C900 PVC $46/LF in 2021 → $61/LF in 2022). https://ci.lubbock.tx.us/storage/images/cYp3CAAbUnp5wAuHaPtcHLKu5U85tKIIsqASTWfR.pdf and https://ci.lubbock.tx.us/storage/images/WqgiPpdqYcMHOFJtCvxiz4RgdXgPeMLa5oLjAqwB.pdf
<a id="cite20"></a>20. One and Done Prep — "Eight Inch Water Main Installation Cost Per Foot." Built-up $122/LF (mat $40 + lab $60 + equip $15 + permits $7). https://oneanddoneprep.com/eight-inch-water-main-installation-cost-per-foot/
<a id="cite21"></a>21. HomeAdvisor 2025 — "How Much Does It Cost to Replace a Main Water Line?" $50–$250/LF. https://www.homeadvisor.com/cost/plumbing/install-a-water-main/
<a id="cite22"></a>22. Angi 2026 — "How Much Does a Fire Hydrant Cost to Install?" $8K–$20K all-in. https://www.angi.com/articles/how-much-fire-hydrant-cost.htm
<a id="cite23"></a>23. Angi 2026 — "Trenching Cost." $5–$12/LF. https://www.angi.com/articles/trenching-cost.htm
<a id="cite24"></a>24. Angi — "How Much Does It Cost To Install a Sewer Line in Houston, TX?" Labor $25–$200/LF Houston. https://www.angi.com/articles/how-much-does-installing-sewer-line-cost/tx/houston
<a id="cite25"></a>25. HomeAdvisor 2025 — "How Much Does Sewer Line Installation Cost?" $50–$250+/LF traditional dig. https://www.homeadvisor.com/cost/plumbing/install-a-sewer-main/
<a id="cite26"></a>26. Houzdepot.blog 2024 — "Sewer Manhole Cost in 2024: What Will You Actually Pay?" 4-ft dia 4–6 ft depth $3,500–$8,000. https://houzdepot.blog/sewer-manhole-cost-2024
<a id="cite27"></a>27. AEP Texas tariff filing PUC Texas Docket 55957 (Dec 2023) — qualified subdivision standard allowance $250/lot. https://interchange.puc.texas.gov/Documents/55957_4_1353955.PDF
<a id="cite28"></a>28. HomeGuide 2026 — "Trenching Cost Per Foot" + "Gas Line Installation Cost" — gas $15–$50+/LF; conduit $5.50–$25/LF. https://homeguide.com/costs/trenching-cost
<a id="cite29"></a>29. Concrete Work Fort Worth 2025 — "Concrete Work Costs in Texas." Sidewalk $6–$12/SF. https://concreteworkfortworthtx.com/concrete-work-costs-texas/
<a id="cite30"></a>30. § 154.33 Street Lighting (Willis TX, equivalent boilerplate to RGV cities) — developer pays full subdivision streetlight cost. https://codelibrary.amlegal.com/codes/willis/latest/willis_tx/0-0-0-12585
<a id="cite31"></a>31. ADN Lite — "How Much Does It Cost to Install a Street Light?" $2,000–$3,000 + $1,000 install. Decorative pole +$2,500–$7,000. https://adnsolarstreetlight.com/blog/how-much-does-it-cost-to-install-a-street-light
<a id="cite32"></a>32. 24hPlans — "Land & Site Development Cost." Engineering 5–15% of construction. https://www.24hplans.com/land-and-site-development-cost/
<a id="cite33"></a>33. City of Edinburg Planning & Zoning — Subdivisions page. https://cityofedinburg.com/departments/planning_and_zoning/subdivisions.php (phone: 956-388-8204)
<a id="cite34"></a>34. McAllen Public Utilities (eCode360) — MPU does not charge impact fees; reimbursement fees only in certified areas. https://ecode360.com/43410607
<a id="cite35"></a>35. HRK Engineering & Field Services 2024 — "What Does a Geotechnical Report Cost in 2024?" Avg $2,700; range $1K–$5K. https://hrkus.com/what-does-a-geotechnical-report-cost-in-2024/
<a id="cite36"></a>36. Soils-Inc — "How Much Does Pre-Construction Soil Testing Cost?" $1K–$15K subdivision. https://soils-inc.com/how-much-does-pre-construction-soil-testing-cost/
<a id="cite37"></a>37. Aegis Environmental 2025 — "Phase I ESA Costs & Best Practices." $1,800–$3,500 typical commercial. https://aegisenvironmentalinc.com/phase-i-environmental-site-assessment-costs/
<a id="cite38"></a>38. CRG Texas Environmental Services 2025 — "How Much Does an Environmental Survey Cost?" TX $2K–$5K Phase I ESA. https://crgtexas.com/2025/03/06/how-much-does-an-environmental-survey-cost-find-out-now/
<a id="cite39"></a>39. Houzeo 2024 — "How Much is Title Insurance Going to Cost You in Texas?" 0.5–1.0% of sale price. https://www.houzeo.com/blog/how-much-is-title-insurance-texas/
<a id="cite40"></a>40. Bankrate — "How Much Are Closing Costs In Texas, And Who Pays?" 2–5% buyer; 6–10% seller. https://www.bankrate.com/real-estate/closing-costs-in-texas/
<a id="cite41"></a>41. Biz2Credit — "Rates on Commercial Real Estate Loans in Texas in 2026." Construction 7.5–9.5%; South TX materials +10–15%. https://www.biz2credit.com/texas/texas-commercial-real-estate-loans-trends
<a id="cite42"></a>42. Terrydale Capital — "Commercial Loan Rate Averages February 2026." Construction average ~7.75%; range 5.50–8.75%. https://terrydalecapital.com/market-updates/commercial-loan-rate-averages-february-2026
<a id="cite43"></a>43. The Edinburg Advocate — "Hidalgo County Adopts $316 Million Budget Without Raising Tax Rate" (Sept 2024). FY 2025 county rate $0.575/$100. https://theedinburgadvocate.com/2024/09/hidalgo-county-adopts-316-million-budget-without-raising-tax-rate/
<a id="cite44"></a>44. Texas Border Business — "Edinburg City Council Approves Balanced Budget for 2024-2025 Fiscal Year." City rate $0.6300/$100, lowest since 1991. https://texasborderbusiness.com/edinburg-city-council-approves-balanced-budget-for-2024-2025-fiscal-year/
<a id="cite45"></a>45. MyRGV/The Monitor (Sept 2024) — "Edinburg approves $164M budget, keeps same tax rate." https://myrgv.com/publications/the-monitor/2024/09/19/edinburg-approves-164m-budget-keeps-same-tax-rate/
<a id="cite46"></a>46. Ownwell — Edinburg, Hidalgo County TX Property Taxes. Combined median effective rate 1.78%. https://www.ownwell.com/trends/texas/hidalgo-county/edinburg
<a id="cite47"></a>47. TxDOT Highway Cost Index Report October 2025 (2012 base) — Index 320.82; 12-mo weighted avg 326.82. +61% from May 2020 to May 2024. https://www.txdot.gov/content/dam/docs/division/cst/hci-binder.pdf
<a id="cite48"></a>48. Texas Border Business — "City moves forward with Tres Lagos development" — $232M private + $151M county = ~$148K/ac public infrastructure benchmark for 2,571-ac master plan. https://texasborderbusiness.com/city-moves-forward-with-tres-lagos-development-2-billion-2600-acre-project-grows-mcallen-north/
<a id="cite49"></a>49. Hidalgo County Subdivision Rules (Effective Oct 2018, 2020 amendments) — model subdivision rules. https://www.hidalgocounty.us/350/Hidalgo-County-Subdivision-Rules
<a id="cite50"></a>50. Tres Lagos TIRZ document (City of McAllen) — public infrastructure financing detail. https://www.mcallen.net/docs/default-source/citymanager/economic-priorities/tres-lagos-tirz.pdf
<a id="cite51"></a>51. NAHB Cost of Constructing a Home 2024 (PDF, Jan 2025) — full survey. https://www.nahb.org/-/media/NAHB/news-and-economics/docs/housing-economics-plus/special-studies/2025/special-study-cost-of-constructing-a-home-2024-january-2025.pdf
<a id="cite52"></a>52. Dallas Water Utilities Average Cost Manual (Sept 2021) — secondary TX municipal water/sewer cost reference. https://dallascityhall.com/departments/waterutilities/DCH%20Documents/pdf/DWU%20Average%20Cost%20Manual%202021.pdf
<a id="cite53"></a>53. Forney TX Item Bid Tabulation (Feb 2024) — secondary TX municipal engineer's estimate reference. https://www.forneytx.gov/AgendaCenter/ViewFile/Item/10228?fileID=18334
<a id="cite54"></a>54. Texas Real Estate Research Center, Texas A&M — research portal. https://trerc.tamu.edu/
<a id="cite55"></a>55. Build McAllen Development Review Guide. https://www.buildmcallen.com/

---

## 11. 250-word summary

**Per-lot consensus horizontal development cost: $41,200/lot (mid case, 27 lots, 2026 dollars, 15% contingency included; horizontal-only, excludes land basis, vertical construction, and 6% sales commission).** Range: $32,000 (low, single-family street classification negotiated, no lift station) to $58,000 (high, full residential collector pavement + lift station + complex HCID release). Total project mid: $1.11M; per-acre $267K. Hard cost is $636K (paving $93K at 40' pavement, water $115K, sanitary $107K, storm + detention $109K, dry utilities $88K, sidewalks $60K, curb $24K, lighting $25K, signage $5K, clearing $10K). Soft cost is $277K (engineering+survey 11% combined, plat/permits/park-fee, GC fee 8%, geotech, drainage study + HCID coord, legal/HOA). Carry $54K (12-mo build, 9% loan rate, $10K/yr property taxes). The build-up is anchored on **TxDOT District 21 Pharr 12-month-average bid prices (Aug 2024)** for ~60% of hard cost, escalated 8% to 2026 via the TxDOT Highway Cost Index (October 2025 = 320.82), with a 35% private-subdivision premium over highway-grade bids. Soft-cost inputs are NAHB 2024 Cost of Constructing a Home, Hutson Land Planners TX guide, and TX-specific environmental/geotech firms. 55+ distinct citations.

**Three biggest sources of uncertainty:** (1) **Pavement-width classification** — Edinburg UDC strict reading requires 40' for multi-family townhomes (used in mid); if classified as single-family lots, drops to 32', saving ~$700/lot. (2) **Lift station risk** — desktop research can't confirm whether gravity sanitary tie reaches an existing trunk; if not, add $200K (+$7,400/lot). (3) **HCID No. 1 abandoned-canal release process** — undocumented online; abandonment paperwork could add $15K–$35K and 60–120 days; if HCID refuses release, the 45' canal ROW becomes a permanent dead zone and reshapes the plat. **Action items before feasibility expires 2026-06-13:** phone-verify Edinburg Planning at (956) 388-8204 (street classification, plat fees, sanitary trunk location), and contact HCID No. 1 at hcid1.com (canal abandonment process, easement release).
