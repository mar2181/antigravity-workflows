#!/usr/bin/env python3
"""
Client Onboarding Orchestrator — Antigravity Digital
=====================================================

One command. URL + business name. Beautiful onboarding report + system integration.

Usage:
    python onboard_client.py --generate-report --data research_bundle.json
    python onboard_client.py --integrate --data research_bundle.json
    python onboard_client.py --full --data research_bundle.json
"""

import json
import os
import sys
import shutil
import argparse
import textwrap
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ONBOARDING_DIR = BASE_DIR / "onboarding_reports"
TEMPLATES_DIR = BASE_DIR / "templates"

# Mission Control paths
MC_PROJECT_CONFIG = Path(
    "C:/Users/mario/Projects/missioncontrol/dashboard/src/lib/project-config.ts"
)
MC_CLIENT_STATUS = Path(
    "C:/Users/mario/Projects/missioncontrol/dashboard/src/lib/client-status-data.ts"
)
CLIENT_CONTACTS = BASE_DIR / "client_contacts.json"
CLIENT_CONSTRAINTS = BASE_DIR / "higgsfield_qc" / "client_constraints.yml"
MASTER_WORKFLOW = BASE_DIR / "MASTER_WORKFLOW.md"
MC_CLIENTS_REF = BASE_DIR / "claudeclaw" / "context" / "_shared" / "clients.md"

# ── Color System (matches Mission Control glassmorphism dark theme) ──────
COLORS = {
    "bg": "#0a0a0f",
    "surface": "rgba(18, 18, 30, 0.85)",
    "surface_raised": "rgba(25, 25, 42, 0.9)",
    "border": "rgba(255, 255, 255, 0.06)",
    "border_active": "rgba(99, 102, 241, 0.35)",
    "text_primary": "#e4e4ec",
    "text_secondary": "#9494a8",
    "text_muted": "#5e5e78",
    "accent": "#6366f1",
    "accent_glow": "rgba(99, 102, 241, 0.25)",
    "success": "#22c55e",
    "success_glow": "rgba(34, 197, 94, 0.2)",
    "warning": "#f59e0b",
    "warning_glow": "rgba(245, 158, 11, 0.2)",
    "danger": "#ef4444",
    "danger_glow": "rgba(239, 68, 68, 0.2)",
    "info": "#3b82f6",
    "info_glow": "rgba(59, 130, 246, 0.2)",
    "purple": "#a855f7",
    "purple_glow": "rgba(168, 85, 247, 0.2)",
    "cyan": "#06b6d4",
    "cyan_glow": "rgba(6, 182, 212, 0.2)",
}


def score_color(score: int) -> str:
    """Return hex color for a 0-100 score."""
    if score >= 80:
        return COLORS["success"]
    elif score >= 60:
        return COLORS["warning"]
    else:
        return COLORS["danger"]


def score_glow(score: int) -> str:
    if score >= 80:
        return COLORS["success_glow"]
    elif score >= 60:
        return COLORS["warning_glow"]
    else:
        return COLORS["danger_glow"]


def score_label(score: int) -> str:
    if score >= 85:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Fair"
    elif score >= 30:
        return "Weak"
    else:
        return "Critical"


# ── HTML Report Template ─────────────────────────────────────────────────
# This is a self-contained, beautiful, dark-themed glassmorphism report.
# No external dependencies. All CSS/JS inline. Print-friendly.


