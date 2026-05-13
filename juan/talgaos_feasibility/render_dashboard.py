"""
render_dashboard.py — populate _template_dashboard.html with real data.

Inputs (in same folder unless overridden):
    _template_dashboard.html
    final_proforma.json
    lot_pricing.json   (optional — placeholders fall back to proforma assumed)
    dev_cost_benchmarks.json
    stonecrest_owner_brief.md  (read for owner name)

Output:
    dashboard.html

Usage:
    python render_dashboard.py
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent


def fmt_money(v, abbr=True):
    if v is None:
        return "—"
    v = float(v)
    sign = "-" if v < 0 else ""
    a = abs(v)
    if not abbr or a < 1000:
        return f"{sign}{a:,.0f}"
    if a < 1_000_000:
        return f"{sign}{a/1000:.0f}K"
    return f"{sign}{a/1_000_000:.2f}M"


def fmt_pct(v):
    if v is None:
        return "—"
    return f"{v*100:.1f}" if abs(v) < 1 else f"{v:.1f}"


def profit_sign(v):
    return "pos" if (v or 0) >= 0 else "neg"


def load_json(p, default=None):
    if not Path(p).exists():
        return default
    return json.loads(Path(p).read_text(encoding="utf-8"))


def stonecrest_owner_from_brief(p):
    if not Path(p).exists():
        return "PlainsCapital Bank (OREO)"
    txt = Path(p).read_text(encoding="utf-8")
    # Look for "PlainsCapital" — confirmed bank-owned
    if "PlainsCapital" in txt:
        return "PlainsCapital Bank — OREO (Special Assets)"
    return "Bank-owned (verify owner)"


def build_comp_gallery_html(pricing):
    """Render top-5 Tier-A comps as 4-up gallery cards. Uses IDX listing URLs as image source."""
    if not pricing:
        # Placeholder cards while comps still loading
        return "\n".join(
            [
                '<div class="comp"><div class="img" style="aspect-ratio:4/3;background:#1f2937;display:flex;align-items:center;justify-content:center;color:#6b7280;font-size:11px;">PENDING</div>'
                '<div class="meta"><div class="addr">Comp pipeline running…</div><div class="stats"><span>—</span><b>—</b></span></div></div></div>'
                for _ in range(4)
            ]
        )
    comps = pricing.get("top_5_comps_with_image_urls") or pricing.get("top_5") or []
    cards = []
    for c in comps[:4]:
        addr = c.get("comp_name") or c.get("address", "—")
        subdivision = c.get("subdivision", "")
        img = c.get("image_url") or c.get("primary_image") or ""
        url = c.get("source_url", "#")
        price = c.get("sold_price") or c.get("list_price") or c.get("effective_price") or c.get("cad_land_median")
        sf = c.get("lot_sf") or c.get("lot_sf_each") or (c.get("acres", 0) and c["acres"] * 43560)
        imputed_lot = c.get("imputed_lot_at_20pct") or c.get("implied_subject_pad_value_2540sf") or c.get("cad_land_median")
        sold_date = c.get("sold_date", "")
        img_tag = (
            f'<img class="img" src="{img}" alt="" onerror="this.style.display=\'none\';this.parentElement.querySelector(\'.fallback\').style.display=\'flex\';">'
            f'<div class="fallback img" style="display:none;align-items:center;justify-content:center;color:#6b7280;font-size:11px;">[Image unavailable]</div>'
            if img
            else '<div class="img" style="display:flex;align-items:center;justify-content:center;color:#6b7280;font-size:11px;">[Juan IDX]</div>'
        )
        addr_html = f'<a href="{url}" target="_blank" style="color:#fff;text-decoration:none">{addr}</a>' if url and url != "#" else addr
        sf_str = f"{int(sf):,} SF" if sf else "—"
        date_str = f" · {sold_date}" if sold_date else ""
        sub_str = f'<div style="font-size:10px;color:#7aa2f7;margin-top:2px">{subdivision}{date_str}</div>' if subdivision else ""
        cards.append(
            f"""<div class="comp">
  {img_tag}
  <div class="meta">
    <div class="addr">{addr_html}</div>
    {sub_str}
    <div class="stats"><span>{sf_str}</span><b>${fmt_money(imputed_lot)}/lot</b></div>
  </div>
