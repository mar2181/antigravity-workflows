"""
subdivision_proforma.py — Reusable horizontal subdivision pro forma model

Designed for Juan Elizondo (RE/MAX Elite) buyer-side land deals in the RGV.
First use: Talgaos LLC, 000 Rogers Rd Edinburg (4.16 ac, ~27 townhouse lots).

Usage:
    python subdivision_proforma.py \
        --subject path/to/subject.json \
        --benchmarks path/to/dev_cost_benchmarks.json \
        --pricing path/to/lot_pricing.json \
        --output-dir path/to/output/

Outputs:
    - proforma.json           — full structured model (single source of truth)
    - proforma.csv            — line-item breakdown (Excel-friendly)
    - sensitivity.csv         — ±20% hard cost × ±10% lot count grid
    - scenarios.csv           — wholesale / vertical-build / contract-flip
    - proforma_summary.md     — narrative summary
"""

import argparse
import json
from pathlib import Path
import csv
import sys


# ─────────────────────────────────────────────────────────────────────────────
# Defaults — can be overridden by benchmarks JSON. RGV-tuned 2025-2026.
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_BENCHMARKS = {
    # Hard costs — unit costs (RGV residential subdivision, 2025-2026 dollars)
    "clearing_grading_per_acre": 7500,           # $/ac
    "asphalt_pavement_per_sy": 35,                # $/SY (2" surface + 6" base, 26'-wide)
    "concrete_pavement_per_sy": 75,               # $/SY
    "curb_gutter_per_lf": 22,                     # $/LF
    "storm_sewer_per_lf": 95,                     # $/LF for RCP avg
    "storm_inlet_per_ea": 3500,                   # $/EA
    "detention_grading_per_cy": 12,               # $/CY
    "detention_outfall_lump": 25000,              # $/lump structure
    "water_main_per_lf": 55,                      # $/LF for 8" PVC
    "fire_hydrant_per_ea": 5500,                  # $/EA installed
    "water_service_per_lot": 1800,                # $/lot lateral + meter box
    "sewer_main_per_lf": 75,                      # $/LF for 8"
    "sewer_manhole_per_ea": 4500,                 # $/EA
    "sewer_service_per_lot": 1500,                # $/lot lateral
    "dry_utility_per_lot": 3500,                  # $/lot trench + AEP/MVEC coordination
    "sidewalk_per_sf": 7,                         # $/SF for 4' walk
    "street_light_per_ea": 4500,                  # $/EA fixture+conduit
    "signage_striping_per_lot": 350,              # $/lot allocated
    # Soft costs — % or unit
    "engineering_pct_of_hard": 0.10,              # 10% of hard
    "permit_plat_fees_per_lot": 850,              # City of Edinburg fee+building permit
    "geotech_environmental_lump": 18000,          # Phase I + soils
    "drainage_study_lump": 22000,                 # HCID coordination + LOMR if needed
    "construction_management_pct": 0.05,          # 5% of hard
    "contingency_pct": 0.15,                      # 15% (raised from 10% per Mario — no engineer validation)
    "soft_cost_other_pct": 0.04,                  # legal, title, insurance during construction
    # Carry / financing
    "construction_loan_rate_apr": 0.09,           # 9% APR for South TX dev loan
    "loan_to_cost_pct": 0.70,                     # 70% LTC
    "construction_months": 9,
    "sellout_months": 15,                         # avg time to sell all lots
    "property_tax_during_dev_pct": 0.025,         # of land basis annually
    # Sales
    "broker_commission_pct": 0.06,                # 6% on lot sale
    "marketing_pct_of_revenue": 0.01,             # 1% marketing
}


# ─────────────────────────────────────────────────────────────────────────────
def load_inputs(subject_path, benchmarks_path, pricing_path):
    with open(subject_path) as f:
        subject = json.load(f)
    benchmarks = DEFAULT_BENCHMARKS.copy()
    if benchmarks_path and Path(benchmarks_path).exists():
        with open(benchmarks_path) as f:
            benchmarks.update(json.load(f))
    pricing = None
    if pricing_path and Path(pricing_path).exists():
        with open(pricing_path) as f:
            pricing = json.load(f)
    return subject, benchmarks, pricing


