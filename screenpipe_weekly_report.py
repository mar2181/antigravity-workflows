#!/usr/bin/env python3
"""
screenpipe_weekly_report.py — Aggregate 7 days of Screenpipe daily reports into trends.

Reads existing daily reports from screenpipe_reports/YYYY-MM-DD/ and computes:
- Client attention trends (which clients got more/less focus)
- Productivity score trends
- AI tool adoption changes
- Top recurring topics across the week
- Audio insights summary (if audio-miner reports exist)

Usage:
  python screenpipe_weekly_report.py                # last 7 days
  python screenpipe_weekly_report.py --days 14      # last 14 days
  python screenpipe_weekly_report.py --telegram     # send summary to Telegram
"""

import sys
import re
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXECUTION_DIR = Path(__file__).parent
REPORTS_DIR = EXECUTION_DIR / "screenpipe_reports"

BUSINESS_NAMES = {
    "sugar_shack": "The Sugar Shack",
    "island_arcade": "Island Arcade",
    "island_candy": "Island Candy",
    "juan": "Juan Elizondo RE/MAX",
    "spi_fun_rentals": "SPI Fun Rentals",
    "custom_designs_tx": "Custom Designs TX",
    "optimum_clinic": "Optimum Clinic",
    "optimum_foundation": "Optimum Foundation",
}


def _notify_mario(text: str) -> bool:
    try:
        from screenpipe_verifier import notify_mario
        return notify_mario(text)
    except ImportError:
        return False


def _parse_time_breakdown(path: Path) -> dict:
    """Parse a time-breakdown.md and return {app: minutes, total: N, productivity: N}."""
    data = {"apps": {}, "categories": {}, "total": 0, "productivity": 0}
    if not path.exists():
        return data
    text = path.read_text(encoding="utf-8")

    # Parse "- **AppName**: NN min (XX%)"
    for m in re.finditer(r"\*\*(.+?)\*\*:\s+(\d+)\s+min\s+\(([0-9.]+)%\)", text):
        name, mins, pct = m.group(1), int(m.group(2)), float(m.group(3))
        data["apps"][name] = mins

    # Parse total tracked time
    total_match = re.search(r"Total tracked time:\*\*\s+(\d+)\s+minutes", text)
    if total_match:
        data["total"] = int(total_match.group(1))

    # Parse productivity score
    prod_match = re.search(r"\*\*(\d+)%\*\*", text)
    if prod_match:
        data["productivity"] = int(prod_match.group(1))

    # Parse categories
    cat_section = False
    for line in text.split("\n"):
        if "By Category" in line:
            cat_section = True
            continue
        if cat_section and line.startswith("- **"):
            m = re.match(r"- \*\*(\w+)\*\*:\s+(\d+)\s+min", line)
            if m:
                data["categories"][m.group(1)] = int(m.group(2))
        if cat_section and line.startswith("##") and "Category" not in line:
            cat_section = False

    return data


def _parse_idea_scout(path: Path) -> dict:
    """Parse idea-scout.md for client mention counts."""
    data = {"client_mentions": {}, "total_snippets": 0}
    if not path.exists():
        return data
    text = path.read_text(encoding="utf-8")

    for m in re.finditer(r"### (.+?) \((\d+) mentions\)", text):
        name, count = m.group(1), int(m.group(2))
        data["client_mentions"][name] = count
        data["total_snippets"] += count

    return data


def _parse_audio_miner(path: Path) -> dict:
    """Parse audio-miner.md for action items and client mentions."""
    data = {"action_items": 0, "client_mentions": 0, "strategy_notes": 0, "duration_min": 0}
    if not path.exists():
        return data
    text = path.read_text(encoding="utf-8")

    for m in re.finditer(r"\*\*Action items found:\*\*\s+(\d+)", text):
        data["action_items"] = int(m.group(1))
    for m in re.finditer(r"\*\*Client mentions:\*\*\s+(\d+)", text):
        data["client_mentions"] = int(m.group(1))
    for m in re.finditer(r"\*\*Strategy notes:\*\*\s+(\d+)", text):
        data["strategy_notes"] = int(m.group(1))
    for m in re.finditer(r"\*\*Duration:\*\*\s+(\d+)\s+min", text):
        data["duration_min"] = int(m.group(1))

    return data


