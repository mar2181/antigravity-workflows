"""
compute_final_proforma.py — Talgaos LLC final all-in proforma + 3 scenarios.

Reads:
    subject.json                   — geometry + parties + dates
    dev_cost_benchmarks.json       — calibrated dev cost totals (from agent T2.1)
    lot_pricing.json (optional)    — retail lot $/lot from comps agent T1.5

Outputs:
    final_proforma.json            — single source of truth (all-in stack + 3 scenarios)
    final_proforma.csv             — line items + totals (Excel-friendly)
    sensitivity_grid.csv           — hard cost ±20% × lot count {24, 27, 28, 32}
    scenarios.csv                  — wholesale, vertical-build, contract-flip
"""

import json
import csv
from pathlib import Path
import argparse


def load(path):
    with open(path) as f:
        return json.load(f)


def compute_carry_extended(loan_amount, loan_rate, months_active, avg_drawn_pct=0.5):
    """Carry interest on the average drawn balance."""
    return loan_amount * avg_drawn_pct * loan_rate * (months_active / 12)


def build_proforma(subject, benchmarks, pricing=None, lot_count=27,
                   per_lot_dev_override=None):
    """Compute final all-in proforma for a given lot count + per-lot dev cost."""
    cal = benchmarks["calibrated_totals_27_lots"]
    sens = benchmarks["lot_count_sensitivity"]

    if per_lot_dev_override is not None:
        per_lot_dev = per_lot_dev_override
        total_dev = per_lot_dev * lot_count
    else:
        # Use calibrated sensitivity table for this lot count
        if str(lot_count) in sens:
            total_dev = sens[str(lot_count)]["total"]
            per_lot_dev = sens[str(lot_count)]["per_lot"]
        else:
            # Linear interpolation as fallback
            per_lot_dev = cal["per_lot_mid"]
            total_dev = per_lot_dev * lot_count

    land_basis = benchmarks["land_basis"]["combined"]

    # Closing costs (Buyer side)
    closing_costs = land_basis * 0.015  # ~1.5% Buyer-side per Texas norm

    # Sales commission and marketing on lot dispositions
    if pricing:
        # New schema (T1 final): recommended_per_lot_for_proforma.midpoint
        rec = pricing.get("recommended_per_lot_for_proforma")
        if isinstance(rec, dict):
            lot_retail = rec.get("midpoint", 55000)
        else:
            # Legacy schema fallback
            lot_retail = pricing.get("blended_recommended_per_lot_for_proforma", 55000)
    else:
        lot_retail = 50000  # placeholder pending T1.5

    gross_revenue = lot_count * lot_retail
    commission = gross_revenue * 0.06
    marketing = gross_revenue * 0.01
    net_revenue = gross_revenue - commission - marketing

    all_in = land_basis + total_dev + closing_costs
    gross_profit = net_revenue - all_in
    gross_margin_pct = gross_profit / net_revenue if net_revenue else 0
    profit_per_lot = gross_profit / lot_count

    # Timeline assumption
    months_total = 12 + 15  # construction + sellout

    return {
        "lot_count": lot_count,
        "land_basis": land_basis,
        "closing_costs": closing_costs,
        "total_dev_cost": total_dev,
        "per_lot_dev_cost": per_lot_dev,
        "all_in": all_in,
        "per_lot_all_in": all_in / lot_count,
        "lot_retail_assumed": lot_retail,
        "gross_revenue": gross_revenue,
        "commission_6pct": commission,
        "marketing_1pct": marketing,
        "net_revenue": net_revenue,
        "gross_profit": gross_profit,
        "gross_margin_pct": gross_margin_pct,
        "profit_per_lot": profit_per_lot,
        "months_total": months_total,
        "annualized_return_pct": (gross_profit / all_in) * (12 / months_total) if all_in else 0,
    }


