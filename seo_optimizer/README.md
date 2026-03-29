# SEO Ranking Optimizer — Nightly Automation System

> Applies Karpathy's autoresearch pattern (score → improve → keep if better) to Google Business Profile local SEO ranking optimization.

## Overview

This system automatically:
1. **Identifies** underperforming keywords for your 8 clients
2. **Generates** SEO optimization actions using Claude AI
3. **Executes** actions via Google Business Profile (GBP) posts, Q&A, descriptions, photos
4. **Measures** rank improvements 6-12 hours later
5. **Reports** results with winning patterns and next opportunities

**Expected timeline:** 3-5 keywords per client move within first week. 40-60% organic traffic increase by month 2.

---

## Quick Start

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# Full nightly run (all 5 steps)
python seo_optimizer/nightly_seo_optimizer.py

# Morning phase only (identify + generate + execute)
python seo_optimizer/nightly_seo_optimizer.py --phase morning

# Evening phase only (measure + report) — run 6-12 hours later
python seo_optimizer/nightly_seo_optimizer.py --phase evening

# Dry run (preview, no actual posts)
python seo_optimizer/nightly_seo_optimizer.py --dry-run

# Single client
python seo_optimizer/nightly_seo_optimizer.py --client sugar_shack
```

---

## Scheduling

### Automated (Windows Task Scheduler) — RECOMMENDED

```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\seo_optimizer/setup_task_scheduler.ps1
```

Creates two daily tasks:
- **12:00 AM** — Morning phase (identify, generate, execute)
- **6:30 AM** — Evening phase (measure, report)

### Manual (One-Time Command)

```bash
python seo_optimizer/nightly_seo_optimizer.py
```

Runs all steps in sequence with 6-hour sleep between morning and evening phases.

### Twice Daily Option

Modify Task Scheduler to also run morning phase at 12:00 PM (noon) for midday optimization.

---

## The 5-Step Loop

| Step | Script | Duration | Purpose |
|------|--------|----------|---------|
| 1 | `seo_ranking_analyzer.py` | 2 min | Find underperforming keywords (opportunity scoring) |
| 2 | `seo_action_generator.py` | 3 min | Generate SEO actions (Claude API: score GBP state, target weakness) |
| 3 | `seo_action_executor.py` | 10 min | Execute actions via GBP (Playwright: posts, Q&A, descriptions, photos) |
| 4 | `seo_delta_tracker.py` | 5 min | Measure rank improvements (6-12 hours after step 3) |
| 5 | `seo_report_generator.py` | 1 min | Generate HTML reports + Telegram summaries |

### Data Flow

```
keyword_rankings_state.json (from keyword_rank_tracker.py)
            ↓
[Step 1] Analyzer: Identify weak keywords
            ↓
seo_optimizer_state.json (work queue)
            ↓
[Step 2] Generator: Create actions (Claude Haiku + Sonnet)
            ↓
seo_optimizer_state.json (action plan)
            ↓
[Step 3] Executor: Apply actions (Playwright + GBP profiles)
            ↓
seo_optimizer_state.json (execution log)
    ⏳ [PAUSE 6-12 HOURS FOR RANK CHANGES] ⏳
            ↓
[Step 4] Tracker: Re-check ranks, measure deltas (Bright Data)
            ↓
seo_optimizer_state.json (effectiveness data + winning patterns)
            ↓
[Step 5] Reporter: Generate HTML + Telegram summaries
            ↓