def run_weekly_report(days_back: int = 7, send_telegram: bool = False) -> str:
    """Aggregate daily reports into a weekly trend report."""

    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days_back)]
    dates.reverse()  # oldest first

    print(f"Weekly Report — aggregating {days_back} days ({dates[0]} to {dates[-1]})")

    # Collect daily data
    daily_time = {}      # {date: {apps, categories, total, productivity}}
    daily_scout = {}     # {date: {client_mentions, total_snippets}}
    daily_audio = {}     # {date: {action_items, client_mentions, ...}}
    days_with_data = []

    for date_str in dates:
        day_dir = REPORTS_DIR / date_str

        tb = _parse_time_breakdown(day_dir / "time-breakdown.md")
        sc = _parse_idea_scout(day_dir / "idea-scout.md")
        au = _parse_audio_miner(day_dir / "audio-miner.md")

        if tb["total"] > 0 or sc["total_snippets"] > 0:
            days_with_data.append(date_str)

        daily_time[date_str] = tb
        daily_scout[date_str] = sc
        daily_audio[date_str] = au

    print(f"  Days with data: {len(days_with_data)} / {days_back}")

    if not days_with_data:
        msg = "No daily reports found for the requested period. Run `python screenpipe_pipe_runner.py --daily` to generate daily reports first."
        print(f"  {msg}")
        return msg

    # ─── Aggregate ──────────────────────────────────────────────────────
    # Total time per app across the week
    app_totals = Counter()
    category_totals = Counter()
    productivity_scores = []
    total_tracked = 0

    for date_str in days_with_data:
        tb = daily_time[date_str]
        for app, mins in tb["apps"].items():
            app_totals[app] += mins
        for cat, mins in tb["categories"].items():
            category_totals[cat] += mins
        if tb["productivity"] > 0:
            productivity_scores.append(tb["productivity"])
        total_tracked += tb["total"]

    # Client attention across the week
    client_attention = Counter()
    for date_str in days_with_data:
        for name, count in daily_scout[date_str]["client_mentions"].items():
            client_attention[name] += count

    # Audio totals
    total_action_items = sum(daily_audio[d]["action_items"] for d in dates)
    total_strategy_notes = sum(daily_audio[d]["strategy_notes"] for d in dates)
    total_audio_min = sum(daily_audio[d]["duration_min"] for d in dates)

    # ─── Generate Report ────────────────────────────────────────────────
    lines = [
        "# Weekly Screenpipe Report",
        f"**Period:** {dates[0]} to {dates[-1]} ({days_back} days, {len(days_with_data)} with data)",
        f"**Total tracked time:** {total_tracked} min ({total_tracked / 60:.1f} hours)",
        "",
    ]

    # Productivity trend
    if productivity_scores:
        avg_prod = sum(productivity_scores) / len(productivity_scores)
        lines += [
            "## Productivity Trend",
            f"- **Average productivity score:** {avg_prod:.0f}%",
            f"- **Range:** {min(productivity_scores)}% — {max(productivity_scores)}%",
            "",
            "| Date | Score |",
            "|---|---|",
        ]
        for date_str in days_with_data:
            score = daily_time[date_str]["productivity"]
            if score > 0:
                bar = "#" * (score // 5)
                lines.append(f"| {date_str} | {score}% {bar} |")
        lines.append("")

    # Top apps
    if app_totals:
        lines += ["## Top Apps (Week Total)", ""]
        for app, mins in app_totals.most_common(10):
            pct = (mins / total_tracked * 100) if total_tracked else 0
            bar = "#" * int(pct / 3)
            lines.append(f"- **{app}**: {mins} min ({pct:.0f}%) {bar}")
        lines.append("")

    # Category breakdown
    if category_totals:
        lines += ["## Time by Category", ""]
        for cat, mins in category_totals.most_common():
            pct = (mins / total_tracked * 100) if total_tracked else 0
            lines.append(f"- **{cat}**: {mins} min ({pct:.0f}%)")
        lines.append("")

    # Client attention distribution
    if client_attention:
        lines += ["## Client Attention Distribution", ""]
        total_mentions = sum(client_attention.values())
        for name, count in client_attention.most_common():
            pct = (count / total_mentions * 100) if total_mentions else 0
            bar = "#" * max(1, int(pct / 3))
            lines.append(f"- **{name}**: {count} mentions ({pct:.0f}%) {bar}")
        lines.append("")

    # Daily summary table
    lines += [
        "## Daily Summary",
        "",
        "| Date | Tracked (min) | Productivity | Client Mentions | Audio (min) |",
        "|---|---|---|---|---|",
    ]
    for date_str in dates:
        tb = daily_time[date_str]
        sc = daily_scout[date_str]
        au = daily_audio[date_str]
        tracked = tb["total"] if tb["total"] > 0 else "-"
        prod = f"{tb['productivity']}%" if tb["productivity"] > 0 else "-"
        mentions = sc["total_snippets"] if sc["total_snippets"] > 0 else "-"
        audio = au["duration_min"] if au["duration_min"] > 0 else "-"
        lines.append(f"| {date_str} | {tracked} | {prod} | {mentions} | {audio} |")
    lines.append("")

    # Audio intelligence summary
    if total_audio_min > 0:
        lines += [
            "## Audio Intelligence Summary",
            f"- **Total transcribed audio:** {total_audio_min} min",
            f"- **Action items found:** {total_action_items}",
            f"- **Strategy notes captured:** {total_strategy_notes}",
            "",
        ]

    # Gaps / recommendations
    missing_days = [d for d in dates if d not in days_with_data]
    if missing_days:
        lines += [
            "## Data Gaps",
            f"- **Missing reports for:** {', '.join(missing_days)}",
            "- Run `python screenpipe_pipe_runner.py --daily` to generate daily reports",
            "",
        ]

    report = "\n".join(lines)

    # Save
    week_label = f"{dates[0]}_to_{dates[-1]}"
    report_path = REPORTS_DIR / f"weekly_{week_label}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n  Saved: {report_path}")

    # HTML version
    html_lines = []
    for line in lines:
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("| "):
            html_lines.append(line)  # handled below
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.startswith("**"):
            html_lines.append(f"<p>{line}</p>")
        elif line:
            html_lines.append(f"<p>{line}</p>")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Weekly Report — {week_label}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #0d1117; color: #c9d1d9; }}
h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
h2 {{ color: #79c0ff; margin-top: 30px; }}
li {{ margin-bottom: 6px; line-height: 1.5; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ border: 1px solid #30363d; padding: 8px 12px; text-align: left; }}
th {{ background: #161b22; color: #58a6ff; }}
strong {{ color: #e6edf3; }}
</style></head><body>
{"".join(html_lines)}
</body></html>"""
    html_path = REPORTS_DIR / f"weekly_{week_label}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  Saved: {html_path}")

    if send_telegram:
        # Send compact summary
        summary = "\n".join(l for l in lines if l.startswith("- **") or l.startswith("# "))[:2000]
        _notify_mario(f"Weekly Screenpipe Report\n\n{summary}")
        print("  Sent to Telegram")

    return report


def main():
    parser = argparse.ArgumentParser(description="Screenpipe Weekly Report — aggregate daily data into trends")
    parser.add_argument("--days", type=int, default=7, help="Days to aggregate (default: 7)")
    parser.add_argument("--telegram", action="store_true", help="Send summary to Telegram")
    args = parser.parse_args()

    run_weekly_report(days_back=args.days, send_telegram=args.telegram)


if __name__ == "__main__":
    main()