def build_scenarios(subject, benchmarks, pricing=None):
    """Three exit strategies."""
    base = build_proforma(subject, benchmarks, pricing, lot_count=27)
    lot_retail = base["lot_retail_assumed"]
    land = benchmarks["land_basis"]["combined"]
    dev = base["total_dev_cost"]
    closing = base["closing_costs"]

    scenarios = []

    # A — Wholesale finished lots to a single builder (~70% of retail)
    wholesale_price = lot_retail * 0.70
    rev_a = 27 * wholesale_price
    comm_a = rev_a * 0.04  # bulk commission lower
    profit_a = rev_a - comm_a - (land + dev + closing)
    scenarios.append({
        "scenario": "A — Wholesale finished lots to builder",
        "revenue": rev_a,
        "all_in_cost": land + dev + closing + comm_a,
        "gross_profit": profit_a,
        "margin_pct": profit_a / rev_a if rev_a else 0,
        "months": 14,
        "strategy_note": f"Sell all 27 lots in bulk at ~70% of ${lot_retail:,.0f} = ${wholesale_price:,.0f}/lot",
    })

    # B — Vertical build & sell townhomes (best play if margins work)
    townhome_avg_price = 215000
    cogs_per_unit = 140000  # vertical construction only (lot already platted)
    rev_b = 27 * townhome_avg_price
    cogs_b = 27 * cogs_per_unit
    comm_b = rev_b * 0.05
    marketing_b = rev_b * 0.015
    all_in_b = land + dev + closing + cogs_b + comm_b + marketing_b
    profit_b = rev_b - all_in_b
    scenarios.append({
        "scenario": "B — Vertical build & sell townhomes (recommended)",
        "revenue": rev_b,
        "all_in_cost": all_in_b,
        "gross_profit": profit_b,
        "margin_pct": profit_b / rev_b if rev_b else 0,
        "months": 30,
        "strategy_note": f"Build 27 townhomes @ $140K COGS, sell @ $215K avg",
    })

    # C — Contract flip pre-closing (assignment allowed per ¶22E)
    assignment_fee = 35000
    flip_cost = 5500 + 500  # legal + indep consideration
    profit_c = assignment_fee - flip_cost
    scenarios.append({
        "scenario": "C — Contract flip pre-closing",
        "revenue": assignment_fee,
        "all_in_cost": flip_cost,
        "gross_profit": profit_c,
        "margin_pct": profit_c / assignment_fee,
        "months": 1.5,
        "strategy_note": "Assign contract for $35K (Stonecrest contingency makes assignee hard to find)",
    })
    return scenarios


def build_sensitivity(subject, benchmarks, pricing):
    """3x3 grid: hard cost ±20% × lot count {24, 27, 28, 32}."""
    rows = []
    base = benchmarks["calibrated_totals_27_lots"]["per_lot_mid"]
    for lc in [24, 27, 28, 32]:
        for hm_label, hm in [("low_-20%", 0.80), ("mid", 1.00), ("high_+20%", 1.20)]:
            per_lot = base * hm * (
                benchmarks["lot_count_sensitivity"][str(lc)]["per_lot"]
                / benchmarks["calibrated_totals_27_lots"]["per_lot_mid"]
            )
            r = build_proforma(subject, benchmarks, pricing,
                               lot_count=lc, per_lot_dev_override=per_lot)
            rows.append({
                "lot_count": lc,
                "hard_cost_scenario": hm_label,
                "per_lot_dev": round(per_lot),
                "total_dev": round(per_lot * lc),
                "all_in": round(r["all_in"]),
                "gross_profit": round(r["gross_profit"]),
                "margin_pct": round(r["gross_margin_pct"] * 100, 1),
                "per_lot_all_in": round(r["per_lot_all_in"]),
            })
    return rows