# ─────────────────────────────────────────────────────────────────────────────
def compute_hard_costs(subject, b, lot_count_override=None):
    """Build hard-cost line items from plat geometry + unit costs."""
    geo = subject["plat_geometry"]
    combined = subject["combined_project"]

    lot_count = lot_count_override or geo.get("lot_count_total_buildable", 27)
    total_acres = combined["total_acres"]
    row_lf = (
        geo["right_of_way"]["n_turquesa_st_length_lf"]
        + geo["right_of_way"]["e_aqua_st_length_lf"]
    )
    pavement_width_ft = 26  # back-of-curb to back-of-curb for 50' ROW
    pavement_sy = (row_lf * pavement_width_ft) / 9.0
    detention_cy = geo["common_area"]["detention_pond_sf"] * 6.0 / 27.0  # ~6' avg depth
    sidewalk_sf = row_lf * 4.0 * 2  # 4' walks both sides

    items = [
        ("Clearing & grading",        total_acres * b["clearing_grading_per_acre"]),
        ("Asphalt pavement",          pavement_sy * b["asphalt_pavement_per_sy"]),
        ("Curb & gutter",             row_lf * 2 * b["curb_gutter_per_lf"]),  # both sides
        ("Storm sewer",               row_lf * 0.6 * b["storm_sewer_per_lf"]),  # 60% of street
        ("Storm inlets (8 ea)",       8 * b["storm_inlet_per_ea"]),
        ("Detention pond grading",    detention_cy * b["detention_grading_per_cy"]),
        ("Detention outfall",         b["detention_outfall_lump"]),
        ("Water main",                row_lf * b["water_main_per_lf"]),
        ("Fire hydrants (3 ea)",      3 * b["fire_hydrant_per_ea"]),
        ("Water services",            lot_count * b["water_service_per_lot"]),
        ("Sewer main",                row_lf * b["sewer_main_per_lf"]),
        ("Sewer manholes (4 ea)",     4 * b["sewer_manhole_per_ea"]),
        ("Sewer services",            lot_count * b["sewer_service_per_lot"]),
        ("Dry utilities",             lot_count * b["dry_utility_per_lot"]),
        ("Sidewalks",                 sidewalk_sf * b["sidewalk_per_sf"]),
        ("Street lighting (5 ea)",    5 * b["street_light_per_ea"]),
        ("Signage & striping",        lot_count * b["signage_striping_per_lot"]),
    ]
    hard_total = sum(v for _, v in items)
    return items, hard_total


def compute_soft_costs(hard_total, lot_count, b):
    items = [
        ("Engineering & surveying",        hard_total * b["engineering_pct_of_hard"]),
        ("Permit & plat fees",             lot_count * b["permit_plat_fees_per_lot"]),
        ("Geotech / environmental",        b["geotech_environmental_lump"]),
        ("Drainage study (HCID)",          b["drainage_study_lump"]),
        ("Construction management",        hard_total * b["construction_management_pct"]),
        ("Soft cost other (legal/title)",  hard_total * b["soft_cost_other_pct"]),
    ]
    soft_total = sum(v for _, v in items)
    return items, soft_total


def compute_carry(land_basis, hard_plus_soft, b):
    loan_amount = (land_basis + hard_plus_soft) * b["loan_to_cost_pct"]
    months = b["construction_months"] + (b["sellout_months"] / 2)
    interest = loan_amount * b["construction_loan_rate_apr"] * (months / 12)
    prop_tax = land_basis * b["property_tax_during_dev_pct"] * (months / 12)
    return {"loan_interest": interest, "property_tax_during_dev": prop_tax,
            "carry_total": interest + prop_tax}