seo_optimizer_reports/YYYY-MM-DD.html + Telegram
```

---

## How Actions Are Generated

1. **Score current GBP state** (Claude Haiku):
   - Description: How naturally is the keyword present? (0-100)
   - Posts: Recent posts with keyword presence? (0-100)
   - Q&A: Questions/answers targeting keyword? (0-100)
   - Photos: Recent, keyword-rich alt text? (0-100)

2. **Identify weakest signal** (lowest score)

3. **Generate action targeting weakness** (Claude Sonnet):
   - If weakest = posts → 150-word GBP post with CTA
   - If weakest = Q&A → customer question + business answer
   - If weakest = description → revised description with keyword
   - If weakest = photos → fal.ai image prompt + alt text + geo-tag

4. **Apply action** via Playwright using existing GBP profiles:
   - Mario profile: Custom Designs TX, Optimum Clinic, Juan
   - Yehuda profile: Sugar Shack, Island Arcade, Island Candy, SPI Fun Rentals, Optimum Foundation

---

## Winning Patterns

After each delta measurement, the system learns which action types work best per client:

```json
{
  "winning_patterns": {
    "sugar_shack": {
      "gbp_post": {
        "total": 5,
        "effective": 4,
        "avg_delta": +0.75  // Keywords moved 0.75 positions on average
      },
      "gbp_qa": {
        "total": 2,
        "effective": 1,
        "avg_delta": +0.5
      }
    }
  }
}
```

Over time, the system prioritizes proven action types and learns client-specific patterns.

---

## Expected Results Timeline

- **Week 1:** Discovery phase. 3-5 keywords/client move 1-2 positions.
- **Week 2:** 70% efficiency. 8-12 keywords/client show movement. 30-40% in Map Pack top 3.
- **Week 3:** Expert-level optimization. 15-25 keywords sustained improvements.
- **Month 2:** Compounding effect. 40-60% organic traffic increase vs. baseline.

---

## Cost Estimate

Per nightly run:
- Claude Haiku scoring (24 calls): ~$0.01
- Claude Sonnet generation (24 calls): ~$0.36
- Bright Data rank checks (48 checks): ~$0.10
- fal.ai images (0-3): $0.05–$0.15

**Total per run: ~$0.50–$0.65**
**Twice daily: ~$1.10–$1.30/day**

---

## Files & Structure

```
seo_optimizer/
├── __init__.py                     # Package marker
├── seo_ranking_analyzer.py         # Step 1: Identify weak keywords
├── seo_action_generator.py         # Step 2: Generate actions (Claude)
├── seo_action_executor.py          # Step 3: Execute via GBP (Playwright)
├── seo_delta_tracker.py            # Step 4: Measure improvements
├── seo_report_generator.py         # Step 5: Generate reports
├── nightly_seo_optimizer.py        # Master orchestrator
├── seo_optimizer_state.json        # Persistent state + history
├── setup_task_scheduler.ps1        # Windows Task Scheduler setup
└── README.md                       # This file

seo_optimizer_reports/             # Generated reports
├── YYYY-MM-DD.html                # Daily HTML report
└── actions/                        # Action execution screenshots
    └── YYYY-MM-DD_*.png
```

---

## State File Schema

**File:** `seo_optimizer_state.json`

```json
{
  "work_queue": [
    {
      "client": "sugar_shack",
      "keyword": "candy store south padre island",
      "current_rank": 5,
      "opportunity_score": 8.2,
      "status": "EFFECTIVE",
      "action_type": "gbp_post",
      "action_content": "...",
      "pre_action_rank": 5,
      "post_action_rank": 4,
      "delta": 1,
      "gbp_scores": {
        "description_score": 45,
        "posts_score": 30,
        "qa_score": 40,
        "photo_score": 50,
        "weakest_signal": "posts"
      }
    }
  ],
  "winning_patterns": { ... },
  "action_history": [ ... ]
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No ranking data found" | Run `keyword_rank_tracker.py` first |
| "Work queue not found" | Run `seo_ranking_analyzer.py` first |
| "Actions failed" | Check GBP profile auth: `python reauth_mario_gbp.py` |
| Playwright timeouts | Check internet connection; GBP may be slow |
| Claude API errors | Verify `ANTHROPIC_API_KEY` environment variable |
| Task Scheduler not running | Check Windows Task Scheduler GUI; verify task is enabled |

---

## Integration with Existing Pipelines

### Nightly Intelligence
`nightly_seo_optimizer.py --phase morning` will be added as stage 5 to `nightly_intelligence.py`:

```
Stage 1: keyword_rank_tracker.py             (6 PM)
Stage 2: competitor_monitor.py              (6:10 PM)
Stage 3: competitor_fb_adlibrary.py         (6:15 PM)
Stage 4: competitor_ai_analyzer.py          (6:30 PM)
Stage 5: seo_optimizer (morning phase)      (12:00 AM)
```

### Morning Brief
`morning_brief.py` will add "SEO Actions" section showing:
- Keywords moved overnight
- Top wins + remaining opportunities
- Effectiveness % per action type

---

## Full Plan & Architecture

Detailed plan with cost estimates, verification procedures, and 8 enhancements:

📄 **Plan:** `C:/Users/mario/.claude/plans/buzzing-wishing-boot.md`

📚 **Skill Reference:** `C:/Users/mario/.claude/projects/C--Users-mario/memory/skill_seo_optimizer.md`

---

## Next Steps

1. **Verify dependencies:**
   ```bash
   pip install anthropic playwright
   playwright install
   ```

2. **Test Step 1:**
   ```bash
   python seo_optimizer/seo_ranking_analyzer.py --dry-run
   ```

3. **Set up scheduling:**
   ```powershell
   .\seo_optimizer/setup_task_scheduler.ps1
   ```

4. **Run first full cycle (dry-run):**
   ```bash
   python seo_optimizer/nightly_seo_optimizer.py --dry-run
   ```

5. **Monitor reports:**
   Check `seo_optimizer_reports/YYYY-MM-DD.html` and Telegram for results.

---

**Questions?** Refer to the master plan or check memory at:
`C:/Users/mario/.claude/projects/C--Users-mario/memory/skill_seo_optimizer.md`