def write_outputs(out_dir, base, scenarios, sensitivity):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Master JSON
    with (out / "final_proforma.json").open("w") as f:
        json.dump({
            "base_case_27_lots": base,
            "scenarios": scenarios,
            "sensitivity_grid": sensitivity,
        }, f, indent=2, default=str)

    # CSV — base case line items
    with (out / "final_proforma.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Category", "Line Item", "Amount USD"])
        w.writerow(["Land", "Subject ($385K) + Stonecrest ($40K cap)", f"${base['land_basis']:,.0f}"])
        w.writerow(["Land", "Closing costs (1.5%)", f"${base['closing_costs']:,.0f}"])
        w.writerow(["Dev", f"Horizontal dev cost ({base['lot_count']} lots × ${base['per_lot_dev_cost']:,.0f}/lot)", f"${base['total_dev_cost']:,.0f}"])
        w.writerow(["", "TOTAL ALL-IN", f"${base['all_in']:,.0f}"])
        w.writerow(["", "PER-LOT ALL-IN", f"${base['per_lot_all_in']:,.0f}"])
        w.writerow([])
        w.writerow(["Revenue (assumption)", f"Lot retail ${base['lot_retail_assumed']:,.0f} × {base['lot_count']}", f"${base['gross_revenue']:,.0f}"])
        w.writerow(["", "Commission (6%)", f"${base['commission_6pct']:,.0f}"])
        w.writerow(["", "Marketing (1%)", f"${base['marketing_1pct']:,.0f}"])
        w.writerow(["", "NET REVENUE", f"${base['net_revenue']:,.0f}"])
        w.writerow([])
        w.writerow(["Result", "Gross profit", f"${base['gross_profit']:,.0f}"])
        w.writerow(["Result", "Gross margin %", f"{base['gross_margin_pct']*100:.1f}%"])
        w.writerow(["Result", "Profit per lot", f"${base['profit_per_lot']:,.0f}"])
        w.writerow(["Result", "Annualized return", f"{base['annualized_return_pct']*100:.1f}%"])

    # CSV — scenarios
    with (out / "scenarios.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(scenarios[0].keys()))
        w.writeheader()
        for row in scenarios:
            w.writerow({k: f"{v:,.2f}" if isinstance(v, float) else v for k, v in row.items()})

    # CSV — sensitivity
    with (out / "sensitivity_grid.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sensitivity[0].keys()))
        w.writeheader()
        for row in sensitivity:
            w.writerow(row)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--subject", required=True)
    p.add_argument("--benchmarks", required=True)
    p.add_argument("--pricing", default=None)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    subject = load(args.subject)
    benchmarks = load(args.benchmarks)
    pricing = load(args.pricing) if args.pricing and Path(args.pricing).exists() else None

    base = build_proforma(subject, benchmarks, pricing, lot_count=27)
    scenarios = build_scenarios(subject, benchmarks, pricing)
    sensitivity = build_sensitivity(subject, benchmarks, pricing)
    write_outputs(args.output_dir, base, scenarios, sensitivity)

    print(f"=== FINAL PRO FORMA — Talgaos LLC ===")
    print(f"Land basis: ${base['land_basis']:,.0f}")
    print(f"Dev cost (27 lots × ${base['per_lot_dev_cost']:,.0f}/lot): ${base['total_dev_cost']:,.0f}")
    print(f"Closing costs (1.5%): ${base['closing_costs']:,.0f}")
    print(f"TOTAL ALL-IN: ${base['all_in']:,.0f}")
    print(f"PER-LOT ALL-IN: ${base['per_lot_all_in']:,.0f}")
    print(f"")
    print(f"Lot retail assumed: ${base['lot_retail_assumed']:,.0f}")
    print(f"Gross revenue: ${base['gross_revenue']:,.0f}")
    print(f"Net revenue: ${base['net_revenue']:,.0f}")
    print(f"GROSS PROFIT: ${base['gross_profit']:,.0f}  ({base['gross_margin_pct']*100:.1f}%)")
    print(f"")
    print(f"=== SCENARIOS ===")
    for s in scenarios:
        print(f"{s['scenario']:<55} profit=${s['gross_profit']:>12,.0f}  margin={s['margin_pct']*100:>5.1f}%  ({s['months']:>4.1f} mo)")
    print(f"")
    print(f"Outputs written to: {args.output_dir}")


if __name__ == "__main__":
    main()