def compute_proforma(subject, benchmarks, pricing=None, lot_count_override=None,
                     hard_cost_multiplier=1.0):
    b = benchmarks
    lot_count = lot_count_override or subject["plat_geometry"]["lot_count_total_buildable"]
    land_basis = subject["combined_project"]["combined_land_basis"]

    hard_items, hard_total_raw = compute_hard_costs(subject, b, lot_count)
    hard_total = hard_total_raw * hard_cost_multiplier
    contingency = hard_total * b["contingency_pct"]
    hard_with_cont = hard_total + contingency

    soft_items, soft_total = compute_soft_costs(hard_with_cont, lot_count, b)

    dev_cost = hard_with_cont + soft_total
    carry = compute_carry(land_basis, dev_cost, b)
    all_in = land_basis + dev_cost + carry["carry_total"]

    per_lot_dev = dev_cost / lot_count
    per_lot_all_in = all_in / lot_count

    # Revenue
    if pricing:
        lot_price = pricing.get("blended_recommended_per_lot_for_proforma", 35000)
    else:
        lot_price = 35000  # placeholder
    gross_revenue = lot_count * lot_price
    commissions = gross_revenue * b["broker_commission_pct"]
    marketing = gross_revenue * b["marketing_pct_of_revenue"]
    net_revenue = gross_revenue - commissions - marketing

    gross_profit = net_revenue - all_in
    gross_margin_pct = gross_profit / net_revenue if net_revenue else 0
    profit_per_lot = gross_profit / lot_count

    months_total = (b["construction_months"] + b["sellout_months"])
    annualized_return = (gross_profit / all_in) * (12 / months_total) if all_in else 0

    return {
        "lot_count": lot_count,
        "hard_cost_multiplier": hard_cost_multiplier,
        "land_basis": land_basis,
        "hard_costs_raw": hard_total_raw,
        "hard_costs": hard_total,
        "contingency": contingency,
        "soft_costs": soft_total,
        "dev_cost": dev_cost,
        "carry": carry,
        "all_in": all_in,
        "per_lot_dev": per_lot_dev,
        "per_lot_all_in": per_lot_all_in,
        "lot_retail_price": lot_price,
        "gross_revenue": gross_revenue,
        "commissions": commissions,
        "marketing": marketing,
        "net_revenue": net_revenue,
        "gross_profit": gross_profit,
        "gross_margin_pct": gross_margin_pct,
        "profit_per_lot": profit_per_lot,
        "months_total": months_total,
        "annualized_return": annualized_return,
        "_hard_items": hard_items,
        "_soft_items": soft_items,
    }


# ─────────────────────────────────────────────────────────────────────────────
def run_sensitivity(subject, benchmarks, pricing):
    """3x3 grid: hard cost ±20% × lot count {floor, base, ceiling}."""
    base = subject["plat_geometry"]["lot_count_total_buildable"]
    counts = [int(base * 0.9), base, int(base * 1.1)]
    multipliers = [0.8, 1.0, 1.2]
    grid = []
    for lc in counts:
        for hm in multipliers:
            r = compute_proforma(subject, benchmarks, pricing,
                                 lot_count_override=lc, hard_cost_multiplier=hm)
            grid.append({
                "lot_count": lc, "hard_mult": hm,
                "all_in": r["all_in"], "gross_profit": r["gross_profit"],
                "gross_margin_pct": r["gross_margin_pct"],
                "per_lot_all_in": r["per_lot_all_in"],
            })
    return grid