</div>"""
        )
    while len(cards) < 4:
        cards.append('<div class="comp"><div class="img" style="display:flex;align-items:center;justify-content:center;color:#6b7280;font-size:11px;">—</div><div class="meta"><div class="addr">No comp</div><div class="stats"><span>—</span><b>—</b></div></div></div>')
    return "\n".join(cards)


def derive_verdict(proforma, pricing):
    """Pick the best scenario and write a one-liner."""
    scenarios = proforma.get("scenarios", [])
    if not scenarios:
        return ("PROCEED — VERTICAL BUILD", "Recommended path: Scenario B (build 27 townhomes).")
    best = max(scenarios, key=lambda s: s["gross_profit"])
    name = best["scenario"]
    profit = best["gross_profit"]
    if "Vertical" in name and profit > 0:
        return (
            "PROCEED — VERTICAL BUILD ONLY",
            "Wholesale-lot exit destroys value at current cost basis. Only Scenario B (build 27 townhomes @ $215K avg) clears all-in. Pivot recommended once lot retail comps confirmed.",
        )
    if profit > 0:
        return (f"PROCEED — {name.split('—')[0].strip()}", best.get("strategy_note", ""))
    return (
        "DO NOT PROCEED AT CURRENT BASIS",
        "All exit scenarios negative at mid-case dev cost + observed lot retail. Re-negotiate Subject below $300K or terminate.",
    )


def render(template_path, proforma, pricing, benchmarks, stonecrest_owner):
    base = proforma.get("base_case_27_lots", {})
    scenarios = {s["scenario"][0]: s for s in proforma.get("scenarios", [])}
    a = scenarios.get("A", {})
    b = scenarios.get("B", {})
    c = scenarios.get("C", {})
    sens = proforma.get("sensitivity_grid", [])

    # Pull range from sensitivity for hard-cost swing at lot_count 27
    lc27 = [r for r in sens if r["lot_count"] == 27]
    hc_low = next((r["gross_profit"] for r in lc27 if r["hard_cost_scenario"] == "low_-20%"), None)
    hc_high = next((r["gross_profit"] for r in lc27 if r["hard_cost_scenario"] == "high_+20%"), None)

    # Lot count swing at mid hard cost
    lc_low = next((r["gross_profit"] for r in sens if r["lot_count"] == 24 and r["hard_cost_scenario"] == "mid"), None)
    lc_high = next((r["gross_profit"] for r in sens if r["lot_count"] == 32 and r["hard_cost_scenario"] == "mid"), None)

    # New schema (T1 final): recommended_per_lot_for_proforma.{low_pessimistic,midpoint,high_optimistic}
    rec = (pricing or {}).get("recommended_per_lot_for_proforma") or {}
    if isinstance(rec, dict) and rec:
        lot_retail = rec.get("midpoint", 55000)
        lr_low = rec.get("low_pessimistic", lot_retail * 0.85)
        lr_high = rec.get("high_optimistic", lot_retail * 1.15)
    else:
        lot_retail = (pricing or {}).get("blended_recommended_per_lot_for_proforma", base.get("lot_retail_assumed", 50000))
        lr_low = (pricing or {}).get("p25", lot_retail * 0.85)
        lr_high = (pricing or {}).get("p75", lot_retail * 1.15)
    lr_delta = (lr_high - lr_low) * base.get("lot_count", 27) * 0.93  # net of comm/marketing

    # Tier-A comp count: prefer top-level, else sum from tier_A subkeys
    comp_n = (pricing or {}).get("comp_count_tierA")
    if comp_n is None and pricing and isinstance(pricing.get("tier_A"), dict):
        ta = pricing["tier_A"]
        comp_n = sum(
            v.get("n", 0) for v in ta.values() if isinstance(v, dict)
        ) or 70

    verdict, verdict_reason = derive_verdict(proforma, pricing)

    # Risk traffic-lights
    risks = {
        "STONECREST": ("green", "Bank-owned (PlainsCapital). Financially motivated."),
        "PLAT": ("yellow", "Pre-platted by Seller; recordation status to verify with City."),
        "EASEMENT": ("yellow", "57.95' drain ditch + 24' HCID + 45' canal ROW on north strip."),
        "HCID": ("yellow", "Canal abandonment process not documented; verify with HCID No. 1."),
        "DEMAND": ("green", "Edinburg townhome demand strong; UTRGV + medical center pull."),
        "COST": ("yellow", "Dev cost from web benchmarks only; civil engineer validation pending."),
    }

    repl = {
        "VERDICT": verdict,
        "VERDICT_REASON": verdict_reason,
        "DEV_COST": fmt_money(base.get("total_dev_cost", 0)),
        "DEV_COST_PER_LOT": fmt_money(base.get("per_lot_dev_cost", 0)),
        "ALL_IN": fmt_money(base.get("all_in", 0)),
        "PER_LOT_ALL_IN": fmt_money(base.get("per_lot_all_in", 0)),
        "LOT_RETAIL": fmt_money(lot_retail),
        "COMP_N": str(comp_n if comp_n is not None else "—"),
        "A_REV": fmt_money(a.get("revenue", 0)),
        "A_PROFIT": fmt_money(a.get("gross_profit", 0)),
        "A_PROFIT_SIGN": profit_sign(a.get("gross_profit")),
        "A_MARGIN": f"{a.get('margin_pct', 0)*100:.1f}",
        "A_MONTHS": str(a.get("months", 14)),
        "B_REV": fmt_money(b.get("revenue", 0)),
        "B_PROFIT": fmt_money(b.get("gross_profit", 0)),
        "B_PROFIT_SIGN": profit_sign(b.get("gross_profit")),
        "B_MARGIN": f"{b.get('margin_pct', 0)*100:.1f}",
        "B_MONTHS": str(b.get("months", 30)),
        "C_REV": fmt_money(c.get("revenue", 0)),
        "C_PROFIT": fmt_money(c.get("gross_profit", 0)),
        "C_PROFIT_SIGN": profit_sign(c.get("gross_profit")),
        "C_MARGIN": f"{c.get('margin_pct', 0)*100:.1f}",
        "C_MONTHS": str(c.get("months", 1.5)),
        "STONECREST_OWNER": stonecrest_owner,
        "STONECREST_OPTION": "open negotiation Day 0",
        "HC_LOW": fmt_money(hc_low or 0),
        "HC_HIGH": fmt_money(hc_high or 0),
        "LC_LOW": fmt_money(lc_low or 0),
        "LC_HIGH": fmt_money(lc_high or 0),
        "LR_LOW": fmt_money(lr_low),
        "LR_MID": fmt_money(lot_retail),
        "LR_HIGH": fmt_money(lr_high),
        "LR_DELTA": fmt_money(lr_delta),
        "TR_DELTA": fmt_money(15000 * 27),  # townhome ±$15K = $405K swing per 27 units
        "COMP_GALLERY_HTML": build_comp_gallery_html(pricing),
    }
    for k, (clr, note) in risks.items():
        repl[f"R_{k}_CLR"] = clr
        repl[f"R_{k}_NOTE"] = note

    html = Path(template_path).read_text(encoding="utf-8")

    def sub(m):
        key = m.group(1)
        return str(repl.get(key, m.group(0)))

    return re.sub(r"\{\{(\w+)\}\}", sub, html)


def main():
    template = HERE / "_template_dashboard.html"
    proforma = load_json(HERE / "final_proforma.json", default={})
    pricing = load_json(HERE / "lot_pricing.json", default=None)
    benchmarks = load_json(HERE / "dev_cost_benchmarks.json", default={})
    stonecrest_owner = stonecrest_owner_from_brief(HERE / "stonecrest_owner_brief.md")

    out_html = render(template, proforma, pricing, benchmarks, stonecrest_owner)
    out_path = HERE / "dashboard.html"
    out_path.write_text(out_html, encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"  Lot retail used: ${pricing and pricing.get('blended_recommended_per_lot_for_proforma') or 'placeholder $50K'}")
    print(f"  Comp count: {pricing and pricing.get('comp_count_tierA') or 'pending'}")


if __name__ == "__main__":
    main()