def build_html_report(data: dict) -> str:
    """Build a complete self-contained HTML onboarding report from research JSON."""

    client = data.get("client", {})
    scores = data.get("scores", {})
    executive = data.get("executive_summary", "")
    website = data.get("website_scan", {})
    gbp = data.get("gbp_audit", {})
    competitors = data.get("competitor_intel", {})
    tech_seo = data.get("technical_seo", {})
    ai_vis = data.get("ai_visibility", {})
    social = data.get("social_scan", {})
    backlinks = data.get("backlink_profile", {})
    keywords = data.get("keyword_map", {})
    actions = data.get("prioritized_actions", [])
    plan_90 = data.get("ninety_day_plan", {})

    name = client.get("name", "New Client")
    url = client.get("url", "")
    city = client.get("city", "")
    vertical = client.get("vertical", "")
    onboarded = client.get("onboarded_at", datetime.now(timezone.utc).isoformat())

    overall = scores.get("overall_readiness", 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(name)} — Onboarding Report | Antigravity Digital</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: {COLORS["bg"]};
    --surface: {COLORS["surface"]};
    --surface-raised: {COLORS["surface_raised"]};
    --border: {COLORS["border"]};
    --border-active: {COLORS["border_active"]};
    --text-primary: {COLORS["text_primary"]};
    --text-secondary: {COLORS["text_secondary"]};
    --text-muted: {COLORS["text_muted"]};
    --accent: {COLORS["accent"]};
    --accent-glow: {COLORS["accent_glow"]};
    --success: {COLORS["success"]};
    --warning: {COLORS["warning"]};
    --danger: {COLORS["danger"]};
    --radius: 16px;
    --radius-sm: 10px;
    --radius-xs: 6px;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text-primary);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}

  /* Subtle grid background */
  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(99, 102, 241, 0.015) 1px, transparent 1px),
      linear-gradient(90deg, rgba(99, 102, 241, 0.015) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none;
    z-index: 0;
  }}

  /* Ambient glow orbs */
  body::after {{
    content: '';
    position: fixed;
    top: -30%;
    left: -20%;
    width: 80%;
    height: 80%;
    background: radial-gradient(ellipse, rgba(99, 102, 241, 0.04) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
  }}

  .container {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 32px;
    position: relative;
    z-index: 1;
  }}

  /* ── Header ── */
  .header {{
    padding: 64px 0 48px;
    text-align: center;
    position: relative;
  }}

  .header-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    border-radius: 999px;
    background: var(--surface-raised);
    border: 1px solid var(--border);
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 24px;
    letter-spacing: 0.02em;
  }}

  .header-badge .dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--success);
    box-shadow: 0 0 8px var(--success);
  }}

  .header h1 {{
    font-size: 42px;
    font-weight: 700;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--text-primary) 0%, #a5a5c8 50%, var(--accent) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 12px;
  }}

  .header .url {{
    font-size: 16px;
    color: var(--accent);
    text-decoration: none;
    font-weight: 500;
    transition: opacity 0.2s;
  }}

  .header .url:hover {{ opacity: 0.8; }}

  .header .meta {{
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 16px;
    flex-wrap: wrap;
  }}

  .header .meta span {{
    font-size: 14px;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .header .meta .sep {{
    color: var(--text-muted);
  }}

  /* ── Overall Score ── */
  .overall-score {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 48px;
    padding: 48px 0;
    flex-wrap: wrap;
  }}

  .score-ring {{
    position: relative;
    width: 180px;
    height: 180px;
  }}

  .score-ring svg {{
    transform: rotate(-90deg);
  }}

  .score-ring .value {{
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }}

  .score-ring .value .number {{
    font-size: 56px;
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 1;
  }}

  .score-ring .value .label {{
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}

  .score-breakdown {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }}

  .score-item {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 18px;
    border-radius: var(--radius-xs);
    background: var(--surface);
    border: 1px solid var(--border);
    min-width: 200px;
  }}

  .score-item .domain {{
    flex: 1;
    font-size: 14px;
    color: var(--text-secondary);
  }}

  .score-item .val {{
    font-size: 18px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }}

  .score-item .bar-bg {{
    width: 60px;
    height: 4px;
    border-radius: 2px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
  }}

  .score-item .bar-fill {{
    height: 100%;
    border-radius: 2px;
    transition: width 0.6s ease;
  }}

  /* ── Executive Summary ── */
  .exec-summary {{
    padding: 36px 40px;
    margin: 0 0 48px;
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--border-active);
    position: relative;
    overflow: hidden;
  }}

  .exec-summary::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: var(--accent);
    border-radius: 4px 0 0 4px;
  }}

  .exec-summary h2 {{
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 16px;
    color: var(--text-primary);
    letter-spacing: -0.02em;
  }}

  .exec-summary p {{
    font-size: 16px;
    color: var(--text-secondary);
    line-height: 1.8;
  }}

  /* ── Section Cards ── */
  .section {{
    margin-bottom: 32px;
  }}

  .section-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }}

  .section-header .icon {{
    width: 40px;
    height: 40px;
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  }}

  .section-header h3 {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.02em;
  }}

  .section-header .badge {{
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }}

  .card {{
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--border);
    overflow: hidden;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
  }}

  .card-body {{
    padding: 28px 32px;
  }}

  .card-body h4 {{
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 20px 0 10px;
    letter-spacing: -0.01em;
  }}

  .card-body h4:first-child {{
    margin-top: 0;
  }}

  .card-body p, .card-body li {{
    font-size: 14.5px;
    color: var(--text-secondary);
    line-height: 1.7;
  }}

  .card-body ul {{
    list-style: none;
    padding: 0;
  }}

  .card-body ul li {{
    padding: 6px 0 6px 20px;
    position: relative;
  }}

  .card-body ul li::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 13px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    opacity: 0.5;
  }}

  /* ── Stat Grid ── */
  .stat-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }}

  .stat-card {{
    padding: 20px;
    border-radius: var(--radius-sm);
    background: var(--surface-raised);
    border: 1px solid var(--border);
    text-align: center;
  }}

  .stat-card .stat-value {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1;
  }}

  .stat-card .stat-label {{
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }}

  /* ── Competitor Table ── */
  .comp-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }}

  .comp-table th {{
    text-align: left;
    padding: 12px 16px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid var(--border);
  }}

  .comp-table td {{
    padding: 14px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    color: var(--text-secondary);
  }}

  .comp-table tr:last-child td {{
    border-bottom: none;
  }}

  .comp-table .rank {{
    font-weight: 700;
    font-size: 16px;
    color: var(--text-primary);
  }}

  .comp-table .rank-1 {{ color: #fbbf24; }}
  .comp-table .rank-2 {{ color: #94a3b8; }}
  .comp-table .rank-3 {{ color: #cd7b47; }}

  /* ── Action Items ── */
  .action-list {{
    list-style: none;
    padding: 0;
  }}

  .action-item {{
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 16px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }}

  .action-item:last-child {{
    border-bottom: none;
  }}

  .action-rank {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    flex-shrink: 0;
    background: var(--surface-raised);
    border: 1px solid var(--border);
  }}

  .action-rank.p1 {{ border-color: var(--danger); color: var(--danger); }}
  .action-rank.p2 {{ border-color: var(--warning); color: var(--warning); }}
  .action-rank.p3 {{ border-color: var(--accent); color: var(--accent); }}

  .action-content h4 {{
    font-size: 15px;
    font-weight: 600;
    margin: 0 0 4px;
  }}

  .action-content p {{
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
  }}

  .action-tags {{
    display: flex;
    gap: 8px;
    margin-top: 6px;
    flex-wrap: wrap;
  }}

  .tag {{
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.02em;
  }}

  .tag-impact-high {{ background: {COLORS["danger_glow"]}; color: var(--danger); }}
  .tag-impact-medium {{ background: {COLORS["warning_glow"]}; color: var(--warning); }}
  .tag-impact-low {{ background: {COLORS["info_glow"]}; color: var(--info); }}

  /* ── 90-Day Plan ── */
  .timeline {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }}

  .timeline-month {{
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 28px;
    position: relative;
    overflow: hidden;
  }}

  .timeline-month::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
  }}

  .timeline-month.m1::before {{ background: var(--accent); }}
  .timeline-month.m2::before {{ background: var(--purple); }}
  .timeline-month.m3::before {{ background: var(--success); }}

  .timeline-month h4 {{
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 6px;
    letter-spacing: -0.02em;
  }}

  .timeline-month .month-label {{
    font-size: 12px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 20px;
  }}

  .timeline-month ul {{
    list-style: none;
    padding: 0;
  }}

  .timeline-month ul li {{
    padding: 8px 0 8px 18px;
    position: relative;
    font-size: 13.5px;
    color: var(--text-secondary);
    border-bottom: 1px solid rgba(255,255,255,0.03);
  }}

  .timeline-month ul li::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 14px;
    width: 5px;
    height: 5px;
    border-radius: 50%;
  }}

  .timeline-month.m1 ul li::before {{ background: var(--accent); }}
  .timeline-month.m2 ul li::before {{ background: var(--purple); }}
  .timeline-month.m3 ul li::before {{ background: var(--success); }}

  /* ── Findings Grid ── */
  .findings-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin-top: 20px;
  }}

  .finding {{
    padding: 16px 20px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    font-size: 13.5px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }}

  .finding .indicator {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 5px;
    flex-shrink: 0;
  }}

  .finding.pass {{ background: rgba(34,197,94,0.06); border-color: rgba(34,197,94,0.15); }}
  .finding.pass .indicator {{ background: var(--success); box-shadow: 0 0 6px var(--success); }}

  .finding.warn {{ background: rgba(245,158,11,0.06); border-color: rgba(245,158,11,0.15); }}
  .finding.warn .indicator {{ background: var(--warning); box-shadow: 0 0 6px var(--warning); }}

  .finding.fail {{ background: rgba(239,68,68,0.06); border-color: rgba(239,68,68,0.15); }}
  .finding.fail .indicator {{ background: var(--danger); box-shadow: 0 0 6px var(--danger); }}

  .finding .finding-text strong {{
    display: block;
    color: var(--text-primary);
    margin-bottom: 3px;
  }}

  .finding .finding-text span {{
    color: var(--text-muted);
    font-size: 12px;
  }}

  /* ── Footer ── */
  .footer {{
    text-align: center;
    padding: 64px 0 48px;
    color: var(--text-muted);
    font-size: 13px;
    border-top: 1px solid var(--border);
    margin-top: 48px;
  }}

  .footer .brand {{
    font-weight: 700;
    color: var(--text-secondary);
    letter-spacing: -0.01em;
  }}

  .footer .brand span {{
    color: var(--accent);
  }}

  /* ── Print Styles ── */
  @media print {{
    body {{ background: #fff; color: #111; }}
    body::before, body::after {{ display: none; }}
    .card, .exec-summary, .timeline-month, .stat-card, .finding, .score-item {{
      background: #fff;
      border: 1px solid #ddd;
      box-shadow: none;
      backdrop-filter: none;
    }}
    .header h1 {{ -webkit-text-fill-color: #111; }}
    .section-header h3, .exec-summary h2 {{ color: #111; }}
    .card-body p, .card-body li, .score-item .domain {{ color: #444; }}
    .stat-card .stat-label, .header .meta span {{ color: #666; }}
    .timeline-month.m1::before, .timeline-month.m2::before, .timeline-month.m3::before {{
      background: #333;
    }}
    .container {{ max-width: 100%; }}
  }}

  /* ── Responsive ── */
  @media (max-width: 768px) {{
    .container {{ padding: 0 20px; }}
    .header h1 {{ font-size: 28px; }}
    .overall-score {{ flex-direction: column; gap: 32px; }}
    .score-breakdown {{ grid-template-columns: 1fr; }}
    .timeline {{ grid-template-columns: 1fr; }}
    .stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .comp-table {{ font-size: 12px; }}
    .comp-table th, .comp-table td {{ padding: 8px 10px; }}
  }}
</style>
</head>
<body>

<div class="container">

  <!-- Header -->
  <header class="header">
    <div class="header-badge">
      <span class="dot"></span> Onboarding Report &middot; {escape_html(onboarded[:10])}
    </div>
    <h1>{escape_html(name)}</h1>
    {f'<a href="{escape_html(url)}" class="url" target="_blank" rel="noopener">{escape_html(url)}</a>' if url else ''}
    <div class="meta">
      <span>&#9673; {escape_html(vertical)}</span>
      <span class="sep">&middot;</span>
      <span>&#9961; {escape_html(city)}</span>
      <span class="sep">&middot;</span>
      <span>Antigravity Digital</span>
    </div>
  </header>

  <!-- Overall Score -->
  <div class="overall-score">
    <div class="score-ring">
      <svg width="180" height="180" viewBox="0 0 180 180">
        <circle cx="90" cy="90" r="80" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="10"/>
        <circle cx="90" cy="90" r="80" fill="none"
          stroke="{score_color(overall)}"
          stroke-width="10"
          stroke-linecap="round"
          stroke-dasharray="{overall * 5.0265} 502.65"
          style="filter: drop-shadow(0 0 12px {score_glow(overall)});"/>
      </svg>
      <div class="value">
        <span class="number" style="color:{score_color(overall)}">{overall}</span>
        <span class="label">{score_label(overall)}</span>
      </div>
    </div>
    <div class="score-breakdown">
      {build_score_items(scores)}
    </div>
  </div>

  <!-- Executive Summary -->
  <div class="exec-summary">
    <h2>Executive Summary</h2>
    <p>{escape_html(executive) if executive else 'No executive summary provided.'}</p>
  </div>

  <!-- Website Scan -->
  {build_website_section(website)}

  <!-- GBP Audit -->
  {build_gbp_section(gbp)}

  <!-- Competitor Intelligence -->
  {build_competitor_section(competitors)}

  <!-- Technical SEO -->
  {build_tech_seo_section(tech_seo)}

  <!-- AI Visibility -->
  {build_ai_section(ai_vis)}

  <!-- Social Media -->
  {build_social_section(social)}

  <!-- Backlink Profile -->
  {build_backlink_section(backlinks)}

  <!-- Keyword Map -->
  {build_keyword_section(keywords)}

  <!-- Prioritized Actions -->
  {build_actions_section(actions)}

  <!-- 90-Day Plan -->
  {build_plan_section(plan_90)}

  <!-- Footer -->
  <footer class="footer">
    <div class="brand">Antigravity<span>Digital</span></div>
    <div style="margin-top:8px;">Generated {escape_html(onboarded[:19])} &middot; Onboarding Orchestrator v1.0</div>
    <div style="margin-top:4px;">Confidential — Prepared for {escape_html(name)}</div>
  </footer>

</div>

</body>
</html>"""


# ── HTML Section Builders ────────────────────────────────────────────────


def build_score_items(scores: dict) -> str:
    domains = [
        ("website_quality", "Website Quality"),
        ("gbp_completeness", "GBP Completeness"),
        ("technical_seo", "Technical SEO"),
        ("ai_visibility", "AI Visibility"),
        ("social_presence", "Social Presence"),
        ("backlink_strength", "Backlink Strength"),
        ("keyword_coverage", "Keyword Coverage"),
    ]
    items = []
    for key, label in domains:
        val = scores.get(key, 0)
        items.append(
            f"""<div class="score-item">
          <span class="domain">{label}</span>
          <div class="bar-bg"><div class="bar-fill" style="width:{val}%;background:{score_color(val)};box-shadow:0 0 8px {score_glow(val)};"></div></div>
          <span class="val" style="color:{score_color(val)}">{val}</span>
        </div>"""
        )
    return "\n".join(items)


def build_website_section(data: dict) -> str:
    if not data:
        return ""
    summary = data.get("business_summary", data.get("summary", ""))
    services = data.get("services", data.get("services_offered", []))
    trust = data.get("trust_signals", [])
    content = data.get("content_audit", {})
    contact = data.get("contact_info", {})
    brand = data.get("brand_voice", "")

    rows = []
    if summary:
        rows.append(f"<p>{escape_html(str(summary))}</p>")

    if services:
        if isinstance(services, list):
            rows.append(
                "<h4>Services Offered</h4><ul>"
                + "".join(f"<li>{escape_html(str(s))}</li>" for s in services)
                + "</ul>"
            )
        else:
            rows.append(f"<h4>Services</h4><p>{escape_html(str(services))}</p>")

    if brand:
        rows.append(
            f"<h4>Brand Voice</h4><p>{escape_html(str(brand))}</p>"
        )

    if trust:
        if isinstance(trust, list):
            rows.append(
                "<h4>Trust Signals</h4><ul>"
                + "".join(f"<li>{escape_html(str(t))}</li>" for t in trust)
                + "</ul>"
            )
        else:
            rows.append(f"<h4>Trust Signals</h4><p>{escape_html(str(trust))}</p>")

    if contact:
        rows.append("<h4>Contact Information</h4><ul>")
        for k, v in contact.items():
            rows.append(f"<li><strong>{escape_html(str(k))}:</strong> {escape_html(str(v))}</li>")
        rows.append("</ul>")

    if content:
        rows.append("<h4>Content Audit</h4>")
        if isinstance(content, dict):
            for k, v in content.items():
                rows.append(
                    f"<p><strong>{escape_html(str(k))}:</strong> {escape_html(str(v))}</p>"
                )
        else:
            rows.append(f"<p>{escape_html(str(content))}</p>")

    if not rows:
        return ""

    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(99,102,241,0.12);">&#127760;</div>
      <h3>Website Deep Scan</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_gbp_section(data: dict) -> str:
    if not data:
        return ""
    rows = []

    identity = data.get("identity", data.get("gbp_identity", {}))
    if identity:
        rows.append("<h4>GBP Identity</h4><ul>")
        for k, v in identity.items():
            rows.append(f"<li><strong>{escape_html(str(k))}:</strong> {escape_html(str(v))}</li>")
        rows.append("</ul>")

    review = data.get("review_audit", data.get("reviews", {}))
    if review:
        rows.append("<h4>Review Audit</h4><ul>")
        if isinstance(review, dict):
            for k, v in review.items():
                rows.append(f"<li><strong>{escape_html(str(k))}:</strong> {escape_html(str(v))}</li>")
        else:
            rows.append(f"<li>{escape_html(str(review))}</li>")
        rows.append("</ul>")

    completeness = data.get("completeness_score", data.get("completeness", None))
    if completeness is not None:
        rows.append(f"<h4>Completeness Score</h4><p>{escape_html(str(completeness))}</p>")

    nap = data.get("nap_consistency", "")
    if nap:
        rows.append(f"<h4>NAP Consistency</h4><p>{escape_html(str(nap))}</p>")

    issues = data.get("issues_found", data.get("issues", []))
    if issues:
        if isinstance(issues, list):
            rows.append(
                "<h4>Issues Found</h4><ul>"
                + "".join(f"<li>{escape_html(str(i))}</li>" for i in issues)
                + "</ul>"
            )
        else:
            rows.append(f"<h4>Issues Found</h4><p>{escape_html(str(issues))}</p>")

    if not rows:
        return ""

    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(34,197,94,0.12);">&#127969;</div>
      <h3>Google Business Profile Audit</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_competitor_section(data: dict) -> str:
    if not data:
        return ""
    competitors_list = data.get("competitors", data.get("top_competitors", []))
    matrix = data.get("matrix", data.get("competitive_matrix", ""))
    attack = data.get("attack_vectors", data.get("opportunities", []))

    rows = []

    if competitors_list:
        rows.append("""<table class="comp-table">
          <thead><tr><th>#</th><th>Business</th><th>Rating</th><th>Reviews</th><th>Strengths</th><th>Weaknesses</th></tr></thead>
          <tbody>""")
        for i, comp in enumerate(competitors_list):
            if isinstance(comp, dict):
                name = comp.get("name", comp.get("business_name", "Unknown"))
                rating = comp.get("rating", comp.get("gbp_rating", "—"))
                reviews = comp.get("reviews", comp.get("review_count", "—"))
                strengths = comp.get("strengths", comp.get("key_strengths", "—"))
                weaknesses = comp.get("weaknesses", comp.get("key_weaknesses", "—"))
                rank_class = f"rank-{i+1}" if i < 3 else ""
                rows.append(
                    f"""<tr>
              <td class="rank {rank_class}">{i+1}</td>
              <td><strong>{escape_html(str(name))}</strong></td>
              <td>{escape_html(str(rating))}</td>
              <td>{escape_html(str(reviews))}</td>
              <td>{escape_html(str(strengths))}</td>
              <td>{escape_html(str(weaknesses))}</td>
            </tr>"""
                )
        rows.append("</tbody></table>")

    if matrix:
        rows.append(f"<h4>Competitive Matrix</h4><p>{escape_html(str(matrix))}</p>")

    if attack:
        rows.append("<h4>Attack Vectors</h4><ul>")
        for v in attack:
            rows.append(f"<li>{escape_html(str(v))}</li>")
        rows.append("</ul>")

    if not rows:
        return ""

    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(239,68,68,0.12);">&#9878;</div>
      <h3>Competitor Intelligence</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_tech_seo_section(data: dict) -> str:
    if not data:
        return ""
    findings = data.get("findings", data.get("checks", []))
    summary = data.get("summary", data.get("scorecard_summary", ""))

    rows = []
    if summary:
        rows.append(f"<p>{escape_html(str(summary))}</p>")

    if findings:
        rows.append('<div class="findings-grid">')
        for f in findings:
            if isinstance(f, dict):
                check = f.get("check", f.get("name", ""))
                status = str(f.get("status", f.get("result", "warn"))).lower()
                detail = f.get("detail", f.get("note", ""))
                cls = "pass" if status in ("pass", "passed", "ok", "yes", "true") else (
                    "fail" if status in ("fail", "failed", "missing", "no", "false") else "warn"
                )
                rows.append(
                    f"""<div class="finding {cls}">
              <div class="indicator"></div>
              <div class="finding-text">
                <strong>{escape_html(str(check))}</strong>
                <span>{escape_html(str(detail))}</span>
              </div>
            </div>"""
                )
        rows.append("</div>")

    if not rows:
        return ""

    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(59,130,246,0.12);">&#9881;</div>
      <h3>Technical SEO Sweep</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_ai_section(data: dict) -> str:
    if not data:
        return ""
    presence = data.get("presence", data.get("platform_presence", {}))
    entity = data.get("entity_strength", data.get("entity_score", ""))
    recs = data.get("recommendations", [])

    rows = []
    if presence:
        rows.append("<h4>Platform Presence</h4><ul>")
        if isinstance(presence, dict):
            for platform, status_val in presence.items():
                rows.append(
                    f"<li><strong>{escape_html(str(platform))}:</strong> {escape_html(str(status_val))}</li>"
                )
        else:
            rows.append(f"<li>{escape_html(str(presence))}</li>")
        rows.append("</ul>")

    if entity:
        rows.append(f"<h4>Entity Strength</h4><p>{escape_html(str(entity))}</p>")

    if recs:
        rows.append("<h4>Recommendations</h4><ul>")
        for r in recs:
            rows.append(f"<li>{escape_html(str(r))}</li>")
        rows.append("</ul>")

    if not rows:
        return ""

    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(168,85,247,0.12);">&#10025;</div>
      <h3>AI Visibility Assessment</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_social_section(data: dict) -> str:
    if not data:
        return ""
    platforms = data.get("platforms", data.get("presence_map", {}))
    quality = data.get("content_quality", data.get("quality_score", ""))
    recs = data.get("recommendations", [])

    rows = []
    if platforms:
        rows.append("<h4>Social Presence</h4><ul>")
        if isinstance(platforms, dict):
            for platform, detail in platforms.items():
                rows.append(
                    f"<li><strong>{escape_html(str(platform))}:</strong> {escape_html(str(detail))}</li>"
                )
        else:
            rows.append(f"<li>{escape_html(str(platforms))}</li>")
        rows.append("</ul>")

    if quality:
        rows.append(f"<h4>Content Quality</h4><p>{escape_html(str(quality))}</p>")

    if recs:
        rows.append("<h4>Recommendations</h4><ul>")
        for r in recs:
            rows.append(f"<li>{escape_html(str(r))}</li>")
        rows.append("</ul>")

    if not rows:
        return ""

    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(6,182,212,0.12);">&#128247;</div>
      <h3>Social Media Scan</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_backlink_section(data: dict) -> str:
    if not data:
        return ""
    authority = data.get("domain_authority", data.get("authority_estimate", ""))
    top_domains = data.get("top_referring_domains", data.get("top_domains", []))
    toxic = data.get("toxic_flags", data.get("toxic_links", []))
    gap = data.get("gap_analysis", data.get("competitor_gap", ""))

    rows = []
    if authority:
        rows.append(f"<h4>Domain Authority</h4><p>{escape_html(str(authority))}</p>")

    if top_domains:
        rows.append("<h4>Top Referring Domains</h4><ul>")
        for d in top_domains:
            rows.append(f"<li>{escape_html(str(d))}</li>")
        rows.append("</ul>")

    if toxic:
        rows.append("<h4>Toxic Link Flags</h4><ul>")
        for t in toxic:
            rows.append(f"<li>{escape_html(str(t))}</li>")
        rows.append("</ul>")

    if gap:
        rows.append(f"<h4>Competitor Gap Analysis</h4><p>{escape_html(str(gap))}</p>")

    if not rows:
        return ""

    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(245,158,11,0.12);">&#128279;</div>
      <h3>Backlink Profile</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_keyword_section(data: dict) -> str:
    if not data:
        return ""
    top_kws = data.get("top_keywords", data.get("target_keywords", []))
    clusters = data.get("clusters", data.get("keyword_clusters", {}))
    opportunities = data.get("opportunities", data.get("low_hanging_fruit", []))

    rows = []
    if top_kws:
        rows.append("<h4>Top Keyword Opportunities</h4><ul>")
        for kw in top_kws[:20]:
            if isinstance(kw, dict):
                kw_name = kw.get("keyword", kw.get("query", kw.get("term", "")))
                kw_vol = kw.get("volume", kw.get("search_volume", ""))
                kw_diff = kw.get("difficulty", kw.get("competition", ""))
                rows.append(
                    f"<li><strong>{escape_html(str(kw_name))}</strong> — Vol: {escape_html(str(kw_vol))}, Difficulty: {escape_html(str(kw_diff))}</li>"
                )
            else:
                rows.append(f"<li>{escape_html(str(kw))}</li>")
        rows.append("</ul>")

    if clusters:
        rows.append("<h4>Keyword Clusters</h4>")
        if isinstance(clusters, dict):
            for cluster_name, cluster_kws in clusters.items():
                kws_str = (
                    ", ".join(str(k) for k in cluster_kws)
                    if isinstance(cluster_kws, list)
                    else str(cluster_kws)
                )
                rows.append(
                    f"<p><strong>{escape_html(str(cluster_name))}:</strong> {escape_html(kws_str)}</p>"
                )

    if opportunities:
        rows.append("<h4>Low-Hanging Fruit</h4><ul>")
        for o in opportunities:
            rows.append(f"<li>{escape_html(str(o))}</li>")
        rows.append("</ul>")

    if not rows:
        return ""

    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(34,197,94,0.12);">&#128270;</div>
      <h3>Keyword Opportunity Map</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_actions_section(actions: list) -> str:
    if not actions:
        return ""
    rows = ['<ul class="action-list">']
    for i, a in enumerate(actions[:15]):
        if isinstance(a, dict):
            rank = a.get("rank", i + 1)
            action_text = a.get("action", a.get("description", ""))
            impact = str(a.get("impact", "medium")).lower()
            effort = a.get("effort", a.get("estimated_effort", ""))
            domain = a.get("domain", "")
            rank_cls = "p1" if rank <= 3 else ("p2" if rank <= 6 else "p3")
            rows.append(
                f"""<li class="action-item">
          <div class="action-rank {rank_cls}">{rank}</div>
          <div class="action-content">
            <h4>{escape_html(str(action_text))}</h4>
            <p>{escape_html(str(domain))} &middot; Est. effort: {escape_html(str(effort))}</p>
            <div class="action-tags">
              <span class="tag tag-impact-{impact}">{impact.upper()} IMPACT</span>
            </div>
          </div>
        </li>"""
            )
    rows.append("</ul>")
    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(239,68,68,0.12);">&#9878;</div>
      <h3>Prioritized Action Items</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


def build_plan_section(plan: dict) -> str:
    if not plan:
        return ""
    months = [
        ("m1", "Month 1", plan.get("month_1", plan.get("month1", []))),
        ("m2", "Month 2", plan.get("month_2", plan.get("month2", []))),
        ("m3", "Month 3", plan.get("month_3", plan.get("month3", []))),
    ]
    rows = ['<div class="timeline">']
    for cls, label, items in months:
        rows.append(f'<div class="timeline-month {cls}">')
        rows.append(f"<h4>{label}</h4>")
        rows.append(f'<div class="month-label">Focus Phase</div>')
        if items:
            rows.append("<ul>")
            for item in items:
                rows.append(f"<li>{escape_html(str(item))}</li>")
            rows.append("</ul>")
        rows.append("</div>")
    rows.append("</div>")
    return f"""
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background:rgba(99,102,241,0.12);">&#128197;</div>
      <h3>90-Day Acceleration Plan</h3>
    </div>
    <div class="card">
      <div class="card-body">
        {"".join(rows)}
      </div>
    </div>
  </div>"""


# ── HTML Escape ──────────────────────────────────────────────────────────


def escape_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ── Report Generator ─────────────────────────────────────────────────────


def generate_report(json_path: str, output_path: str | None = None) -> str:
    """Read research JSON, generate beautiful HTML report."""

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = build_html_report(data)

    if output_path is None:
        client_key = _slugify(data.get("client", {}).get("name", "new_client"))
        output_dir = ONBOARDING_DIR / client_key
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / "onboarding_report.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Also write the research bundle to the same directory for reference
    bundle_dir = Path(output_path).parent
    bundle_path = bundle_dir / "research_bundle.json"
    if not bundle_path.exists():
        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  Report generated: {output_path}")
    print(f"  Research bundle:  {bundle_path}")
    return output_path


# ── System Integration ───────────────────────────────────────────────────


def integrate_client(json_path: str) -> dict:
    """Read research JSON and update all config files for the new client."""

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    client = data.get("client", {})
    name = client.get("name", "")
    url = client.get("url", "")
    city = client.get("city", "")
    vertical = client.get("vertical", "")
    client_key = _slugify(name)

    results = {}

    # 1. Update client_contacts.json
    results["contacts"] = _update_client_contacts(client_key, name)
    # 2. Update project-config.ts
    results["project_config"] = _update_project_config(client_key, name, url, city, vertical)
    # 3. Update client_constraints.yml
    results["constraints"] = _update_client_constraints(client_key, name, vertical)
    # 4. Generate program.md
    results["program_md"] = _generate_program_md(client_key, name, url, city, vertical, data)
    # 5. Create integration log
    results["integration_log"] = _write_integration_log(client_key, name, results)

    return results


def _slugify(name: str) -> str:
    """Convert business name to client key."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    return slug


def _update_client_contacts(key: str, name: str) -> str:
    """Add client to client_contacts.json."""
    contacts_path = CLIENT_CONTACTS
    if contacts_path.exists():
        with open(contacts_path, "r", encoding="utf-8") as f:
            contacts = json.load(f)
    else:
        contacts = {}

    if key not in contacts:
        contacts[key] = {"client_name": name, "email": None, "cc": None}
        with open(contacts_path, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2, ensure_ascii=False)
        return f"Added '{key}' to client_contacts.json"
    return f"'{key}' already in client_contacts.json"


def _update_project_config(key: str, name: str, url: str, city: str, vertical: str) -> str:
    """Add client entry to Mission Control project-config.ts."""
    if not MC_PROJECT_CONFIG.exists():
        return f"MISSING: {MC_PROJECT_CONFIG} — add client manually"

    content = MC_PROJECT_CONFIG.read_text(encoding="utf-8")

    hostname = ""
    if url:
        hostname = re.sub(r"https?://(www\.)?", "", url).rstrip("/")

    if key in content or (hostname and hostname in content):
        return f"'{key}' already appears in project-config.ts"

    # Find the closing of the CLIENT_PROJECTS array
    # Look for the last '};' before 'export' or end of file
    array_end = content.rfind("];")
    if array_end == -1:
        return "Could not find CLIENT_PROJECTS array closing — add manually"

    # Build the new entry matching the existing format
    new_entry = f"""  {{
    hostname: "{hostname}",
    projectId: 0,
    label: "{name}",
    industry: "{vertical}",
    clientDbId: "",
    pythonKey: "{key}",
    hasFacebook: false,
    hasGbp: false,
  }},
"""

    new_content = content[:array_end] + new_entry + content[array_end:]
    MC_PROJECT_CONFIG.write_text(new_content, encoding="utf-8")
    return f"Added '{key}' to project-config.ts (hostname: {hostname})"


def _update_client_constraints(key: str, name: str, vertical: str) -> str:
    """Add client entry to client_constraints.yml."""
    constraints_path = CLIENT_CONSTRAINTS
    if not constraints_path.exists():
        return f"MISSING: {constraints_path} — add client manually"

    content = constraints_path.read_text(encoding="utf-8")

    if key in content:
        return f"'{key}' already in client_constraints.yml"

    new_entry = f"""
{key}:
  label: "{name}"
  vertical: "{vertical}"
  forbidden_contexts: []
  forbidden_vehicles: []
  motion_requirements: "static"
  negative_clause: ""
  required_alternative: ""
  notes: "Auto-generated by onboarding orchestrator. Review and customize."
"""
    with open(constraints_path, "a", encoding="utf-8") as f:
        f.write(new_entry)
    return f"Added '{key}' to client_constraints.yml"


def _generate_program_md(
    key: str, name: str, url: str, city: str, vertical: str, data: dict
) -> str:
    """Generate a program.md steering document from research data."""
    output_dir = BASE_DIR / key
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "program.md"

    website = data.get("website_scan", {})
    gbp = data.get("gbp_audit", {})
    competitors = data.get("competitor_intel", {})
    summary = data.get("executive_summary", "")
    scores = data.get("scores", {})

    services = website.get("services", website.get("services_offered", []))
    if isinstance(services, list):
        services_str = "\n".join(f"  - {s}" for s in services)
    else:
        services_str = f"  - {services}"

    comp_list = competitors.get("competitors", competitors.get("top_competitors", []))
    comp_str = ""
    for c in comp_list[:5]:
        if isinstance(c, dict):
            comp_str += f"\n  - **{c.get('name', c.get('business_name', ''))}** — {c.get('strengths', c.get('key_strengths', ''))}"

    content = f"""# {name} — Program

> Auto-generated by Onboarding Orchestrator
> Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
> Key: `{key}`

---

## Overview

- **Website:** {url}
- **City:** {city}
- **Vertical:** {vertical}
- **Client Key:** `{key}`

## Executive Summary

{summary}

## Readiness Scores

| Domain | Score |
|---|---|
| Overall Readiness | {scores.get('overall_readiness', '—')}/100 |
| Website Quality | {scores.get('website_quality', '—')}/100 |
| GBP Completeness | {scores.get('gbp_completeness', '—')}/100 |
| Technical SEO | {scores.get('technical_seo', '—')}/100 |
| AI Visibility | {scores.get('ai_visibility', '—')}/100 |
| Social Presence | {scores.get('social_presence', '—')}/100 |
| Backlink Strength | {scores.get('backlink_strength', '—')}/100 |

## Services

{services_str}

## Key Competitors
{comp_str}

## Active Channels

- [ ] Google Business Profile
- [ ] Facebook Page
- [ ] Instagram
- [ ] Blog / Content
- [ ] Email Marketing
- [ ] Paid Ads

## Quick Links

- Website: {url}
- GBP: [To be added]
- Facebook: [To be added]
- GSC: [To be added]
- GA4: [To be added]

## Notes

This program.md was auto-generated from the onboarding research bundle.
Review and customize all sections before client-facing use.

---

*Managed by Antigravity Digital*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return f"Generated {key}/program.md"


def _write_integration_log(key: str, name: str, results: dict) -> str:
    """Write a timestamped integration log."""
    output_dir = ONBOARDING_DIR / key
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "integration_log.txt"

    lines = [
        f"Integration Log — {name} ({key})",
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
        f"",
    ]
    for step, result in results.items():
        lines.append(f"[{step}] {result}")

    log_text = "\n".join(lines)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(log_text)

    return str(log_path)


# ── CLI ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Client Onboarding Orchestrator — Antigravity Digital",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python onboard_client.py --generate-report --data research_bundle.json
              python onboard_client.py --integrate --data research_bundle.json
              python onboard_client.py --full --data research_bundle.json
              python onboard_client.py --sample --name "ACME Corp" --url "https://acme.com" --city "McAllen" --vertical "plumbing"
        """),
    )

    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate HTML report from research JSON",
    )
    parser.add_argument(
        "--integrate",
        action="store_true",
        help="Update all config files from research JSON",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate report AND integrate (both steps)",
    )
    parser.add_argument(
        "--data",
        type=str,
        help="Path to research_bundle.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for HTML report (optional)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Generate a sample research bundle for testing",
    )
    parser.add_argument("--name", type=str, help="Business name (for --sample)")
    parser.add_argument("--url", type=str, help="Website URL (for --sample)")
    parser.add_argument("--city", type=str, help="City (for --sample)")
    parser.add_argument("--vertical", type=str, help="Vertical/category (for --sample)")

    args = parser.parse_args()

    if args.sample:
        _generate_sample(args)
        return

    if not args.data:
        print("ERROR: --data <path> is required (or use --sample to generate test data)")
        sys.exit(1)

    if not os.path.exists(args.data):
        print(f"ERROR: File not found: {args.data}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  Antigravity Digital — Onboarding Orchestrator")
    print("=" * 60)
    print()

    if args.generate_report or args.full:
        print("[Phase 3] Generating onboarding report...")
        report_path = generate_report(args.data, args.output)
        print(f"  Done: {report_path}")
        print()

    if args.integrate or args.full:
        print("[Phase 5] Integrating client into system...")
        results = integrate_client(args.data)
        for step, result in results.items():
            print(f"  {step}: {result}")
        print()

    print("=" * 60)
    print("  Onboarding complete.")
    print("=" * 60)
    print()


def _generate_sample(args):
    """Generate a sample research bundle for testing the report generator."""
    name = args.name or "ACME Home Services"
    url = args.url or "https://acmehomeservices.com"
    city = args.city or "McAllen"
    vertical = args.vertical or "home-services"

    sample = {
        "client": {
            "name": name,
            "url": url,
            "city": city,
            "vertical": vertical,
            "onboarded_at": datetime.now(timezone.utc).isoformat(),
        },
        "executive_summary": f"{name} is a {vertical} provider serving {city} and surrounding areas. Their website shows solid foundational content but has significant technical SEO gaps including missing schema markup, slow page speeds, and no AI crawler configuration. Their Google Business Profile has a strong review base but incomplete attributes and minimal photo content. With targeted technical fixes, GBP optimization, and a structured content strategy, we project a 40-60% increase in local organic visibility within 90 days.",
        "scores": {
            "overall_readiness": 54,
            "website_quality": 62,
            "gbp_completeness": 48,
            "technical_seo": 41,
            "ai_visibility": 22,
            "social_presence": 35,
            "backlink_strength": 45,
            "keyword_coverage": 58,
        },
        "website_scan": {
            "business_summary": f"A locally owned and operated {vertical} business serving residential and commercial clients across {city} and the Rio Grande Valley since 2012. Their website emphasizes reliable service, licensed technicians, and competitive pricing.",
            "services": [
                f"Residential {vertical}",
                f"Commercial {vertical}",
                "Emergency repairs",
                "Maintenance plans",
                "Free estimates",
            ],
            "brand_voice": "Professional, trustworthy, community-focused. Uses straightforward language with emphasis on reliability and local expertise.",
            "trust_signals": [
                "Licensed & Insured (displayed in footer)",
                "12+ years in business",
                "BBB Accredited (A- rating)",
                "Customer testimonials on homepage (8 reviews shown)",
                "Serving RGV since 2012",
            ],
            "contact_info": {
                "Phone": "(956) 555-0123",
                "Email": "info@acmehomeservices.com",
                "Address": "123 Main St, McAllen, TX 78501",
                "Contact Form": "Yes — /contact page with form",
            },
            "content_audit": {
                "Blog": "Yes — 12 posts, last updated 3 months ago",
                "Service Pages": "5 pages, well-structured",
                "About Page": "Present, good story but no schema",
                "FAQ": "Not found — opportunity",
                "Total Pages Indexed": "~35 pages",
            },
        },
        "gbp_audit": {
            "identity": {
                "Place ID": "ChIJSamplePlaceID12345",
                "CID (hex)": "0xSampleCIDHex",
                "CID (decimal)": "12345678901234567890",
                "Lat/Lng": "26.2034, -98.2300",
                "Primary Category": vertical.replace("-", " ").title(),
                "Secondary Categories": "None set",
            },
            "review_audit": {
                "Total Reviews": "47",
                "Average Rating": "4.6 / 5.0",
                "Response Rate": "~40% (needs improvement)",
                "Last Review": "2 weeks ago",
                "Review Velocity": "~3/month",
            },
            "completeness_score": "48/100 — Missing: secondary categories, attributes, Q&A, posts, description under 750 chars",
            "nap_consistency": "Address matches website exactly. Phone and business name are consistent.",
            "issues_found": [
                "No secondary categories selected — missing keyword-rich categories",
                "Only 12 photos (target: 100+ for 520% more calls)",
                "Business description is only 200 chars (750 available)",
                "No Google Posts in last 90 days",
                "Q&A section is empty — seed with FAQs",
                "Attributes section incomplete — missing service options, payment types, accessibility",
            ],
        },
        "competitor_intel": {
            "competitors": [
                {
                    "name": "RGV Pro Services",
                    "rating": "4.8",
                    "reviews": "156",
                    "strengths": "Dominant review count, active GBP posting weekly, strong backlink profile from local news sites",
                    "weaknesses": "Website is slow (3.8s LCP), no blog content, poor mobile experience",
                },
                {
                    "name": "McAllen Premier Home",
                    "rating": "4.5",
                    "reviews": "89",
                    "strengths": "Excellent website UX, strong blog with 40+ posts ranking for long-tail keywords",
                    "weaknesses": "Lower review count, no review responses, no social media presence",
                },
                {
                    "name": "Valley Wide Services",
                    "rating": "4.3",
                    "reviews": "210",
                    "strengths": "Highest review volume, multiple locations (3 GBP listings), Google Ads running",
                    "weaknesses": "Generic brand, no unique value proposition, website is templated Wix site",
                },
                {
                    "name": "Top Choice Home Repair",
                    "rating": "4.7",
                    "reviews": "62",
                    "strengths": "Strong video content (YouTube channel with 2K subscribers), excellent GBP photos (80+)",
                    "weaknesses": "Website not HTTPS (critical), no schema markup, thin service pages",
                },
                {
                    "name": "Ace Maintenance Co",
                    "rating": "4.4",
                    "reviews": "34",
                    "strengths": "Ranking #1 for '{vertical} near me', well-optimized title tags and meta descriptions",
                    "weaknesses": "Lowest review count in top 5, no blog, GBP profile incomplete",
                },
            ],
            "attack_vectors": [
                "Outrank Ace Maintenance for '{vertical} near me' — their website is weak but their on-page SEO is good. We need better content + more backlinks.",
                "Close the review gap with RGV Pro Services — they have 3x more reviews. Implement review generation system.",
                "Exploit Top Choice's HTTPS vulnerability — Google is favoring HTTPS sites. Their ranking will decline without a fix.",
                "Build content moat — none of the top 5 have a strong content strategy. Own the long-tail with a blog.",
                "Activate GBP fully — all competitors have incomplete GBP profiles. A 100% optimized GBP can leapfrog 2-3 positions.",
            ],
        },
        "technical_seo": {
            "summary": "The website has foundational SEO elements in place but multiple critical gaps. Mobile experience is acceptable but page speed is below Core Web Vitals thresholds. Schema markup is entirely missing — this is the highest-impact quick fix.",
            "findings": [
                {"check": "HTTPS", "status": "pass", "detail": "Valid SSL, no mixed content"},
                {"check": "robots.txt", "status": "pass", "detail": "Present and correctly configured"},
                {"check": "sitemap.xml", "status": "pass", "detail": "Present at /sitemap.xml, 35 URLs indexed"},
                {"check": "Mobile Responsive", "status": "pass", "detail": "Viewport meta present, touch targets adequate"},
                {"check": "Title Tags", "status": "warn", "detail": "Present but generic — no city or service keywords"},
                {"check": "Meta Descriptions", "status": "warn", "detail": "Present on 60% of pages, many are auto-generated snippets"},
                {"check": "Schema Markup", "status": "fail", "detail": "COMPLETELY MISSING — no LocalBusiness, Organization, FAQ, or Article schema found"},
                {"check": "Heading Hierarchy", "status": "warn", "detail": "Multiple H1s on homepage, inconsistent H2/H3 usage"},
                {"check": "Image Alt Text", "status": "fail", "detail": "80% of images missing alt text — accessibility + SEO gap"},
                {"check": "Canonical Tags", "status": "pass", "detail": "Present on all pages, correctly configured"},
                {"check": "404 Page", "status": "warn", "detail": "Exists but generic — no navigation links or search"},
                {"check": "Page Speed (LCP)", "status": "fail", "detail": "Estimated 3.2s — above 2.5s threshold"},
                {"check": "Security Headers", "status": "fail", "detail": "Missing CSP, HSTS, X-Frame-Options, X-Content-Type-Options"},
                {"check": "Open Graph Tags", "status": "warn", "detail": "Present on homepage only — missing on service and blog pages"},
            ],
        },
        "ai_visibility": {
            "presence": {
                "Google AI Overviews": "Not detected for any tracked queries",
                "ChatGPT / Browse": "Not cited — business not recognized as entity",
                "Perplexity": "Not mentioned in local recommendations",
                "Claude": "Not in training data or browse results",
            },
            "entity_strength": "Weak — no Knowledge Graph entry, no Wikipedia/Wikidata presence, no schema markup to establish entity",
            "recommendations": [
                "Implement LocalBusiness + Organization JSON-LD schema immediately — this is how AI engines identify businesses",
                "Add FAQ schema to service pages — structured Q&A is heavily favored by AI overviews",
                "Configure robots.txt to allow GPTBot, Claude-Extended, PerplexityBot (currently blocking all AI crawlers by omission)",
                "Build entity-rich About page with clear NAP, founding date, service area, and industry affiliations",
                "Pursue Wikidata entry and local news citations to strengthen Knowledge Graph presence",
            ],
        },
        "social_scan": {
            "platforms": {
                "Facebook": "Page exists — 340 likes, posting ~1/month, 4.2 rating from 18 reviews",
                "Instagram": "Not found",
                "LinkedIn": "Personal profiles only — no business page",
                "TikTok": "Not present",
                "YouTube": "Not present",
                "Twitter/X": "Not present",
            },
            "content_quality": "Facebook page has potential but is underutilized. Posts are irregular and mostly links to the website. No video content. Cover photo and profile image need updating. Call-to-action button not configured.",
            "recommendations": [
                "Update Facebook page assets (cover photo, profile image, CTA button)",
                "Increase posting frequency to 3x/week minimum",
                "Launch Instagram account — this vertical performs well on Instagram",
                "Respond to all unreviewed Facebook recommendations",
                "Consider Nextdoor presence for hyper-local visibility",
            ],
        },
        "backlink_profile": {
            "domain_authority": "Estimated DA: 18-22 (below average for local {vertical} in McAllen — top competitors range 25-40)",
            "top_referring_domains": [
                "yelp.com (business listing)",
                "bbb.org (accreditation listing)",
                "localchamber.com (chamber of commerce)",
                "angi.com (1 review, no-follow)",
                "nextdoor.com (business page)",
            ],
            "toxic_flags": [
                "3 low-quality directory links from sites with DA <5",
                "No evidence of link network or spam (clean profile overall)",
            ],
            "gap_analysis": "Main gap is quantity, not quality. Competitors average 40-60 referring domains vs. our ~15. Priority: local sponsorships, industry directories, and guest posting on RGV news/lifestyle sites.",
        },
        "keyword_map": {
            "top_keywords": [
                {"keyword": f"{vertical} {city}", "volume": "1,200/mo", "difficulty": "Medium"},
                {"keyword": f"best {vertical} in {city}", "volume": "480/mo", "difficulty": "Low"},
                {"keyword": f"{vertical} near me", "volume": "2,400/mo", "difficulty": "High"},
                {"keyword": f"{vertical} company {city} tx", "volume": "320/mo", "difficulty": "Low"},
                {"keyword": f"{vertical} repair {city}", "volume": "880/mo", "difficulty": "Medium"},
                {"keyword": f"affordable {vertical} {city}", "volume": "260/mo", "difficulty": "Low"},
                {"keyword": f"{vertical} free estimate {city}", "volume": "180/mo", "difficulty": "Very Low"},
                {"keyword": f"emergency {vertical} {city}", "volume": "590/mo", "difficulty": "Medium"},
                {"keyword": f"{vertical} cost {city} tx", "volume": "390/mo", "difficulty": "Low"},
                {"keyword": f"licensed {vertical} {city}", "volume": "150/mo", "difficulty": "Very Low"},
            ],
            "clusters": {
                "Service Intent": ["repair", "installation", "replacement", "maintenance", "emergency"],
                "Location Intent": [f"{city}", f"{city} tx", "near me", "rio grande valley", "hidalgo county"],
                "Commercial Intent": ["cost", "price", "free estimate", "affordable", "quote"],
                "Trust Intent": ["licensed", "insured", "best", "top rated", "reviews"],
            },
            "opportunities": [
                f"'Best {vertical} in {city}' — position 11-15, 480/mo volume, low difficulty",
                f"'Licensed {vertical} {city}' — not ranking, 150/mo, very low difficulty",
                f"'{vertical} free estimate {city}' — position 20+, 180/mo, very low difficulty",
                "FAQ long-tail keywords — zero content targeting question-based queries",
                "Neighborhood-specific keywords (e.g., 'Sharyland', 'Mission') — no content targeting these",
            ],
        },
        "prioritized_actions": [
            {"rank": 1, "action": "Implement LocalBusiness + Organization JSON-LD schema on all pages", "impact": "high", "effort": "2-3 hours", "domain": "Technical SEO"},
            {"rank": 2, "action": "Optimize GBP — add secondary categories, complete all attributes, upload 50+ photos", "impact": "high", "effort": "3-4 hours", "domain": "GBP"},
            {"rank": 3, "action": "Fix page speed — optimize images, enable caching, add resource hints", "impact": "high", "effort": "4-6 hours", "domain": "Technical SEO"},
            {"rank": 4, "action": "Add security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)", "impact": "medium", "effort": "1 hour", "domain": "Technical SEO"},
            {"rank": 5, "action": "Build 10-page content hub targeting keyword clusters (service + location + trust)", "impact": "high", "effort": "2-3 weeks", "domain": "Content"},
            {"rank": 6, "action": "Implement review generation system — target 50+ new reviews in 90 days", "impact": "high", "effort": "ongoing", "domain": "GBP"},
            {"rank": 7, "action": "Create and verify Instagram + Nextdoor business profiles", "impact": "medium", "effort": "2 hours", "domain": "Social"},
            {"rank": 8, "action": "Add FAQ schema to service pages and create dedicated FAQ page", "impact": "medium", "effort": "3-4 hours", "domain": "Content"},
            {"rank": 9, "action": "Fix image alt text across the site (80% missing)", "impact": "medium", "effort": "2-3 hours", "domain": "Technical SEO"},
            {"rank": 10, "action": "Build 5 local backlinks — chamber sponsorships, RGV news mentions, industry directories", "impact": "medium", "effort": "1-2 weeks", "domain": "Backlinks"},
            {"rank": 11, "action": "Configure AI crawler access in robots.txt and build entity-rich About page", "impact": "high", "effort": "1-2 hours", "domain": "AI Visibility"},
            {"rank": 12, "action": "Set up Google Search Console and submit sitemap (if not already done)", "impact": "high", "effort": "30 min", "domain": "Technical SEO"},
        ],
        "ninety_day_plan": {
            "month_1": [
                "Week 1: Implement schema markup (JSON-LD), fix security headers, configure AI crawler access",
                "Week 2: GBP overhaul — categories, attributes, description, upload 50+ photos, start posting weekly",
                "Week 3: Page speed optimization — compress images, enable caching, defer non-critical JS",
                "Week 4: Set up GSC + GA4 (if needed), fix image alt text, update title tags and meta descriptions",
            ],
            "month_2": [
                "Begin 10-page content hub — publish 2-3 articles/week targeting keyword clusters",
                "Launch review generation campaign — email/SMS past customers, in-person QR codes",
                "Create Instagram + Nextdoor profiles, begin 3x/week Facebook posting cadence",
                "Build first 5 local backlinks — chamber, sponsorships, directories",
                "Add FAQ schema to all service pages",
            ],
            "month_3": [
                "Content hub: 8-10 articles live, begin interlinking strategy",
                "Review count target: 30+ new reviews, maintain 100% response rate",
                "Audit keyword rankings — adjust content strategy based on 60-day data",
                "Evaluate AI visibility — recheck presence in AI overviews and ChatGPT",
                "Month 4 planning: identify what's working, double down, kill what's not",
            ],
        },
    }

    client_key = _slugify(name)
    output_dir = ONBOARDING_DIR / client_key
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = output_dir / "research_bundle.json"

    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)

    print(f"  Sample research bundle created: {bundle_path}")
    print()

    # Auto-generate the report from the sample
    print("[Phase 3] Generating onboarding report from sample...")
    report_path = generate_report(str(bundle_path), args.output)
    print(f"  Done: {report_path}")
    print()
    print("  Open the report to preview the onboarding system output.")
    print(f"  file:///{report_path.replace(chr(92), '/')}")


if __name__ == "__main__":
    main()
