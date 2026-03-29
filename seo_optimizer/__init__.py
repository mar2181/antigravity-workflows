"""
SEO Ranking Optimizer — Automated nightly/midday Google Business Profile optimization.

Applies Karpathy's autoresearch pattern (score → improve → keep if better) to local SEO.
For each client, identifies weak keywords, generates optimization actions, executes them via GBP,
measures rank deltas, and reports winning patterns.

Master scripts:
  - nightly_seo_optimizer.py — orchestrator (runs all 5 steps)
  - seo_ranking_analyzer.py — identify weak keywords (opportunity scoring)
  - seo_action_generator.py — generate SEO actions (Claude API)
  - seo_action_executor.py — apply actions via GBP (Playwright)
  - seo_delta_tracker.py — measure rank improvements
  - seo_report_generator.py — generate HTML + Telegram reports

State file: seo_optimizer_state.json (persistent action log, rank history, winning patterns)
Reports: seo_optimizer_reports/YYYY-MM-DD.html + Telegram
"""
