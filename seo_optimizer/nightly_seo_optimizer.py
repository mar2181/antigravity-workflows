#!/usr/bin/env python3
"""
nightly_seo_optimizer.py — Master orchestrator for the entire SEO ranking optimizer.

Runs the complete autoresearch loop in sequence:
  1. seo_ranking_analyzer.py        (2 min) — identify weak keywords
  2. seo_action_generator.py         (3 min) — generate SEO actions (Claude API)
  3. seo_action_executor.py          (10 min) — apply actions via GBP (Playwright)
  [PAUSE 6-12 hours for rank changes to propagate]
  4. seo_delta_tracker.py            (5 min) — measure rank improvements
  5. seo_report_generator.py         (1 min) — generate reports + Telegram

Two scheduling options:
  A) Single task with sleep: Run all 5 steps, pause 6-12 hours internally
  B) Two separate tasks: First 3 steps at 12:00 AM, last 2 steps at 6:00+ AM

Recommended: Windows Task Scheduler (option B) — more reliable than sleep.

Usage:
  # Full nightly run (all steps)
  python seo_optimizer/nightly_seo_optimizer.py

  # Steps 1-3 only (action phase)
  python seo_optimizer/nightly_seo_optimizer.py --phase morning

  # Steps 4-5 only (measurement phase)
  python seo_optimizer/nightly_seo_optimizer.py --phase evening

  # Dry run (preview only)
  python seo_optimizer/nightly_seo_optimizer.py --dry-run

  # Single client
  python seo_optimizer/nightly_seo_optimizer.py --client sugar_shack

State file: seo_optimizer_state.json
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.parent
OPTIMIZER_DIR = SCRIPT_DIR / "seo_optimizer"

STEPS = {
    "analyze": (OPTIMIZER_DIR / "seo_ranking_analyzer.py", "📊 Analyzing keywords..."),
    "generate": (OPTIMIZER_DIR / "seo_action_generator.py", "🤖 Generating actions..."),
    "execute": (OPTIMIZER_DIR / "seo_action_executor.py", "🚀 Executing actions..."),
    "track": (OPTIMIZER_DIR / "seo_delta_tracker.py", "📈 Tracking deltas..."),
    "report": (OPTIMIZER_DIR / "seo_report_generator.py", "📝 Generating reports..."),
}

def run_step(step_name, step_path, args):
    """Run a single step script."""
    print(f"\n{'='*60}")
    print(STEPS[step_name][1])
    print(f"{'='*60}\n")

    cmd = [sys.executable, str(step_path)]

    # Add arguments
    if args.client:
        cmd.extend(["--client", args.client])
    if args.dry_run:
        cmd.append("--dry-run")

    try:
        result = subprocess.run(cmd, timeout=600)  # 10 min timeout per step
        if result.returncode != 0:
            print(f"\n⚠️  Step {step_name} exited with code {result.returncode}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print(f"\n❌ Step {step_name} timed out (>10 min)")
        return False
    except Exception as e:
        print(f"\n❌ Step {step_name} failed: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Master SEO optimizer orchestrator")
    parser.add_argument(
        "--phase",
        choices=["full", "morning", "evening"],
        default="full",
        help="Which steps to run: full (all), morning (1-3), evening (4-5)",
    )
    parser.add_argument("--client", help="Single client to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no actual changes")
    parser.add_argument("--sleep-hours", type=int, default=6, help="Hours to sleep between morning and evening phases")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           SEO RANKING OPTIMIZER — MASTER ORCHESTRATOR        ║
║                                                              ║
║  Autoresearch Pattern Applied to Local SEO Ranking          ║
║  (Score → Improve → Keep if Better)                        ║
╚══════════════════════════════════════════════════════════════╝

Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Phase: {args.phase.upper()}
Clients: {args.client or 'ALL'}
""")

    if args.dry_run:
        print("⚠️  DRY RUN MODE — No actual posts or changes will be made\n")

    # Phase: Morning (Steps 1-3)
    if args.phase in ["full", "morning"]:
        print("🌅 MORNING PHASE — Analyze, Generate, Execute\n")

        steps_to_run = ["analyze", "generate", "execute"]

        for step_name in steps_to_run:
            if not run_step(step_name, STEPS[step_name][0], args):
                print(f"\n❌ Morning phase failed at {step_name}")
                return

        print(f"\n✅ Morning phase complete!")

        if args.phase == "full":
            print(f"\n⏸️  Sleeping {args.sleep_hours} hours for rank changes to propagate...")
            print(f"   (Will resume evening phase at ~{datetime.now().hour + args.sleep_hours:02d}:00)\n")
            time.sleep(args.sleep_hours * 3600)

    # Phase: Evening (Steps 4-5)
    if args.phase in ["full", "evening"]:
        print("🌙 EVENING PHASE — Track, Report\n")

        steps_to_run = ["track", "report"]

        for step_name in steps_to_run:
            if not run_step(step_name, STEPS[step_name][0], args):
                print(f"\n❌ Evening phase failed at {step_name}")
                return

        print(f"\n✅ Evening phase complete!")

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    ✅ ALL PHASES COMPLETE                    ║
╚══════════════════════════════════════════════════════════════╝

Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Next steps:
  • Review HTML report in seo_optimizer_reports/
  • Check Telegram for summary
  • Verify GBP posts on Google Business Profile

Re-run this script with --phase morning at 12:00 AM,
or use Windows Task Scheduler for automated scheduling.

Questions? Check the plan:
  C:\\Users\\mario\\.claude\\plans\\buzzing-wishing-boot.md
""")

if __name__ == "__main__":
    main()