def run_scenarios(subject, benchmarks, pricing):
    """3 exit strategies."""
    base = compute_proforma(subject, benchmarks, pricing)
    scenarios = []

    # Scenario A: Wholesale finished lots to a builder at ~70% of retail
    wholesale_price = pricing.get("blended_recommended_per_lot_for_proforma", 35000) * 0.70 if pricing else 24500
    rev_a = base["lot_count"] * wholesale_price
    profit_a = rev_a - base["all_in"]
    scenarios.append({
        "scenario": "A_wholesale_to_builder", "revenue": rev_a,
        "all_in": base["all_in"], "gross_profit": profit_a,
        "margin_pct": profit_a / rev_a if rev_a else 0,
        "months": 14, "notes": "Sell all 27 lots in bulk to a single builder at ~70% of retail"
    })

    # Scenario B: Vertical build & sell townhomes
    townhome_avg_price = 200000  # placeholder — refine with townhome retail comps
    cogs_per_unit = 130000
    rev_b = base["lot_count"] * townhome_avg_price
    cogs_b = base["lot_count"] * cogs_per_unit
    profit_b = rev_b - cogs_b - base["land_basis"]
    scenarios.append({
        "scenario": "B_vertical_build_sell", "revenue": rev_b,
        "all_in": cogs_b + base["land_basis"], "gross_profit": profit_b,
        "margin_pct": profit_b / rev_b if rev_b else 0,
        "months": 30, "notes": "Build 27 townhomes, sell at $200K avg"
    })

    # Scenario C: Contract flip (assignment) pre-closing
    assignment_fee = 30000
    scenarios.append({
        "scenario": "C_contract_flip", "revenue": assignment_fee,
        "all_in": 5500, "gross_profit": assignment_fee - 5500,
        "margin_pct": 1.0, "months": 1.5,
        "notes": "Assign contract pre-closing for $30K (Stonecrest contingency makes this hard)"
    })

    return scenarios


# ─────────────────────────────────────────────────────────────────────────────
def write_outputs(out_dir, proforma, sensitivity, scenarios):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Full proforma JSON
    with (out / "proforma.json").open("w") as f:
        # Strip private items for cleaner JSON
        clean = {k: v for k, v in proforma.items() if not k.startswith("_")}
        json.dump(clean, f, indent=2, default=str)

    # CSV line items
    with (out / "proforma.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Category", "Line Item", "Amount USD"])
        for name, amt in proforma["_hard_items"]:
            w.writerow(["Hard", name, f"{amt:,.0f}"])
        w.writerow(["Hard", "Contingency", f"{proforma['contingency']:,.0f}"])
        for name, amt in proforma["_soft_items"]:
            w.writerow(["Soft", name, f"{amt:,.0f}"])
        w.writerow(["Carry", "Loan interest", f"{proforma['carry']['loan_interest']:,.0f}"])
        w.writerow(["Carry", "Property tax", f"{proforma['carry']['property_tax_during_dev']:,.0f}"])
        w.writerow(["Land", "Combined land basis", f"{proforma['land_basis']:,.0f}"])
        w.writerow(["", "TOTAL ALL-IN", f"{proforma['all_in']:,.0f}"])
        w.writerow(["", "PER-LOT ALL-IN", f"{proforma['per_lot_all_in']:,.0f}"])

    # Sensitivity
    with (out / "sensitivity.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sensitivity[0].keys()))
        w.writeheader()
        for row in sensitivity:
            w.writerow({k: f"{v:,.2f}" if isinstance(v, float) else v for k, v in row.items()})

    # Scenarios
    with (out / "scenarios.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(scenarios[0].keys()))
        w.writeheader()
        for row in scenarios:
            w.writerow({k: f"{v:,.2f}" if isinstance(v, float) else v for k, v in row.items()})


# ─────────────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--subject", required=True)
    p.add_argument("--benchmarks", default=None)
    p.add_argument("--pricing", default=None)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    subject, benchmarks, pricing = load_inputs(args.subject, args.benchmarks, args.pricing)
    proforma = compute_proforma(subject, benchmarks, pricing)
    sensitivity = run_sensitivity(subject, benchmarks, pricing)
    scenarios = run_scenarios(subject, benchmarks, pricing)
    write_outputs(args.output_dir, proforma, sensitivity, scenarios)

    print(f"All-in: ${proforma['all_in']:,.0f}")
    print(f"Per-lot dev: ${proforma['per_lot_dev']:,.0f}")
    print(f"Per-lot all-in: ${proforma['per_lot_all_in']:,.0f}")
    print(f"Gross profit: ${proforma['gross_profit']:,.0f}")
    print(f"Gross margin: {proforma['gross_margin_pct']*100:.1f}%")
    print(f"Outputs written to: {args.output_dir}")


if __name__ == "__main__":
    main()
